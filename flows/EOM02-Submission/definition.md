# EOM-02 — Submission (the front door)

**Trigger:** Power Apps (V2), called by `scrUpload`.
**Returns:** `{ ok, code, message, versionNo, submissionId, needsFiling }`.

Was `EOM-05 App Upload`. Renamed to match the programme handoff, and rewritten
against the routing finding: **the four portfolios are four separate SharePoint
site collections**, and their folders are found rather than built.

The app supplies logical identifiers. **It never supplies a path.**

```
Submission_Request_ID  a GUID the app minted BEFORE this call
Installation_ID        LACKLAND_AFB
Reporting_Period       2026-08
Requirement_ID         REQ-001
Facility_ID            optional — null for installation and contract scope
File                   content + original filename
On_Behalf_Of           optional
Note                   optional
```

Moving Lackland to another portfolio is then an edit to
`MF_Installation.Portfolio_ID`. It is not a change to the app.

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

## Why a flow instead of the Attachments control

The Attachments control binds to a Form, targets lists and Dataverse rather
than document libraries, and behaves badly on Teams and mobile. Those are real
limitations and they are a reason not to use that control.

They are **not** a reason to stop people uploading through the app. Reverting
to folder-drop-only would reintroduce the exact classification risk the
declaration removes: a file dropped in a folder has to be inferred; a file
declared at upload does not. `EOM-02b Legacy Intake` keeps the discovery path
as an exception route only.

## The declaration is the classification

Installation, facility, requirement and period are declared in the app before
the file is chosen. The submission is written with
`Intake_Method = 'App upload'`, `Classification_Method = 'Declared at upload'`
and `Classification_Confidence = 'Declared'`.

The filename is stored as evidence and read for nothing. **Upload must work
with an arbitrary filename**, and that is an acceptance test — try
`Copy of copy FINAL(2).xlsx`.

---

## Step 1 — Authorise, before anything touches storage

```
mapping = MF_Security_Mapping where UPN = caller AND Active_Flag
if none                                   -> PERMISSION_DENIED, log, stop
if Installation_ID not in caller's scope  -> PERMISSION_DENIED, log, stop
if MF_App_Config.ReadOnlyMode             -> READ_ONLY, stop
```

**The caller's UPN comes from the flow's authenticated context, never from the
app payload.** A client that can name its own user is not an authorisation
system, and this flow can be invoked directly by anyone who can see it.

Each of these is also checked in the app. The app's version gives a fast,
specific error; this one is the control.

## Step 1a — Idempotency, before anything is written

```
if a MF_EOM_Submission row already carries this Submission_Request_ID:
        return that row's result   — ok, its Submission_ID, its Version_No
        log SUBMISSION_REPLAY
        stop. Create no file. Create no row.
```

**The check happens before the file write, not after it.** A check that runs
after the upload has already created the duplicate it was meant to prevent.

`Submission_Request_ID` is minted by the app when the user picks the file, not
when the call is made, and it is **resent unchanged on every retry of the same
user action**. A new file or a changed declaration is a new request and gets a
new GUID.

**A user pressing Submit twice after a timeout is the normal case on a
government network, not the edge case.** The first request usually succeeded and
the response was lost; the client that timed out is precisely the one that
cannot know. Without this, that user gets two files and two submission rows, one
of them superseding the other for no reason a reviewer can explain.

**Disabling the button in Power Apps is not protection.** The flow can be
invoked directly, the app can be reloaded mid-call, and a dropped connection
does not ask the button's permission. This must hold at the workflow and data
layer:

* `Submission_Request_ID` is **required and indexed**, and is part of
  `MF_EOM_Submission`'s declared unique key.
* The lookup filters on it server-side — an indexed equality, delegable.
* If two calls race past the lookup, the unique constraint rejects the second
  write. Handle that rejection by re-reading the winner and returning its
  result, **not** by retrying the write.

## Step 2 — Resolve the expected item

```
item = MF_EOM_Item where Reporting_Period + Requirement_ID
                     + (Facility_ID, or Installation_ID for installation scope)
if none -> NO_EXPECTED_ITEM
```

**The flow does not create a tracker row.** No expected item means no
obligation the system knows about; the app says so and offers the Needs
Classification route. Nobody conjures a requirement by uploading against it.

## Step 3 — Resolve the destination, and fail closed

```
portfolio   = MF_Installation[Installation_ID].Portfolio_ID
destination = MF_Document_Destination where Portfolio_ID + Document_Domain

if none                        -> DESTINATION_NOT_CONFIGURED
if Active_Flag is FALSE        -> DESTINATION_NOT_CONFIGURED
if Verified_By is blank        -> DESTINATION_NOT_VERIFIED
if Site_URL is blank           -> CONFIGURATION_REQUIRED
```

Three gates, all defaulting to no. A submission that cannot be placed in a
verified location is **not written somewhere convenient**.

`Site_URL` is bound at import from `MF_Portfolio{n}_SiteURL` and is blank in
source — a `.mil` site URL in a tracked file is a destination leak and the
pre-release scan blocks it. The four site slugs are **not derivable from one
another**: Portfolio 2 carries a `Legacy_` prefix the other three do not, so a
URL built by pattern 404s on exactly one portfolio. See
`deployment/site-bindings.md`.

## Step 4 — Find the folder. Never create one.

`Folder_Template` is `{FiscalYearShort}/{MonthFolder}`. These name folders that
**already exist** and are curated by hand. The template is a description of
what to look for, not a path to render.

```
root  = Site_URL + Library_Name + Root_Folder
fy    = a child of root matching the fiscal year   (FY26 for 2026-08, Oct-Sep)
month = a child of fy matching the reporting month

both found -> write there
otherwise  -> Fallback_Policy
```

Matching is case-insensitive and accent-insensitive, anywhere in the folder
name:

| Level | Accepted |
|---|---|
| Fiscal year | `FY26`, `FY 26`, `FY-26`, `FY2026`, `FY 2026` |
| Month | the full name, then the three-letter form, then the two-digit number |

Strongest signal first, because `08. August` carries both. Where a folder
states a year it must be the right one — `Aug 25` never receives an August 2026
submission. A folder stating no year is accepted as written; plenty of sites
keep the year only on the FY folder above.

**Match, do not construct.** All four sites name their root folders
differently — `H. Monthly Data Call`, `5. Monthly Data Call`, and two bare
`Monthly Data Call`. There is no reason to believe they name their month
folders alike.

**`Create_Missing_Folders` is FALSE, permanently.** A flow that creates folders
will eventually produce `Aug 26` beside someone's `August 2026`. Both look
right, half the submissions go to each, and nobody notices for a month — at
which point there is no way to tell which folder a given base was told to use.

### When the folder is not found

`Fallback_Policy = FIND_OR_ROOT` — the R1 policy on all four rows:

```
write to the Monthly Data Call root
Needs_Filing = TRUE
Filing_Note  = "no child of FY26 matched August 2026"
log SUBMISSION_FILED_AT_ROOT
```

**A submission that lands somewhere findable beats one that fails.** The base
did their part; the mess is ours, and it is visible. Admin surfaces the count —
*"3 submissions filed at root — folder not matched"* — with the installation,
period and what was looked for, so somebody can either move the file or fix
`Month_Folder_Pattern_Note` on the destination row.

`FIND_OR_FAIL` returns `DESTINATION_FOLDER_NOT_FOUND` instead. It exists for a
destination where a stray file at root would be worse than a failed upload. No
R1 row uses it.

The reference implementation is `scripts/folder_resolver.py`, and
`tests/test_folder_resolver.py` holds this spec and that code to each other.

## Step 5 — Create the file

Sanitise every path segment: strip `" * : < > ? / \ |`, collapse whitespace,
trim to the SharePoint limit. Display names come from the registry, never from
the raw source string — `CHARLESTON, JB` is written as `JB Charleston`.

**The original filename is preserved as uploaded. No naming convention is
applied, required or inferred.** `Scan0023948.pdf` is fine; the record carries
the meaning. If a file of that name already exists, append ` (v2)`, ` (v3)` —
that is collision avoidance, not versioning. SharePoint version history is not
the record; `MF_EOM_Submission` is.

**Never overwrite a file.**

## Step 6 — Record the submission

```
supersede any Is_Current submission for this item:
    Is_Current = false, Superseded_By = new Submission_ID

create MF_EOM_Submission:
    Submission_Request_ID  as supplied — the idempotency key
    Version_No             prior count + 1
    File_Name              as uploaded
    SharePoint_Unique_ID   the document GUID — THE DURABLE HANDLE
    SharePoint_File_ID     list item ID
    File_URL               resolved from the GUID; convenience, not truth
    Destination_ID · Source_Library · Source_Path
    Needs_Filing · Filing_Note
    Uploaded_By            authenticated identity, always the real uploader
    Submitted_On_Behalf_Of when the caller holds Can_Submit_On_Behalf
    Intake_Method          'App upload'
    Classification_Method  'Declared at upload'
    Is_Current             true
    QC_Status              'Pending Review'

update MF_EOM_Item:
    Received_Flag, Current_Submission_ID
    Initial_Submitted_DateTime      first version only
    Initial_Submission_On_Time      against Effective_Due_Date
    Final_Status RECEIVED_PENDING_QC, Status_Code 2

log SUBMISSION_CREATED
```

**Store the GUID; resolve the URL from it.** A file that gets moved or renamed
keeps its unique ID and loses its URL — and under FIND_OR_ROOT files get moved
*by design*, by the human who files them properly. A build that stored only the
URL would lose the audit trail on exactly the submissions somebody had to
rescue.

**Never duplicate the checklist row.** v1 keeps its row, its file and its QC
comment. The audit question is "what did they send and what did the reviewer
say", for every attempt.

## Step 7 — Confirm, or fail loudly

If the file was created but the record write failed, return
`SUBMISSION_NOT_CONFIRMED` with a correlation ID and log it. A file in
SharePoint with no submission record is invisible to the app and will be found
by nobody. **Never report success on a partial write.**

---

## Submitting on behalf

When the caller holds `Can_Submit_On_Behalf` and the app's on-behalf toggle is
set, `Submitted_On_Behalf_Of` carries the target `Facility_ID` or
`Installation_ID`. Without it, a document that arrived by email and was
uploaded by an AFSVC MFM misattributes to AFSVC and the missing counts go wrong
silently. `Uploaded_By` stays the actual uploader — both facts are recorded.

## Status after upload

The engine runs once, here. A new submission is `Pending Review`, so the item
becomes `RECEIVED_PENDING_QC` / `Status_Code 2` / owner `Reviewer`. If the
requirement carries `QC_Required = false` and `MF_App_Config.RequireQC` is
false, the submission is written `Accepted` and the item goes `ACCEPTED` / `3`.

Nothing here chooses a colour. The flow writes back the fields one evaluation
returned. `scripts/status_engine.py` is that evaluation.

## Corrections

A resubmission goes to the **same folder** and creates v2. Both files remain;
v1 becomes `Is_Current = false` with `Superseded_By` pointing forward. The
application knows these are two Mission Feeding versions — it does not rely on
SharePoint version history to know that.

## One authoritative copy

One SharePoint file, one submission record pointing at it. There is no central
intake duplicate: a second copy creates ambiguity about which is authoritative,
a retention problem, and broken links when the two diverge.

## Errors the app must handle

```
PERMISSION_DENIED             plain message plus Request access
READ_ONLY                     maintenance banner, upload disabled
NO_EXPECTED_ITEM              Needs Classification route
DESTINATION_NOT_CONFIGURED    admin message, submission blocked
DESTINATION_NOT_VERIFIED      admin message, submission blocked
CONFIGURATION_REQUIRED        CONFIGURATION_REQUIRED screen
DESTINATION_FOLDER_NOT_FOUND  admin message  (FIND_OR_FAIL destinations only)
TOO_LARGE                     size from MF_App_Config.MaxUploadSizeMB
SUBMISSION_NOT_CONFIRMED      "We couldn't confirm your submission" + correlation ID
```

**None of these surfaces a path, a site URL, a GUID or a raw connector
message.** A user who cannot upload does not need the tenant's topology to
report the problem.

## Audit and telemetry

`MF_EOM_Audit`: `Action = 'Uploaded'`, entity the submission.
`MF_App_Event_Log`: `SubmissionCreated`, plus `VersionSuperseded` when a prior
current version was demoted, plus `SUBMISSION_FILED_AT_ROOT` when the folder
could not be matched, plus `SUBMISSION_REPLAY` when a request arrived twice.
All stamped with `App_Version`.

**`SUBMISSION_REPLAY` is not an error and is not shown to the user.** They see
the same confirmation they would have seen the first time, because from where
they are standing that is what happened. The count of replays is worth watching
though: a sustained rise means the flow is timing out before it finishes.
