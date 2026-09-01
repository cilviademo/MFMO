# EOM-02 Submission — manual rebuild, click by click

Derived action-by-action from the implemented workflow JSON (`solution/src/Workflows/EOM02Submission-*.json`). Nothing here is from memory. Build it in the browser designer: Power Automate → Create → **Instant cloud flow** → trigger **PowerApps (V2)** → name it `EOM-02 Submission`.

In this manual edition every solution environment variable becomes a **flow variable initialized at the top**. Fill each from your own links sheet.

## Step 0 — the trigger contract (PowerApps V2 inputs)

Add one **Text** input per property, named exactly:

- [ ] `submissionRequestId` (shown as "Submission_Request_ID")
- [ ] `installationId`
- [ ] `reportingPeriod`
- [ ] `requirementId`
- [ ] `facilityId`
- [ ] `fileName`
- [ ] `fileContent`
- [ ] `onBehalfOf`
- [ ] `note`

The app calls `EOM02_Submission.Run(...)` with these in this order; a missing or renamed input breaks the call visibly in Studio, which is the good failure mode.

## Step 0b — Initialize the operator variables

One **Initialize variable** action per row, Type = String, placed before everything else. Every value is **OPERATOR VALUE — from your links sheet**; none ships in this kit.

| Variable name | Holds |
|---|---|
| `varMF_SharePointSiteURL` | your SharePointSiteURL — OPERATOR VALUE |
| `varMF_ConfigList` | your ConfigList — OPERATOR VALUE |
| `varMF_ItemList` | your ItemList — OPERATOR VALUE |
| `varMF_SubmissionList` | your SubmissionList — OPERATOR VALUE |
| `varMF_SecurityList` | your SecurityList — OPERATOR VALUE |
| `varMF_AuditList` | your AuditList — OPERATOR VALUE |
| `varMF_InstallationList` | your InstallationList — OPERATOR VALUE |
| `varMF_DestinationList` | your DestinationList — OPERATOR VALUE |

## The actions, in order

### 1. Add **Initialize variable** — rename it exactly: `Initialize ExpectedSchemaVersion`

Inputs:

```json
{
  "variables": [
    {
      "name": "ExpectedSchemaVersion",
      "type": "string",
      "value": "5.0"
    }
  ]
}
```

### 2. Add **SharePoint — Get items** — rename it exactly: `Get the deployed schema version`

Run after: `Initialize ExpectedSchemaVersion` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_ConfigList')` |
| `$filter` | `Config_Key eq 'SchemaVersion'` |
| `$top` | `1` |

### 3. Add **Condition** — rename it exactly: `Stop on a schema mismatch`

Run after: `Get the deployed schema version` [Succeeded]

Condition (use **Edit in advanced mode** and paste verbatim):

```
{
  "not": {
    "equals": [
      "@first(body('Get_the_deployed_schema_version')?['value'])?['Config_Value']",
      "@variables('ExpectedSchemaVersion')"
    ]
  }
}
```

#### 4. IF TRUE: Add **Terminate** — rename it exactly: `CONFIGURATION REQUIRED`

Inputs (paste each expression verbatim):

```json
{
  "runStatus": "Failed",
  "runError": {
    "code": "CONFIGURATION_REQUIRED",
    "message": "This flow expects a different schema version than MF_App_Config reports. A newer flow writing against an older schema patches columns that do not exist, which writes nothing rather than erroring. Stopped before any write. See docs/SHAREPOINT_SCHEMA_MANIFEST.md."
  }
}
```

### 5. Add **Compose (Data Operation)** — rename it exactly: `Caller`

Run after: `Stop on a schema mismatch` [Succeeded]

Inputs (paste each expression verbatim):

```json
"@{triggerOutputs()?['headers']?['x-ms-user-email-encoded']}"
```

### 6. Add **SharePoint — Get items** — rename it exactly: `Get the callers scope`

> WHY THIS EXISTS: the flow trusts only its own authenticated caller lookup, never anything the app claims. A client that can name its own user is not an authorisation system.

Run after: `Caller` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_SecurityList')` |
| `$filter` | `UPN eq '@{outputs('Caller')}' and Active_Flag eq 1` |
| `$top` | `50` |

### 7. Add **Condition** — rename it exactly: `Refuse an unmapped or out of scope caller`

Run after: `Get the callers scope` [Succeeded]

Condition (use **Edit in advanced mode** and paste verbatim):

```
{
  "or": [
    {
      "equals": [
        "@length(body('Get_the_callers_scope')?['value'])",
        0
      ]
    },
    {
      "equals": [
        "@length(filter(body('Get_the_callers_scope')?['value'], or(equals(item()?['Scope_Type']?['Value'], 'Enterprise'), equals(item()?['Installation_ID'], triggerBody()?['installationId']))))",
        0
      ]
    }
  ]
}
```

#### 8. IF TRUE: Add **Respond to a PowerApp or flow** — rename it exactly: `PERMISSION DENIED`

Inputs (paste each expression verbatim):

```json
{
  "statusCode": 403,
  "body": {
    "ok": false,
    "code": "PERMISSION_DENIED",
    "message": "You do not have access to that installation."
  }
}
```

### 9. Add **SharePoint — Get items** — rename it exactly: `Look for a replay`

> WHY THIS EXISTS: the idempotency guard. The app sends a unique submissionRequestId; if a row already carries it, a double-click or a retry returns the FIRST result instead of writing a duplicate file and a duplicate row.

Run after: `Refuse an unmapped or out of scope caller` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_SubmissionList')` |
| `$filter` | `Submission_Request_ID eq '@{triggerBody()?['submissionRequestId']}'` |
| `$top` | `1` |

### 10. Add **Condition** — rename it exactly: `Return the first result if this is a replay`

Run after: `Look for a replay` [Succeeded]

Condition (use **Edit in advanced mode** and paste verbatim):

```
{
  "greater": [
    "@length(body('Look_for_a_replay')?['value'])",
    0
  ]
}
```

#### 11. IF TRUE: Add **Respond to a PowerApp or flow** — rename it exactly: `SUBMISSION REPLAY`

Inputs (paste each expression verbatim):

```json
{
  "statusCode": 200,
  "body": {
    "ok": true,
    "code": "SUBMISSION_REPLAY",
    "submissionId": "@{first(body('Look_for_a_replay')?['value'])?['Submission_ID']}",
    "versionNo": "@first(body('Look_for_a_replay')?['value'])?['Version_No']",
    "message": "Submitted."
  }
}
```

### 12. Add **SharePoint — Get items** — rename it exactly: `Find the expected item`

Run after: `Return the first result if this is a replay` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_ItemList')` |
| `$filter` | `Reporting_Period eq '@{triggerBody()?['reportingPeriod']}' and Requirement_ID eq '@{triggerBody()?['requirementId']}' and Facility_ID eq '@{triggerBody()?['facilityId']}'` |
| `$top` | `1` |

### 13. Add **Condition** — rename it exactly: `Refuse if nothing is expected`

Run after: `Find the expected item` [Succeeded]

Condition (use **Edit in advanced mode** and paste verbatim):

```
{
  "equals": [
    "@length(body('Find_the_expected_item')?['value'])",
    0
  ]
}
```

#### 14. IF TRUE: Add **Respond to a PowerApp or flow** — rename it exactly: `NO EXPECTED ITEM`

Inputs (paste each expression verbatim):

```json
{
  "statusCode": 200,
  "body": {
    "ok": false,
    "code": "NO_EXPECTED_ITEM",
    "message": "There's no expected requirement matching that facility, document and period. Send it to Needs Classification and someone will confirm whether the requirement should exist."
  }
}
```

### 15. Add **SharePoint — Get items** — rename it exactly: `Get the installation`

Run after: `Refuse if nothing is expected` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_InstallationList')` |
| `$filter` | `Installation_ID eq '@{triggerBody()?['installationId']}'` |
| `$top` | `1` |

### 16. Add **SharePoint — Get items** — rename it exactly: `Get the destination`

Run after: `Get the installation` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_DestinationList')` |
| `$filter` | `Portfolio_ID eq '@{first(body('Get_the_installation')?['value'])?['Portfolio_ID']}' and Document_Domain eq 'EOM' and Active_Flag eq 1` |
| `$top` | `1` |

### 17. Add **Condition** — rename it exactly: `Fail closed on the destination`

> WHY THIS EXISTS: fail closed. An inactive, unverified or missing destination refuses the upload with DESTINATION_NOT_CONFIGURED rather than guessing a path.

Run after: `Get the destination` [Succeeded]

Condition (use **Edit in advanced mode** and paste verbatim):

```
{
  "or": [
    {
      "equals": [
        "@length(body('Get_the_destination')?['value'])",
        0
      ]
    },
    {
      "equals": [
        "@coalesce(first(body('Get_the_destination')?['value'])?['Verified_By'], '')",
        ""
      ]
    },
    {
      "equals": [
        "@coalesce(first(body('Get_the_destination')?['value'])?['Site_URL'], '')",
        ""
      ]
    }
  ]
}
```

#### 18. IF TRUE: Add **Respond to a PowerApp or flow** — rename it exactly: `DESTINATION NOT USABLE`

Inputs (paste each expression verbatim):

```json
{
  "statusCode": 200,
  "body": {
    "ok": false,
    "code": "DESTINATION_NOT_CONFIGURED",
    "message": "Uploads for this portfolio aren't configured yet. An administrator has been notified."
  }
}
```

### 19. Add **Compose (Data Operation)** — rename it exactly: `Destination`

Run after: `Fail closed on the destination` [Succeeded]

Inputs (paste each expression verbatim):

```json
"@first(body('Get_the_destination')?['value'])"
```

### 20. Add **Compose (Data Operation)** — rename it exactly: `Root`

Run after: `Destination` [Succeeded]

Inputs (paste each expression verbatim):

```json
"@{concat(outputs('Destination')?['Library_Url_Segment'], '/', outputs('Destination')?['Root_Folder'])}"
```

### 21. Add **SharePoint — Get files (properties only)** — rename it exactly: `List the fiscal year folders`

> WHY THIS EXISTS: FIND, never CREATE. The flow locates the existing FY/month folder by listing what is actually on the site. It never creates folders: a wrong guess would scatter documents into structures nobody maintains.

Run after: `Root` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@{outputs('Destination')?['Site_URL']}` |
| `table` | `@{outputs('Destination')?['Library_Url_Segment']}` |
| `$filter` | `FSObjType eq 1` |

### 22. Add **Compose (Data Operation)** — rename it exactly: `Resolve the folder`

> WHY THIS EXISTS: when no month folder matches, the file goes to the configured ROOT and the submission is flagged Needs_Filing = TRUE with a Filing_Note saying what was looked for. NOTHING ERRORS -- the Exceptions screen surfaces the count, and a human files the document one level down.

Run after: `List the fiscal year folders` [Succeeded]

Inputs (paste each expression verbatim):

```json
{
  "rule": "MATCH, DO NOT CONSTRUCT. Fiscal year: FY26, FY 26, FY-26, FY2026, FY 2026. Month: the full name, then the three-letter form, then the two-digit number, in that order, case- and accent-insensitively. Where a folder states a year it must be the right one.",
  "reference": "scripts/folder_resolver.py, held to this spec by tests/test_folder_resolver.py",
  "createMissing": "NEVER. Create_Missing_Folders is FALSE permanently: a flow that creates folders eventually produces 'Aug 26' beside someone's 'August 2026' and nobody notices for a month.",
  "fallback": "FIND_OR_ROOT. Write to the Monthly Data Call root, Needs_Filing TRUE, Filing_Note naming what was searched for. NEVER above that root: a file at a site or library root looks like it worked and is somewhere nobody will look."
}
```

### 23. Add **SharePoint — Create file** — rename it exactly: `Create the file`

Run after: `Resolve the folder` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@{outputs('Destination')?['Site_URL']}` |
| `folderPath` | `@{outputs('Root')}` |
| `name` | `@{triggerBody()?['fileName']}` |
| `body` | `@{triggerBody()?['fileContent']}` |

### 24. Add **SharePoint — Get items** — rename it exactly: `Supersede the current version`

> WHY THIS EXISTS: versioning. The previous current submission flips Is_Current = FALSE; history is kept, never overwritten.

Run after: `Create the file` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_SubmissionList')` |
| `$filter` | `EOM_Item_ID eq '@{first(body('Find_the_expected_item')?['value'])?['EOM_Item_ID']}' and Is_Current eq 1` |
| `$top` | `1` |

### 25. Add **SharePoint — Create item** — rename it exactly: `Record the submission`

Run after: `Supersede the current version` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_SubmissionList')` |
| `item` | `{"Submission_Request_ID": "@{triggerBody()?['submissionRequestId']}", "EOM_Item_ID": "@{first(body('Find_the_expected_item')?['value'])?['EOM_Item_ID']}", "Version_No": "@add(length(body('Supersede_the_current_version')?['value']), 1)", "File_Name": "@{triggerBody()?['fileName']}", "SharePoint_Unique_ID": "@{body('Create_the_file')?['{Identifier}']}", "SharePoint_File_ID": "@{body('Create_the_file')?['Id']}", "File_URL": "@{body('Create_the_file')?['Path']}", "Destination_ID": "@{outputs('Destination')?['Destination_ID']}", "Source_Library": "@{outputs('Destination')?['Library_Url_Segment']}", "Source_Path": "@{outputs('Root')}", "Uploaded_By": "@{outputs('Caller')}", "Submitted_On_Behalf_Of": "@{triggerBody()?['onBehalfOf']}", "Intake_Method": "App upload", "Classification_Method": "Declared at upload", "Classification_Confidence": "Declared", "Is_Current": true, "Is_Pilot": "@equals(outputs('Pilot_mode'), 'True')", "QC_Status": "Pending Review"}` |

### 26. Add **SharePoint — Create item** — rename it exactly: `Audit the upload`

Run after: `Record the submission` [Succeeded]

| Parameter | Value (verbatim) |
|---|---|
| `dataset` | `@variables('varMF_SharePointSiteURL')` |
| `table` | `@variables('varMF_AuditList')` |
| `item` | `{"Action": "Uploaded", "Action_DateTime": "@{utcNow()}", "Entity_Type": "Submission", "Entity_ID": "@{body('Record_the_submission')?['Submission_ID']}", "Actor_UPN": "@{outputs('Caller')}", "Detail": "@{concat('Version ', body('Record_the_submission')?['Version_No'], ' of ', triggerBody()?['fileName'])}"}` |

### 27. Add **Condition** — rename it exactly: `Confirm or fail loudly`

> WHY THIS EXISTS: the flow never reports success it cannot prove. If the confirmation read-back fails, the app shows SUBMISSION_NOT_CONFIRMED instead of a silent maybe.

Run after: `Audit the upload` [Succeeded, Failed]

Condition (use **Edit in advanced mode** and paste verbatim):

```
{
  "equals": [
    "@empty(body('Record_the_submission')?['ID'])",
    true
  ]
}
```

#### 28. IF TRUE: Add **Respond to a PowerApp or flow** — rename it exactly: `SUBMISSION NOT CONFIRMED`

Inputs (paste each expression verbatim):

```json
{
  "statusCode": 200,
  "body": {
    "ok": false,
    "code": "SUBMISSION_NOT_CONFIRMED",
    "correlationId": "@{workflow()['run']['name']}",
    "message": "We couldn't confirm your submission. Quote this reference when you report it."
  }
}
```

#### 29. IF FALSE: Add **Respond to a PowerApp or flow** — rename it exactly: `OK`

Inputs (paste each expression verbatim):

```json
{
  "statusCode": 200,
  "body": {
    "ok": true,
    "code": "SUBMISSION_CREATED",
    "submissionId": "@{body('Record_the_submission')?['Submission_ID']}",
    "versionNo": "@body('Record_the_submission')?['Version_No']",
    "needsFiling": "@outputs('Resolve_the_folder')?['needsFiling']",
    "message": "Submitted."
  }
}
```

### 30. Add **Compose (Data Operation)** — rename it exactly: `Pilot mode`

Run after: `Refuse an unmapped or out of scope caller` [Succeeded]

Inputs (paste each expression verbatim):

```json
"@{first(body('Get_the_callers_scope')?['value'])?['Is_Pilot']}"
```


## Test procedure — one synthetic submission

1. From the app (or the flow's Test pane) call the flow with a synthetic
   `submissionRequestId` (any fresh GUID-like string), a real pilot
   `installationId`/`reportingPeriod`/`requirementId` from your seeded
   data, and a small test file.
2. EXPECT: one new row in your Submission list with `Is_Current = Yes`,
   `Submission_Request_ID` equal to what you sent, and
   `SharePoint_Unique_ID` populated.
3. EXPECT: the file lands in the destination's matched month folder --
   or, if no month folder matches, at the configured ROOT with
   `Needs_Filing = Yes` and a `Filing_Note`. Either is correct behaviour;
   a file anywhere else is not.
4. Run the SAME call again, same `submissionRequestId`. EXPECT: no second
   row, no second file -- the response returns the first result
   (SUBMISSION_REPLAY). That is the idempotency guard working.
5. NOT TESTABLE LOCALLY, verified only here, in your tenant: connector
   auth, folder listings against the real site, and write permissions.
