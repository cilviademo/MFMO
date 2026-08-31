> **ARCHIVED 31 Aug 2026. Superseded by
> `docs/handoffs/MASTER_HANDOFF_2026-08-31.md`.**
>
> The later document is roughly twice the length, carries the Figma UX and
> .mil/DoW security material this one does not, and states in its own header
> that it "supersedes earlier assumptions where conflicts exist".
>
> Kept because several decisions in the live tree are still traceable to
> sections here, and `docs/handoffs/RECONCILIATION.md` cites it by section.

# MISSION FEEDING OPERATIONS — MASTER HANDOFF
## EOM Document Submission, Power Apps, Power Automate, SharePoint/Teams, Power BI COP
**Status:** Consolidated project handoff  
**Date:** 31 Aug 2026  
**Primary objective:** Build a government-compatible, source-controlled Mission Feeding Operations solution whose first production module automates End-of-Month (EOM) document requirements, discovery, reconciliation, versioning, QC, exceptions, and COP/status visualization.

---

# 1. BLUF

Build **Mission Feeding Operations** as a lean Microsoft Power Platform operational system:

**Teams / SharePoint = document repository and front door**  
**Power Apps = human workflow / action interface**  
**Power Automate = background discovery, reconciliation, expected-row generation, notifications**  
**Power BI = leadership COP / visualization**  
**SharePoint Lists = configuration, workflow state, security, audit/status data**

The MVP is **EOM document management only**. Do not expand v1 into SAIIT, FMAT, training, equipment, contracts, Five-Year Plan, etc.; however, architect the shell so those modules can be added later.

The system must not depend on a fixed file-naming convention. Users will normally upload EOM documents into the designated FY/period location in the applicable Mission Feeding Portfolio Teams/SharePoint folder. The system must discover those files, reconcile them against expected requirements, classify them using available context/evidence, and route uncertainty to a small **Needs Classification** queue.

The design must support facility-, installation-, and contract-level requirements; facility-level operating models and security; full document version history; Power BI-ready status output; government-cloud constraints; accessibility; and source-controlled deployment.

---

# 2. PRIME DIRECTIVES

1. Do not build another giant dashboard or monolithic SharePoint List.
2. Do not make Power Apps the required document repository.
3. Do not make filename conventions authoritative.
4. Do not silently ignore unmatched files.
5. Do not hard-code Legacy/Food 2.0/MAFFO requirements in app formulas.
6. Do not hard-code “due by the 10th” until authoritative guidance validates it.
7. Do not assume Food 2.0 requirements equal Legacy requirements.
8. Do not let Power BI reconstruct operational business logic from raw submissions.
9. Do not overwrite corrected documents; retain every version.
10. Do not require AI Builder, Dataverse, Graph, custom connectors, PCF, premium pipelines, or multiple Power Platform environments for MVP.
11. Do not expose users to data outside their authorized facility/installation/portfolio scope through rollups.
12. Unresolved requirements remain configurable and cannot create adverse status unless deliberately approved as a management rule.

---

# 3. TARGET ARCHITECTURE

```text
Mission Feeding Portfolio Teams / SharePoint
                |
                |-- Portfolio FY / EOM folders
                |-- Normal user document uploads
                |
                v
        Document Discovery / Intake
                |
                |-- source folder context
                |-- SharePoint metadata
                |-- file type
                |-- deterministic content/structure
                |-- optional AI Builder if authorized
                |-- filename only as weak evidence
                |
                v
         Classification Engine
          |             |
          | confident   | uncertain
          v             v
   Expected EOM Item   Needs Classification
          |
          v
   Versioned Submission
          |
          v
       Portfolio QC
          |
          v
 Canonical MF_EOM_Status
          |
     +----+----+
     |         |
     v         v
 Power Apps   Power BI
 Action UX    COP / analytics
```

Power Apps should feel like an operational workbench: **what arrived, what is missing, what needs my action, what is waiting on someone else, and what is complete**.

---

# 4. SOURCE DOCUMENT LOCATION / INTAKE

EOM documents will be uploaded into a specified folder for the FY in the applicable Mission Feeding Portfolio Teams folder.

Exact physical folder structure still needs final mapping, but support patterns such as:

```text
Portfolio
└── EOM
    └── FY2027
        └── 2026-10
            └── Lackland
                └── Bldg-1234-DFAC
                    └── files
```

Prefer structured folder context because Portfolio, location, FY and reporting period can be inferred before document classification.

**Important architecture finding:** if SharePoint native Rules copy files into a flat central File Intake library, the destination trigger loses original Portfolio path context. Do not resolve installation using the central destination `{FullPath}`. Preserve origin through destination subfolders/metadata, or use small source intake flows that capture source context before copying/stamping the central file.

A central intake library is optional. Monitoring each approved Portfolio library directly is valid.

---

# 5. FILE NAMING / CLASSIFICATION

Naming conventions are subject to change. **Filename is never authoritative.**

Classification evidence priority:

1. Approved source library/folder context.
2. SharePoint metadata.
3. Installation/facility/contract mapping.
4. Reporting-period context.
5. File extension/type.
6. Known workbook/PDF structure.
7. Known internal text, headings, cells, or form signatures.
8. Filename tokens/aliases as supplemental evidence only.
9. Optional AI Builder/document processing if approved.
10. Human classification if confidence is insufficient.

Suggested outputs:

```text
Classification_Status
Classification_Method
Classification_Confidence
Suggested_Installation_ID
Suggested_Facility_ID
Suggested_Requirement_ID
Suggested_Reporting_Period
Classification_Reason
```

Use deterministic classification as MVP baseline. AI Builder is optional and feature-flagged.

---

# 6. REQUIREMENT ENGINE

Requirements are configuration/data, not code.

Supported `Requirement_Scope` values:

```text
Facility
Installation
Contract
```

Reserve `Portfolio` for future use.

`Operating_Model` must live at **facility grain** because an installation may contain facilities using different models.

```text
Facility
→ Operating Model
→ Facility Type
→ Active Requirement
→ Requirement Scope
→ Expected EOM Item
```

- Facility scope → one expected row per applicable facility.
- Installation scope → one installation row; `Facility_ID = null`.
- Contract scope → one contract row; `Contract_ID` populated; `Facility_ID` nullable.

---

# 7. WORKING REQUIREMENT MATRIX

| Requirement | Working Scope | Current Treatment |
|---|---|---|
| 1119 / Daily Feeding Summary | Facility | Strong facility-grain assumption |
| 1119-1 | Facility | Working facility-grain assumption; validate applicability |
| SIK Bill | Installation or Facility | Scope requires validation |
| SF 1080 | Installation or Facility | Applicability/scope requires validation |
| SAIIT | Facility | Facility accountability assumption |
| DAF Form 79 | Validate | Configurable |
| AF/DAF 1038 | Validate | Scope/frequency configurable |
| Food 2.0 contractor invoice/support | Contract / Installation / Facility | Do not force facility grain |
| Five-Year Plan | Installation | Future module |
| FMAT evidence | Facility + possible installation findings | Future module |
| Go for Green assessment | Facility | Future module |
| ServSafe/training compliance | Facility rollup | Future module |

Known verified EOM baseline from earlier source material: Monthly Calendar; Field Feeding Summary 1119; Food Service Form 1119-1; SIK Bills / financial reporting support. SF 1080 and several other candidates remain unverified.

Every requirement needs `Authority_Status`: `VERIFIED`, `MANAGEMENT_RULE`, `UNVERIFIED`, or `RETIRED`.

---

# 8. CORE DATA MODEL

## MF_Installation
`Installation_ID, Installation_Name, Portfolio_ID, Active_Flag`

## MF_Facility
`Facility_ID, Installation_ID, Facility_Name, Facility_Type, Operating_Model, Contract_ID, Active_Flag`

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
Required_Flag
QC_Required
Filename_Primary_Token
Filename_Aliases
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

Filename fields are hints only.

## MF_EOM_Item

**Grain: scope target × requirement × reporting period.** Persistent expected obligation/checklist row.

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
Due_Date
Grace_Date
Current_Submission_ID
Received_Flag
Received_Date
On_Time_Flag
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

Deterministic key example: `2026-10|FAC-1234|REQ-001`.

## MF_EOM_Submission

**Grain: one recognized file/version.**

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
QC_By
QC_DateTime
QC_Comment
Correction_Due_Date
Final_Acceptance_Date
Record_Key
Source_System
```

## MF_EOM_Unmatched_File

```text
Unmatched_ID
File_Name
File_URL
Source_Path
Portfolio_ID
Fiscal_Year
Discovered_DateTime
Uploaded_By
Suggested_Installation_ID
Suggested_Facility_ID
Suggested_Document_Code
Suggested_Reporting_Period
Match_Confidence
Reason
Resolution_Status
Resolved_Submission_ID
Alias_Added_Flag
```

## MF_Document_Location

```text
Location_ID
Source_Site_URL
Source_Library
Source_Folder_Path
Portfolio_ID
Installation_ID
Facility_ID
Mission_Feeding_Model
Domain
Active_Flag
```

## MF_Security_Mapping

```text
User_UPN
Role
Scope_Type
Portfolio_ID
Installation_ID
Facility_ID
Developer_Flag
Tester_Flag
Admin_Flag
Active_Flag
```

Scopes: Facility, Installation, Portfolio, Enterprise.

## MF_App_Config

```text
Config_Key
Config_Value
Config_Type
Description
Admin_Only
Active
```

Examples: `CurrentFiscalYear`, `OpenReportingPeriod`, `MaintenanceMode`, `ReadOnlyMode`, `EnableAIBuilder`, `RequireQC`, `AppVersion`, `PowerBIReportURL`.

## MF_Feature_Flags

`Feature_Key, Feature_Name, Enabled_Prod, Enabled_Testers, Minimum_Role, Effective_Date, Notes`

## MF_App_Event_Log

```text
Event_DateTime
User_UPN
Role
Portfolio_ID
Installation_ID
Facility_ID
Event_Type
Record_ID
Result
Error_Code
Error_Message
App_Version
```

Log meaningful events, not every click.

---

# 9. VERSIONING

All versions are retained. Nothing is overwritten or deleted.

```text
EOM_Item
├── Submission v1 → Correction Required
└── Submission v2 → Accepted / Current
```

Version fields: `Version_No, Is_Current, Superseded_By, Uploaded_By, Uploaded_DateTime`.

QC applies to the current version; prior versions and comments remain visible.

---

# 10. STATUS ENGINE

Do not collapse semantic status and visual color into one field.

Store:

```text
Final_Status
Status_Code
Action_Owner_Type
Action_Required
```

Semantic statuses:

```text
NOT_APPLICABLE
NOT_DUE
PENDING_REQUIREMENT_VALIDATION
IN_PROGRESS
MISSING
OVERDUE
RECEIVED_PENDING_QC
CORRECTION_REQUIRED
WRONG_DOCUMENT
ACCEPTED
SOURCE_MISSING
NEEDS_CLASSIFICATION
```

Visual codes:

```text
0 = Gray / N-A / disabled
1 = Red / missing / overdue / adverse action
2 = Yellow / review / correction / ambiguity
3 = Green / accepted
4 = Blue / not due / in progress / informational
```

Submission-level QC does not directly equal parent item status.

Action ownership examples:
- OVERDUE → Facility, actionable.
- RECEIVED_PENDING_QC → PortfolioManager, actionable.
- CORRECTION_REQUIRED → Facility, actionable.
- ACCEPTED → None.

“My Work” filters by action ownership, not merely color.

---

# 11. PACKAGE ROLLUPS

Roll up Requirement → Facility Package → Installation Package → Portfolio.

Semantic logic:

```text
if any applicable required item is OVERDUE/MISSING:
    ACTION_REQUIRED
else if any is CORRECTION_REQUIRED:
    ACTION_REQUIRED
else if any is RECEIVED_PENDING_QC:
    IN_REVIEW
else if all currently applicable required items are ACCEPTED:
    COMPLETE
else if future/not-due requirements remain:
    IN_PROGRESS
else:
    NOT_APPLICABLE
```

Installation rollup includes facility packages plus installation- and applicable contract-level requirements.

Apply security **before** calculating/displaying user-visible rollups.

---

# 12. POWER BI CANONICAL STATUS TABLE

Create `MF_EOM_Status` at Installation × Facility/Scope Target × Period × Requirement grain.

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
Due_Date
Received_Flag
Received_DateTime
Version_No
QC_Status
Final_Status
Status_Code
Action_Owner_Type
Action_Required
Days_Late
On_Time_Flag
Current_File_URL
```

Power BI consumes this table and does not reproduce workflow logic.

COP: period selector, complete/missing/overdue/awaiting QC/correction/unmatched/on-time KPIs; Installation → Facility → Requirement matrix; conditional formatting from `Status_Code`; evidence links; RLS aligned with app security.

---

# 13. POWER AUTOMATE FLOWS

## EOM-01 Expected Package Generator
- read active requirements;
- evaluate facility model/type/scope;
- generate idempotent expected items;
- flag facilities with no applicable requirement set.

## EOM-02 Document Discovery / Intake / Classification
- capture source context;
- resolve location/period;
- classify;
- match expected item;
- create new submission version;
- supersede prior current version;
- otherwise create unmatched record;
- never silently ignore.

## EOM-03 Reconciliation
- expected vs current submissions;
- received/on-time/days-late/final status/action owner;
- anomaly detection;
- safe derived-state repair;
- canonical status refresh/update.

## EOM-04 Notifications / Escalation
- notify actionable owners only;
- missing/overdue → responsible location;
- pending QC → reviewers;
- corrections → submitters;
- configurable cadence; avoid spam.

Human QC occurs in Power Apps.

---

# 14. POWER APPS UX — FINAL DIRECTION

The app should not feel like an administrative SharePoint tracker.

### Facility user
`Home | My Package`

### Installation MFM/accountant
`Home | Submissions | Installations | Activity` plus secondary `Submit on behalf`.

### Portfolio Manager
`Home | Review | Installations | Exceptions | Activity`

### Admin
`Home | Review | Installations | Exceptions | Activity | Admin`

Admin: Requirements, Facilities, Security, Configuration, System Health.

---

# 15. HOME — ROLE AWARE

Home answers: **What do I need to do?**

Facility example:

```text
Bldg 1234 DFAC
August 2026

ACTION NEEDED
1119-1 — Overdue since Sep 10

WAITING ON AFSVC
SAIIT — Submitted Sep 11

RECENTLY ACCEPTED
1119 — Accepted Sep 6
```

Portfolio example:

```text
PORTFOLIO 3
August 2026

28 / 31 facilities complete
7 awaiting review
3 corrections required
2 overdue
1 unclassified

MY REVIEW QUEUE
...
```

---

# 16. GLOBAL REPORTING PERIOD

Use one app-level reporting-period selector. Do not hard-code August 2026 throughout screens.

Prior-period browsing should primarily use this selector rather than a separate history screen.

---

# 17. SUBMISSIONS / MY PACKAGE

Normal intake occurs in Teams/SharePoint. Demote the prototype's primary `Upload` tab.

Facility package:

```text
AUGUST EOM PACKAGE
3 of 4 complete

1119       Accepted
1119-1     Accepted
SAIIT      Pending review
SIK        Installation-level

[ Open EOM Folder ]
```

Manual/on-behalf registration is an exception path for emailed/recovery documents.

---

# 18. INSTALLATION WORKSPACE

Use drill-through instead of vertically rendering all facilities/requirements:

`Portfolio → Installation → Facility → Requirement → Submission/version`

Provide search/filter and facility package summaries.

---

# 19. REVIEW UX

Document-centric review. Show current file, location, period, requirement, due date, submitter, version history, prior comments, and open-document action.

Decisions:
- Accept.
- Return for correction.
- Wrong document.
- Not applicable.

Progressive disclosure:
- correction suspense only for Correction Required;
- comment required for Correction/Wrong Document;
- consider reason/authority for N/A.

---

# 20. NEEDS CLASSIFICATION / EXCEPTIONS

Confidence-first UX:

```text
Creech Aug Financials.xlsx

We think this belongs to:
Creech                High confidence
Possible document:
SIK Bill              Medium confidence
Reporting period:
August 2026           High confidence

[ Confirm ] [ Change classification ] [ Not an EOM document ]
```

Only expose full cascading selectors when needed.

`Installation → Facility filtered to installation → Requirement filtered by model/type/scope → Period`.

---

# 21. ACTIVITY / AUDIT

Rename History to Activity. Filters: All, Uploads, Reviews, Corrections, Classifications, System.

Version history stays with each requirement/submission.

---

# 22. ADMIN / SYSTEM HEALTH

Keep internal authority/governance details primarily in Admin.

System Health should show configuration, automation, and data integrity such as unmapped facilities, missing requirement sets, stale reconciliation, unmatched files, failed flows, duplicate current versions, and expected-package generation status.

---

# 23. UX / VISUAL DESIGN

Use Fluent 2/native modern controls, responsive auto-layout containers, restrained Microsoft 365/Teams visual language, limited cards, clear hierarchy, plain-language labels, and accessible status badges.

Status visual language:
- Green = Accepted / Complete.
- Amber = Pending review / Correction.
- Red = Missing / Overdue.
- Blue = Not due / In progress / informational.
- Gray = N/A / disabled.

Never rely on color alone. On narrow Teams/mobile widths, use record cards rather than merely hiding table columns.

---

# 24. ACCESSIBILITY / SECTION 508

Acceptance gate:
- keyboard-only navigation;
- logical focus order;
- meaningful labels;
- screen-reader support;
- sufficient contrast;
- no color-only status;
- accessible errors/forms/document links;
- responsive zoom;
- native controls where possible;
- reasonable target sizes.

Use Power Apps Accessibility Checker plus manual testing.

---

# 25. CLEAN POWER FX / IMPLEMENTATION STANDARDS

Preserve domain boundaries: configuration, domain rules, security, submission/version services, classification, audit/telemetry, UI/components, app state.

Use one authoritative status evaluator returning semantic state, color code, label, action owner, and action requirement.

Prefer `With()`, named formulas/App.Formulas, delegable filters, reusable components, environment variables/configuration, and explicit error handling.

Avoid giant App.OnStart, whole-list collections, nested ForAll, cross-screen control references, hard-coded URLs, duplicated business logic, and one-off styling.

Suggested names: `scrHome`, `scrMyPackage`, `scrSubmissions`, `scrInstallation`, `scrReview`, `scrExceptions`, `scrActivity`, `scrAdmin`, `cmpStatusBadge`, `cmpEOMItem`, `cmpMetricCard`, etc.

---

# 26. SHAREPOINT / SCALE

Design for delegation from day one. Server-filter by period/portfolio/installation/facility/requirement/status/current version.

Index commonly filtered columns:
`Reporting_Period, Portfolio_ID, Installation_ID, Facility_ID, Requirement_ID, Final_Status, Is_Current, EOM_Item_Key`.

Use deterministic keys for idempotency/duplicate prevention.

---

# 27. ERROR HANDLING

Every operation needs loading, success, failure, and exception/retry paths.

Classification states: `Pending, Classified, Needs Review, Failed`.

Track `Last_Error_Code, Last_Error_Message, Last_Processing_DateTime, Retry_Count` where appropriate.

User errors must be actionable, not raw HTTP codes.

---

# 28. GOVERNMENT / DAF COMPATIBILITY MODE

MVP must work without Managed Environments, premium pipelines, multiple environments, AI Builder, custom connectors, HTTP, Graph, service principals, PCF, Code Apps, or Dataverse.

Core target: Power Apps Canvas + SharePoint Online + Power Automate + Power BI + Entra identity.

Verify locally: exact GCC/GCC High/DoD environment, connectors, Solutions, PAC CLI authorization, AI Builder, PCF, Code Apps, premium/custom connector permissions.

Microsoft availability does not equal local DAF authorization.

---

# 29. SINGLE-ENVIRONMENT SAFETY

Support constrained government tenants with feature flags, tester/developer-only surfaces, maintenance/read-only mode, app version, telemetry, release notes, rollback documentation, and semantic releases.

---

# 30. SOURCE CONTROL / ALM

Solution: `MissionFeedingOperations`

```text
power-platform/
├── solution/MissionFeedingOperations/
├── canvas-app/{screens,components,formulas,data-sources}/
├── flows/{EOM01-ExpectedPackage,EOM02-DocumentIntake,EOM03-Reconciliation,EOM04-Notifications}/
├── configuration/{requirements.csv,connection-references.json,environment-variables.json}/
├── tests/
├── docs/
├── deployment/
├── changelog/
└── dist/MissionFeedingOperations_<version>.zip
```

Use supported solution/PAC tooling and `.pa.yaml` source where applicable. Repository source is authoritative; ZIP/MSAPP is an artifact. Document unavoidable post-import SharePoint rebinding/manual steps.

---

# 31. ENVIRONMENT VARIABLES / CONFIG

Recommended:

```text
MF_SharePointSiteURL
MF_FileIntakeLibrary
MF_RequirementList
MF_EOMItemList
MF_SubmissionList
MF_DocumentLocationList
MF_SecurityList
MF_PowerBIReportURL
```

Support Portfolio-specific site/library configuration without hard-coded references.

---

# 32. OPEN-SOURCE / RESEARCH PATTERNS

Study/borrow from:
- Microsoft PowerApps-Samples.
- PnP powerapps-samples.
- PnP Student Application Process.
- PnP Request Sign-Off / List Formatting.
- PowerCAT Creator Kit.
- CoE Starter Kit.
- Microsoft Building Access sample/AppSettings pattern.
- PBIR, pbir.tools, pbi-tools.
- Microsoft Fluent 2/modern controls, responsive containers, coding/delegation/accessibility guidance.
- Section508.gov.

Borrow patterns, not unnecessary dependencies. Native modern controls first; reusable Canvas components second; Creator Kit if approved; PCF last.

---

# 33. CURRENT HTML PROTOTYPE — PRESERVE

Preserve: restrained palette, typography, status chips with text + marker, facility/installation/contract scope, expected item vs versioned submission separation, review queue, version history, Needs Classification, role test harness, requirement configuration, authority status, audit concept, responsive direction, and no destructive overwrite.

---

# 34. CURRENT HTML PROTOTYPE — REQUIRED IMPROVEMENTS

1. Demote Upload; normal intake is Teams/SharePoint.
2. Replace with My Package/Submissions.
3. Role-aware Home.
4. My Work filtered by action ownership.
5. Separate Final_Status and Status_Code.
6. Add Blue/In Progress state.
7. Semantic package rollup.
8. Fix facility security leakage.
9. Explicitly authorize installation/contract items for facility users.
10. Drill-through Installation workspace.
11. Global period selector.
12. History → Activity.
13. Progressive Review UX.
14. Wrong Document is submission QC, not permanently parent Red.
15. Confidence-first Needs Classification.
16. Cascading exception selectors.
17. Keep UNVERIFIED detail primarily in Admin.
18. Permission-aware navigation.
19. Mobile cards instead of truncated tables.
20. Admin configuration/system-health warnings.
21. One authoritative status object/function.
22. Reusable styles/components rather than inline styling.
23. Centralized date handling.
24. Surface facilities with no requirement set.

---

# 35. KNOWN PROTOTYPE SECURITY BUG

Facility-scoped users can currently see an installation rollup derived from other facilities because `installationPackage()` uses all facilities at the installation. `myItems()` also allows all non-facility records at the installation. Production must authorize scope explicitly before rollup/display; contract-level visibility requires actual facility-contract association.

---

# 36. CONFIGURATION HEALTH CHECKS

Detect: facility with no requirement set; unknown model; duplicate expected keys; multiple current versions; unmapped document location; conflicting security scope; missing authority; missing due rule; unmatched backlog; failed automation; stale reconciliation; missing expected package.

---

# 37. PILOT / ACCEPTANCE

Pilot 3–5 locations covering Legacy/APF, Food 2.0, MAFFO/MAF if applicable, all three requirement scopes, normal folder upload, manual/on-behalf intake, correction/versioning, wrong document, unmatched, overdue, unverified, facility security, and portfolio QC.

Acceptance: idempotent expected rows; no silent unmatched; every version retained; correct current version; security before rollup; correct package/action ownership; QC rules; evidence links; Power BI status output; RLS; responsive/accessibility; no nondelegable production errors; no filename dependency; no hard-coded URLs; no adverse status from unverified requirements unless configured; system health detects gaps.

Target: ≥95% of clearly identifiable pilot files reconciled automatically and 100% of unresolved files routed visibly to Needs Classification.

---

# 38. MVP NON-GOALS

No full content-level financial validation, full SAIIT/FMAT/G4G/training/equipment/contract/Five-Year Plan modules, AI-only classification, custom PCF, Dataverse migration, Code Apps rewrite, or full enterprise COP beyond EOM in v1.

---

# 39. FUTURE MODULE BACKLOG

After EOM stabilizes: SAIIT Automation Recovery; DFAC Standard Levels of Service / CLIN Responsibility Matrix; Three-Tier Mission Feeding Modernization Model; FMAT; G4G 2.0; ServSafe/training; equipment/maintenance/calibration; Five-Year Plan.

---

# 40. EXISTING ARTIFACTS

Previously generated/referenced:
- `Mission_Feeding_COP_Claude_Codex_Handoff_v1.docx`
- `Mission_Feeding_EOM_Submission_QC_Automation_Handoff_v1.md`
- `MF_EOM_Requirement_Import.csv`
- `MF_EOM_Submission_Tracker_Import.csv`
- `MF_EOM_PowerAutomate_Build_Instructions.md`
- Claude R2A: `MF_COP_R2A.pbix`, `MF_COP_R2A_Demo.pptx`, `MF_COP_R2A_Handoff.docx`, `README.md`, `source_catalog.csv`

This handoff supersedes earlier artifacts for the **Power Apps EOM MVP direction** where conflicts exist.

---

# 41. FINAL CODEX / CLAUDE EXECUTION DIRECTIVE

Build an importable/source-controlled Power Platform solution named `MissionFeedingOperations` whose first release is an EOM Requirement / Evidence / QC / COP application.

Use SharePoint/Teams as source-document repository, SharePoint Lists as configuration/workflow storage, Power Automate for expected-row generation/document discovery/classification/reconciliation/notifications, Power Apps for human interaction/QC, and Power BI for COP visualization.

Requirements are data-driven and support Facility, Installation, and Contract scopes. Operating model is facility-level. Separate persistent expected `MF_EOM_Item` records from versioned `MF_EOM_Submission` records. Retain every version/audit event.

Normal users are not forced to upload through Power Apps. Discover/reconcile files from approved Portfolio FY/EOM locations. Manual/on-behalf registration is an exception workflow.

Do not depend on filenames. Use context/metadata/deterministic document evidence/optional authorized intelligence/manual exceptions.

Implement one authoritative status engine with `Final_Status`, `Status_Code`, `Action_Owner_Type`, and `Action_Required`. Power BI consumes flattened `MF_EOM_Status` and does not reproduce workflow logic.

Build role-aware Home, My Package/Submissions, Installation workspace, Review Queue, Exceptions, Activity, and Admin/System Health. Use native modern controls, responsive containers, Fluent 2 patterns, progressive disclosure, plain language, and Section 508-conscious accessibility.

Build for government constraints and feature-gate optional capabilities. Use environment variables/configuration. Include feature flags, developer/tester access, maintenance/read-only mode, telemetry, release notes, rollback instructions. All production-scale queries must be delegable.

Produce source-controlled solution files, Canvas source where supported, flows, configuration seeds, SharePoint schema/provisioning instructions, environment variables, connection references, Power Fx/components, Power BI integration schema, deployment README, post-import steps, accessibility/government checklists, pilot fixtures, test report, changelog, rollback procedure, and `dist/MissionFeedingOperations_<version>.zip` where supported.

Do not falsely promise zero-touch deployment if tenant-specific SharePoint rebinding or government configuration requires manual steps.

---

# 42. INFORMATION STILL NEEDED

1. Exact Portfolio Teams/SharePoint FY/EOM folder structure.
2. Portfolio → installation mapping.
3. Installation → facility mapping.
4. Facility type and operating model per facility.
5. Contract IDs/coverage where needed.
6. Final requirement matrix with Scope/applicability.
7. Authority references/status.
8. Exact due/suspense rules.
9. Sanitized representative documents for deterministic classification.
10. QC authority/decision rules.
11. Role/security mapping and multi-facility coverage.
12. Exact government cloud and locally approved Power Platform capabilities.
13. PAC CLI authorization.
14. AI Builder/document-processing authorization.
15. Historical backfill requirement.
16. Power BI destination/RLS expectations.
17. Whether contract evidence can span multiple installations.

Treat unresolved policy questions as configuration inputs rather than schema blockers wherever possible.

---

# 43. SUCCESS STATE

```text
User uploads EOM evidence to approved Teams folder
                        ↓
System discovers it
                        ↓
System identifies context / requirement
                        ↓
Expected item becomes Received
                        ↓
Reviewer sees only items requiring review
                        ↓
Accept / Correction / Wrong Document
                        ↓
Facility and installation package update automatically
                        ↓
Power BI COP changes automatically
```

Uncertain files go to **Needs Classification**, then rejoin normal workflow after a human confirms the minimum necessary context.

The desired result is not merely a better document tracker. It is a **Mission Feeding operational control system** where routine evidence discovery and status reconciliation are automatic, humans handle true decisions/exceptions, and leadership receives a trustworthy COP without duplicating operational logic in Power BI.
