# EOM-02 — File Intake

**Trigger:** *When a file is created (properties only)* on the **Portfolio
document library** — not on an FY folder.

The older folder-scoped trigger is deprecated and does not fire recursively for
subfolders. Binding to the library and filtering by path in the flow means
FY2028 needs a config edit, not a rebuilt flow.

```
Trigger:  Portfolio Documents library
Filter:   path starts with MF_App_Config.EOM_Root_Path
          AND path contains MF_App_Config.CurrentFiscalYear
Else:     exit silently
```

Exists **only** for folder drops. Files uploaded through the app are already
declared and must be ignored.

## Logic

```
if the file sits under mfops_MF_EvidenceRootPath:
        exit — the app wrote it, nothing to classify

else:
    store SharePoint_File_ID — it survives a rename or a move; the URL does not
    portfolio  = segment 1 of the folder path
    fiscalYear = segment 2 of the folder path
    uploader   = file.Author

    // Weak hints only. NEVER auto-applied. No filename convention exists
    // and none is assumed.
    suggestedInstallation = installation of the uploader's facility,
                            resolved through MF Security Mapping on UPN
    suggestedDocumentCode = first Document_Code appearing in the filename,
                            or blank

    create MF Unmatched File with Resolution_Status = 'Needs Classification'
    log MF App Event Log: ClassificationUncertain

// Tier 2 and 3 sit here, both feature-flagged OFF:
//   if MF_App_Config.EnableDocumentContentAI -> inspect workbook/PDF structure
//   if MF_App_Config.EnableAIBuilder         -> AI Builder document processing
// Neither is built in R1 and neither may ever become a dependency.
```

**No content parsing, no AI Builder, no filename logic in MVP.** A human
resolves the queue in the app, which writes a real MF EOM Submission with
`Intake_Method = 'Manual classification'`.

Uploader identity is the strongest available signal, because base DFAC managers
and accountants upload their own documents. It stays a hint, not a decision — an
AFSVC MFM uploading an emailed document would otherwise resolve to the wrong
installation.

## Success criterion
The queue should trend toward empty as adoption rises. A persistently large
queue means people are bypassing the app — a training problem, not an
engineering one.
