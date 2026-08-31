# EOM-05 — App Upload (the front door)

**Trigger:** Power Apps (V2), called by `scrUpload`.
**Returns:** `{ ok, code, message, versionNo, submissionId }`.

New in the reconciled build. V3 had `scrUpload` patch the lists directly and
attach through the Power Apps **Attachments control**; this flow replaces that.

## Why a flow instead of the Attachments control

The Attachments control binds to a Form, targets lists and Dataverse rather
than document libraries, and behaves badly on Teams and mobile. Those are real
limitations and they are a reason not to use that control.

They are **not** a reason to stop people uploading through the app. Reverting
to folder-drop-only would reintroduce the exact classification risk the
declaration removes: a file dropped in a folder has to be inferred; a file
declared at upload does not.

So the app collects the file and the declared metadata and calls this flow;
the flow writes the library and the lists. Both paths stay open; the app is
preferred. See `docs/handoffs/RECONCILIATION.md` §1.

## The declaration is the classification

Installation, facility, requirement and period are declared in the app before
the file is chosen. The submission is written with
`Intake_Method = 'App upload'`, `Classification_Method = 'Declared at upload'`
and `Classification_Confidence = 'Declared'`.

The filename is stored as evidence and read for nothing. **Upload must work
with an arbitrary filename**, and that is an acceptance test — try
`Copy of copy FINAL(2).xlsx`.

## Server-side checks

Each is also checked in the app. The app's version gives a fast, specific
error; this one is the control.

| Check | Failure code |
|---|---|
| `MF_App_Config.ReadOnlyMode` is false | `READ_ONLY` |
| The caller's `MF_Security_Mapping` covers the target facility or installation | `NOT_AUTHORIZED` |
| `eomItemId` resolves to a real `MF_EOM_Item` | `NO_SUCH_ITEM` |
| Size within `MaxUploadSizeMB` | `TOO_LARGE` |

`NOT_AUTHORIZED` is the one that matters: the app only offers facilities the
user is mapped to, but a flow invoked directly would not be so polite.

**`NO_SUCH_ITEM` does not create anything.** No expected item means no
obligation the system knows about; the app tells the user so and offers the
Needs Classification route. Never invent a requirement.

## Version handling

```
current = MF EOM Submission where EOM_Item_ID = X and Is_Current = true
nextVer = coalesce(current.Version_No, 0) + 1

write the file to
  <EvidenceRootPath>/<FY>/<Installation_ID>/<Facility_ID or scope>/<period>/
  <EOM_Item_Key>__v<nextVer>__<original filename>

patch current: Is_Current = false, Superseded_By = newId    (if one exists)
create the new submission: Is_Current = true, QC_Status = 'Pending Review'
patch MF EOM Item: Current_Submission_ID, Received_Flag, Received_DateTime
```

**Never overwrite a file. Never duplicate the checklist row.** v1 keeps its
row, its file and its QC comment; the audit question is "what did they send and
what did the reviewer say", for every attempt.

The path carries the item key and version so a human browsing the library can
orient — but the list row is truth and the path is convenience. The app
re-resolves links from `SharePoint_File_ID`, because files get moved and
renamed and the URL goes stale while the ID does not.

The write lands under `EvidenceRootPath`, which is the first thing EOM-02
checks, so the app's own writes never come back round as unclassified strays.

## Submitting on behalf

When the caller holds `Can_Submit_On_Behalf` and the app's on-behalf toggle is
set, `Submitted_On_Behalf_Of` carries the target `Facility_ID` or
`Installation_ID`. Without it, a document that arrived by email and was
uploaded by an AFSVC MFM misattributes to AFSVC and the missing counts go wrong
silently.

`Uploaded_By` stays the actual uploader. Both facts are recorded.

## Status after upload

The engine runs once, here. A new submission is `Pending Review`, so the item
becomes `RECEIVED_PENDING_QC` / `Status_Code 2` / owner `Reviewer`. If the
requirement carries `QC_Required = false` and `MF_App_Config.RequireQC` is
false, the submission is written `Accepted` and the item goes `ACCEPTED` / `3`.

Nothing here chooses a colour. The flow writes back the four fields one
evaluation returned.

## Audit and telemetry

`MF_EOM_Audit`: `Action = 'Uploaded'`, entity the submission.
`MF_App_Event_Log`: `SubmissionCreated`, plus `VersionSuperseded` when a prior
current version was demoted, both stamped with `App_Version`.
