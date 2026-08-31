"""Canonical Mission Feeding Operations (EOM) schema.

Single source of truth for the SharePoint provisioning script, the data
dictionary, the Power Apps data-source definitions and the Power BI status view.

Design decisions locked by review, 26 Aug 2026:
  1. Operating_Model lives at FACILITY grain, not installation.
  2. Requirement_Scope supports Facility | Installation | Contract.
     Portfolio is reserved but not implemented.
  3. Facility_ID is NULLABLE on MF_EOM_Item for installation/contract-scope rows.
  4. The persistent expected row (MF_EOM_Item) is SEPARATE from the versioned
     submission (MF_EOM_Submission). Do not duplicate the checklist row on
     every resubmission.
  5. Unresolved form applicability is UNVERIFIED configuration, never code.
  6. Rollups run facility -> installation -> portfolio.
  7. One security mapping serves both Power Apps and Power BI RLS.
"""

# SharePoint column types: Text, Note, Number, Currency, DateTime, Boolean,
# Choice, Lookup, User, URL, Calculated
def c(name, ctype, req=False, indexed=False, choices=None, note="", maxlen=None):
    return dict(name=name, type=ctype, required=req, indexed=indexed,
                choices=choices or [], note=note, maxlen=maxlen)


LISTS = {}

# ---------------------------------------------------------------- reference
LISTS["MF_Installation"] = dict(
    title="MF Installation",
    grain="One row per installation",
    columns=[
        c("Installation_ID", "Text", req=True, indexed=True,
          note="Canonical key. Must match the COP MF_Installation.Installation_ID."),
        c("Installation_Name", "Text", req=True),
        c("Portfolio_ID", "Text", req=True, indexed=True),
        c("MAJCOM", "Text"),
        c("Component", "Choice", req=True, choices=["Active", "ANG", "AFRC"],
          note="ROUTING FIELD. DAFMAN 34-131 7.14.5: ANG DFAC managers send the EOY inventory "
               "last page to NGB/A1X, everyone else to AFSVC/VMF. Without this the EOY "
               "requirement routes ANG submissions to the wrong organisation."),
        c("EOM_Folder_URL", "URL", note="Teams/SharePoint FY folder root for this installation"),
        c("Generation_Enabled", "Boolean", req=True,
          note="EOM-01 generates expected rows ONLY where this is TRUE. This is what lets the app "
               "be built and piloted before the enterprise facility registry is complete: turn a "
               "base on once its facilities and operating models are validated. A base with "
               "Generation_Enabled FALSE shows as 'not yet onboarded', never as compliant."),
        c("Registry_Validated_By", "Text"),
        c("Registry_Validated_Date", "DateTime"),
        c("Active_Flag", "Boolean", req=True),
    ])

LISTS["MF_Facility"] = dict(
    title="MF Facility",
    grain="One row per feeding facility",
    note="Operating_Model is HERE, not on the installation. Lackland can run a "
         "legacy DFAC and a Food 2.0 cafe simultaneously; the requirement set is "
         "driven by the facility's model.",
    columns=[
        c("Facility_ID", "Text", req=True, indexed=True,
          note="Unique enterprise-wide, not per installation"),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Facility_Name", "Text", req=True),
        c("Facility_Type", "Choice", req=True,
          choices=["Main DFAC", "Flight Kitchen", "Kiosk", "Satellite", "MAF", "Contract Cafe"]),
        c("Operating_Model", "Choice", req=True,
          choices=["Legacy/APF", "Food 2.0", "MAFFO/MAF", "AOR/CDS"],
          note="Drives which requirements apply to THIS facility"),
        c("Contract_ID", "Text", note="Nullable. Set for contract-scope requirements."),
        c("Active_Flag", "Boolean", req=True),
    ])

LISTS["MF_EOM_Requirement"] = dict(
    title="MF EOM Requirement",
    grain="One row per document requirement per operating model",
    note="THE requirement engine. The app queries this; it contains no "
         "'if Legacy then require 1119' logic. Changing a requirement next year "
         "is a list edit, not an app rebuild. The drop boxes on the installation "
         "screen ARE this list, filtered.",
    columns=[
        c("Requirement_ID", "Text", req=True, indexed=True),
        c("Document_Code", "Text", req=True, note="1119, 1119-1, SIK, SF1080, DAF79, 1038, SAIIT"),
        c("Document_Name", "Text", req=True),
        c("Applicable_Model", "Choice", req=True,
          choices=["Legacy/APF", "Food 2.0", "MAFFO/MAF", "AOR/CDS", "All"],
          note="'All' applies regardless of facility model"),
        c("Requirement_Scope", "Choice", req=True,
          choices=["Facility", "Installation", "Contract"],
          note="Determines the grain of the generated EOM_Item. Portfolio reserved, "
               "not implemented."),
        c("Applicable_Facility_Types", "Text",
          note="Semicolon list. Blank = all types. Kiosks rarely file a 1119."),
        c("Frequency", "Choice", req=True,
          choices=["Monthly", "Quarterly", "Semiannual", "Annual", "Conditional"],
          note="Conditional requirements are NEVER auto-generated. The 1119-1 is field feeding "
               "and only exists when field feeding occurred, so it is added by the base or the "
               "reviewer, not by EOM-01."),
        c("Applicable_Period_Month", "Number",
          note="For Annual. 9 = the September period, where EOY requirements land. EOY is the "
               "same engine, not a second application."),
        c("Routing_Org", "Text",
          note="Where the accepted document goes. Usually AFSVC/VMF; NGB/A1X for ANG on the EOY "
               "inventory. Resolved against MF_Installation.Component."),
        c("Required_Flag", "Boolean", req=True),
        c("Due_Day", "Number", req=True,
          note="FIRST suspense. Day of the month following the reporting period. Confirmed 26 Aug "
               "2026: 5 days after month end. Configurable — changing it never touches the app."),
        c("Due_Basis", "Choice", req=True, choices=["CALENDAR", "DUTY"],
          note="CALENDAR is the baseline. The source says 'within 5 days' and does not say duty "
               "days, business days or workdays. Do not infer duty days without a citation."),
        c("Final_Due_Day", "Number", req=True,
          note="SECOND and final call — the 10th. This is a MANAGEMENT_RULE from the programme, "
               "not from the procedure deck. Label it as such."),
        c("Final_Due_Basis", "Choice", req=True, choices=["CALENDAR", "DUTY"]),
        c("NonDutyDay_Policy", "Choice", req=True,
          choices=["NEXT_DUTY_DAY", "PREVIOUS_DUTY_DAY", "NO_ADJUSTMENT"],
          note="What happens when a nominal suspense lands on a weekend or federal holiday. "
               "Default NEXT_DUTY_DAY. Configured, never buried in Power Fx."),
        c("Due_Offset_Months", "Number", note="Usually 1. Set higher for lagging requirements."),
        c("QC_Required", "Boolean", req=True),
        c("Accepted_File_Types", "Text", note="Advisory only in MVP. xlsx;pdf"),
        c("Authority_Reference", "Text",
          note="UNVERIFIED means do not enforce. The app still shows the box; the "
               "requirement is inactive until validated."),
        c("Authority_Status", "Choice", req=True,
          choices=["VERIFIED", "MANAGEMENT_RULE", "PROPOSED", "UNVERIFIED",
                   "RETIRED_OR_NOT_APPLICABLE"],
          note="Authority for the REQUIREMENT EXISTING. VERIFIED means a cited source says this "
               "document is part of the package. MANAGEMENT_RULE means leadership set it and no "
               "external citation is needed or claimed. RETIRED keeps a definition on the record "
               "without generating it, so later guidance can reactivate without a schema change."),
        c("Scope_Confidence", "Choice", req=True,
          choices=["High", "Medium", "Low", "Proposed"],
          note="SEPARATE from Authority_Status. A source can confirm a document exists without "
               "saying at what grain it is filed. Conflating the two marks a guess as policy."),
        c("Scope_Basis", "Text",
          note="Why this grain. 'SAIIT is written around DFAC/storeroom management' is a reason; "
               "'seems right' is not."),
        c("Sort_Order", "Number"),
        c("Active_Flag", "Boolean", req=True),
    ])

# ---------------------------------------------------------------- transactional
LISTS["MF_EOM_Item"] = dict(
    title="MF EOM Item",
    grain="One PERSISTENT row per expected submission per reporting period",
    note="Generated by flow EOM-01. This row is created once and never duplicated. "
         "Corrections attach as new MF_EOM_Submission versions pointing at the same "
         "item. Facility_ID is NULL for Installation and Contract scope.",
    columns=[
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("EOM_Item_Key", "Text", req=True, indexed=True,
          note="Human-readable compound key: LACKLAND|BLDG1234|2026-10|1119. Drives "
               "duplicate prevention and flow idempotency."),
        c("Portfolio_ID", "Text", req=True, indexed=True,
          note="Denormalized. The portfolio filter is the first server-side filter on "
               "every query, so it must be on the row."),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Facility_ID", "Text", indexed=True,
          note="NULLABLE. Null for Installation-scope and Contract-scope rows."),
        c("Contract_ID", "Text", note="NULLABLE. Set for Contract-scope rows."),
        c("Reporting_Period", "Text", req=True, indexed=True, note="YYYY-MM"),
        c("Requirement_ID", "Text", req=True, indexed=True),
        c("Requirement_Scope", "Choice", req=True,
          choices=["Facility", "Installation", "Contract"],
          note="Denormalized from the requirement so the app can filter without a join"),
        c("Required_Flag", "Boolean", req=True),
        c("Nominal_Due_Date", "DateTime", req=True,
          note="The policy date. Leadership and reporting see this — 'the 5th' stays the 5th."),
        c("Effective_Due_Date", "DateTime", req=True, indexed=True,
          note="The actionable date after NonDutyDay_Policy. Users are held to this. Status "
               "evaluation uses this, never the nominal date."),
        c("Nominal_Final_Call_Date", "DateTime", req=True),
        c("Effective_Final_Call_Date", "DateTime", req=True, indexed=True),
        c("Due_Date_Adjusted", "Boolean", req=True,
          note="TRUE when the two differ. The package screen shows 'Due 5 Sep (Mon 7 Sep)' so "
               "nobody argues about a Saturday suspense."),
        c("Initial_Submitted_DateTime", "DateTime",
          note="When the FIRST version arrived, whatever became of it"),
        c("Initial_Submission_On_Time", "Boolean",
          note="Did any version arrive by Effective_Due_Date. 'Did the base do its job on time.'"),
        c("Current_Acceptable_Evidence_DateTime", "DateTime",
          note="When an ACCEPTED version came into existence"),
        c("Final_Evidence_On_Time", "Boolean",
          note="Was acceptable evidence in hand by Effective_Final_Call_Date. 'Did AFSVC have "
               "usable evidence on time.' Different question, different answer, both stored — "
               "and both translated to plain English in the UI, never shown as bare booleans."),
        c("Current_Submission_ID", "Text",
          note="Points at the Is_Current submission. Null until the first upload."),
        c("Received_Flag", "Boolean", req=True),
        c("Final_Status", "Choice", req=True,
          choices=["NOT_APPLICABLE", "NOT_DUE", "PENDING_VALIDATION", "OVERDUE",
                   "NOT_SATISFIED", "CORRECTION_REQUIRED", "RECEIVED_PENDING_QC", "ACCEPTED"],
          note="Semantic status. CALCULATED by EOM-03, never user-selectable. Independent "
               "of Status_Code — never derive one from the other."),
        c("Action_Owner", "Choice", req=True,
          choices=["Facility", "Reviewer", "Admin", "None"],
          note="Status_Code alone cannot answer 'is this mine'. Amber covers both correction "
               "needed (facility) and awaiting review (AFSVC). Home filters on this."),
        c("Action_Required", "Boolean", req=True),
        c("Status_Code", "Number", req=True, indexed=True,
          note="VISUAL code only. 0 Gray not-applicable, 1 Red overdue, 2 Amber pending, "
               "3 Green accepted, 4 Blue not-due/informational. Five states, not four: "
               "collapsing 'not applicable' and 'not due yet' into Gray made an installation "
               "whose requirements had simply not come due read as Not Applicable."),
        c("Exception_Flag", "Boolean", req=True,
          note="Set when the item needs human attention beyond normal QC"),
        c("Correction_Due", "DateTime", note="Set when QC returns a correction"),
        c("Waived_Flag", "Boolean", note="Portfolio Manager may waive a requirement for a period"),
        c("Waiver_Reason", "Note"),
    ])

LISTS["MF_EOM_Submission"] = dict(
    title="MF EOM Submission",
    grain="One row per uploaded file version",
    note="Versioned evidence. v1 Correction Required and v2 Accepted both persist; "
         "nothing is overwritten or deleted. QC applies to the Is_Current version.",
    columns=[
        c("Submission_ID", "Text", req=True, indexed=True),
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("Version_No", "Number", req=True, note="Assigned by upload timestamp order"),
        c("File_Name", "Text", req=True, note="As uploaded. No naming convention required."),
        c("File_URL", "URL", req=True,
          note="THE LIST ROW IS TRUTH, THE PATH IS CONVENIENCE. Never derive status "
               "from the path — files get moved and renamed."),
        c("File_Size_KB", "Number"),
        c("Uploaded_By", "User", req=True, note="SharePoint identity of the actual uploader"),
        c("Uploaded_DateTime", "DateTime", req=True, indexed=True),
        c("Submitted_On_Behalf_Of", "Text",
          note="Facility_ID or Installation_ID when an AFSVC MFM uploads a document that "
               "arrived by email. Without this, emailed submissions misattribute to AFSVC "
               "and the missing/overdue counts go wrong silently."),
        c("Intake_Method", "Choice", req=True,
          choices=["App upload", "Folder drop", "Manual classification"],
          note="App upload needs no classification. Folder drop may."),
        c("Classification_Method", "Choice",
          choices=["Declared at upload", "Folder context", "Document content",
                   "AI Builder", "Manual"],
          note="'Declared at upload' is the production baseline. Filename is NEVER a method."),
        c("Classification_Status", "Choice",
          choices=["Pending", "Classified", "Needs Review", "Failed"]),
        c("Last_Error_Code", "Text"),
        c("Last_Error_Message", "Note",
          note="User-facing, plain language. Never a raw HTTP status."),
        c("Last_Processing_DateTime", "DateTime"),
        c("Retry_Count", "Number"),
        c("Source_Path", "Text",
          note="Where the file was found. Diagnostic only — the list row is truth."),
        c("SharePoint_File_ID", "Text", note="Survives a rename or move; the URL does not."),
        c("Classification_Confidence", "Choice",
          choices=["Declared", "High", "Low", "Unresolved"],
          note="'Declared' = the app captured it at upload. That is the whole point of "
               "making the app the front door."),
        c("Is_Current", "Boolean", req=True),
        c("Superseded_By", "Text", note="Submission_ID of the version that replaced this one"),
        c("QC_Status", "Choice", req=True,
          choices=["Pending Review", "Accepted", "Correction Required", "Incomplete",
                   "Wrong Document", "Wrong Reporting Period", "Wrong Facility",
                   "Recalled", "Not Applicable"],
          note="Reviewers open the file in Teams and verify content, so the verdict has to say "
               "WHY. The base sees the specific reason on their dashboard, not a generic return."),
        c("QC_By", "User"),
        c("QC_DateTime", "DateTime"),
        c("QC_Comment", "Note",
          note="REQUIRED when QC_Status is Correction Required or Wrong Document"),
    ])

LISTS["MF_Unmatched_File"] = dict(
    title="MF Unmatched File",
    grain="One row per file found in the FY folder that could not be resolved",
    note="The safety net for folder drops. Should be near-empty once people use the "
         "app. No content parsing or AI Builder in MVP — a human picks from dropdowns.",
    columns=[
        c("Unmatched_ID", "Text", req=True, indexed=True),
        c("File_Name", "Text", req=True),
        c("File_URL", "URL", req=True),
        c("Portfolio_ID", "Text", note="Derivable from the folder — that much the path gives us"),
        c("Fiscal_Year", "Text", note="Derivable from the folder"),
        c("Discovered_DateTime", "DateTime", req=True),
        c("Uploaded_By", "User"),
        c("Suggested_Installation_ID", "Text", note="Weak hint only. Never auto-applied."),
        c("Suggested_Document_Code", "Text", note="Weak hint only."),
        c("Resolution_Status", "Choice", req=True,
          choices=["Needs Classification", "Classified", "Not an EOM document", "Duplicate"]),
        c("Resolved_Submission_ID", "Text"),
        c("Resolved_By", "User"),
        c("Resolved_DateTime", "DateTime"),
    ])

LISTS["MF_Security_Mapping"] = dict(
    title="MF Security Mapping",
    grain="One row per user per granted scope",
    note="ONE mapping for both Power Apps filtering and Power BI RLS. Do not maintain "
         "two permission models. Also drives dropdown defaulting: a DFAC manager with "
         "one facility row sees no dropdowns at all, just an upload box.",
    columns=[
        c("Security_ID", "Text", req=True, indexed=True),
        c("UPN", "Text", req=True, indexed=True),
        c("Scope_Type", "Choice", req=True,
          choices=["Enterprise", "Portfolio", "Installation", "Facility"]),
        c("Portfolio_ID", "Text"),
        c("Installation_ID", "Text"),
        c("Facility_ID", "Text"),
        c("Role", "Choice", req=True,
          choices=["BASE_USER", "PORTFOLIO_MANAGER"],
          note="TWO roles, because that is what users can hold in their heads. Capability "
               "lives in the flags below, NOT in the role. Everyone gets BASE_USER "
               "automatically from CAC and GAL; PORTFOLIO_MANAGER is granted."),
        c("Job_Title", "Text",
          note="Display only — 'Base Accountant', 'DFAC Manager', 'Operations Manager'. "
               "Never drives a permission decision."),
        c("Can_QC", "Boolean", req=True,
          note="Review submissions. Default TRUE for PORTFOLIO_MANAGER."),
        c("Can_Submit_On_Behalf", "Boolean", req=True),
        c("Can_Edit_Requirements", "Boolean", req=True,
          note="Change the requirement catalogue, thresholds and configuration. SEPARATE "
               "from Can_QC so review and configuration can be split later without a "
               "schema change."),
        c("Can_Grant_Access", "Boolean", req=True,
          note="THE control that stops the role self-propagating. Defaults FALSE even for "
               "PORTFOLIO_MANAGER. If every PM could grant PM, the population could only "
               "ever grow and no holder would need anyone's approval to expand it. That is "
               "a privilege escalation path and it is the first thing an ISSM asks about."),
        c("Grant_Scope", "Choice", req=True,
          choices=["None", "Portfolio", "Enterprise"],
          note="How far a grant reaches. Portfolio means a PM grants only inside their own "
               "portfolio. Enterprise is two or three people at AFSVC, not a default."),
        c("Grant_Type", "Choice", req=True,
          choices=["GAL derived", "Requested", "Manual"],
          note="GAL derived is the default path: CAC identifies the user, their GAL location gives "
               "the installation, and they get it without anyone provisioning them. Requested "
               "covers a PCS who still owes their losing base a package."),
        c("Granted_By", "Text", note="Null for GAL-derived"),
        c("Granted_Date", "DateTime"),
        c("Expires_Date", "DateTime",
          note="Requested access should expire. A PCS finishing a handover needs 60 days, not "
               "permanent rights to a base they left."),
        c("Developer_Flag", "Boolean", req=True,
          note="Sees feature-flagged and diagnostic surfaces. Required because a DAF tenant "
               "may allow only ONE environment — unreleased work has to coexist with "
               "production safely."),
        c("Tester_Flag", "Boolean", req=True, note="Sees Enabled_Testers features only"),
        c("Active_Flag", "Boolean", req=True),
    ])

LISTS["MF_EOM_Audit"] = dict(
    title="MF EOM Audit",
    grain="One row per state change",
    note="Cheap now, invaluable during an IG. Every QC decision and every generated "
         "item is recorded.",
    columns=[
        c("Audit_ID", "Text", req=True, indexed=True),
        c("Entity_Type", "Choice", req=True, choices=["EOM_Item", "EOM_Submission", "Requirement"]),
        c("Entity_ID", "Text", req=True, indexed=True),
        c("Action", "Choice", req=True,
          choices=["Generated", "Uploaded", "QC Accepted", "QC Correction Required",
                   "QC Wrong Document", "Waived", "Reclassified", "Status Recalculated"]),
        c("Actor_UPN", "Text", req=True),
        c("Action_DateTime", "DateTime", req=True),
        c("Old_Value", "Text"),
        c("New_Value", "Text"),
        c("Detail", "Note"),
    ])


# ============================================================================
# v2 — government single-environment safety, capability gating, telemetry
#
# Driven by the constraint that a DAF tenant may allow exactly ONE Power
# Platform environment. Everything below exists so unreleased work can sit
# safely alongside production in the same environment.
# ============================================================================

LISTS["MF_App_Config"] = dict(
    title="MF App Config",
    grain="One row per configuration key",
    note="Admin-managed, read-only to everyone else. Pattern borrowed from the Microsoft "
         "Building Access sample. This is the kill switch: when something breaks after a "
         "publish you flip MaintenanceMode rather than racing to unpublish.",
    columns=[
        c("Config_Key", "Text", req=True, indexed=True),
        c("Config_Value", "Text", req=True),
        c("Config_Type", "Choice", req=True, choices=["String", "Boolean", "Number", "Date"]),
        c("Description", "Note"),
        c("Admin_Only", "Boolean", req=True),
        c("Active_Flag", "Boolean", req=True),
    ])

LISTS["MF_Feature_Flags"] = dict(
    title="MF Feature Flags",
    grain="One row per feature",
    note="Ship a new screen inside the published app while normal users still see the old "
         "one. Beats the manual old-screen/new-screen swap: no renaming, no rebuild, and "
         "the rollback is a checkbox.",
    columns=[
        c("Feature_Key", "Text", req=True, indexed=True),
        c("Feature_Name", "Text", req=True),
        c("Enabled_Prod", "Boolean", req=True),
        c("Enabled_Testers", "Boolean", req=True),
        c("Minimum_Role", "Choice", req=True,
          choices=["DFAC Manager", "Accountant", "MFM", "Portfolio Manager",
                   "AFSVC Leadership", "Admin", "Developer"]),
        c("Effective_Date", "DateTime"),
        c("Notes", "Note"),
    ])

LISTS["MF_App_Event_Log"] = dict(
    title="MF App Event Log",
    grain="One row per meaningful business event",
    note="Business telemetry, NOT click tracking. Answers 'why didn't Minot's 1119 show up' "
         "operationally, and 'how many manual interventions did we avoid' strategically. "
         "Append-only; never bind a gallery directly to it.",
    columns=[
        c("Event_ID", "Text", req=True, indexed=True),
        c("Event_DateTime", "DateTime", req=True, indexed=True),
        c("User_UPN", "Text", req=True),
        c("Role", "Text"),
        c("Portfolio_ID", "Text"),
        c("Installation_ID", "Text", indexed=True),
        c("Facility_ID", "Text"),
        c("Event_Type", "Choice", req=True,
          choices=["AppOpened", "DocumentDiscovered", "SubmissionCreated", "VersionSuperseded",
                   "ClassificationSucceeded", "ClassificationUncertain", "ManualClassification",
                   "ExpectedItemMatched", "QCAccepted", "QCCorrectionRequired",
                   "QCWrongDocument", "ExpectedGenerationFailed", "ReconciliationMismatch",
                   "FlowFailure", "PermissionDenied", "MaintenanceModeBlocked"]),
        c("Record_ID", "Text"),
        c("Result", "Choice", req=True, choices=["Success", "Warning", "Failure"]),
        c("Error_Code", "Text"),
        c("Error_Message", "Note"),
        c("App_Version", "Text", req=True,
          note="Which build produced this event. Essential when one environment holds "
               "released and unreleased code at once."),
    ])

LISTS["MF_EOM_Status"] = dict(
    title="MF EOM Status",
    grain="One flat row per EOM item — the canonical Power BI fact",
    note="Materialized by EOM-03. Power BI NEVER reconstructs workflow logic; it reads "
         "Status_Code and formats. Both the numeric code and the semantic string are stored "
         "so Power BI can colour on one and label on the other.",
    columns=[
        c("Status_ID", "Text", req=True, indexed=True),
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("Reporting_Period", "Text", req=True, indexed=True),
        c("Fiscal_Year", "Text", req=True),
        c("Portfolio_ID", "Text", req=True, indexed=True),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Installation_Name", "Text", req=True),
        c("Facility_ID", "Text", note="Null for Installation and Contract scope"),
        c("Facility_Name", "Text"),
        c("Operating_Model", "Text"),
        c("Contract_ID", "Text"),
        c("Requirement_ID", "Text", req=True),
        c("Requirement_Name", "Text", req=True),
        c("Document_Code", "Text", req=True),
        c("Requirement_Scope", "Text", req=True),
        c("Authority_Status", "Text", req=True,
          note="Carried through so the COP can dim provisional requirements too"),
        c("Required_Flag", "Boolean", req=True),
        c("Due_Date", "DateTime", req=True),
        c("Received_Flag", "Boolean", req=True),
        c("Received_DateTime", "DateTime"),
        c("Version_No", "Number"),
        c("QC_Status", "Text"),
        c("Final_Status", "Text", req=True),
        c("Status_Code", "Number", req=True, note="0 Gray 1 Red 2 Yellow 3 Green"),
        c("Status_Semantic", "Text", req=True,
          note="NOT_APPLICABLE | NOT_DUE | PENDING_VALIDATION | OVERDUE | NOT_SATISFIED | "
               "CORRECTION_REQUIRED | RECEIVED_PENDING_QC | ACCEPTED. Never colour-only."),
        c("Action_Owner", "Text", req=True),
        c("Action_Required", "Boolean", req=True),
        c("Package_State", "Text", req=True,
          note="Facility-level rollup: ACTION_REQUIRED | IN_REVIEW | COMPLETE | IN_PROGRESS | "
               "NOT_APPLICABLE. Computed over semantic statuses, never over colour codes."),
        c("Days_Late", "Number"),
        c("On_Time_Flag", "Boolean"),
        c("Current_File_URL", "URL"),
        c("Generated_DateTime", "DateTime", req=True),
    ])


# ============================================================================
# v3 — suspense calendar
# Authored dates live apart from generated ones. Changing when a 1119 is due is
# a requirement change (Due_Day on MF_EOM_Requirement), never a calendar edit —
# otherwise the item desynchronises from the requirement that produced it and
# the next generation run silently overwrites the edit.
# ============================================================================

LISTS["MF_Calendar_Event"] = dict(
    title="MF Calendar Event",
    grain="One row per authored calendar entry",
    note="ADDED v3. Generated suspenses come from MF_EOM_Item.Due_Date and are read-only on "
         "the calendar. This list holds what a Portfolio Manager or MFM authors: correction "
         "suspenses, assessment windows, data-call cut-offs, taskers. The two sources render "
         "on one surface and never merge.",
    columns=[
        c("Event_ID", "Text", req=True, indexed=True),
        c("Event_Type", "Choice", req=True,
          choices=["Suspense", "Correction due", "Assessment", "Data call", "Reminder"]),
        c("Title", "Text", req=True, note="One line. It renders in a calendar cell."),
        c("Event_Date", "DateTime", req=True, indexed=True),
        c("End_Date", "DateTime", note="Nullable. Assessment visits span days."),
        c("All_Day", "Boolean", req=True),
        c("Scope_Type", "Choice", req=True,
          choices=["Enterprise", "Portfolio", "Installation", "Facility"],
          note="One post reaches every base in a portfolio without copying it eleven times"),
        c("Scope_ID", "Text", indexed=True, note="Null when Scope_Type is Enterprise"),
        c("Linked_Item_ID", "Text",
          note="Nullable FK to MF_EOM_Item — set for a correction suspense so the event "
               "opens the item"),
        c("Status_Code", "Number", req=True,
          note="Same five-state palette as everything else. Author sets it for standalone "
               "events; a linked event inherits from its item."),
        c("Created_By", "User", req=True),
        c("Created_DateTime", "DateTime", req=True),
        c("Active_Flag", "Boolean", req=True),
    ])


# ============================================================================
# v4 — access requests
# CAC + GAL gives someone their own installation automatically. This list is the
# exception path, modelled on how Teams handles a request to join.
# ============================================================================

LISTS["MF_Access_Request"] = dict(
    title="MF Access Request",
    grain="One row per request for access to an installation the requester is not posted to",
    note="ADDED v4. Nobody is provisioned for their own base — CAC identifies them and the GAL "
         "gives the installation. This covers the person who PCS'd and still owes their losing "
         "base an EOM package, and the AFSVC member covering a portfolio temporarily.",
    columns=[
        c("Request_ID", "Text", req=True, indexed=True),
        c("Requester_UPN", "Text", req=True, indexed=True),
        c("Requester_Name", "Text", req=True),
        c("Home_Installation", "Text", note="From the GAL, for context in the approval"),
        c("Requested_Installation_ID", "Text", req=True, indexed=True),
        c("Justification", "Note", req=True, note="Required. One line is fine."),
        c("Requested_Until", "DateTime", note="Default 60 days out. Access is temporary."),
        c("Status", "Choice", req=True, choices=["Pending", "Approved", "Denied", "Expired"]),
        c("Decided_By", "Text"),
        c("Decided_Date", "DateTime"),
        c("Decision_Comment", "Note"),
    ])

LISTS["MF_Notification_Rule"] = dict(
    title="MF Notification Rule",
    grain="One row per notification trigger",
    note="ADDED v4. Built now, mostly switched off. Two are on from day one: an upload notifies "
         "the portfolio org box, and a status change notifies the submitter. Everything else "
         "ships disabled so the queue can be tuned before anyone's inbox is involved.",
    columns=[
        c("Rule_ID", "Text", req=True, indexed=True),
        c("Trigger_Event", "Choice", req=True,
          choices=["SubmissionCreated", "StatusChanged", "DueSoon", "FirstSuspensePassed",
                   "FinalSuspensePassed", "CorrectionSuspensePassed", "PendingReviewAging",
                   "AccessRequested"]),
        c("Recipient_Type", "Choice", req=True,
          choices=["Submitter", "Portfolio org box", "Installation POC", "Reviewer",
                   "Portfolio Manager", "AFSVC"]),
        c("Recipient_Address", "Text", note="Org box address when Recipient_Type is a mailbox"),
        c("Enabled", "Boolean", req=True),
        c("Digest", "Boolean", req=True,
          note="TRUE means one message per recipient per run listing everything. Per-item mail is "
               "how a notification system gets muted in week one."),
        c("Cadence_Days", "Number", note="Repeat interval. Null means once."),
        c("Subject_Template", "Text"),
        c("Notes", "Note"),
    ])


# ============================================================================
# v5 — non-duty days
# The nominal suspense is policy. The effective suspense is what a person can
# actually be held to. Both are stored; this list is what separates them.
# ============================================================================

LISTS["MF_Non_Duty_Day"] = dict(
    title="MF Non Duty Day",
    grain="One row per non-duty date",
    note="ADDED v5. Federal holidays, down days, and any locally directed non-duty day. "
         "Without this the effective-suspense calculation has to hard-code a holiday table, "
         "which is wrong the first time a base takes a family day.",
    columns=[
        c("Non_Duty_ID", "Text", req=True, indexed=True),
        c("Date", "DateTime", req=True, indexed=True),
        c("Name", "Text", req=True),
        c("Scope_Type", "Choice", req=True,
          choices=["Enterprise", "Portfolio", "Installation"],
          note="A federal holiday is Enterprise. A wing down day is Installation."),
        c("Scope_ID", "Text", note="Null for Enterprise"),
        c("Active_Flag", "Boolean", req=True),
    ])
