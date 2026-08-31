#!/usr/bin/env python3
"""
MissionFeedingOperations — SharePoint schema, single source of truth.

Twelve lists. Derived from the V3 build (`reference/v3/scripts/eom_schema.py`)
with ten corrections recorded in `docs/handoffs/RECONCILIATION.md`; nothing
here is invented.

    python3 scripts/eom_schema.py --validate
    python3 scripts/eom_schema.py --json > provisioning/schema.generated.json
    python3 scripts/eom_schema.py --markdown > docs/data-model.md
    python3 scripts/eom_schema.py --dictionary > docs/MF_EOM_Data_Dictionary.csv
    python3 scripts/eom_schema.py --summary

Nothing else in this repository may declare a list or a column. The
provisioning script, the data dictionary, the Power Apps data-source contract,
the Power BI fact and the documentation are all generated from or checked
against this module.

Decisions locked by review and carried forward from V3:

  1. Operating_Model lives at FACILITY grain, not installation. One base can
     run a legacy DFAC and a Food 2.0 cafe, and the requirement set follows
     the facility.
  2. Requirement_Scope is Facility | Installation | Contract. Portfolio is
     reserved and not implemented.
  3. Facility_ID is NULLABLE on MF_EOM_Item — null, never empty string — for
     Installation- and Contract-scope rows.
  4. MF_EOM_Item (persistent expected obligation) is separate from
     MF_EOM_Submission (versioned evidence). The checklist row is never
     duplicated on resubmission and no file is ever overwritten.
  5. Unresolved applicability is UNVERIFIED configuration, never code.
  6. Rollups run facility -> installation -> portfolio, over semantic
     statuses and over what the viewer may see.
  7. One security mapping serves both Power Apps filtering and Power BI RLS.

And the two the status model rests on:

  8. Final_Status is the SEMANTIC string. Status_Code is the NUMERIC visual
     code, 0-4. Both are stored, written together by one evaluation, and
     neither is derived from the other.
  9. Nothing that a human sets is a status. There is no colour picker.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass, asdict

SCHEMA_VERSION = "3.0"
EXPECTED_LIST_COUNT = 12
MAX_INDEXES_PER_LIST = 20
MAX_INTERNAL_NAME = 32

TYPES = {"Text", "Note", "Number", "Currency", "DateTime", "Boolean",
         "Choice", "Lookup", "User", "URL", "Calculated"}


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    required: bool = False
    indexed: bool = False
    choices: tuple = ()
    note: str = ""

    def validate(self, list_name):
        errs = []
        if self.type not in TYPES:
            errs.append(f"{list_name}.{self.name}: unknown type {self.type!r}")
        if len(self.name) > MAX_INTERNAL_NAME:
            errs.append(f"{list_name}.{self.name}: internal name is {len(self.name)} "
                        f"chars, SharePoint's limit is {MAX_INTERNAL_NAME}")
        if self.type == "Choice" and not self.choices:
            errs.append(f"{list_name}.{self.name}: choice column with no choices")
        if self.choices and self.type not in ("Choice",):
            errs.append(f"{list_name}.{self.name}: choices on a non-choice column")
        return errs


@dataclass(frozen=True)
class ListDef:
    name: str
    title: str
    grain: str
    columns: tuple
    note: str = ""
    volume_estimate: int = 0
    unique_key: tuple = ()

    @property
    def indexed_columns(self):
        return tuple(c.name for c in self.columns if c.indexed)

    def validate(self):
        errs, seen = [], set()
        for c in self.columns:
            if c.name in seen:
                errs.append(f"{self.name}: duplicate column {c.name}")
            seen.add(c.name)
            errs.extend(c.validate(self.name))
        if len(self.indexed_columns) > MAX_INDEXES_PER_LIST:
            errs.append(f"{self.name}: {len(self.indexed_columns)} indexed columns, "
                        f"SharePoint allows {MAX_INDEXES_PER_LIST}")
        for k in self.unique_key:
            if k not in seen:
                errs.append(f"{self.name}: unique_key names unknown column {k}")
        if not self.grain.strip():
            errs.append(f"{self.name}: no grain declared")
        return errs


def c(name, ctype, req=False, indexed=False, choices=None, note=""):
    return Column(name, ctype, required=req, indexed=indexed,
                  choices=tuple(choices or ()), note=note)


# ==========================================================================
# Controlled vocabularies.
#
# These are referenced by the status engine, the flows, the seeds and the
# Power BI model. They live here and nowhere else.
# ==========================================================================

OPERATING_MODEL = ("Legacy/APF", "Food 2.0", "MAFFO/MAF", "AOR/CDS")
APPLICABLE_MODEL = OPERATING_MODEL + ("All",)

FACILITY_TYPE = ("Main DFAC", "Flight Kitchen", "Kiosk", "Satellite", "MAF",
                 "Contract Cafe")

REQUIREMENT_SCOPE = ("Facility", "Installation", "Contract")   # Portfolio reserved

FREQUENCY = ("Monthly", "Quarterly", "Semiannual", "Annual", "Conditional")

# UNVERIFIED requirements generate items but never drive Red. All twelve
# seeded requirements are UNVERIFIED today, so that is the default path.
AUTHORITY_STATUS = ("Verified", "UNVERIFIED", "Management decision")

# The eight semantic statuses. Final_Status.
FINAL_STATUS = (
    "NOT_APPLICABLE",
    "NOT_DUE",
    "PENDING_VALIDATION",
    "OVERDUE",
    "NOT_SATISFIED",
    "CORRECTION_REQUIRED",
    "RECEIVED_PENDING_QC",
    "ACCEPTED",
)

# The five visual codes. Status_Code. Blue (4) separates "not due yet" and
# "informational" from "not applicable" (0) — four states displayed an
# installation whose requirements had simply not come due as Not Applicable.
STATUS_CODE_VALUES = (0, 1, 2, 3, 4)
STATUS_CODE_NAMES = {0: "Gray", 1: "Red", 2: "Amber", 3: "Green", 4: "Blue"}

ACTION_OWNER = ("Facility", "Reviewer", "Admin", "None")

# Package rollup states. Computed over semantic statuses, never over colour.
PACKAGE_STATE = ("ACTION_REQUIRED", "IN_REVIEW", "COMPLETE", "IN_PROGRESS",
                 "NOT_APPLICABLE")

QC_STATUS = ("Pending Review", "Accepted", "Correction Required",
             "Wrong Document", "Not Applicable")

INTAKE_METHOD = ("App upload", "Folder drop", "Manual classification")

CLASSIFICATION_METHOD = ("Declared at upload", "Folder context",
                         "Document content", "AI Builder", "Manual")

CLASSIFICATION_STATUS = ("Pending", "Classified", "Needs Review", "Failed")

CLASSIFICATION_CONFIDENCE = ("Declared", "High", "Low", "Unresolved")

RESOLUTION_STATUS = ("Needs Classification", "Classified",
                     "Not an EOM document", "Duplicate")

SCOPE_TYPE = ("Enterprise", "Portfolio", "Installation", "Facility")

ROLE = ("DFAC Manager", "Accountant", "MFM", "Portfolio Manager",
        "AFSVC Leadership", "Admin")

FLAG_ROLE = ROLE + ("Developer",)

CONFIG_TYPE = ("String", "Boolean", "Number", "Date")

AUDIT_ENTITY = ("EOM_Item", "EOM_Submission", "Requirement")

AUDIT_ACTION = ("Generated", "Uploaded", "QC Accepted", "QC Correction Required",
                "QC Wrong Document", "QC Not Applicable", "Waived",
                "Reclassified", "Status Recalculated", "Notification Suppressed",
                "Notification Sent")

EVENT_TYPE = ("AppOpened", "DocumentDiscovered", "SubmissionCreated",
              "VersionSuperseded", "ClassificationSucceeded",
              "ClassificationUncertain", "ManualClassification",
              "ExpectedItemMatched", "QCAccepted", "QCCorrectionRequired",
              "QCWrongDocument", "ExpectedGenerationFailed",
              "ReconciliationMismatch", "FlowFailure", "PermissionDenied",
              "MaintenanceModeBlocked")

EVENT_RESULT = ("Success", "Warning", "Failure")


# ==========================================================================
# Reference lists
# ==========================================================================

MF_Installation = ListDef(
    name="MF_Installation",
    title="MF Installation",
    grain="One row per installation",
    volume_estimate=89,
    unique_key=("Installation_ID",),
    columns=(
        c("Installation_ID", "Text", req=True, indexed=True,
          note="Canonical key. Must match the COP MF_Installation.Installation_ID."),
        c("Installation_Name", "Text", req=True),
        c("Portfolio_ID", "Text", req=True, indexed=True),
        c("MAJCOM", "Text"),
        c("EOM_Folder_URL", "URL",
          note="Teams/SharePoint FY folder root for this installation"),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_Facility = ListDef(
    name="MF_Facility",
    title="MF Facility",
    grain="One row per feeding facility",
    volume_estimate=500,
    unique_key=("Facility_ID",),
    note="Operating_Model is HERE, not on the installation. One base can run a "
         "legacy DFAC and a Food 2.0 cafe simultaneously; the requirement set is "
         "driven by the facility's model.",
    columns=(
        c("Facility_ID", "Text", req=True, indexed=True,
          note="Unique enterprise-wide, not per installation"),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Facility_Name", "Text", req=True),
        c("Facility_Type", "Choice", req=True, choices=FACILITY_TYPE),
        c("Operating_Model", "Choice", req=True, choices=OPERATING_MODEL, indexed=True,
          note="Drives which requirements apply to THIS facility"),
        c("Contract_ID", "Text",
          note="Nullable. Set where the facility is covered by a contract."),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_EOM_Requirement = ListDef(
    name="MF_EOM_Requirement",
    title="MF EOM Requirement",
    grain="One row per document requirement per operating model",
    volume_estimate=200,
    unique_key=("Requirement_ID",),
    note="THE requirement engine. The app queries this; it contains no "
         "'if Legacy then require 1119' logic. Changing a requirement next year "
         "is a list edit, not an app rebuild. The drop boxes on the installation "
         "screen ARE this list, filtered.",
    columns=(
        c("Requirement_ID", "Text", req=True, indexed=True),
        c("Document_Code", "Text", req=True,
          note="1119, 1119-1, SIK, SF1080, DAF79, 1038, SAIIT, CONTRACTOR-INV"),
        c("Document_Name", "Text", req=True),
        c("Applicable_Model", "Choice", req=True, choices=APPLICABLE_MODEL,
          note="'All' applies regardless of facility model"),
        c("Requirement_Scope", "Choice", req=True, choices=REQUIREMENT_SCOPE,
          note="Determines the grain of the generated EOM_Item. Portfolio reserved, "
               "not implemented."),
        c("Applicable_Facility_Types", "Text",
          note="Semicolon list. Blank = all types. Kiosks rarely file a 1119."),
        c("Frequency", "Choice", req=True, choices=FREQUENCY),
        c("Required_Flag", "Boolean", req=True),
        c("Due_Day", "Number",
          note="Day of the month following the reporting period. Configurable — "
               "changing 10 to 15 never touches the app."),
        c("Due_Offset_Months", "Number",
          note="Usually 1. Set higher for lagging requirements."),
        c("QC_Required", "Boolean", req=True),
        c("Accepted_File_Types", "Text", note="Advisory only in MVP. xlsx;pdf"),
        c("Authority_Reference", "Text",
          note="UNVERIFIED means do not enforce. The app still shows the box; the "
               "requirement cannot drive an adverse status until validated."),
        c("Authority_Status", "Choice", req=True, choices=AUTHORITY_STATUS, indexed=True,
          note="UNVERIFIED requirements generate items but never drive Red"),
        c("Sort_Order", "Number"),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)


# ==========================================================================
# Transactional lists
# ==========================================================================

MF_EOM_Item = ListDef(
    name="MF_EOM_Item",
    title="MF EOM Item",
    grain="One PERSISTENT row per expected submission per reporting period",
    volume_estimate=250000,
    unique_key=("EOM_Item_ID",),
    note="Generated by EOM-01. Created once and never duplicated. Corrections "
         "attach as new MF_EOM_Submission versions pointing at the same item. "
         "Facility_ID is NULL for Installation and Contract scope. This is the "
         "list that crosses the delegation ceiling first, so every column a "
         "production query touches is indexed and Reporting_Period is always "
         "the first filter.",
    columns=(
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("EOM_Item_Key", "Text", req=True, indexed=True,
          note="Human-readable compound key: LACKLAND|BLDG1234|2026-10|1119. Drives "
               "duplicate prevention and flow idempotency."),
        c("Portfolio_ID", "Text", req=True, indexed=True,
          note="Denormalized. The portfolio filter is the first server-side filter "
               "on every query, so it must be on the row."),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Facility_ID", "Text", indexed=True,
          note="NULLABLE — null, never empty string. Null for Installation-scope "
               "and Contract-scope rows."),
        c("Contract_ID", "Text", note="NULLABLE. Set for Contract-scope rows."),
        c("Reporting_Period", "Text", req=True, indexed=True, note="YYYY-MM"),
        c("Requirement_ID", "Text", req=True, indexed=True),
        c("Requirement_Scope", "Choice", req=True, choices=REQUIREMENT_SCOPE,
          note="Denormalized from the requirement so the app filters without a join. "
               "Also how the app asks 'is this a facility row' — IsBlank(Facility_ID) "
               "does not delegate."),
        # C4. Decision rule 2 reads this. A join does not delegate, so without it
        # the app cannot evaluate its own second rule.
        c("Authority_Status", "Choice", req=True, choices=AUTHORITY_STATUS, indexed=True,
          note="Denormalized at generation. Rule 2 of the status engine reads it, and "
               "a lookup to MF_EOM_Requirement would not delegate."),
        c("Required_Flag", "Boolean", req=True),
        c("Due_Date", "DateTime", req=True, indexed=True),
        c("Current_Submission_ID", "Text",
          note="Points at the Is_Current submission. Null until the first upload."),
        c("Received_Flag", "Boolean", req=True),
        # C5. V3's own DAX referenced MF_EOM_Item[Received_Date], which did not exist.
        c("Received_DateTime", "DateTime",
          note="Upload timestamp of the current submission. Null until received."),
        c("Final_Status", "Choice", req=True, choices=FINAL_STATUS, indexed=True,
          note="SEMANTIC status. Calculated by EOM-03 and by the app's QC action, "
               "never user-selectable. Independent of Status_Code — one evaluation "
               "writes both; neither is derived from the other."),
        c("Status_Code", "Number", req=True, indexed=True,
          note="VISUAL code only. 0 Gray not-applicable, 1 Red overdue, 2 Amber "
               "needs attention, 3 Green accepted, 4 Blue not-due/informational. "
               "Five states, not four: collapsing 'not applicable' and 'not due yet' "
               "into Gray made an installation whose requirements had simply not "
               "come due read as Not Applicable. Stored so Filter() delegates."),
        c("Action_Owner", "Choice", req=True, choices=ACTION_OWNER,
          note="Status_Code alone cannot answer 'is this mine'. Amber covers both "
               "correction needed (facility) and awaiting review (AFSVC). Home "
               "filters on this, not on colour."),
        c("Action_Required", "Boolean", req=True, indexed=True),
        # C6. EOM-03's spec sets these rather than leaving them to DAX.
        c("Days_Late", "Number",
          note="Set by EOM-03, not computed in DAX. Null until received or overdue."),
        c("On_Time_Flag", "Boolean", note="Received on or before Due_Date."),
        # C7. MASTER's stale-reconciliation health check has nothing to check
        # without this.
        c("Last_Reconciled_DateTime", "DateTime",
          note="Stamped by EOM-03. System Health flags items not reconciled recently."),
        c("Exception_Flag", "Boolean", req=True,
          note="Set when the item needs human attention beyond normal QC"),
        c("Correction_Due", "DateTime", note="Set when QC returns a correction"),
        c("Waived_Flag", "Boolean",
          note="Portfolio Manager may waive a requirement for a period"),
        c("Waiver_Reason", "Note"),
    ),
)

MF_EOM_Submission = ListDef(
    name="MF_EOM_Submission",
    title="MF EOM Submission",
    grain="One row per uploaded file version",
    volume_estimate=400000,
    unique_key=("Submission_ID",),
    note="Versioned evidence. v1 Correction Required and v2 Accepted both persist; "
         "nothing is overwritten or deleted. QC applies to the Is_Current version.",
    columns=(
        c("Submission_ID", "Text", req=True, indexed=True),
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("Version_No", "Number", req=True, note="Assigned by upload timestamp order"),
        c("File_Name", "Text", req=True,
          note="As uploaded. No naming convention required, and the name is never "
               "read for meaning."),
        c("File_URL", "URL", req=True,
          note="THE LIST ROW IS TRUTH, THE PATH IS CONVENIENCE. Never derive status "
               "from the path — files get moved and renamed."),
        c("File_Size_KB", "Number"),
        c("Uploaded_By", "User", req=True, note="SharePoint identity of the actual uploader"),
        c("Uploaded_DateTime", "DateTime", req=True, indexed=True),
        c("Submitted_On_Behalf_Of", "Text",
          note="Facility_ID or Installation_ID when an AFSVC MFM uploads a document "
               "that arrived by email. Without this, emailed submissions misattribute "
               "to AFSVC and the missing/overdue counts go wrong silently."),
        c("Intake_Method", "Choice", req=True, choices=INTAKE_METHOD,
          note="App upload needs no classification. Folder drop may."),
        c("Classification_Method", "Choice", choices=CLASSIFICATION_METHOD,
          note="'Declared at upload' is the production baseline. Filename is NEVER "
               "a method, at any tier."),
        c("Classification_Status", "Choice", choices=CLASSIFICATION_STATUS, indexed=True),
        c("Classification_Confidence", "Choice", choices=CLASSIFICATION_CONFIDENCE,
          note="'Declared' = the app captured it at upload. That is the whole point "
               "of making the app the front door."),
        c("Last_Error_Code", "Text"),
        c("Last_Error_Message", "Note",
          note="User-facing, plain language. Never a raw HTTP status."),
        c("Last_Processing_DateTime", "DateTime"),
        c("Retry_Count", "Number"),
        c("Source_Path", "Text",
          note="Where the file was found. Diagnostic only — the list row is truth."),
        c("SharePoint_File_ID", "Text", indexed=True,
          note="Survives a rename or move; the URL does not."),
        c("Is_Current", "Boolean", req=True, indexed=True),
        c("Superseded_By", "Text",
          note="Submission_ID of the version that replaced this one"),
        c("QC_Status", "Choice", req=True, choices=QC_STATUS, indexed=True),
        c("QC_By", "User"),
        c("QC_DateTime", "DateTime"),
        c("QC_Comment", "Note",
          note="REQUIRED when QC_Status is Correction Required or Wrong Document"),
    ),
)

MF_Unmatched_File = ListDef(
    name="MF_Unmatched_File",
    title="MF Unmatched File",
    grain="One row per file found in the FY folder that could not be resolved",
    volume_estimate=5000,
    unique_key=("Unmatched_ID",),
    note="The safety net for folder drops. Should trend toward empty once people "
         "use the app. No content parsing and no AI Builder in MVP — a human picks "
         "from dropdowns. NEVER INVENT A REQUIREMENT: resolving a row here attaches "
         "the file to an existing expected item and never creates one.",
    columns=(
        c("Unmatched_ID", "Text", req=True, indexed=True),
        c("File_Name", "Text", req=True),
        c("File_URL", "URL", req=True),
        c("Portfolio_ID", "Text", indexed=True,
          note="Derivable from the folder — that much the path gives us"),
        c("Fiscal_Year", "Text", note="Derivable from the folder"),
        c("Discovered_DateTime", "DateTime", req=True, indexed=True),
        c("Uploaded_By", "User"),
        c("Suggested_Installation_ID", "Text", note="Weak hint only. Never auto-applied."),
        c("Suggested_Document_Code", "Text", note="Weak hint only."),
        c("Resolution_Status", "Choice", req=True, choices=RESOLUTION_STATUS, indexed=True),
        c("Resolved_Submission_ID", "Text"),
        c("Resolved_By", "User"),
        c("Resolved_DateTime", "DateTime"),
    ),
)

MF_Security_Mapping = ListDef(
    name="MF_Security_Mapping",
    title="MF Security Mapping",
    grain="One row per user per granted scope",
    volume_estimate=5000,
    unique_key=("Security_ID",),
    note="ONE mapping for both Power Apps filtering and Power BI RLS. Do not "
         "maintain two permission models. Also drives dropdown defaulting: a DFAC "
         "manager with one facility row sees no dropdowns at all, just an upload box.",
    columns=(
        c("Security_ID", "Text", req=True, indexed=True),
        c("UPN", "Text", req=True, indexed=True),
        c("Scope_Type", "Choice", req=True, choices=SCOPE_TYPE, indexed=True),
        c("Portfolio_ID", "Text", indexed=True),
        c("Installation_ID", "Text", indexed=True),
        c("Facility_ID", "Text", indexed=True),
        c("Role", "Choice", req=True, choices=ROLE),
        c("Can_QC", "Boolean", req=True, note="Portfolio Manager and Admin only"),
        c("Can_Submit_On_Behalf", "Boolean", req=True,
          note="MFM, Portfolio Manager, Admin"),
        c("Can_Edit_Requirements", "Boolean", req=True, note="Admin only"),
        c("Developer_Flag", "Boolean", req=True,
          note="Sees feature-flagged and diagnostic surfaces. Required because a DAF "
               "tenant may allow only ONE environment — unreleased work has to "
               "coexist with production safely."),
        c("Tester_Flag", "Boolean", req=True, note="Sees Enabled_Testers features only"),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_EOM_Audit = ListDef(
    name="MF_EOM_Audit",
    title="MF EOM Audit",
    grain="One row per state change",
    volume_estimate=1000000,
    unique_key=("Audit_ID",),
    note="Cheap now, invaluable during an IG. Every QC decision, every generated "
         "item, and every notification the system decided not to send.",
    columns=(
        c("Audit_ID", "Text", req=True, indexed=True),
        c("Entity_Type", "Choice", req=True, choices=AUDIT_ENTITY),
        c("Entity_ID", "Text", req=True, indexed=True),
        c("Action", "Choice", req=True, choices=AUDIT_ACTION, indexed=True),
        c("Actor_UPN", "Text", req=True),
        c("Action_DateTime", "DateTime", req=True, indexed=True),
        c("Old_Value", "Text"),
        c("New_Value", "Text"),
        c("Detail", "Note"),
    ),
)


# ==========================================================================
# Government single-environment safety, capability gating, telemetry
#
# Driven by the constraint that a DAF tenant may allow exactly ONE Power
# Platform environment. Everything below exists so unreleased work can sit
# safely alongside production in the same environment. These are not
# nice-to-haves; they are the substitute for an environment tier.
# ==========================================================================

MF_App_Config = ListDef(
    name="MF_App_Config",
    title="MF App Config",
    grain="One row per configuration key",
    volume_estimate=100,
    unique_key=("Config_Key",),
    note="Admin-managed, read-only to everyone else. This is the kill switch: when "
         "something breaks after a publish you flip MaintenanceMode rather than "
         "racing to unpublish. Every environment-variable value has a matching row "
         "here, so neither path is load-bearing alone.",
    columns=(
        c("Config_Key", "Text", req=True, indexed=True),
        c("Config_Value", "Text", req=True),
        c("Config_Type", "Choice", req=True, choices=CONFIG_TYPE),
        c("Description", "Note"),
        c("Admin_Only", "Boolean", req=True),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_Feature_Flags = ListDef(
    name="MF_Feature_Flags",
    title="MF Feature Flags",
    grain="One row per feature",
    volume_estimate=100,
    unique_key=("Feature_Key",),
    note="Ship a new screen inside the published app while normal users still see "
         "the old one. Beats the manual old-screen/new-screen rename: no rebuild, "
         "and the rollback is a checkbox.",
    columns=(
        c("Feature_Key", "Text", req=True, indexed=True),
        c("Feature_Name", "Text", req=True),
        c("Enabled_Prod", "Boolean", req=True),
        c("Enabled_Testers", "Boolean", req=True),
        c("Minimum_Role", "Choice", req=True, choices=FLAG_ROLE),
        c("Effective_Date", "DateTime"),
        c("Notes", "Note"),
    ),
)

MF_App_Event_Log = ListDef(
    name="MF_App_Event_Log",
    title="MF App Event Log",
    grain="One row per meaningful business event",
    volume_estimate=2000000,
    unique_key=("Event_ID",),
    note="Business telemetry, NOT click tracking. Answers 'why didn't Minot's 1119 "
         "show up' operationally, and 'how many manual interventions did we avoid' "
         "strategically. Append-only; never bind a gallery directly to it.",
    columns=(
        c("Event_ID", "Text", req=True, indexed=True),
        c("Event_DateTime", "DateTime", req=True, indexed=True),
        c("User_UPN", "Text", req=True, indexed=True),
        c("Role", "Text"),
        c("Portfolio_ID", "Text"),
        c("Installation_ID", "Text", indexed=True),
        c("Facility_ID", "Text"),
        c("Event_Type", "Choice", req=True, choices=EVENT_TYPE, indexed=True),
        c("Record_ID", "Text", indexed=True),
        c("Result", "Choice", req=True, choices=EVENT_RESULT),
        c("Error_Code", "Text"),
        c("Error_Message", "Note"),
        c("App_Version", "Text", req=True,
          note="Which build produced this event. Essential when one environment "
               "holds released and unreleased code at once."),
    ),
)

MF_EOM_Status = ListDef(
    name="MF_EOM_Status",
    title="MF EOM Status",
    grain="One flat row per EOM item — the canonical Power BI fact",
    volume_estimate=250000,
    unique_key=("Status_ID",),
    note="Materialized by EOM-03. Power BI NEVER reconstructs workflow logic; it "
         "colours on Status_Code and labels with Final_Status. Every workflow "
         "decision is resolved before the report sees the row.",
    columns=(
        c("Status_ID", "Text", req=True, indexed=True),
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("Reporting_Period", "Text", req=True, indexed=True),
        c("Fiscal_Year", "Text", req=True),
        c("Portfolio_ID", "Text", req=True, indexed=True),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Installation_Name", "Text", req=True),
        c("Facility_ID", "Text", indexed=True,
          note="Null for Installation and Contract scope"),
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
        # C8. V3 carried Final_Status AND a duplicate Status_Semantic. Two columns
        # that must always agree are a defect waiting to happen.
        c("Final_Status", "Text", req=True, indexed=True,
          note="The semantic string, copied verbatim from the item. This is the ONLY "
               "semantic column: Power BI labels with it and never re-derives it."),
        c("Status_Code", "Number", req=True, indexed=True,
          note="0 Gray 1 Red 2 Amber 3 Green 4 Blue. Copied verbatim from the item."),
        c("Action_Owner", "Text", req=True),
        c("Action_Required", "Boolean", req=True),
        c("Package_State", "Text", req=True, choices=(),
          note="Facility-level rollup: ACTION_REQUIRED | IN_REVIEW | COMPLETE | "
               "IN_PROGRESS | NOT_APPLICABLE. Computed over semantic statuses, never "
               "over colour codes — a colour rollup calls [ACCEPTED, NOT_DUE, NOT_DUE] "
               "Complete when it is IN_PROGRESS."),
        c("Days_Late", "Number"),
        c("On_Time_Flag", "Boolean"),
        c("Current_File_URL", "URL"),
        c("Generated_DateTime", "DateTime", req=True),
    ),
)


LISTS = (
    MF_Installation,
    MF_Facility,
    MF_EOM_Requirement,
    MF_EOM_Item,
    MF_EOM_Submission,
    MF_Unmatched_File,
    MF_Security_Mapping,
    MF_EOM_Audit,
    MF_App_Config,
    MF_Feature_Flags,
    MF_App_Event_Log,
    MF_EOM_Status,
)

LISTS_BY_NAME = {l.name: l for l in LISTS}


def total_columns():
    return sum(len(l.columns) for l in LISTS)


def validate():
    errs = []
    if len(LISTS) != EXPECTED_LIST_COUNT:
        errs.append(f"expected {EXPECTED_LIST_COUNT} lists, found {len(LISTS)}")
    seen = set()
    for l in LISTS:
        if l.name in seen:
            errs.append(f"duplicate list {l.name}")
        seen.add(l.name)
        errs.extend(l.validate())

    item = LISTS_BY_NAME["MF_EOM_Item"]
    by_name = {c.name: c for c in item.columns}

    # Reporting_Period is the first filter in every production query, and
    # MF_EOM_Item crosses the delegation ceiling in the first year.
    for required in ("Reporting_Period", "Portfolio_ID", "Installation_ID",
                     "Facility_ID", "Status_Code", "Final_Status",
                     "Authority_Status", "Action_Required", "Due_Date"):
        col = by_name.get(required)
        if col is None:
            errs.append(f"MF_EOM_Item is missing {required}")
        elif not col.indexed:
            errs.append(f"MF_EOM_Item.{required} must be indexed before the list "
                        "crosses 5,000 items — SharePoint will not add it after")

    # Null, never empty string, for Installation- and Contract-scope rows.
    if by_name["Facility_ID"].required:
        errs.append("MF_EOM_Item.Facility_ID must be nullable for Installation "
                    "and Contract scope")

    # Final_Status and Status_Code are both stored, and neither is derived from
    # the other. Losing either one collapses the model back to four states.
    if by_name["Final_Status"].type != "Choice":
        errs.append("MF_EOM_Item.Final_Status must be the semantic Choice column")
    if by_name["Status_Code"].type != "Number":
        errs.append("MF_EOM_Item.Status_Code must be the numeric visual code")

    # The fact carries exactly one semantic column.
    fact_cols = {c.name for c in LISTS_BY_NAME["MF_EOM_Status"].columns}
    if "Status_Semantic" in fact_cols:
        errs.append("MF_EOM_Status carries both Final_Status and Status_Semantic; "
                    "two columns that must always agree are a defect waiting to happen")

    # Never store a percentage or any rate the app would have to recompute.
    for l in LISTS:
        for col in l.columns:
            low = col.name.lower()
            if "percent" in low or low.endswith(("_pct", "_rate")):
                errs.append(f"{l.name}.{col.name}: a stored percentage is forbidden; "
                            "the COP counts packages by state")
    return errs


def to_dict():
    return {
        "schema_version": SCHEMA_VERSION,
        "list_count": len(LISTS),
        "column_count": total_columns(),
        "lists": [
            {**{k: v for k, v in asdict(l).items() if k != "columns"},
             "columns": [asdict(c_) for c_ in l.columns],
             "indexed_columns": list(l.indexed_columns)}
            for l in LISTS
        ],
        "vocabularies": {
            "OPERATING_MODEL": list(OPERATING_MODEL),
            "APPLICABLE_MODEL": list(APPLICABLE_MODEL),
            "FACILITY_TYPE": list(FACILITY_TYPE),
            "REQUIREMENT_SCOPE": list(REQUIREMENT_SCOPE),
            "FREQUENCY": list(FREQUENCY),
            "AUTHORITY_STATUS": list(AUTHORITY_STATUS),
            "FINAL_STATUS": list(FINAL_STATUS),
            "STATUS_CODE_VALUES": list(STATUS_CODE_VALUES),
            "ACTION_OWNER": list(ACTION_OWNER),
            "PACKAGE_STATE": list(PACKAGE_STATE),
            "QC_STATUS": list(QC_STATUS),
            "ROLE": list(ROLE),
            "SCOPE_TYPE": list(SCOPE_TYPE),
        },
    }


def to_markdown():
    out = ["<!-- GENERATED by scripts/eom_schema.py — do not edit by hand. -->", "",
           "# Data model", "",
           f"Schema version **{SCHEMA_VERSION}** — **{len(LISTS)} lists**, "
           f"**{total_columns()} columns**.", "",
           "Derived from the V3 build with the corrections recorded in "
           "[`handoffs/RECONCILIATION.md`](handoffs/RECONCILIATION.md). Regenerate "
           "with `python3 scripts/eom_schema.py --markdown > docs/data-model.md`.", "",
           "| List | Grain | Columns | Indexed | Est. rows (yr 1) |",
           "|---|---|---:|---:|---:|"]
    for l in LISTS:
        out.append(f"| `{l.name}` | {l.grain} | {len(l.columns)} | "
                   f"{len(l.indexed_columns)} | {l.volume_estimate:,} |")
    out.append("")
    for l in LISTS:
        out += [f"## `{l.name}`", "", f"**Grain:** {l.grain}", ""]
        if l.note:
            out += [l.note, ""]
        if l.unique_key:
            out += ["Unique key: " + ", ".join(f"`{k}`" for k in l.unique_key), ""]
        out += ["| Column | Type | Req | Idx | Notes |", "|---|---|:-:|:-:|---|"]
        for col in l.columns:
            note = col.note
            if col.choices:
                note = (note + " " if note else "") + "Choices: " + \
                    ", ".join(f"`{x}`" for x in col.choices) + "."
            out.append(f"| `{col.name}` | {col.type} | {'Y' if col.required else ''} "
                       f"| {'Y' if col.indexed else ''} | {note} |")
        out.append("")
    return "\n".join(out)


def to_dictionary_csv():
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["List", "Display_Title", "Grain", "Column", "Type", "Required",
                "Indexed", "Choices", "Column_Note", "List_Note"])
    for l in LISTS:
        for col in l.columns:
            w.writerow([l.name, l.title, l.grain, col.name, col.type,
                        "Y" if col.required else "N",
                        "Y" if col.indexed else "N",
                        "; ".join(col.choices), col.note, l.note])
    return buf.getvalue()


def summary():
    lines = [f"MissionFeedingOperations schema v{SCHEMA_VERSION}"]
    for l in LISTS:
        lines.append(f"  {l.name:<22}{len(l.columns):>4} columns  "
                     f"{len(l.indexed_columns):>2} indexed  ~{l.volume_estimate:,} rows")
    lines.append(f"  {'TOTAL':<22}{total_columns():>4} columns across {len(LISTS)} lists")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--dictionary", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--validate", action="store_true")
    args = p.parse_args(argv)

    emitting = args.json or args.markdown or args.dictionary or args.summary
    if args.validate or not emitting:
        errs = validate()
        if errs:
            for e in errs:
                print(f"SCHEMA ERROR: {e}", file=sys.stderr)
            return 1
        if not emitting:
            print(summary())
            print("\nschema OK")
            return 0

    if args.json:
        print(json.dumps(to_dict(), indent=2))
    if args.markdown:
        print(to_markdown())
    if args.dictionary:
        sys.stdout.write(to_dictionary_csv())
    if args.summary:
        print(summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
