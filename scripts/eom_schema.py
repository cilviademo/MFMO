#!/usr/bin/env python3
"""
MissionFeedingOperations — SharePoint schema, single source of truth.

Schema version 2.0 — 12 lists, 164 columns.

Nothing else in this repository may declare a list or a column. The
provisioning script, the validation script, the flow definitions, the
Power Fx data-source contract and the documentation are all generated
from or checked against this module.

    python3 scripts/eom_schema.py --validate
    python3 scripts/eom_schema.py --json  > provisioning/schema.generated.json
    python3 scripts/eom_schema.py --markdown > docs/data-model.md
    python3 scripts/eom_schema.py --summary

Design rules enforced here (see docs/status-calculation.md):

  * No column stores a percentage or any figure the app would have to
    recompute. ``Status_Code`` is stored precisely so ``Filter()`` on it
    delegates to the server.
  * ``Facility_ID`` is nullable, never an empty string, for
    Installation- and Contract-scope rows.
  * Every column a production query filters, sorts or joins on is
    indexed. SharePoint refuses to add an index to a list that has
    already crossed the 5,000-item list view threshold, so the indexes
    are created at provisioning time or never.
  * SharePoint permits at most 20 indexed columns per list.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict

SCHEMA_VERSION = "2.0"
EXPECTED_LIST_COUNT = 12
EXPECTED_COLUMN_COUNT = 164
MAX_INDEXES_PER_LIST = 20

# SharePoint internal names may not exceed 32 characters before the
# encoding SharePoint applies to spaces and punctuation. We only ever
# create columns whose internal name equals the field name below.
MAX_INTERNAL_NAME = 32

TYPES = {
    "Text",        # single line of text
    "Note",        # multi-line plain text
    "Number",
    "Boolean",
    "DateTime",
    "Choice",
    "MultiChoice",
    "Url",
}


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    description: str
    required: bool = False
    indexed: bool = False
    nullable: bool = True
    choices: tuple = ()
    default: object = None
    max_length: int = 255
    # ``title`` marks the built-in SharePoint Title field, renamed. It is
    # always present, always indexed by SharePoint, and counts toward the
    # column total because it carries real meaning in every list here.
    title: bool = False

    def validate(self, list_name: str) -> list:
        errs = []
        if self.type not in TYPES:
            errs.append(f"{list_name}.{self.name}: unknown type {self.type!r}")
        if len(self.name) > MAX_INTERNAL_NAME:
            errs.append(
                f"{list_name}.{self.name}: internal name is "
                f"{len(self.name)} chars, limit {MAX_INTERNAL_NAME}"
            )
        if self.type in ("Choice", "MultiChoice") and not self.choices:
            errs.append(f"{list_name}.{self.name}: choice column with no choices")
        if self.type not in ("Choice", "MultiChoice") and self.choices:
            errs.append(f"{list_name}.{self.name}: choices on a non-choice column")
        if self.required and self.nullable is False and self.default is None:
            pass  # required + non-nullable + no default is legitimate
        if not self.description.strip():
            errs.append(f"{list_name}.{self.name}: missing description")
        return errs


@dataclass(frozen=True)
class ListDef:
    name: str
    display_name: str
    description: str
    columns: tuple
    # Rows expected in the first production year. Anything over the 5,000
    # list view threshold makes delegation mandatory rather than advisory.
    volume_estimate: int = 0
    versioning: bool = False
    unique_key: tuple = ()

    @property
    def indexed_columns(self):
        return tuple(c.name for c in self.columns if c.indexed or c.title)

    def validate(self) -> list:
        errs = []
        seen = set()
        titles = [c for c in self.columns if c.title]
        if len(titles) != 1:
            errs.append(f"{self.name}: expected exactly one Title column, found {len(titles)}")
        for c in self.columns:
            if c.name in seen:
                errs.append(f"{self.name}: duplicate column {c.name}")
            seen.add(c.name)
            errs.extend(c.validate(self.name))
        if len(self.indexed_columns) > MAX_INDEXES_PER_LIST:
            errs.append(
                f"{self.name}: {len(self.indexed_columns)} indexed columns, "
                f"SharePoint allows {MAX_INDEXES_PER_LIST}"
            )
        for k in self.unique_key:
            if k not in seen:
                errs.append(f"{self.name}: unique_key names unknown column {k}")
        return errs


# --------------------------------------------------------------------------
# Controlled vocabularies. These are referenced by the flows, the Power Fx
# and the Power BI model, so they live here and nowhere else.
# --------------------------------------------------------------------------

REQUIREMENT_SCOPE = ("Facility", "Installation", "Contract")

OPERATING_MODEL = ("Legacy_DFAC", "Food_2_0", "Hybrid", "Contractor_Operated")

FACILITY_TYPE = ("DFAC", "Cafe", "Grab_and_Go", "Field_Feeding", "Warehouse", "Other")

VERIFICATION_STATUS = ("UNVERIFIED", "VERIFIED", "RETIRED")

FREQUENCY = ("Monthly", "Quarterly", "SemiAnnual", "Annual")

PERIOD_TYPE = ("Month", "Quarter", "FiscalYear")

PERIOD_STATE = ("FUTURE", "OPEN", "CLOSING", "CLOSED")

# The eleven status codes. One engine, one evaluation. See
# docs/status-calculation.md and scripts/status_engine.py.
STATUS_CODE = (
    "NOT_DUE",
    "DUE_SOON",
    "SUBMITTED",
    "IN_REVIEW",
    "RETURNED",
    "ACCEPTED",
    "OVERDUE",
    "PROVISIONAL_OVERDUE",
    "WAIVED",
    "NOT_APPLICABLE",
    "SUPERSEDED",
)

# Five visual states. Blue separates "not due yet" from "not applicable".
FINAL_STATUS = ("Blue", "Amber", "Red", "Green", "Gray")

ACTION_OWNER = ("Facility", "Reviewer", "Program", "None")

QC_STATUS = ("PENDING", "IN_REVIEW", "ACCEPTED", "RETURNED")

SUBMISSION_CHANNEL = ("APP_UPLOAD", "FOLDER_DROP", "ADMIN")

# Tier 0 through tier 4 of the classification ladder. Tiers 2 and 3 are
# behind feature flags that ship False.
CLASSIFICATION_METHOD = (
    "DECLARED",       # tier 0 — production baseline, ~95% of volume
    "FOLDER_HINT",    # tier 1 — suggestion only, never applied
    "CONTENT",        # tier 2 — EnableDocumentContentAI, ships False
    "AI_BUILDER",     # tier 3 — EnableAIBuilder, ships False
    "MANUAL",         # tier 4 — the Needs Classification queue
    "UNCLASSIFIED",
)

CLASSIFICATION_STATUS = (
    "CLASSIFIED",
    "NEEDS_CLASSIFICATION",
    "REJECTED_DUPLICATE",
    "ERROR",
)

ROLE = (
    "FacilityUser",
    "FacilityManager",
    "Reviewer",
    "InstallationManager",
    "PortfolioManager",
    "Admin",
    "Developer",
    "Tester",
)

SCOPE_TYPE = ("Facility", "Installation", "Portfolio", "Global")

PRINCIPAL_TYPE = ("User", "Group")

CONFIG_TYPE = ("Text", "Number", "Boolean", "Date")

FLAG_SCOPE = ("Global", "Role", "User")

SEVERITY = ("Debug", "Info", "Warning", "Error")

EVENT_TYPE = (
    "AppOpen",
    "ScreenView",
    "Upload",
    "UploadFailed",
    "QCDecision",
    "Classification",
    "AdminAction",
    "FlowRun",
    "AccessDenied",
    "Error",
)

REQUIREMENT_CATEGORY = (
    "Accountability",
    "Inventory",
    "Financial",
    "Food_Safety",
    "Equipment",
    "Personnel",
    "Contract",
    "Customer",
    "Closeout",
    "Nutrition",
)


def T(name, desc, **kw):
    return Column(name, "Text", desc, **kw)


def N(name, desc, **kw):
    return Column(name, "Number", desc, **kw)


def B(name, desc, **kw):
    return Column(name, "Boolean", desc, **kw)


def D(name, desc, **kw):
    return Column(name, "DateTime", desc, **kw)


def C(name, desc, choices, **kw):
    return Column(name, "Choice", desc, choices=tuple(choices), **kw)


def MC(name, desc, choices, **kw):
    return Column(name, "MultiChoice", desc, choices=tuple(choices), **kw)


def NOTE(name, desc, **kw):
    return Column(name, "Note", desc, **kw)


def URL(name, desc, **kw):
    return Column(name, "Url", desc, **kw)


# ==========================================================================
# 1. MF_Installation — 7 columns
# ==========================================================================
MF_Installation = ListDef(
    name="MF_Installation",
    display_name="MF Installation",
    description="Installations in the portfolio. Parent of facility.",
    volume_estimate=89,
    unique_key=("Installation_ID",),
    columns=(
        T("Title", "Installation name. Renamed Title.", required=True, title=True),
        T("Installation_ID", "Stable business key, e.g. INST-FTLIB.", required=True, indexed=True, nullable=False),
        T("Installation_Code", "Short code used in EOM_Item_Key.", required=True),
        T("Service_Branch", "Owning service, free text so joint sites are expressible."),
        T("Region", "Reporting region."),
        T("Portfolio_ID", "Portfolio this installation rolls into. Denormalized onto every downstream row for delegation.", required=True, indexed=True, nullable=False),
        B("Is_Active", "Inactive installations generate no expected items.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 2. MF_Facility — 12 columns
# ==========================================================================
MF_Facility = ListDef(
    name="MF_Facility",
    display_name="MF Facility",
    description=(
        "Facilities. The operating model lives here, not on the installation: "
        "one base can run a legacy DFAC and a Food 2.0 cafe, and requirements "
        "follow the facility."
    ),
    volume_estimate=400,
    unique_key=("Facility_ID",),
    columns=(
        T("Title", "Facility name. Renamed Title.", required=True, title=True),
        T("Facility_ID", "Stable business key, e.g. FAC-FTLIB-01.", required=True, indexed=True, nullable=False),
        T("Installation_ID", "Parent installation.", required=True, indexed=True, nullable=False),
        T("Installation_Name", "Denormalized for display without a lookup."),
        T("Portfolio_ID", "Denormalized for delegable portfolio filtering.", required=True, indexed=True, nullable=False),
        C("Facility_Type", "Physical type of the facility.", FACILITY_TYPE, required=True),
        C("Operating_Model", "Drives which requirements apply. Non-negotiable: this lives on the facility.", OPERATING_MODEL, required=True, indexed=True),
        T("Contract_ID", "Governing contract when contractor operated. Null otherwise."),
        T("Manager_UPN", "Facility manager UPN. Resolved from Entra, never typed."),
        T("Reviewer_UPN", "Default QC reviewer UPN."),
        D("Go_Live_Date", "First reporting period this facility is expected to report."),
        B("Is_Active", "Inactive facilities generate no expected items.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 3. MF_Contract — 9 columns
# ==========================================================================
MF_Contract = ListDef(
    name="MF_Contract",
    display_name="MF Contract",
    description=(
        "Contracts. A contractor invoice may cover several facilities under "
        "one CLIN, which is why Requirement_Scope includes Contract."
    ),
    volume_estimate=150,
    unique_key=("Contract_ID",),
    columns=(
        T("Title", "Contract name. Renamed Title.", required=True, title=True),
        T("Contract_ID", "Stable business key.", required=True, indexed=True, nullable=False),
        T("CLIN", "Contract line item number the obligation attaches to."),
        T("Vendor_Name", "Prime vendor."),
        T("Installation_ID", "Installation the contract is administered from.", indexed=True),
        T("Portfolio_ID", "Denormalized for delegable portfolio filtering.", required=True, indexed=True),
        D("Period_Start", "Period of performance start."),
        D("Period_End", "Period of performance end."),
        B("Is_Active", "Inactive contracts generate no expected items.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 4. MF_Requirement — 19 columns
# ==========================================================================
MF_Requirement = ListDef(
    name="MF_Requirement",
    display_name="MF Requirement",
    description=(
        "The requirement catalogue. Seeded with twelve provisional rows. "
        "Verification_Status governs whether a missed suspense is allowed to "
        "drive Red: an UNVERIFIED requirement never does."
    ),
    volume_estimate=200,
    unique_key=("Requirement_ID",),
    columns=(
        T("Title", "Requirement name. Renamed Title.", required=True, title=True),
        T("Requirement_ID", "Stable business key, e.g. REQ-001.", required=True, indexed=True, nullable=False),
        T("Requirement_Code", "Short code used in EOM_Item_Key.", required=True),
        C("Requirement_Category", "Reporting category.", REQUIREMENT_CATEGORY, required=True),
        C("Requirement_Scope", "Facility, Installation or Contract. Determines whether Facility_ID is null.", REQUIREMENT_SCOPE, required=True, indexed=True),
        MC("Applies_To_Operating_Model", "Operating models this requirement applies to. Empty means all.", OPERATING_MODEL),
        C("Frequency", "How often the obligation recurs.", FREQUENCY, required=True, indexed=True),
        T("Due_Rule", "Human-readable rule, e.g. 'EOM+5BD'. Documentation for the offsets below, never parsed at runtime."),
        N("Due_Offset_Days", "Days after period end that the document is due.", required=True),
        N("Suspense_Offset_Days", "Days after period end that the document becomes late. Must be >= Due_Offset_Days."),
        C("Verification_Status", "UNVERIFIED until a named authority is confirmed.", VERIFICATION_STATUS, required=True, indexed=True),
        D("Verification_Date", "Date the authority reference was confirmed. Null while UNVERIFIED."),
        NOTE("Authority_Reference", "Regulation, contract clause or policy memo the requirement rests on."),
        T("Accepted_File_Types", "Comma-separated extensions accepted at upload."),
        B("Requires_QC", "False means an accepted upload closes the item without review.", default=True),
        C("QC_Role", "Role that performs QC when Requires_QC is true.", ROLE),
        D("Effective_Start_Date", "First period this requirement generates items for."),
        D("Effective_End_Date", "Last period this requirement generates items for. Null means open-ended."),
        B("Is_Active", "Inactive requirements generate no expected items.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 5. MF_Reporting_Period — 9 columns
# ==========================================================================
MF_Reporting_Period = ListDef(
    name="MF_Reporting_Period",
    display_name="MF Reporting Period",
    description=(
        "Fiscal reporting periods. Monthly rows drive EOM; the FiscalYear row "
        "drives EOY closeout. EOM-01 runs against periods in state OPEN."
    ),
    volume_estimate=200,
    unique_key=("Period_ID",),
    columns=(
        T("Title", "Period name, e.g. FY26-P05 or FY26-EOY. Renamed Title.", required=True, title=True),
        T("Period_ID", "Stable business key, identical to Title.", required=True, indexed=True, nullable=False),
        C("Period_Type", "Month, Quarter or FiscalYear.", PERIOD_TYPE, required=True, indexed=True),
        N("Fiscal_Year", "Federal fiscal year, e.g. 2026.", required=True, indexed=True),
        N("Fiscal_Month", "1-12 where 1 is October. Null on FiscalYear rows."),
        D("Period_Start", "First day of the period."),
        D("Period_End", "Last day of the period. All due and suspense dates are offsets from this.", required=True),
        D("Window_Close_Date", "After this date the period accepts no further submissions without an admin override."),
        C("Period_State", "FUTURE, OPEN, CLOSING or CLOSED.", PERIOD_STATE, required=True, indexed=True),
    ),
)

# ==========================================================================
# 6. MF_EOM_Item — 24 columns
# ==========================================================================
MF_EOM_Item = ListDef(
    name="MF_EOM_Item",
    display_name="MF EOM Item",
    description=(
        "The persistent checklist row: one expected obligation per "
        "Facility/Installation/Contract x Requirement x Reporting Period. "
        "Never duplicated on resubmission. This is the list that crosses the "
        "delegation ceiling first, so every column a query touches is indexed "
        "and Reporting_Period_ID is always the first filter."
    ),
    volume_estimate=250000,
    unique_key=("Title",),
    columns=(
        T("Title", "EOM_Item_Key: compound human-readable key, <Scope>|<ScopeID>|<Requirement_Code>|<Period_ID>. Renamed Title and used for idempotency.", required=True, title=True),
        T("EOM_Item_ID", "GUID assigned at generation. Foreign key target for submissions and the fact.", required=True, indexed=True, nullable=False),
        T("Requirement_ID", "Requirement this obligation comes from.", required=True, indexed=True),
        T("Requirement_Name", "Denormalized for display and for the fact."),
        C("Requirement_Scope", "Copied from the requirement so the item filters without a join.", REQUIREMENT_SCOPE, required=True, indexed=True),
        C("Requirement_Verification_Status", "Copied at generation. An UNVERIFIED requirement never drives Red.", VERIFICATION_STATUS, required=True, indexed=True),
        T("Facility_ID", "Null, never empty string, on Installation- and Contract-scope rows.", indexed=True),
        T("Facility_Name", "Denormalized for display."),
        T("Installation_ID", "Always populated, including on facility-scope rows.", required=True, indexed=True),
        T("Installation_Name", "Denormalized for display."),
        T("Contract_ID", "Populated on Contract-scope rows only."),
        T("Portfolio_ID", "Denormalized for delegable portfolio rollups.", required=True, indexed=True),
        T("Reporting_Period_ID", "Always the first filter in every production query.", required=True, indexed=True, nullable=False),
        N("Fiscal_Year", "Denormalized so EOY views filter without a join.", indexed=True),
        D("Due_Date", "Period_End + Requirement.Due_Offset_Days."),
        D("Suspense_Date", "Period_End + Requirement.Suspense_Offset_Days. Reset by a QC return.", indexed=True),
        C("Status_Code", "Stored so Filter() delegates. Written only by the status engine.", STATUS_CODE, required=True, indexed=True),
        T("Status_Semantic", "Human-readable status string stored beside the code. Never derived independently of it."),
        C("Final_Status", "One of five visual states. Independent of Status_Code by design.", FINAL_STATUS, required=True, indexed=True),
        C("Action_Owner_Role", "Who owes the next action.", ACTION_OWNER, required=True),
        B("Action_Required", "True when someone owes an action. Drives My Work.", indexed=True),
        T("Current_Submission_ID", "Submission_ID of the current version. Null until first upload."),
        N("Current_Version_Number", "Version number of the current submission. 0 before first upload.", default=0),
        T("Generation_Run_ID", "EOM-01 run that created the row. Idempotency audit trail."),
    ),
)

# ==========================================================================
# 7. MF_EOM_Submission — 24 columns
# ==========================================================================
MF_EOM_Submission = ListDef(
    name="MF_EOM_Submission",
    display_name="MF EOM Submission",
    description=(
        "One row per uploaded file. Versioned, never overwritten. Rows with a "
        "null EOM_Item_ID and Classification_Status NEEDS_CLASSIFICATION are "
        "the Needs Classification queue: an upload with no matching expected "
        "item lands here and never creates a tracker row."
    ),
    volume_estimate=400000,
    versioning=True,
    unique_key=("Submission_ID",),
    columns=(
        T("Title", "Submission key: <EOM_Item_Key>|v<n>, or UNMATCHED|<guid> when unclassified. Renamed Title.", required=True, title=True),
        T("Submission_ID", "GUID assigned at intake.", required=True, indexed=True, nullable=False),
        T("EOM_Item_ID", "Parent checklist row. NULL for the Needs Classification queue.", indexed=True),
        N("Version_Number", "1 for the first upload against an item, incremented thereafter. Every version is retained.", required=True),
        B("Is_Current_Version", "Exactly one true row per item. Drives the item's Status_Code.", indexed=True),
        T("File_Name", "As uploaded. Evidence only. Filenames are never authoritative and never a classification method."),
        T("SharePoint_File_ID", "The unique file identifier. The list row is truth; the path is convenience.", required=True, indexed=True),
        URL("SharePoint_File_Url", "Convenience link. Re-resolved from SharePoint_File_ID when a file is moved or renamed."),
        N("File_Size_Bytes", "Size at intake."),
        T("Submitted_By_UPN", "Uploader, resolved from Entra identity, never typed.", indexed=True),
        D("Submitted_On", "Intake timestamp.", indexed=True),
        C("Submission_Channel", "APP_UPLOAD is the front door; FOLDER_DROP keeps working.", SUBMISSION_CHANNEL, required=True, indexed=True),
        C("Classification_Method", "Tier 0 DECLARED is the production baseline. Tiers 2 and 3 are feature-flagged off.", CLASSIFICATION_METHOD, required=True),
        C("Classification_Status", "CLASSIFIED, NEEDS_CLASSIFICATION, REJECTED_DUPLICATE or ERROR.", CLASSIFICATION_STATUS, required=True, indexed=True),
        N("Classification_Confidence", "0-100. Always 100 for DECLARED. Advisory only for FOLDER_HINT."),
        T("Suggested_Facility_ID", "Tier 1 folder hint. Displayed as a suggestion, never applied automatically."),
        T("Suggested_Requirement_ID", "Tier 1 folder hint. Displayed as a suggestion, never applied automatically."),
        T("Error_Code", "Machine-readable intake or QC error."),
        NOTE("Error_Message", "Human-readable failure detail for the Needs Classification queue."),
        C("QC_Status", "PENDING, IN_REVIEW, ACCEPTED or RETURNED.", QC_STATUS, indexed=True),
        T("QC_Reviewer_UPN", "Reviewer who made the decision.", indexed=True),
        D("QC_Reviewed_On", "Decision timestamp."),
        NOTE("QC_Comment", "Mandatory on RETURNED. The flow rejects a return without a comment."),
        D("New_Suspense_Date", "Mandatory on RETURNED. Written back to the item's Suspense_Date."),
    ),
)

# ==========================================================================
# 8. MF_EOM_Status — 22 columns
# ==========================================================================
MF_EOM_Status = ListDef(
    name="MF_EOM_Status",
    display_name="MF EOM Status",
    description=(
        "The canonical Power BI fact. One row per checklist item per snapshot. "
        "Every workflow decision is already resolved here so the COP "
        "reconstructs no workflow logic: no DAX in the report may re-derive a "
        "status. Is_Complete and Is_In_Denominator carry the rollup semantics; "
        "the percentage itself is never stored."
    ),
    volume_estimate=3000000,
    unique_key=("Title",),
    columns=(
        T("Title", "Fact key: <EOM_Item_Key>|<Snapshot_Date>. Renamed Title.", required=True, title=True),
        D("Snapshot_Date", "Date the fact row was generated by EOM-03.", required=True, indexed=True),
        T("EOM_Item_ID", "Grain key back to MF_EOM_Item.", required=True, indexed=True),
        T("EOM_Item_Key", "Human-readable grain key for troubleshooting against the app."),
        T("Reporting_Period_ID", "Period dimension key.", required=True, indexed=True),
        N("Fiscal_Year", "Denormalized for EOY reporting.", indexed=True),
        T("Portfolio_ID", "RLS key at portfolio scope.", required=True, indexed=True),
        T("Installation_ID", "RLS key at installation scope.", required=True, indexed=True),
        T("Facility_ID", "RLS key at facility scope. Null on Installation- and Contract-scope rows.", indexed=True),
        T("Facility_Name", "Denormalized label."),
        T("Requirement_ID", "Requirement dimension key.", required=True, indexed=True),
        C("Requirement_Scope", "Facility, Installation or Contract.", REQUIREMENT_SCOPE, required=True),
        C("Requirement_Verification_Status", "Explains why a past-suspense row is Gray rather than Red.", VERIFICATION_STATUS, required=True),
        C("Status_Code", "Copied verbatim from the item. Never recomputed.", STATUS_CODE, required=True, indexed=True),
        T("Status_Semantic", "Copied verbatim from the item."),
        C("Final_Status", "Copied verbatim from the item.", FINAL_STATUS, required=True, indexed=True),
        C("Action_Owner_Role", "Copied verbatim from the item.", ACTION_OWNER, required=True),
        B("Action_Required", "Copied verbatim from the item."),
        D("Due_Date", "Copied verbatim from the item."),
        D("Suspense_Date", "Copied verbatim from the item."),
        B("Is_Complete", "Rollup numerator flag. True only for ACCEPTED.", indexed=True),
        B("Is_In_Denominator", "Rollup denominator flag. False for NOT_DUE, WAIVED, NOT_APPLICABLE and SUPERSEDED.", indexed=True),
    ),
)

# ==========================================================================
# 9. MF_Security_Mapping — 11 columns
# ==========================================================================
MF_Security_Mapping = ListDef(
    name="MF_Security_Mapping",
    display_name="MF Security Mapping",
    description=(
        "One security mapping serves app filtering and Power BI RLS. A user "
        "may hold several rows. Developer_Flag and Tester_Flag gate the "
        "protected developer surface in a single-environment tenant."
    ),
    volume_estimate=5000,
    unique_key=("Title",),
    columns=(
        T("Title", "Mapping key: <Principal_UPN>|<Role>|<Scope_Type>|<Scope_ID>. Renamed Title.", required=True, title=True),
        T("Principal_UPN", "User principal name, or the group's mail nickname when Principal_Type is Group.", required=True, indexed=True),
        C("Principal_Type", "User or Group.", PRINCIPAL_TYPE, required=True),
        T("Entra_Group_Id", "Object id when Principal_Type is Group. Membership is resolved at app start."),
        C("Role", "Role granted at this scope.", ROLE, required=True, indexed=True),
        C("Scope_Type", "Facility, Installation, Portfolio or Global.", SCOPE_TYPE, required=True, indexed=True),
        T("Scope_ID", "Facility_ID, Installation_ID or Portfolio_ID. Null when Scope_Type is Global.", indexed=True),
        T("Portfolio_ID", "Portfolio the scope belongs to. Denormalized for RLS.", indexed=True),
        B("Developer_Flag", "Unlocks scrDiagnostics. Never granted by a role.", default=False),
        B("Tester_Flag", "Unlocks flags scoped to testers without touching production defaults.", default=False),
        B("Is_Active", "Revocation without deletion, so the audit trail survives.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 10. MF_App_Config — 8 columns
# ==========================================================================
MF_App_Config = ListDef(
    name="MF_App_Config",
    display_name="MF App Config",
    description=(
        "Runtime configuration. Holds the kill switch: MaintenanceMode and "
        "ReadOnlyMode. No URL, site GUID or list name is hard-coded anywhere "
        "in the app; they are read from here."
    ),
    volume_estimate=100,
    unique_key=("Title",),
    columns=(
        T("Title", "Config key. Renamed Title.", required=True, title=True),
        NOTE("Config_Value", "Value as text. Coerced by Config_Type at read time.", required=True),
        C("Config_Type", "Text, Number, Boolean or Date.", CONFIG_TYPE, required=True),
        T("Environment_Tag", "DEV, TEST or PROD. A single environment may carry all three; the app reads the tag matching its own.", indexed=True),
        NOTE("Description", "What this key controls and what breaks if it is wrong."),
        D("Effective_From", "Null means immediately."),
        D("Effective_To", "Null means indefinitely."),
        B("Is_Active", "Inactive keys fall back to the app's compiled default.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 11. MF_Feature_Flags — 9 columns
# ==========================================================================
MF_Feature_Flags = ListDef(
    name="MF_Feature_Flags",
    display_name="MF Feature Flags",
    description=(
        "Feature flags. Everything outside the SharePoint / Power Apps / "
        "Power Automate / Power BI / Entra core degrades gracefully behind a "
        "flag. EnableDocumentContentAI and EnableAIBuilder ship False."
    ),
    volume_estimate=100,
    unique_key=("Title",),
    columns=(
        T("Title", "Flag name. Renamed Title.", required=True, title=True),
        B("Flag_Value", "Current value.", required=True, indexed=True),
        B("Default_Value", "Value the app falls back to if the list is unreachable. Never True for an optional dependency."),
        C("Scope", "Global, Role or User.", FLAG_SCOPE, required=True),
        T("Enabled_For_Roles", "Semicolon-delimited roles when Scope is Role."),
        NOTE("Enabled_For_UPNs", "Semicolon-delimited UPNs when Scope is User."),
        NOTE("Description", "What the flag turns on and what it costs."),
        T("Requires_Capability", "Capability gate from docs/government-environment-mode.md that must be green before this flag may be set True."),
        B("Is_Active", "Retired flags stay for the audit trail.", default=True, indexed=True),
    ),
)

# ==========================================================================
# 12. MF_App_Event_Log — 10 columns
# ==========================================================================
MF_App_Event_Log = ListDef(
    name="MF_App_Event_Log",
    display_name="MF App Event Log",
    description=(
        "Structured business telemetry. Writes on app open, screen view, "
        "upload and QC decision at minimum. Not a debug log: every row "
        "answers a question somebody will ask about the programme."
    ),
    volume_estimate=2000000,
    unique_key=("Title",),
    columns=(
        T("Title", "Event key: <Correlation_ID>|<Event_Type>. Renamed Title.", required=True, title=True),
        D("Event_Time", "UTC timestamp.", required=True, indexed=True),
        C("Event_Type", "Business event, not a log level.", EVENT_TYPE, required=True, indexed=True),
        C("Severity", "Debug, Info, Warning or Error.", SEVERITY, required=True, indexed=True),
        T("User_UPN", "Acting identity.", indexed=True),
        T("App_Version", "Semantic version of the app that wrote the row."),
        T("Screen_Name", "Screen the event was raised from."),
        T("Correlation_ID", "Ties an app action to the flow runs it triggered.", indexed=True),
        T("Entity_ID", "EOM_Item_ID, Submission_ID or the affected configuration key."),
        NOTE("Detail_Json", "Event-specific payload. No PII beyond the UPN, no file contents."),
    ),
)


LISTS = (
    MF_Installation,
    MF_Facility,
    MF_Contract,
    MF_Requirement,
    MF_Reporting_Period,
    MF_EOM_Item,
    MF_EOM_Submission,
    MF_EOM_Status,
    MF_Security_Mapping,
    MF_App_Config,
    MF_Feature_Flags,
    MF_App_Event_Log,
)

LISTS_BY_NAME = {l.name: l for l in LISTS}


def total_columns() -> int:
    return sum(len(l.columns) for l in LISTS)


def validate() -> list:
    errs = []
    if len(LISTS) != EXPECTED_LIST_COUNT:
        errs.append(f"expected {EXPECTED_LIST_COUNT} lists, found {len(LISTS)}")
    if total_columns() != EXPECTED_COLUMN_COUNT:
        errs.append(
            f"expected {EXPECTED_COLUMN_COUNT} columns, found {total_columns()}"
        )
    seen = set()
    for l in LISTS:
        if l.name in seen:
            errs.append(f"duplicate list {l.name}")
        seen.add(l.name)
        errs.extend(l.validate())

    # Cross-list invariants that the rest of the build depends on.
    item = LISTS_BY_NAME["MF_EOM_Item"]
    for required in ("Reporting_Period_ID", "Status_Code", "Portfolio_ID", "Facility_ID"):
        col = next((c for c in item.columns if c.name == required), None)
        if col is None:
            errs.append(f"MF_EOM_Item is missing {required}")
        elif not (col.indexed or col.title):
            errs.append(f"MF_EOM_Item.{required} must be indexed before the list crosses 5,000 items")
    fac = next(c for c in item.columns if c.name == "Facility_ID")
    if fac.required:
        errs.append("MF_EOM_Item.Facility_ID must be nullable for Installation and Contract scope")

    # The fact must not carry a stored percentage or any computed rate.
    for l in LISTS:
        for c in l.columns:
            lowered = c.name.lower()
            if "percent" in lowered or lowered.endswith("_pct") or lowered.endswith("_rate"):
                errs.append(
                    f"{l.name}.{c.name}: a stored percentage is forbidden; "
                    "rollups are computed from Is_Complete and Is_In_Denominator"
                )
    return errs


def to_dict() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "list_count": len(LISTS),
        "column_count": total_columns(),
        "lists": [
            {
                **{k: v for k, v in asdict(l).items() if k != "columns"},
                "columns": [asdict(c) for c in l.columns],
                "indexed_columns": list(l.indexed_columns),
            }
            for l in LISTS
        ],
        "vocabularies": {
            "REQUIREMENT_SCOPE": list(REQUIREMENT_SCOPE),
            "OPERATING_MODEL": list(OPERATING_MODEL),
            "VERIFICATION_STATUS": list(VERIFICATION_STATUS),
            "STATUS_CODE": list(STATUS_CODE),
            "FINAL_STATUS": list(FINAL_STATUS),
            "ACTION_OWNER": list(ACTION_OWNER),
            "CLASSIFICATION_METHOD": list(CLASSIFICATION_METHOD),
            "CLASSIFICATION_STATUS": list(CLASSIFICATION_STATUS),
            "ROLE": list(ROLE),
        },
    }


def to_markdown() -> str:
    out = []
    out.append("<!-- GENERATED by scripts/eom_schema.py — do not edit by hand. -->")
    out.append("")
    out.append("# Data model")
    out.append("")
    out.append(
        f"Schema version **{SCHEMA_VERSION}** — **{len(LISTS)} lists**, "
        f"**{total_columns()} columns**."
    )
    out.append("")
    out.append(
        "`scripts/eom_schema.py` is the single source of truth. Regenerate this "
        "file with `python3 scripts/eom_schema.py --markdown > docs/data-model.md`."
    )
    out.append("")
    out.append("| List | Columns | Indexed | Est. rows (yr 1) |")
    out.append("|---|---:|---:|---:|")
    for l in LISTS:
        out.append(
            f"| `{l.name}` | {len(l.columns)} | {len(l.indexed_columns)} | {l.volume_estimate:,} |"
        )
    out.append("")
    for l in LISTS:
        out.append(f"## `{l.name}`")
        out.append("")
        out.append(l.description)
        out.append("")
        if l.unique_key:
            out.append(f"Unique key: {', '.join('`%s`' % k for k in l.unique_key)}.")
            out.append("")
        out.append("| Column | Type | Req | Idx | Notes |")
        out.append("|---|---|:-:|:-:|---|")
        for c in l.columns:
            note = c.description
            if c.choices:
                note += " Choices: " + ", ".join(f"`{x}`" for x in c.choices) + "."
            out.append(
                f"| `{c.name}` | {c.type} | {'Y' if c.required else ''} | "
                f"{'Y' if (c.indexed or c.title) else ''} | {note} |"
            )
        out.append("")
    return "\n".join(out)


def summary() -> str:
    lines = [f"MissionFeedingOperations schema v{SCHEMA_VERSION}"]
    for l in LISTS:
        lines.append(
            f"  {l.name:<22} {len(l.columns):>3} columns  "
            f"{len(l.indexed_columns):>2} indexed  ~{l.volume_estimate:,} rows"
        )
    lines.append(f"  {'TOTAL':<22} {total_columns():>3} columns across {len(LISTS)} lists")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="emit the machine-readable schema")
    p.add_argument("--markdown", action="store_true", help="emit docs/data-model.md")
    p.add_argument("--summary", action="store_true", help="one line per list")
    p.add_argument("--validate", action="store_true", help="check invariants, exit non-zero on failure")
    args = p.parse_args(argv)

    if args.validate or not (args.json or args.markdown or args.summary):
        errs = validate()
        if errs:
            for e in errs:
                print(f"SCHEMA ERROR: {e}", file=sys.stderr)
            return 1
        if not (args.json or args.markdown or args.summary):
            print(summary())
            print("\nschema OK")
            return 0

    if args.json:
        print(json.dumps(to_dict(), indent=2))
    if args.markdown:
        print(to_markdown())
    if args.summary:
        print(summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
