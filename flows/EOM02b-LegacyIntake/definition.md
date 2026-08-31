# EOM-02b — Legacy Intake (the exception route)

**Trigger:** *When a file is created (properties only)* on each portfolio's
document library — not on an FY folder.

**Was `EOM-02 File Intake`.** Renamed when EOM-02 became the app's submission
path. This is the discovery route for files that arrive without a declaration,
and it is an exception route, not the normal one.

```
Trigger:  the Shared Documents library on ONE portfolio site
Filter:   path starts with the destination's Root_Folder
Else:     exit silently
```

## Schema compatibility — checked before any write

```
expected = the schema version this flow was authored against   (a literal)
deployed = MF_App_Config.SchemaVersion

if expected <> deployed:
        return CONFIGURATION_REQUIRED
        log SCHEMA_MISMATCH with both versions
        stop before any write
```

**Every flow makes this comparison independently.** The app disabling its own
submit button is not a control — a flow can be invoked directly, and a flow run
on a schedule has no app in front of it at all.

A newer flow writing against an older schema patches columns that do not exist
yet. SharePoint does not error on that; it writes nothing. A document then reads
as submitted while nothing was recorded, which is the failure this whole build
exists to prevent.

`docs/SHAREPOINT_SCHEMA_MANIFEST.md` is the contract being checked.

## Four sites means four instances of this flow

The four portfolios are four separate **site collections**. A SharePoint trigger
binds to one site, so this flow is deployed once per portfolio, each bound to
its own `MF_Portfolio{n}_SiteURL` and its own `MF_Document_Destination` row.

One instance covering all four is not an option the connector offers, and a
build that assumed it would have silently discovered files in Portfolio 1 only.

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

Files uploaded through the app are already declared and must be ignored. EOM-02
writes a `MF_EOM_Submission` row carrying the file's `SharePoint_Unique_ID`
before this flow ever sees the file, so **the check is "does a submission
already own this GUID"**, not a path comparison.

That matters under `FIND_OR_ROOT`: a file EOM-02 filed at the root, and a human
later moved into the right month folder, changes path twice and keeps its GUID
throughout. A path-based check would rediscover it as an unmatched stray on the
day somebody tidied up.

## Logic

```
if a submission already carries this SharePoint_Unique_ID:
        exit — EOM-02 wrote it, or a human moved it, or this is a re-run
               over the library after an outage. All three are no-ops.

else:
    store SharePoint_Unique_ID — the GUID survives a rename and a move;
                                 the URL and the path survive neither
    portfolio  = the destination row this instance is bound to
    fiscalYear = matched from the folder path, never parsed positionally
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
