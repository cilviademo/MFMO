# EOM-02 — File Intake

**Trigger:** *When a file is created (properties only)* on the **Portfolio
document library** — not on an FY folder.

```
Trigger:  Portfolio Documents library
Filter:   path starts with MF_App_Config.EOM_Root_Path
          AND path contains MF_App_Config.CurrentFiscalYear
Else:     exit silently
```

## Library level, not folder level

A folder-scoped trigger does not fire recursively for subfolders, and Portfolio
FY folders are created every year by people who do not know a flow exists. The
failure is invisible: no error, no run, just files that never arrive.

Binding to the library and filtering by path in the flow means FY2028 needs a
config edit, not a rebuilt flow.

## Exists only for folder drops

**The app is the front door, and folder drops keep working.** This is the
second path, not the fallback for a failure of the first: people will keep
copying files into folders, and a system that loses them is worse than one that
queues them.

Files uploaded through the app are already declared and must be ignored — they
land under `MF_App_Config.EvidenceRootPath`, which is the first thing this flow
checks.

## Logic

```
if the file sits under EvidenceRootPath:
        exit — EOM-05 wrote it, nothing to classify

if a submission already carries this SharePoint_File_ID:
        exit — a re-run over the library after an outage is a no-op

else:
    store SharePoint_File_ID   — it survives a rename or a move; the URL does not
    portfolio  = segment 1 of the folder path
    fiscalYear = segment 2 of the folder path
    uploader   = file.Author

    // Weak hints only. NEVER auto-applied. No filename convention exists and
    // none is assumed.
    suggestedInstallation = installation of the uploader's facility,
                            resolved through MF Security Mapping on UPN
    suggestedDocumentCode = first Document_Code appearing in the filename,
                            or blank

    create MF Unmatched File, Resolution_Status = 'Needs Classification'
    log MF App Event Log: ClassificationUncertain
```

Uploader identity is the strongest available signal, because base DFAC managers
and accountants upload their own documents. It stays a hint, not a decision — an
AFSVC MFM uploading an emailed document would otherwise resolve to the wrong
installation, and the missing counts would go wrong silently.

## Never invent a requirement

There is no branch in this flow that creates an `MF_EOM_Item`, and there must
never be one. A file with no matching expected item stays in the queue until a
human decides what it is — or decides the requirement should exist, which is a
deliberate act on `scrAdminRequirements`.

## The classification ladder

| Tier | Method | Status |
|---|---|---|
| 0 | `Declared at upload` — installation, facility, requirement and period declared in the app | production baseline |
| 1 | `Folder context` — folder path and uploader | **suggestion only, never applied** |
| 2 | `Document content` | `EnableDocumentContentAI`, ships `False`, no code path in R1 |
| 3 | `AI Builder` | `EnableAIBuilder`, ships `False`, no code path in R1 |
| 4 | `Manual` — the queue | `scrUnmatched` |

Tiers 2 and 3 sit behind those flags and are **not built**. Do not build a
classifier the architecture no longer needs, and never let AI Builder become a
dependency whose availability could block the app.

**No content parsing, no AI Builder, no filename logic in MVP.** Filenames are
never authoritative and are never a classification method at any tier.

## Resolving a queued file

`scrUnmatched` writes a real `MF_EOM_Submission` against an **existing**
expected item with `Intake_Method = 'Manual classification'`, sets
`Resolution_Status = 'Classified'` and links `Resolved_Submission_ID`. The
unmatched row is never deleted — a resolved stray keeps the record that it
arrived unclassified.

## Success criterion

The queue trends toward empty as adoption rises. A persistently large queue
means people are bypassing the app: a training problem, not an engineering one.
