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
        c("EOM_Folder_URL", "URL", note="Teams/SharePoint FY folder root for this installation"),
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
          choices=["Monthly", "Quarterly", "Semiannual", "Annual", "Conditional"]),
        c("Required_Flag", "Boolean", req=True),
        c("Due_Day", "Number", note="Day of the month following the reporting period. "
                                    "Configurable — changing 10 to 15 never touches the app."),
        c("Due_Offset_Months", "Number", note="Usually 1. Set higher for lagging requirements."),
        c("QC_Required", "Boolean", req=True),
        c("Accepted_File_Types", "Text", note="Advisory only in MVP. xlsx;pdf"),
        c("Authority_Reference", "Text",
          note="UNVERIFIED means do not enforce. The app still shows the box; the "
               "requirement is inactive until validated."),
        c("Authority_Status", "Choice", req=True,
          choices=["Verified", "UNVERIFIED", "Management decision"],
          note="UNVERIFIED requirements generate items but never drive Red"),
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
        c("Due_Date", "DateTime", req=True),
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
          choices=["Pending Review", "Accepted", "Correction Required", "Wrong Document",
                   "Not Applicable"]),
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
          choices=["DFAC Manager", "Accountant", "MFM", "Portfolio Manager",
                   "AFSVC Leadership", "Admin"]),
        c("Can_QC", "Boolean", req=True, note="Portfolio Manager and Admin only"),
        c("Can_Submit_On_Behalf", "Boolean", req=True, note="MFM, Portfolio Manager, Admin"),
        c("Can_Edit_Requirements", "Boolean", req=True, note="Admin only"),
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
