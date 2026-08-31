# EOM-02 — Submission

**Trigger:** Called from the app when a user submits a document.
**Replaces:** the old file-intake-and-classify flow for the normal path.

The app supplies logical identifiers. It never supplies a path.

```
Installation_ID   LACKLAND_AFB
Reporting_Period  2026-08
Requirement_ID    REQ-001
File              base64 + original filename
On_Behalf_Of      optional
Note              optional
```

## Steps

**1. Authorise — before anything touches storage.**

```
mapping = MF_Security_Mapping where UPN = caller AND Active_Flag
if none                                    -> 403, log PERMISSION_DENIED, stop
if Installation_ID not in caller's scope   -> 403, log PERMISSION_DENIED, stop
```

The caller's UPN comes from the flow's authenticated context, never from the app
payload. A client that can name its own user is not an authorisation system.

**2. Resolve the expected item.**

```
item = MF_EOM_Item where Reporting_Period + Requirement_ID + (Facility_ID or
       Installation_ID for installation scope)
if none -> return NO_EXPECTED_ITEM
```

The flow does **not** create a tracker row. An upload with no expected item goes
to Needs Classification, so nobody can conjure a requirement by uploading against
it.

**3. Resolve the destination.**

```
portfolio    = MF_Installation[Installation_ID].Portfolio_ID
destination  = MF_Document_Destination where Portfolio_ID + Document_Domain
if none                          -> DESTINATION_NOT_CONFIGURED
if Active_Flag is false          -> DESTINATION_NOT_CONFIGURED
if Channel_Type = 'Unverified'   -> DESTINATION_NOT_VERIFIED
if Site_URL is blank             -> CONFIGURATION_REQUIRED
```

Fail closed on every one. A submission that cannot be placed in a verified
location is not written somewhere convenient.

**4. Build the path from the template.**

```
{FiscalYear}       FY26        from Reporting_Period, Oct-Sep
{ReportingPeriod}  2026-08
{InstallationName} Lackland AFB    display name, sanitised for SharePoint
{RequirementCode}  1119
{FacilityName}     optional, facility-scope requirements only

Site_URL + Library_Name + Root_Folder + resolved template
= Portfolio 2/Monthly Documents/FY26/2026-08/Lackland AFB/1119
```

Sanitise every token: strip `" * : < > ? / \ |`, collapse whitespace, trim to
the SharePoint segment limit. `CHARLESTON, JB` becomes `JB Charleston` from the
registry display name, not from the raw source string.

**5. Create the file.**

Create missing folders only when `Create_Missing_Folders` is true. Otherwise a
missing folder is an error — an unexpected path should surface, not silently
grow a new tree.

The original filename is preserved as uploaded. **No naming convention is
applied, required or inferred.** If a file of that name exists, append
` (v2)`, ` (v3)` — SharePoint versioning is not the record; `MF_EOM_Submission`
is.

**6. Record the submission.**

```
supersede any Is_Current submission for this item
create MF_EOM_Submission:
    Version_No             prior count + 1
    File_Name              as uploaded
    SharePoint_Unique_ID   the GUID — the durable handle
    SharePoint_File_ID     list item ID
    File_URL               resolved from the GUID, convenience not truth
    Destination_ID · Source_Library · Source_Path
    Uploaded_By            authenticated identity
    Intake_Method          'App upload'
    Classification_Method  'Declared at upload'
    Is_Current             true
    QC_Status              'Pending Review'
update MF_EOM_Item: Received_Flag, Current_Submission_ID,
    Initial_Submitted_DateTime (first version only),
    Initial_Submission_On_Time (against Effective_Due_Date),
    Final_Status RECEIVED_PENDING_QC, Status_Code 2
log SUBMISSION_CREATED
```

**Store the GUID, resolve the URL from it.** A file that gets moved or renamed
keeps its unique ID and loses its URL, and the whole audit trail hangs off that
pointer.

**7. Confirm, or fail loudly.**

If the file was created but the record write failed, return
`SUBMISSION_NOT_CONFIRMED` and log it. A file in SharePoint with no submission
record is invisible to the app and will be found by nobody. Never report success
on a partial write.

## Corrections

A resubmission goes to the **same requirement folder** and creates v2. Both files
remain. v1 becomes `Is_Current = false` with `Superseded_By` pointing forward.
The application knows these are two Mission Feeding versions; it does not rely on
SharePoint version history to know that.

## One authoritative copy

There is no central intake duplicate. One SharePoint file, one submission record
pointing at it. A second copy creates ambiguity about which is authoritative, a
retention problem, and broken links when the two diverge.

A central intake library remains reserved for legacy, manual or unstructured
discovery if that is ever needed. It is not part of the normal path.

## Errors the app must handle

```
NO_EXPECTED_ITEM            -> Needs Classification
DESTINATION_NOT_CONFIGURED  -> admin message, submission blocked
DESTINATION_NOT_VERIFIED    -> admin message, submission blocked
CONFIGURATION_REQUIRED      -> CONFIGURATION_REQUIRED screen
PERMISSION_DENIED           -> plain message plus Request access
SUBMISSION_NOT_CONFIRMED    -> "We couldn't confirm your submission" + correlation ID
```

None of these surfaces a path, a site URL, a GUID or a connector message.
