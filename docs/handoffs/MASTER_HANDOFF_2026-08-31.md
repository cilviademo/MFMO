# MISSION FEEDING OPERATIONS — CLAUDE CODE MASTER HANDOFF
## Power Apps + Power Automate + SharePoint/Teams + Power BI + Figma UX + .mil/DoW Security
**Status:** Current build/reference handoff  
**Date:** 31 Aug 2026  
**Use:** Paste or place this file at the root of the Claude Code workspace.  
**Priority:** This document supersedes earlier assumptions where conflicts exist.

---

# 0. READ THIS FIRST

This project is the first production module of a broader **DAF Mission Feeding Operations** platform.

The immediate release is a **Legacy/APF End-of-Month (EOM) submission, QC, correction, status, and leadership visibility system** built in Microsoft Power Platform for eventual deployment on the authorized `.mil` government tenant.

The design goal is not “a better SharePoint tracker.” It is an operational control system where:

- base-level Mission Feeding users know exactly what is due;
- they submit evidence in one simple Power App;
- AFSVC Mission Feeding staff review and return/accept submissions;
- expected-document status updates automatically;
- every correction/version is retained;
- leadership receives a trustworthy Power BI COP;
- the package is secure-by-default and ready to bind to government environment configuration after import.

**Do not redesign the project around generic dashboards, passive folder discovery, fake installations, or commercial-cloud assumptions.**

---

# 1. EXECUTIVE BLUF

## Production stack

- **Power Apps Canvas** = primary human workflow / submission / review / action interface.
- **Power Automate** = submission storage, expected-package generation, reconciliation, notification hooks, version/state updates.
- **SharePoint / Teams** = source document repository, configuration/workflow storage, evidence retention.
- **Power BI** = leadership COP / reporting / analytics only; not system of record.
- **Figma** = UX/UI reference; design language should follow **IBM Cognos Analytics + Microsoft Fluent 2 / Teams**.
- **Source-controlled Power Platform solution** = importable build artifact.

## Current MVP

R1 is **Legacy/APF EOM only**.

Do not block R1 on:

- Food 2.0 requirements;
- EOY full policy completion;
- enterprise-wide perfect facility master data;
- AI Builder;
- Dataverse;
- custom connectors;
- HTTP;
- custom PCF;
- external SaaS.

Build the shell so those can be added later.

---

# 2. NON-NEGOTIABLE PRINCIPLES

1. **No giant monolithic SharePoint list.**
2. **No filename-based authority.**
3. **No silent unmatched/failed submission handling.**
4. **Requirements are configuration/data, not hard-coded Power Fx.**
5. **Keep expected EOM obligations separate from submission/version records.**
6. **Never overwrite corrected documents.**
7. **Security is deny-by-default.**
8. **UI filters are not the data-security boundary.**
9. **Power BI never reconstructs operational business logic from raw data.**
10. **No fake DoDAAC/DODAAD/CUI values.**
11. **No commercial-only runtime dependencies in the production candidate.**
12. **No secrets, credentials, tokens, CAC identifiers, or protected operational data in source.**
13. **Production role simulators, mock identities, bypass-security controls, and debug tooling default OFF.**
14. **Unverified policy must remain configurable and cannot create adverse status unless deliberately authorized as a management rule.**
15. **Power Apps must feel operational, dense, restrained, and enterprise-grade — not consumer SaaS.**

---

# 3. USER / ROLE MODEL

## Base / Installation Users

Primary population:

- DFAC Managers
- Accountants
- General Managers
- installation Mission Feeding personnel

Primary tasks:

1. know what documents are due;
2. upload documents;
3. see whether AFSVC received them;
4. see whether AFSVC accepted or returned them;
5. correct/resubmit;
6. understand overall package completion;
7. see due dates and final-call dates.

Base users should **not** need to understand:

- Portfolio_ID;
- Requirement_ID;
- Facility_ID unless necessary;
- SharePoint paths;
- source metadata;
- ingestion/classification logic;
- internal audit fields.

## AFSVC / VMF Mission Feeding Users

All authorized AFSVC Mission Feeding owner-level personnel may review across Portfolios.

Primary tasks:

1. see incoming submissions;
2. QC documents;
3. return/accept;
4. identify missing/late/overdue;
5. monitor package completion;
6. review installations and facilities;
7. manage exceptions;
8. review activity/audit;
9. maintain configuration where authorized.

## Admin

Admin scope includes:

- requirements;
- installation/facility registry;
- security/access;
- reporting periods;
- notification settings;
- feature flags;
- system/configuration health;
- data-quality exceptions.

---

# 4. AUTHENTICATION / ACCESS MODEL

Authentication is provided by the authorized Microsoft government tenant / Entra identity.

Do not implement a custom login.

Use the signed-in user identity and map it to:

`MF_User_Access`

Recommended fields:

```text
User_UPN
Role
Installation_ID
Portfolio_ID
Scope_Type
Effective_From
Effective_To
Access_Source
Approved_By
Approval_Date
Active_Flag
```

Base users should normally be authorized at **installation level**.

Example:

- user at Lackland can access/edit Lackland EOM submissions;
- user does not automatically see other installations;
- temporary access can be requested for PCS/handover scenarios;
- temporary access should have an expiry.

AFSVC users may have Portfolio or Enterprise scope.

**Never use the QRG POC name as the permission authority.**

---

# 5. REAL SOURCE REGISTRY — QRG

Use the attached scrubbed QRG CSV as the seed source for the operational installation/facility registry.

Current analyzed source:

- **261 source rows**
- **107 unique installations**
- **4 Portfolios**
- **14 MAJCOM/organizational categories**
- multiple facilities/program records per installation

Current high-level feeding type counts identified in the scrubbed file:

- Legacy: ~144 rows
- Food 2.0: ~69
- Deployed / Field Feeding: ~22
- MAFFO: ~6
- some unassigned/incomplete records

Source fields include:

```text
INSTALLATION
LOCATION
FACILITY NAME
PORTFOLIO
MAJCOM
DESIGNATION
UNIT
POC
FEEDING TYPE
PROGRAM TYPE
CONTRACT TYPE
PRIMARY PV
POS TERMINALS
```

Do not flatten this into one row per installation.

Canonical hierarchy:

```text
Portfolio
  ↓
Installation
  ↓
Facility / Program Record
  ↓
Applicable Requirement
  ↓
Expected EOM Item
  ↓
Submission / Version
```

---

# 6. CANONICAL REGISTRY DATA MODEL

## MF_Installation

Recommended fields:

```text
Installation_ID
Installation_Name
Location
Portfolio_ID
MAJCOM
Primary_Designation
Active_Flag
Data_Completeness_Status
Needs_Review_Flag
Source_System
Last_Validated_Date
Validated_By
```

Future `.mil` enrichment fields:

```text
DODAAC
DODAAD
Org_Box_Email
Official_POC_UPN
CUI_Profile_ID
```

These must remain blank/null in scrubbed development builds.

## MF_Facility

Recommended fields:

```text
Facility_ID
Installation_ID
Facility_Name
Designation
Unit
Feeding_Type
Program_Type
Contract_Type
Primary_PV
POS_Terminals_Raw
Active_Flag
Data_Completeness_Status
Needs_Review_Flag
Source_Record_ID
Source_System
Last_Validated_Date
Validated_By
```

Future `.mil` fields:

```text
Official_POC_UPN
Org_Box_Email
Facility_DODAAC
Facility_DODAAD
Contract_ID
CUI_Reference_ID
```

Do not infer protected identities or contact data from names.

---

# 7. REGISTRY NORMALIZATION RULES

Preserve source meaning.

Normalize:

- whitespace;
- casing where safe;
- Portfolio labels exactly to:
  - PORTFOLIO 1
  - PORTFOLIO 2
  - PORTFOLIO 3
  - PORTFOLIO 4

Do not auto-assign blank Portfolio values.

Use:

```text
Portfolio_ID = NULL
Needs_Review_Flag = true
```

Preserve raw vendor/program strings where normalization is uncertain.

Recommended pattern:

```text
Primary_PV_Raw
Primary_PV_Normalized
```

For POS terminal data, do not assume numeric cleanliness. Store:

```text
POS_Terminals_Raw
```

before any future normalization.

---

# 8. R1 LEGACY EOM REQUIREMENTS — CONFIRMED

Current authoritative AFSVC EOM/EOY procedure lists:

1. **1119**
2. **SF 1080**
3. **SAIIT**
4. **GPC Bank Statement / GPC Purchases**
5. **1119-1 — Field Feeding**
6. **1038 — Quarterly**

## Do NOT activate

- SIK
- DAF Form 79

Keep them as inactive/unverified definitions rather than deleting them.

Suggested:

```text
SIK
Active_Flag = false
Authority_Status = RETIRED_OR_NOT_APPLICABLE_TO_CURRENT_EOM

DAF Form 79
Active_Flag = false
Authority_Status = UNVERIFIED
```

---

# 9. CURRENT WORKING REQUIREMENT SCOPE

Use configuration-driven scope.

Current R1 assumptions:

| Requirement | Scope | Status |
|---|---|---|
| 1119 | Facility | High confidence |
| 1119-1 | Facility | Medium |
| SAIIT | Facility | High |
| SF 1080 | Installation | PROPOSED |
| GPC Bank Statement | Installation | PROPOSED |
| 1038 | Installation | PROPOSED |

Do not falsely mark proposed scope as policy-verified.

Changing scope after expected rows exist requires period regeneration/reconciliation.

---

# 10. EOM / EOY AUTHORITY NOTES

Current source procedure indicates:

- physical inventories occur at mid-month and EOM;
- SAIIT includes sales, adjustments, invoices, transfers, and inventory review;
- fiscal-year physical inventory is conducted at EOY;
- financial period close/posting is to occur within 5 days after FY end;
- EOM documents are submitted through the Portfolio monthly data folders in Teams.

EOY reuses the EOM framework but has extra evidence.

Current EOY additions identified:

- **Disinterested Party Memorandum**
- **final inventory / last page of inventory**
- related fiscal-year inventory evidence

EOY is therefore **not** simply “September EOM.”

Do not create a separate application. Build annual/EOY applicability into the same requirement engine.

EOY complete rules remain a backlog item.

---

# 11. EOM SUSPENSE / STATUS ENGINE

## Due model

Current operational rule:

- Initial EOM suspense = **5 calendar days after end of reporting month**
- Final call = **10th calendar day of following month**

Treat the 10th as a management rule unless separately validated as policy.

Store both nominal and effective dates:

```text
Nominal_Due_Date
Effective_Due_Date
Nominal_Final_Call_Date
Effective_Final_Call_Date
```

Recommended default non-duty-day behavior:

```text
Nominal date remains 5th / 10th
Effective action suspense rolls to next duty day
```

Keep this configurable.

## Status states

Recommended semantic flow:

```text
NOT_DUE
IN_PROGRESS
LATE
OVERDUE
RECEIVED_PENDING_QC
RETURNED
CORRECTION_REQUIRED
WRONG_DOCUMENT
ACCEPTED
NOT_APPLICABLE
NEEDS_CLASSIFICATION
SOURCE_MISSING
PENDING_REQUIREMENT_VALIDATION
```

## Visual mapping

```text
BLUE   = not due / submission window / informational
AMBER  = late after initial suspense but before final call
YELLOW = received / waiting on AFSVC QC
RED    = overdue / correction required / base action
GREEN  = accepted / complete
GRAY   = N/A / not required / disabled
```

Never rely on color alone.

---

# 12. TWO ON-TIME FACTS

Store both:

```text
Initial_Submitted_DateTime
Initial_Submission_On_Time

Current_Acceptable_Evidence_DateTime
Final_Evidence_On_Time
```

Example:

```text
Uploaded 8 Sep
Returned 9 Sep
Corrected 13 Sep
```

The system can represent:

- initial submission timeliness;
- final acceptable evidence timeliness.

User-facing language should be plain:

> Submitted Sep 8 — Initial submission recorded  
> Final accepted evidence Sep 13 — after suspense

Do not expose cryptic booleans to base users.

---

# 13. EXPECTED PACKAGE GENERATOR

Retain `EOM-01 Expected Package Generator`.

The expected rows must exist **before** documents arrive.

Example:

```text
LACKLAND | 2026-08 | 1119 | Expected
LACKLAND | 2026-08 | SF1080 | Expected
LACKLAND | 2026-08 | SAIIT | Expected
LACKLAND | 2026-08 | GPC | Expected
LACKLAND | 2026-08 | 1119-1 | Expected
```

Quarterly periods add 1038 where applicable.

This is what allows the system to distinguish:

- nothing submitted;
- not yet due;
- late;
- overdue;
- received;
- under review;
- accepted.

Do not generate Legacy EOM packages for Food 2.0, MAFFO, or Deployed/Field Feeding unless explicitly configured.

---

# 14. CORE BUSINESS DATA MODEL

## MF_EOM_Requirement

```text
Requirement_ID
Document_Code
Document_Name
Document_Category
Applicable_Model
Applicable_Facility_Type
Applicable_MAJCOM
Applicable_Contractor
Requirement_Scope
Frequency
Due_Day_Of_Month
Due_Offset_Days
Final_Call_Day
Required_Flag
QC_Required
Allowed_Extensions
Match_Priority
Authority_Status
Authority_Reference
Authority_Validated_By
Authority_Validated_Date
Active_From
Active_To
Active_Flag
Instructions
Sort_Order
```

## MF_EOM_Item

**Grain:** scope target × requirement × reporting period

```text
EOM_Item_ID
EOM_Item_Key
Portfolio_ID
Installation_ID
Facility_ID nullable
Contract_ID nullable
Reporting_Period
Fiscal_Year
Requirement_ID
Requirement_Scope
Applicability_Status
Required_Flag
Nominal_Due_Date
Effective_Due_Date
Nominal_Final_Call_Date
Effective_Final_Call_Date
Current_Submission_ID
Received_Flag
Initial_Submitted_DateTime
Initial_Submission_On_Time
Current_Acceptable_Evidence_DateTime
Final_Evidence_On_Time
Final_Status
Status_Code
Action_Owner_Type
Action_Required
Days_Late
Exception_Flag
Correction_Due
Last_Reconciled_DateTime
Source_System
```

Deterministic key example:

```text
2026-08|CREECH_AFB|REQ-001
```

## MF_EOM_Submission

**Grain:** one recognized file/version

```text
Submission_ID
EOM_Item_ID
Version_No
SharePoint_File_ID
SharePoint_Unique_ID
SharePoint_Item_ID
File_Name
File_Extension
File_URL
Source_Site_URL
Source_Library
Source_Path
Uploaded_By
Uploaded_DateTime
Submitted_On_Behalf_Of
Intake_Method
Classification_Status
Classification_Method
Classification_Confidence
Is_Current
Superseded_By
Automated_Validation_Status
QC_Status
QC_Verdict
QC_Reason
QC_By
QC_DateTime
QC_Comment
Correction_Due_Date
Final_Acceptance_Date
Record_Key
Source_System
```

Every corrected submission creates a new version.

---

# 15. QC / RETURN MODEL

AFSVC reviewers physically open the document in Teams/SharePoint or download/open it to verify the submission.

Primary decision model:

```text
ACCEPT
RETURN FOR CORRECTION
WRONG DOCUMENT
NOT APPLICABLE
```

Return reasons may include:

```text
Incomplete
Wrong reporting period
Wrong installation/facility
Missing pages/information
Wrong document
Other
```

Internally, returning verdicts may collapse to a parent state such as:

```text
RETURNED
```

but the reason must persist on the submission.

Base users must see the actionable reason in plain language.

Example:

```text
ACTION REQUIRED

SAIIT
Correction required

Reason:
Wrong reporting period

AFSVC comment:
The uploaded SAIIT reflects July. Submit August.

[ Submit correction ]
```

---

# 16. NOTIFICATIONS

R1 reliability first.

Pre-build notification hooks, but keep most optional.

Initial useful events:

```text
SUBMISSION_RECEIVED
CORRECTION_REQUIRED
CORRECTION_RESUBMITTED
```

Potential behavior:

- submission → Portfolio org box;
- status change/return → submitter;
- correction resubmission → reviewer/Portfolio org box.

Later:

```text
INITIAL_SUSPENSE_REMINDER
FINAL_CALL_REMINDER
OVERDUE_ESCALATION
PORTFOLIO_DAILY_DIGEST
```

Use configuration toggles.

Recommended `MF_Notification_Config`:

```text
Notification_Key
Enabled
Recipient_Type
Subject_Template
Body_Template
Minimum_Role
```

Do not derive email addresses from display names.

---

# 17. APP UX DIRECTION — IBM COGNOS + FLUENT 2

Primary design reference:

**IBM Cognos Analytics** for:

- workspace hierarchy;
- information density;
- rectangular geometry;
- restrained visual system;
- task-oriented top chrome;
- compact enterprise tables;
- filter/search bars;
- minimal decorative cards;
- strong working canvas.

Use **Microsoft Fluent 2 / Teams** for:

- controls;
- accessibility;
- focus states;
- familiar interaction behavior;
- implementation realism in Power Apps.

Do NOT make the app feel like:

- generic SharePoint;
- Power BI report;
- consumer SaaS;
- military-themed decorative site;
- card-heavy startup dashboard.

---

# 18. VISUAL DESIGN RULES

Preserve:

```text
Background: #FAF9F8
Surface: #FFFFFF
Primary text: #242424
Secondary: #616161
Border: #D1D1D1
Accent: #0F548C
```

Use accent blue only for:

- primary action;
- active navigation;
- selected controls;
- links;
- focus states.

Rules:

- 1px hairline borders
- 2px panel radius
- max 4px input/button radius
- no shadows
- no decorative gradients
- no large blue blocks except launch/prototype splash
- no pills
- compact rectangular status labels
- Fluent outline icons, not emoji
- tables are first-class controls
- large whitespace between sections, compact spacing within data regions

---

# 19. BASE USER NAVIGATION

Recommended:

```text
Home
My Package
Calendar
```

Do not expose enterprise/admin complexity.

## Base Home

Must answer in <5 seconds:

- what month;
- what is required;
- what is missing;
- what is accepted;
- what AFSVC returned;
- what the user must do next.

Example:

```text
LACKLAND AFB
August 2026 EOM

Legacy / APF
Portfolio 2

Initial suspense: 5 Sep
Final call: 10 Sep

AUGUST EOM PACKAGE

4 of 5 submitted
3 accepted · 1 awaiting AFSVC · 1 missing

[ Submit document ]
[ Open package ]
```

Sections:

```text
ACTION REQUIRED
WAITING ON AFSVC
COMPLETE
```

---

# 20. MY PACKAGE SCREEN

Dense Cognos-style table.

Columns:

```text
Requirement
Frequency
Suspense
Submitted
AFSVC status
Action
```

Rows use real Legacy requirements:

- 1119
- SF 1080
- SAIIT
- GPC Bank Statement
- 1119-1
- 1038 when quarterly

Filters:

```text
All
Action required
Under review
Complete
```

Avoid giant row heights.

---

# 21. SUBMIT DOCUMENT UX

Base submission should be achievable in <30 seconds.

Fields:

```text
Installation
Reporting period
Requirement
File
Optional note
```

Installation should default from authorized access context when only one is available.

Do not expose:

- Requirement_ID
- Portfolio_ID
- Facility_ID unless necessary
- SharePoint metadata
- source path
- classification fields

Power Apps is now the preferred structured submission front door for R1.

Passive Teams/SharePoint folder discovery remains an exception/recovery path, not the normal user workflow.

---

# 22. AFSVC NAVIGATION

Recommended:

```text
Overview
Review
Installations
Exceptions
Activity
Admin (authorized only)
```

## AFSVC Overview

Avoid floating cards.

Use full-width metric strip:

```text
ACCEPTED
AWAITING REVIEW
CORRECTIONS
OVERDUE
```

Below:

```text
Search
Portfolio
Status
Requirement
Reset filters
```

Then:

```text
NEEDS YOUR ATTENTION
```

Dense operational table.

---

# 23. INSTALLATION DIRECTORY / WORKSPACE

Use real QRG data.

Enterprise table:

```text
Installation
Portfolio
MAJCOM
Location
Feeding Type
Program
Facilities
Contract
Prime Vendor
EOM Status
```

Filters:

```text
Portfolio
MAJCOM
Feeding Type
Program Type
Contract Type
Prime Vendor
Status
```

Clicking opens:

```text
Installation
  ↓
Facility
  ↓
Requirement
  ↓
Submission/version
```

Example workspace header:

```text
CREECH AFB
Nevada · ACC · Portfolio X

Legacy
Program Type
Unit
Contract Type
Primary Vendor
```

Do not expose CUI that is unavailable in scrubbed builds.

---

# 24. REVIEW SCREEN

Two-column layout.

## Left — Evidence

- requirement;
- installation;
- reporting period;
- current version;
- submitted timestamp;
- Open in Teams;
- Download/Open;
- document preview/placeholder;
- version history;
- prior reviewer comments.

## Right — Decision

Sticky decision panel:

```text
Accept
Return for correction
Wrong document
Not applicable
```

Progressive disclosure.

Return fields only appear when needed:

```text
Reason
Comment
Correction due
```

Comment required for correction/wrong document.

---

# 25. CALENDAR

Operational deadline awareness only.

Highlight:

```text
End of reporting period
Initial suspense
Final call
Quarterly 1038 periods
```

Do not turn this into Outlook/event management.

Show:

```text
5 Sep 2026
Initial EOM suspense
5 documents due
1 remaining

[ View package ]
```

---

# 26. ADMIN / SYSTEM HEALTH

Do not use fake health widgets such as:

- database heartbeat;
- bot webhook;
- fake storage quota;
- fake authentication uptime.

Show actual app/configuration health:

```text
Requirements configuration
Installation registry completeness
Expected package generation
Duplicate expected items
Submission reconciliation
Unmatched/exception records
Notification configuration
Reporting period configuration
Security mapping
Expired temporary access
Missing environment variables
DEV/mock flags in PROD
Multiple current versions
Stale reconciliation
```

Separate:

```text
APPLICATION HEALTH
```

from:

```text
TENANT SECURITY VERIFICATION
```

Tenant-side items should say:

```text
Requires tenant admin verification
```

not fabricate “Healthy.”

---

# 27. POWER BI CANONICAL STATUS

Power BI consumes a flattened canonical table.

Recommended `MF_EOM_Status` grain:

Installation × facility/scope target × period × requirement.

Fields:

```text
Reporting_Period
Fiscal_Year
Portfolio_ID
Installation_ID
Installation_Name
Facility_ID
Facility_Name
Operating_Model
Contract_ID
Requirement_ID
Requirement_Name
Requirement_Scope
Required_Flag
Nominal_Due_Date
Effective_Due_Date
Received_Flag
Initial_Submitted_DateTime
Initial_Submission_On_Time
Current_Acceptable_Evidence_DateTime
Final_Evidence_On_Time
Version_No
QC_Status
Final_Status
Status_Code
Action_Owner_Type
Action_Required
Days_Late
Current_File_URL
```

Power BI does not reproduce operational workflow logic.

Use RLS aligned to app security.

---

# 28. POWER AUTOMATE FLOWS

## EOM-01 Expected Package Generator

- read active requirements;
- evaluate registry/model/scope;
- generate idempotent expected rows;
- never duplicate deterministic keys;
- flag unmapped/invalid registry records;
- do not generate Legacy package for inapplicable models.

## EOM-02 Submission / Intake

Primary R1 flow:

- Power Apps passes installation, period, requirement, file;
- validate authorization/context;
- save file in structured SharePoint library;
- create versioned submission;
- set `RECEIVED_PENDING_QC`;
- update current submission pointer;
- preserve prior versions;
- create audit event;
- trigger optional notification.

Exception/recovery intake may classify files from Teams/SharePoint, but is not the primary base-user path.

## EOM-03 Reconciliation

- compare expected items to current submissions;
- calculate due/late/overdue;
- update action owner;
- reconcile current version;
- refresh canonical status;
- detect anomalies;
- repair safe derived state;
- never silently discard unresolved records.

## EOM-04 Notifications

- feature-gated;
- submission notification;
- correction notification;
- later suspense reminders/digest/escalation.

---

# 29. VERSIONING

Never overwrite corrected evidence.

Example:

```text
EOM Item
├── Submission v1 → Returned
└── Submission v2 → Accepted / Current
```

Fields:

```text
Version_No
Is_Current
Superseded_By
Uploaded_By
Uploaded_DateTime
```

Normal users cannot hard-delete prior evidence.

---

# 30. .MIL / DoW / GOVERNMENT CLOUD SECURITY DIRECTIVE

The source artifact must be secure-by-default and import-ready, but import itself is **not** an ATO.

Target government cloud must be configured during deployment.

Supported deployment profiles:

```text
GCC_HIGH
DOD
```

Do not embed commercial-cloud runtime dependencies.

Use environment variables / connection references for:

```text
MF_CloudEnvironment
MF_SharePointSiteURL
MF_SubmissionLibrary
MF_RequirementList
MF_EOMItemList
MF_SubmissionList
MF_InstallationList
MF_FacilityList
MF_SecurityList
MF_PowerBIReportURL
```

If required configuration is missing:

```text
CONFIGURATION_REQUIRED
```

and writes must be disabled.

---

# 31. NO SECRETS / NO CUI IN SOURCE

Release package must not contain:

```text
passwords
tokens
client secrets
API keys
private keys
CAC identifiers
EDIPI
production accounting strings
GPC account numbers
protected DODAAC/DODAAD data
fund cites
contract-sensitive values
CUI fixtures
```

Use blank nullable extension fields until authorized `.mil` enrichment.

---

# 32. CUI-READY, NOT CUI-BY-DEFAULT

Do not assume all Mission Feeding data is CUI.

Recommended fields:

```text
Information_Protection_Level
CUI_Flag
CUI_Category
CUI_Banner_Marking
Limited_Dissemination_Control
CUI_Authority
CUI_Designation_Source
CUI_Designated_By
CUI_Designation_Date
```

Default:

```text
CUI_Flag = false
```

Only enable after authorized determination.

Do not show CUI-only fields in scrubbed Figma/dev builds.

---

# 33. CONNECTOR DISCIPLINE

R1 should use minimum approved native services.

Preferred:

```text
Power Apps
Power Automate
SharePoint Online
Microsoft 365 government identity
approved Outlook/Users connector if locally authorized
Power BI government
```

Prohibited by default:

```text
HTTP
HTTP with Entra ID
custom connectors
consumer storage
third-party SaaS
external webhooks
public APIs
external telemetry
external AI
```

Tenant DLP remains a deployment-side security control.

---

# 34. FAIL CLOSED

If authorization cannot resolve:

```text
NO ACCESS
```

not broad access.

If user scope cannot resolve:

```text
ACCESS_SCOPE_UNRESOLVED
```

If configuration is missing:

```text
CONFIGURATION_REQUIRED
```

If submission cannot be confirmed:

```text
SUBMISSION_NOT_CONFIRMED
```

Never treat a security or processing failure as success.

---

# 35. UI FILTERS ARE NOT SECURITY

Power Apps visibility/filtering must not be treated as the data-security boundary.

Production deployment requires:

- SharePoint/library/list permissions;
- Entra/security groups;
- authorized environment access;
- app-layer RBAC;
- server-side scoped queries.

Do not preload all enterprise submissions to a base user and locally filter afterward.

---

# 36. APPLICATION AUDIT

Maintain `MF_App_Event_Log`.

Recommended fields:

```text
Event_ID
Event_DateTime
User_UPN
Role
Portfolio_ID
Installation_ID
Object_Type
Record_ID
Event_Type
Previous_Status
New_Status
Result
Correlation_ID
App_Version
Flow_Version
Error_Code
Error_Message
```

Important events:

```text
SUBMISSION_CREATED
SUBMISSION_CORRECTED
QC_ACCEPTED
QC_RETURNED
QC_WRONG_DOCUMENT
STATUS_CHANGED
ACCESS_REQUESTED
ACCESS_GRANTED
ACCESS_REVOKED
ADMIN_REQUIREMENT_CHANGED
CONFIG_CHANGED
```

Do not log document content unnecessarily.

---

# 37. ERROR HANDLING

User-facing errors must be plain language.

Example:

```text
We couldn't save your submission.
No data was changed.
Reference: MF-20260831-A7F4
```

Do not expose raw HTTP errors, tokens, GUIDs, or connector diagnostics.

Store technical detail in controlled logs with a correlation ID.

---

# 38. PRODUCTION FEATURE FLAGS

Required defaults in PROD:

```text
DeveloperTools = false
RoleSimulator = false
DebugPanel = false
MockData = false
SyntheticUsers = false
BypassSecurity = false
AllowManualIdentity = false
ShowHiddenRecords = false
EnableAIBuilder = false
EnableGenerativeAI = false
EnableExternalAI = false
```

Support:

```text
MaintenanceMode
ReadOnlyMode
ApplicationEnabled
SubmissionEnabled
ReviewEnabled
```

This allows kill-switch/read-only behavior without editing source.

---

# 39. RECORDS / RETENTION

Do not implement arbitrary hard deletes or short retention.

Treat EOM/EOY submissions, QC decisions, correction history, and audit events as records subject to government records-management review.

Normal users cannot hard-delete evidence.

Use:

```text
Active
Superseded
Returned
Rejected
Retired
```

rather than destructive deletion.

---

# 40. SECTION 508 / ACCESSIBILITY

Release gate:

- keyboard-only navigation;
- logical focus order;
- meaningful labels;
- screen reader support;
- no color-only status;
- sufficient contrast;
- accessible upload;
- visible focus;
- accessible validation errors;
- responsive zoom;
- native Power Apps controls where possible.

Target desktop first:

```text
1440 × 1024 Teams desktop
1024
768
```

Below ~800px:

- tables become record cards;
- review becomes one column;
- filters wrap;
- metric strip stacks;
- avoid horizontal scrolling for business tables.

---

# 41. SOURCE CONTROL / SOLUTION STRUCTURE

Target:

```text
MissionFeedingOperations/
│
├── solution/
│   └── MissionFeedingOperations/
│
├── canvas-app/
│   ├── screens/
│   ├── components/
│   ├── formulas/
│   └── data-sources/
│
├── flows/
│   ├── EOM01-ExpectedPackage/
│   ├── EOM02-Submission/
│   ├── EOM03-Reconciliation/
│   └── EOM04-Notifications/
│
├── configuration/
│   ├── installations.csv
│   ├── facilities.csv
│   ├── requirements.csv
│   ├── portfolio.csv
│   ├── feature-flags.csv
│   ├── notification-config.csv
│   └── qrg-data-quality.csv
│
├── security/
│   ├── security-manifest.yaml
│   ├── connector-allowlist.yaml
│   ├── role-matrix.csv
│   ├── cui-schema.md
│   └── release-security-checklist.md
│
├── deployment/
│   ├── pre-import-checklist.md
│   ├── import-runbook.md
│   ├── post-import-checklist.md
│   ├── gcc-high-profile.md
│   └── dod-profile.md
│
├── docs/
│   ├── architecture.md
│   ├── data-flow.md
│   ├── qrg-registry-mapping.md
│   ├── data-classification.md
│   ├── records-management.md
│   ├── privacy-assessment.md
│   ├── accessibility-test.md
│   └── rmf/
│       ├── system-description.md
│       ├── security-control-mapping.md
│       ├── external-connections.md
│       ├── test-plan.md
│       ├── known-risks.md
│       └── continuous-monitoring.md
│
├── tests/
│   ├── authorization-tests.md
│   ├── security-tests.md
│   ├── accessibility-tests.md
│   └── regression-tests.md
│
├── CHANGELOG.md
├── RELEASE_NOTES.md
├── ROLLBACK.md
└── README.md
```

---

# 42. IMPORT / DEPLOYMENT SECURITY MANIFEST

Generate:

`deployment/security-manifest.yaml`

Suggested:

```yaml
application:
  name: MissionFeedingOperations
  contains_cui: false
  contains_secrets: false

cloud:
  supported:
    - GCC_HIGH
    - DOD
  commercial_cloud_supported: false

security:
  authentication: ENTRA_GOVERNMENT
  local_authentication: prohibited
  default_access: deny
  scope_model: installation_and_portfolio
  role_simulator_prod: disabled

connectors:
  allowed:
    - SharePoint
  conditional:
    - Office365Users
    - Office365Outlook
    - PowerBI
  prohibited:
    - HTTP
    - CustomConnector
    - ConsumerConnectors
    - ExternalAI

cui:
  framework_enabled: true
  default_cui_flag: false
  embedded_cui_data: false

telemetry:
  external_telemetry: false

release:
  debug_mode: false
  mock_data: false
  bypass_security: false
```

---

# 43. RELEASE-BLOCKING CONDITIONS

Production export must fail or be blocked if:

```text
commercial-only endpoint embedded
secret/credential detected
external HTTP/custom connector used
mock identity enabled
role override enabled
security bypass exists
PROD defaults to DEV
user can assign own role
user can assign own installation access
user can modify audit author
user can modify reviewer identity
normal user can hard-delete evidence
CUI/operational data exists in development fixtures
anonymous/public sharing is created
production URL is hardcoded
app version missing
rollback documentation missing
security tests fail
```

---

# 44. PRE-IMPORT CHECKLIST

```text
Confirm target cloud: GCC High or DoD
Confirm approved Power Platform environment
Confirm functional owner
Confirm cybersecurity/RMF path
Confirm authorized connectors
Confirm DLP policy
Confirm tenant isolation
Confirm SharePoint site/library
Confirm SharePoint permissions
Confirm Entra/security groups
Confirm records-retention determination
Confirm privacy determination
Confirm CUI determination
Confirm Section 508 testing
```

---

# 45. DURING IMPORT

```text
Set MF_CloudEnvironment
Bind SharePoint connections
Set SharePoint environment variables
Bind Power Automate connection references
Configure Power BI government URL
Import scrubbed registry
Populate authorized DoDAAC/DODAAD/CUI fields only on .mil side
Configure MF_User_Access
Disable DEV/TEST flags
Verify PROD configuration
```

---

# 46. POST-IMPORT SECURITY TESTS

Must verify:

```text
Base user sees only authorized installation
Base user cannot deep-link into another installation
Base user cannot modify reviewer fields
Base user cannot directly set accepted status
Reviewer cannot edit Admin config without authorization
App fails closed when user mapping is missing
SharePoint permissions independently block unauthorized access
No anonymous sharing is created
All writes produce audit events
Corrections preserve prior version
Flow failures are logged
Unauthorized connectors fail
Notifications expose minimal information
Power BI RLS works
Accessibility passes
```

---

# 47. TENANT-SIDE ITEMS THAT CANNOT BE “BAKED INTO” THE IMPORT

The app can be ready for these, but the `.mil` environment must configure them:

- DLP enforcement
- connector approval
- tenant isolation
- Entra / Conditional Access
- SharePoint permissions
- Purview auditing
- network allowlisting
- CMK/key configuration
- sensitivity labels
- retention policies
- RMF registration
- security-control assessment
- ATO/cATO authorization
- local STIG applicability

Root README must state:

> **IMPORT SUCCESS != AUTHORIZATION TO OPERATE**

---

# 48. RMF / SECURITY DOCUMENTATION

Maintain `/docs/rmf/`.

At minimum:

```text
system-description.md
data-flow.md
architecture.md
external-connections.md
security-control-mapping.md
roles-responsibilities.md
information-types.md
data-classification.md
configuration-baseline.md
test-plan.md
test-results.md
known-risks.md
poam-template.md
continuous-monitoring.md
```

Map design decisions to at least:

- AC — Access Control
- AU — Audit & Accountability
- CM — Configuration Management
- IA — Identification & Authentication
- SC — System & Communications Protection
- SI — System & Information Integrity
- SA — System & Services Acquisition
- RA — Risk Assessment
- CP — Contingency Planning
- PL — Planning
- PT — Privacy / PII

---

# 49. POWER APPS IMPLEMENTATION STANDARDS

Use:

- modern controls;
- auto-layout containers;
- reusable components;
- `With()`;
- named formulas / App.Formulas;
- delegable filters;
- environment variables;
- explicit error handling;
- centralized status evaluation;
- centralized authorization functions.

Avoid:

- giant `App.OnStart`;
- whole-enterprise collections;
- nested `ForAll`;
- cross-screen control dependencies;
- hardcoded URLs;
- duplicated status logic;
- inline one-off styling.

Suggested components:

```text
cmpTopBar
cmpTaskNav
cmpReportingPeriod
cmpStatusBadge
cmpMetricStrip
cmpFilterToolbar
cmpRequirementRow
cmpUploadTarget
cmpCorrectionTicket
cmpVersionRow
cmpEmptyState
cmpHealthRow
```

Suggested screens:

```text
scrHome
scrMyPackage
scrSubmit
scrCalendar
scrOverview
scrReview
scrInstallations
scrInstallation
scrExceptions
scrActivity
scrAdmin
```

---

# 50. DATA / SHAREPOINT SCALE

Design for delegation from day one.

Index:

```text
Reporting_Period
Portfolio_ID
Installation_ID
Facility_ID
Requirement_ID
Final_Status
Is_Current
EOM_Item_Key
```

Do not preload all 89/107+ installation enterprise data into base-user memory.

Base-user queries must server-filter by authorized installation/period first.

---

# 51. CURRENT PILOT / R1 STRATEGY

Do not block on a perfect enterprise master.

Use `MF_Installation` and `MF_Facility` as the operational registry for R1.

Populate and validate a pilot Legacy subset first.

Expected-package generation must be enabled only for locations that pass minimum registry validation.

Recommended pilot coverage:

- Legacy/APF
- one installation with one facility
- one installation with multiple facilities
- multiple Portfolios
- normal submission
- correction/versioning
- late/overdue
- quarterly 1038
- access control
- reviewer QC
- unmatched/exception recovery if included

---

# 52. FOOD 2.0 BACKLOG

Food 2.0 records remain in the registry, but do not apply Legacy EOM rules.

TODO:

- upload authoritative Food 2.0 handbook;
- define Aramark/Sodexo requirements;
- account for October Portfolio 1–4 reorganization;
- define Food 2.0 EOM requirement matrix;
- define contract/installation/facility scope;
- activate behind feature flag only after validation.

---

# 53. EOY BACKLOG

EOY is partially defined.

Current known additions:

- Disinterested Party Memorandum
- final inventory / last page of inventory

TODO:

- confirm complete EOY required-document set;
- define EOY QC checklist;
- confirm whether all count sheets must be submitted/retained;
- define annual/fiscal closeout status logic;
- implement annual frequency/applicability in same requirement engine.

Do not build a separate EOY app.

---

# 54. FUTURE ENTERPRISE MODULES

After EOM stabilizes:

- SAIIT automation/recovery
- FMAT
- Go for Green
- ServSafe/training
- equipment/maintenance/calibration
- contracts
- Five-Year Plan
- Food 2.0 operational modules
- enterprise Power BI expansion

Do not expand R1 prematurely.

---

# 55. CURRENT SUCCESS STATE

```text
Base user opens Mission Feeding Operations
        ↓
App resolves authorized installation
        ↓
User selects reporting period
        ↓
Expected EOM package already exists
        ↓
User sees what is due / late / returned / accepted
        ↓
User uploads a requirement
        ↓
Power Automate stores/version-controls evidence
        ↓
Item becomes RECEIVED_PENDING_QC
        ↓
AFSVC review queue updates
        ↓
Reviewer opens evidence
        ↓
Accept / Return / Wrong Document / N/A
        ↓
Base package updates
        ↓
Correction creates next version if needed
        ↓
Canonical MF_EOM_Status updates
        ↓
Power BI COP updates
```

---

# 56. FINAL CLAUDE CODE EXECUTION DIRECTIVE

Build **MissionFeedingOperations** as a source-controlled, importable Power Platform solution whose R1 is a Legacy/APF EOM submission and QC application.

Use the real scrubbed QRG to seed installation/facility context. Do not use fake/demo enterprise structure except where clearly labeled as test fixtures.

Use IBM Cognos Analytics as the UX density/workspace benchmark and Fluent 2 / Teams as the control/accessibility benchmark.

Base users must have a dramatically simpler experience than AFSVC users.

Power Apps is the structured submission front door for R1. SharePoint/Teams remains the evidence repository. Power Automate handles expected-package generation, versioned storage, reconciliation, and notification hooks. Power BI consumes canonical status.

Implement real role/security boundaries. Fail closed. Do not treat UI filters as data security. Do not embed CUI, secrets, DoDAAC/DODAAD, production URLs, commercial-cloud dependencies, external HTTP/custom connectors, or external AI.

All environment-specific government configuration must be supplied after import through environment variables, connection references, authorized identity, SharePoint permissions, tenant policy, and `.mil`-side enrichment.

Generate the solution, source files, configuration seeds, QRG import/normalization pipeline, flow definitions, Power Fx/components, security manifest, deployment runbooks, RMF-supporting documentation, accessibility/security/regression tests, changelog, rollback procedure, and a production-candidate distribution package where tooling allows.

Do not claim import equals authorization to operate.

---

# 57. AUTHORITATIVE BUILD PRIORITY

1. Canonical scrubbed QRG registry import.
2. Legacy requirement seed/configuration.
3. User access/security model.
4. Expected-package generation.
5. Base submission flow.
6. Base Home / My Package UX.
7. AFSVC Review workflow.
8. Reconciliation/status engine.
9. Installation workspace.
10. Admin/data health.
11. Notification hooks.
12. Power BI canonical status.
13. Government import hardening.
14. Accessibility/security/regression validation.
15. Food 2.0 / EOY backlog only after R1 stabilizes.

---

# 58. REFERENCE / AUTHORITY NOTES

Current project reference artifacts discussed in the build history include:

- Mission Feeding Operations master handoff
- EOM/EOY procedures deck
- scrubbed Mission Feeding QRG CSV
- Figma prototype / IBM Cognos-inspired redesign direction
- prior Power Automate central-intake design
- Power Apps build framework
- Mission Feeding COP / Power BI architecture notes

Where older artifacts conflict with this handoff, **this handoff controls unless a newer authoritative procedure or explicit project decision supersedes it.**
