# EOM-05 — App upload (the front door)

Called by `scrUpload`. The app collects the file and the declared metadata;
this flow writes the library and the lists.

## Why a flow instead of the Attachments control

The Power Apps Attachments control binds to a Form, targets lists and
Dataverse rather than document libraries, and behaves badly on Teams and
mobile. Those are real limitations and they are a reason not to use the
control.

They are **not** a reason to stop people uploading through the app. Reverting
to folder-drop-only would reintroduce the exact classification risk that the
front door removes: a file dropped in a folder has to be inferred, and a file
declared at upload does not. Both paths stay open; the app is preferred.

So the app calls `EOM05_AppUpload.Run(...)` with the bytes and the
declaration, and gets back `{ ok, code, message, versionNumber, submissionId }`.

## The declaration is the classification

`Classification_Method` is `DECLARED` and `Classification_Confidence` is 100,
because the user picked the installation, facility, document type and
reporting period before choosing the file. This is tier 0 — the production
baseline, roughly 95% of volume — and the filename is never read for meaning.
The upload works with an arbitrary filename, and that is an acceptance test.

## Server-side checks

Every one of these is also checked in the app. The app's version gives a fast,
specific error; this one is the control.

| Check | Failure code |
|---|---|
| `MF_App_Config.ReadOnlyMode` is false | `READ_ONLY` |
| The caller's `MF_Security_Mapping` covers the target facility | `NOT_AUTHORIZED` |
| `eomItemId` names a real `MF_EOM_Item` | `NO_SUCH_ITEM` |
| The item's period is not `CLOSED` | `PERIOD_CLOSED` |
| Size within `MaxUploadSizeMB` | `TOO_LARGE` |
| Extension within the requirement's `Accepted_File_Types` | `BAD_FILE_TYPE` |

`NOT_AUTHORIZED` is the one that matters: the app only offers facilities the
user is mapped to, but a flow invoked directly would not be so polite.

## Versioning

```
current = MF_EOM_Submission where EOM_Item_ID = X and Is_Current_Version = true
next    = coalesce(current.Version_Number, 0) + 1

write the file to  <EvidenceLibraryPath>/<Portfolio>/<FY>/<Installation>/<Facility>/<Period>/
                   <EOM_Item_Key>__v<next>__<original filename>
patch current.Is_Current_Version = false      (if a current version exists)
create the new submission row, Is_Current_Version = true
patch MF_EOM_Item.Current_Submission_ID, Current_Version_Number
```

**Never overwrite a file. Never duplicate the checklist row.** The item is
patched, not recreated; v1 keeps its row, its file and its QC history.

The stored path includes the item key and version so a human browsing the
library can orient — but the list row is truth and the path is convenience.
`SharePoint_File_ID` is what the app re-resolves a link from, because files
get moved and renamed and the URL goes stale while the id does not.

## Status after upload

The engine runs once, here, in the order in `docs/status-calculation.md`. A
new submission is `QC_Status = PENDING`, so the item becomes `SUBMITTED` /
Amber with the action owner `Reviewer` — unless the requirement has
`Requires_QC = false`, in which case the submission is written `ACCEPTED` and
the item goes Green immediately.

Nothing here chooses a colour. The flow writes back the four fields the engine
returned and nothing else.
