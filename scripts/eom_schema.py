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

SCHEMA_VERSION = "5.0"
EXPECTED_LIST_COUNT = 17
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

# R1 is Legacy-only. Food 2.0 installations reorganise into Portfolios 1-4 in
# October, so nothing encodes the current Aramark/Sodexo vendor split.
COMPONENT = ("Active", "ANG", "AFRC")

# The Mission Feeding QRG names operating models differently from the
# requirement catalogue. Left unmapped, Applicable_Model "Legacy/APF" would
# never match Operating_Model "Legacy" and EOM-01 would generate ZERO facility
# rows — silently, because a facility that generates nothing looks exactly like
# a facility with nothing due. The registry is normalised on import.
QRG_OPERATING_MODEL_MAP = {
    "Legacy": "Legacy/APF",
    "MAFFO": "MAFFO/MAF",
    "Deployed / Field Feeding": "AOR/CDS",
    "Food 2.0": "Food 2.0",
}


def normalize_operating_model(value):
    """Map a QRG operating-model string onto the canonical vocabulary.

    Returns None for a blank, which is legitimate: twenty registry rows are
    NO_DFAC placeholders recording that a base has no feeding facility at all.
    That record is worth keeping — it stops someone asking where Arnold's 1119
    is — but it has no operating model and generates nothing.
    """
    value = (value or "").strip()
    if not value:
        return None
    if value in OPERATING_MODEL:
        return value
    try:
        return QRG_OPERATING_MODEL_MAP[value]
    except KeyError:
        raise ValueError(
            f"unmapped operating model {value!r}. Add it to "
            "QRG_OPERATING_MODEL_MAP deliberately — do not let it fall through, "
            "because an unmatched model generates no requirements and reads as "
            "compliant."
        )

# ANG DFAC managers provide the EOY inventory last page to NGB/A1X, not to
# AFSVC/VMF. Without this the EOY requirement routes ANG submissions to the
# wrong organisation and nobody notices until someone asks where they went.
ROUTING_ORG = ("AFSVC/VMF", "NGB/A1X", "AFRC/A1S", "Installation")

# Calendar is the baseline. The source says "within 5 days" and does not say
# duty days, business days or workdays; do not infer duty days without a
# citation.
DUE_BASIS = ("CALENDAR", "DUTY_DAY")

NON_DUTY_DAY_POLICY = ("NEXT_DUTY_DAY", "PREVIOUS_DUTY_DAY", "NO_ADJUSTMENT")

# Authority answers "does this requirement exist". Scope answers "at what grain
# is it filed". They are separate claims: marking a scope guess VERIFIED
# because the document is verified turns a proposal into policy by accident.
SCOPE_CONFIDENCE = ("High", "Medium", "Low", "Proposed")

FACILITY_TYPE = ("Main DFAC", "Flight Kitchen", "Kiosk", "Satellite", "MAF",
                 "Contract Cafe")

REQUIREMENT_SCOPE = ("Facility", "Installation", "Contract")   # Portfolio reserved

FREQUENCY = ("Monthly", "Quarterly", "Semiannual", "Annual", "Conditional")

# UNVERIFIED requirements generate items but never drive Red. All twelve
# seeded requirements are UNVERIFIED today, so that is the default path.
AUTHORITY_STATUS = ("VERIFIED", "MANAGEMENT_RULE", "PROPOSED", "UNVERIFIED",
                    "RETIRED_OR_NOT_APPLICABLE")

# The nine semantic statuses. Final_Status.
#
# LATE and RETURNED are both produced by the decision order in
# docs/status-calculation.md. The v11 schema omitted them from the choice list
# while its own decision table produced them, which would have made the flow
# write a value the column rejects. See handoffs/RECONCILIATION.md C11.
FINAL_STATUS = (
    "NOT_APPLICABLE",
    "NOT_DUE",
    "PENDING_VALIDATION",
    "LATE",
    "OVERDUE",
    "RETURNED",
    "NOT_SATISFIED",
    "RECEIVED_PENDING_QC",
    "ACCEPTED",
)

# The SIX visual codes. Status_Code.
#
# Colour carries OWNERSHIP and time risk, not severity:
#
#   Blue   4  not due, window open        nobody yet
#   Amber  5  past first suspense         the base, with runway
#   Red    1  past final call, or returned the base, out of runway
#   Yellow 2  received, awaiting review   AFSVC
#   Green  3  accepted                    nobody
#   Gray   0  not applicable              nobody
#
# The amber/yellow split is the point. Amber means TIME RISK; yellow means
# SOMEBODY ELSE HAS IT. Collapsing them tells a DFAC manager that a document
# they filed on time and one they never sent are the same kind of problem.
#
# Six is the ceiling. A seventh state would stop being scannable.
STATUS_CODE_VALUES = (0, 1, 2, 3, 4, 5)
STATUS_CODE_NAMES = {0: "Gray", 1: "Red", 2: "Yellow", 3: "Green",
                     4: "Blue", 5: "Amber"}

ACTION_OWNER = ("Facility", "Reviewer", "Admin", "None")

# Package rollup states. Computed over semantic statuses, never over colour.
PACKAGE_STATE = ("ACTION_REQUIRED", "IN_REVIEW", "COMPLETE", "IN_PROGRESS",
                 "NOT_APPLICABLE")

# Seven verdicts plus Recalled. They behave like ticket tags: the status engine
# collapses the four returning verdicts into one RETURNED state, but the
# submitter needs the specific reason to know what to fix, and that reason
# lives here on the submission.
QC_STATUS = ("Pending Review", "Accepted", "Correction Required", "Incomplete",
             "Wrong Document", "Wrong Reporting Period", "Wrong Facility",
             "Recalled", "Not Applicable")

# The four that mean "it came back". Rule 6 of the decision order.
QC_RETURNING = ("Correction Required", "Incomplete",
                "Wrong Reporting Period", "Wrong Facility")

INTAKE_METHOD = ("App upload", "Folder drop", "Manual classification")

CLASSIFICATION_METHOD = ("Declared at upload", "Folder context",
                         "Document content", "AI Builder", "Manual")

CLASSIFICATION_STATUS = ("Pending", "Classified", "Needs Review", "Failed")

CLASSIFICATION_CONFIDENCE = ("Declared", "High", "Low", "Unresolved")

DOCUMENT_DOMAIN = ("EOM", "EOY", "FMAT", "Other")

FALLBACK_POLICY = ("FIND_OR_ROOT", "FIND_OR_FAIL")
# FIND_OR_ROOT is the R1 policy. When the fiscal-year or month folder cannot be
# matched, the file lands at the Monthly Data Call root flagged Needs_Filing and
# a human moves it. A submission that lands somewhere findable beats one that
# fails: the base did their part, and the failure is ours to clean up.

RESOLUTION_STATUS = ("Needs Classification", "Classified",
                     "Not an EOM document", "Duplicate")

SCOPE_TYPE = ("Enterprise", "Portfolio", "Installation", "Facility")

# Two roles, not six. Nobody is provisioned for their own base: CAC identifies
# the user, the GAL gives their installation, and anyone at that installation
# can view and edit its EOM submissions regardless of unit. BASE_USER is
# automatic; PORTFOLIO_MANAGER is granted, and only by a holder of
# Can_Grant_Access at Enterprise scope, which stops the role self-propagating.
ROLE = ("BASE_USER", "PORTFOLIO_MANAGER")

FLAG_ROLE = ROLE + ("DEVELOPER",)

GRANT_TYPE = ("GAL derived", "Requested", "Manual")

GRANT_SCOPE = ("None", "Portfolio", "Enterprise")

ACCESS_REQUEST_STATUS = ("Pending", "Approved", "Denied", "Expired")

CALENDAR_EVENT_TYPE = ("Suspense", "Correction due", "Assessment", "Data call",
                       "Reminder")

NOTIFICATION_TRIGGER = ("SubmissionCreated", "StatusChanged", "DueSoon",
                        "FirstSuspensePassed", "FinalSuspensePassed",
                        "CorrectionSuspensePassed", "PendingReviewAging",
                        "AccessRequested")

NOTIFICATION_RECIPIENT = ("Submitter", "Portfolio org box", "Installation POC",
                          "Reviewer", "Portfolio Manager", "AFSVC")

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
    volume_estimate=103,
    unique_key=("Installation_ID",),
    note="With MF_Facility this is the authoritative EOM operational registry "
         "until an enterprise source supersedes it. CrunchTime, Aloha Enterprise "
         "and Teams all differ and none tracks what EOM needs, so it is built "
         "here by hand and signed off per base.",
    columns=(
        c("Installation_ID", "Text", req=True, indexed=True,
          note="Canonical key. Must match the COP MF_Installation.Installation_ID."),
        c("Installation_Name", "Text", req=True),
        c("Source_Installation_String", "Text",
          note="The base's name exactly as it appeared in the source QRG. Kept so a "
               "registry correction can be traced back rather than argued about."),
        c("Location", "Text", note="State or country, from the QRG."),
        c("Portfolio_ID", "Text", req=True, indexed=True),
        c("MAJCOM", "Text"),
        c("Component", "Choice", req=True, choices=COMPONENT,
          note="Active, ANG or AFRC. ANG routes EOY inventory to NGB/A1X, not "
               "AFSVC/VMF — see MF_EOM_Requirement.Routing_Org."),
        c("EOM_Folder_URL", "URL",
          note="OPTIONAL convenience deep link, set by an administrator, shown "
               "on scrInstallation as 'open this folder in SharePoint'. Blank "
               "in the seed and blank by default -- the registry generator has "
               "no site to point at, and a .mil URL in source is a destination "
               "leak.\n"
               "IT IS NOT A ROUTING MECHANISM. EOM-02 resolves where a file "
               "goes from MF_Document_Destination and never reads this. A "
               "second place that answers 'where do this installation's "
               "documents live' is how the two diverge."),
        c("Generation_Enabled", "Boolean", req=True, indexed=True,
          note="THE onboarding gate. EOM-01 generates only where this is TRUE. A base "
               "with it FALSE reads as 'not yet onboarded', never as compliant. Flip it "
               "after the facilities and operating models are populated and validated."),
        c("Registry_Validated_By", "Text", note="Who signed off this base's registry entry."),
        c("Registry_Validated_Date", "DateTime"),
        c("Source_System", "Text", note="Where the row came from. 'Mission Feeding QRG' for the initial load."),
        c("Needs_Review_Flag", "Boolean",
          note="Set by the QRG import where the source row was ambiguous. See "
               "configuration/qrg-data-quality.csv."),
        c("DODAAC", "Text"),
        c("DODAAD", "Text"),
        c("Org_Box_Email", "Text",
          note="Portfolio or installation org box. Notification target — a person's "
               "mailbox is never a notification target."),
        c("Official_POC_UPN", "Text",
          note="Resolved identity. The QRG POC column is a DISPLAY NAME and is never "
               "an identity; see security/security-manifest.yaml."),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_Facility = ListDef(
    name="MF_Facility",
    title="MF Facility",
    grain="One row per feeding facility",
    volume_estimate=154,
    unique_key=("Facility_ID",),
    note="Operating_Model is HERE, not on the installation. One base can run a "
         "legacy DFAC and a Food 2.0 cafe simultaneously, and the requirement set "
         "follows the facility. Multi-facility installations are normal: the SAIIT "
         "guidance describes transfers between a second DFAC and a flight kitchen "
         "at the same base, and the 1119 initialises ONE facility and one month.",
    columns=(
        c("Facility_ID", "Text", req=True, indexed=True,
          note="Unique enterprise-wide, not per installation. INSTALLATION|FACILITY."),
        c("Installation_ID", "Text", req=True, indexed=True),
        c("Facility_Name", "Text", req=True),
        c("Designation", "Text", note="Local designation where the QRG carried one."),
        c("Unit", "Text", note="Owning unit, e.g. 97 FSS."),
        c("Facility_Type", "Choice", choices=FACILITY_TYPE,
          note="Nullable: the QRG does not carry it for every row, and guessing a "
               "type would silently change which requirements generate."),
        c("Operating_Model", "Choice", choices=OPERATING_MODEL, indexed=True,
          note="Drives which requirements apply to THIS facility. NULLABLE: the "
               "twenty NO_DFAC registry rows record that a base has no feeding "
               "facility, and they legitimately have no model. A facility with no "
               "model generates nothing and is surfaced by the health check, never "
               "read as compliant."),
        c("Source_Operating_Model", "Text",
          note="The feeding type AS THE QRG WRITES IT, before normalisation. "
               "Operating_Model above is the normalised value the requirement "
               "catalogue filters on -- the QRG says 'Legacy', the catalogue "
               "says 'Legacy/APF'. Keeping the raw string means a mapping can "
               "be corrected without re-reading the source, and an unmapped "
               "value is visible rather than silently blank."),
c("Program_Type", "Text", note="QRG programme string, e.g. 'Legacy - SB'."),
        c("Contract_Type", "Text", note="Mess Attendant, Aramark, Sodexo, and so on."),
        c("Primary_PV", "Text", note="Prime vendor."),
        c("POS_Terminals_Raw", "Text", note="As recorded in the QRG. Unparsed."),
        c("POC_Display_Name", "Text",
          note="DISPLAY NAME from the QRG. Never an identity and never used for "
               "authorization — see security/security-manifest.yaml."),
        c("In_R1_Scope", "Boolean", indexed=True,
          note="R1 is Legacy-only. Food 2.0 and MAFFO facilities are carried in the "
               "registry but out of scope until their handbooks land."),
        c("Source_Row", "Number", note="Row number in the source QRG, for traceability."),
        c("Source_System", "Text"),
        c("Facility_DODAAC", "Text"),
        c("Contract_ID", "Text", note="Nullable. Set where the facility is covered by a contract."),
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
         "is a list edit, not an app rebuild.",
    columns=(
        c("Requirement_ID", "Text", req=True, indexed=True),
        c("Document_Code", "Text", req=True,
          note="1119, 1119-1, SF1080, SAIIT, GPC, 1038, EOY-MFR, EOY-INV"),
        c("Document_Name", "Text", req=True),
        c("Applicable_Model", "Choice", req=True, choices=APPLICABLE_MODEL,
          note="'All' applies regardless of facility model"),
        c("Requirement_Scope", "Choice", req=True, choices=REQUIREMENT_SCOPE,
          note="Determines the grain of the generated EOM_Item. Portfolio reserved."),
        # Authority and scope are SEPARATE claims. The procedures deck confirms
        # which documents are in the package; it says nothing about the grain
        # each is filed at.
        c("Scope_Confidence", "Choice", req=True, choices=SCOPE_CONFIDENCE,
          note="How sure we are of the GRAIN, which is a different question from "
               "whether the requirement exists. Marking a scope guess VERIFIED "
               "because the document is verified turns a proposal into policy by "
               "accident."),
        c("Scope_Basis", "Note",
          note="Why that grain. A reason, not a hunch."),
        c("Applicable_Facility_Types", "Text",
          note="Semicolon list. Blank = all types."),
        c("Applicable_Period_Month", "Number",
          note="For Annual requirements: the fiscal month the obligation lands in. "
               "9 for EOY. Null for Monthly and Quarterly."),
        c("Routing_Org", "Choice", choices=ROUTING_ORG,
          note="Where the submission goes. ANG routes EOY inventory to NGB/A1X "
               "per DAFMAN 34-131 7.14.5, not to AFSVC/VMF."),
        c("Frequency", "Choice", req=True, choices=FREQUENCY, indexed=True,
          note="Conditional requirements are NEVER auto-generated. The 1119-1 is "
               "field feeding: auto-generating it would put a permanent red row on "
               "every DFAC that ran no field feeding exercise, which is exactly the "
               "kind of false overdue that teaches people to ignore the dashboard."),
        c("Required_Flag", "Boolean", req=True),
        # Two suspenses. Between them an item is LATE, not overdue — and that
        # middle window is the only week in the cycle where a reminder still
        # changes the outcome.
        c("Due_Day", "Number", req=True,
          note="First suspense: day of the month following the reporting period. "
               "5 for the Legacy package."),
        c("Due_Basis", "Choice", req=True, choices=DUE_BASIS,
          note="CALENDAR is the baseline. The source says 'within 5 days' and does "
               "not say duty days; do not infer duty days without a citation."),
        c("Final_Due_Day", "Number",
          note="Final call. 10 for the Legacy package — a MANAGEMENT_RULE from the "
               "programme, not from the source deck."),
        c("Final_Due_Basis", "Choice", choices=DUE_BASIS),
        c("NonDutyDay_Policy", "Choice", choices=NON_DUTY_DAY_POLICY,
          note="Resolved against MF_Non_Duty_Day. Defaults to NEXT_DUTY_DAY. A "
               "nominal suspense landing on a Saturday cannot be the date someone "
               "is held to, and burying that in a formula produces a monthly argument."),
        c("QC_Required", "Boolean", req=True),
        c("Accepted_File_Types", "Text", note="Advisory only in MVP. xlsx;pdf"),
        c("Authority_Reference", "Text",
          note="The citation. AFSVC EOM/EOY procedures, DAFMAN 34-131 ch 7.14, "
               "DFAC Manager Handbook 1.7.5, Storeroom Handbook 5.3.4."),
        c("Authority_Status", "Choice", req=True, choices=AUTHORITY_STATUS, indexed=True,
          note="Does this requirement EXIST. UNVERIFIED requirements generate items "
               "but never drive an adverse status. RETIRED_OR_NOT_APPLICABLE keeps a "
               "retired requirement on the record so later guidance can reactivate "
               "it without a schema change."),
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
         "The checklist exists before any file arrives, which is the only way to "
         "distinguish 'nothing was submitted' from 'the system has no record'. "
         "Facility_ID is NULL for Installation and Contract scope.",
    columns=(
        c("EOM_Item_ID", "Text", req=True, indexed=True),
        c("EOM_Item_Key", "Text", req=True, indexed=True,
          note="Human-readable compound key. Drives duplicate prevention and flow "
               "idempotency."),
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
          note="Denormalized so the app filters without a join. Also how the app "
               "asks 'is this a facility row' — IsBlank(Facility_ID) does not "
               "delegate."),
        c("Authority_Status", "Choice", req=True, choices=AUTHORITY_STATUS, indexed=True,
          note="Denormalized at generation. Rule 2 of the status engine reads it, "
               "and a lookup to MF_EOM_Requirement would not delegate."),
        c("Required_Flag", "Boolean", req=True),

        # ---- four dates -------------------------------------------------
        # Status evaluation ALWAYS uses the effective dates. Reporting uses the
        # nominal ones, so "the 5th" stays the 5th in a leadership brief while
        # the base is held to the date they can actually meet.
        c("Nominal_Due_Date", "DateTime", req=True,
          note="The policy date. The 5th stays the 5th."),
        c("Effective_Due_Date", "DateTime", req=True, indexed=True,
          note="After NonDutyDay_Policy. What a person actually owes, and what the "
               "status engine evaluates against."),
        c("Nominal_Final_Call_Date", "DateTime",
          note="The policy final call. The 10th."),
        c("Effective_Final_Call_Date", "DateTime", indexed=True,
          note="After NonDutyDay_Policy."),
        c("Due_Date_Adjusted", "Boolean", req=True,
          note="TRUE where nominal and effective differ. The package screen shows "
               "both: 'Due 5 Sep (Mon 8 Sep)'."),

        # ---- on-time is two questions ------------------------------------
        # Uploaded 4 Sep, returned 9 Sep, corrected and accepted 12 Sep: the base
        # submitted on time and AFSVC did not have usable evidence on time. Both
        # are true, and they are shown to different audiences.
        c("Initial_Submitted_DateTime", "DateTime",
          note="When the FIRST version arrived. Never overwritten by a resubmission."),
        c("Initial_Submission_On_Time", "Boolean",
          note="First version by Effective_Due_Date. This is what the base is told."),
        c("Acceptable_Evidence_DateTime", "DateTime",
          note="When an accepted version first existed. Renamed from the v11 "
               "Current_Acceptable_Evidence_DateTime, which was 35 characters and "
               "over SharePoint's 32-character internal name limit."),
        c("Final_Evidence_On_Time", "Boolean",
          note="Accepted evidence by Effective_Final_Call_Date. This is what "
               "leadership is told."),

        c("Current_Submission_ID", "Text",
          note="Points at the Is_Current submission. Null until the first upload."),
        c("Received_Flag", "Boolean", req=True),

        # ---- status, written together by ONE evaluation -------------------
        c("Final_Status", "Choice", req=True, choices=FINAL_STATUS, indexed=True,
          note="SEMANTIC status. Calculated by EOM-03 and by the app's QC action, "
               "never user-selectable. Independent of Status_Code."),
        c("Status_Code", "Number", req=True, indexed=True,
          note="VISUAL code. 0 Gray n/a, 1 Red base out of runway, 2 Yellow AFSVC "
               "owns it, 3 Green accepted, 4 Blue not due, 5 Amber base with "
               "runway. Colour carries OWNERSHIP, not severity. Stored so "
               "Filter() delegates."),
        c("Action_Owner", "Choice", req=True, choices=ACTION_OWNER,
          note="Status_Code alone cannot answer 'is this mine'. Home filters on "
               "this, not on colour."),
        c("Action_Required", "Boolean", req=True, indexed=True),

        c("Days_Late", "Number",
          note="Magnitude against Effective_Final_Call_Date. Set by EOM-03, not "
               "computed in DAX. Amber and Red share an owner; this carries the "
               "difference in degree."),
        c("Last_Reconciled_DateTime", "DateTime",
          note="Stamped by EOM-03. System Health flags items not reconciled "
               "recently — stale reconciliation looks exactly like a quiet month."),
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
    unique_key=("Submission_ID", "Submission_Request_ID"),
    note="Versioned evidence. v1 Correction Required and v2 Accepted both persist; "
         "nothing is overwritten or deleted. QC applies to the Is_Current version.",
    columns=(
        c("Submission_ID", "Text", req=True, indexed=True),
        c("Submission_Request_ID", "Text", req=True, indexed=True,
          note="IDEMPOTENCY KEY. A GUID minted by the app BEFORE the file is "
               "sent, and resent unchanged on every retry of the same user "
               "action. EOM-02 looks it up before writing anything; a second "
               "arrival returns the first result instead of creating a second "
               "file and a second row.\n"
               "On a government network a user pressing Submit again after a "
               "timeout is the NORMAL case, not the edge case -- the request "
               "usually succeeded and the response was lost. Disabling the "
               "button in Power Apps is not protection: the flow can be "
               "invoked directly, and the client that timed out is the one "
               "that cannot know what happened."),
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
        c("Portfolio_ID", "Text", indexed=True,
          note="The folder path gives portfolio and month; the uploader's GAL gives "
               "the installation; the app declaration gives facility and document "
               "type. Nothing is inferred from a filename."),
        c("Classification_Confidence", "Choice", choices=CLASSIFICATION_CONFIDENCE,
          note="'Declared' = the app captured it at upload. That is the whole point "
               "of making the app the front door."),
        c("Last_Error_Code", "Text"),
        c("Last_Error_Message", "Note",
          note="User-facing, plain language. Never a raw HTTP status."),
        c("Last_Processing_DateTime", "DateTime"),
        c("Retry_Count", "Number"),
        c("Destination_ID", "Text", indexed=True,
          note="FK to MF_Document_Destination. Which configured destination "
               "received this file, so a routing change is auditable after the "
               "fact rather than inferred from a path."),
        c("Source_Library", "Text",
          note="The library the file landed in. Recorded because the four "
               "portfolios are four separate site collections and 'Shared "
               "Documents' is an assumption until each site is walked."),
        c("Source_Path", "Text",
          note="Where the file was found or placed. Diagnostic only — the list "
               "row is truth."),
        c("Needs_Filing", "Boolean", indexed=True,
          note="TRUE when the fiscal-year or month folder could not be matched "
               "and the file landed at the Monthly Data Call root under "
               "FIND_OR_ROOT. Indexed because Admin filters on it, and the "
               "count is the whole point: a file nobody knows is misfiled is "
               "worse than one that failed to upload."),
        c("Filing_Note", "Text",
          note="What was looked for and not found — 'no child of FY26 matched "
               "August 2026'. The person moving the file needs to know whether "
               "to move it or fix the configuration."),
        c("SharePoint_Unique_ID", "Text", indexed=True,
          note="THE DURABLE HANDLE. The document GUID survives a rename and a "
               "move; File_URL survives neither, and under FIND_OR_ROOT files "
               "get moved by design. Store the GUID, resolve the URL from it."),
        c("SharePoint_File_ID", "Text", indexed=True,
          note="List item ID. Convenient for a lookup within one library; not "
               "durable across a move between libraries or sites."),
        c("Is_Current", "Boolean", req=True, indexed=True),
        c("Superseded_By", "Text",
          note="Submission_ID of the version that replaced this one"),
        c("QC_Status", "Choice", req=True, choices=QC_STATUS, indexed=True,
          note="Seven verdicts plus Recalled. The status engine collapses the four "
               "returning verdicts into RETURNED, but the base reads the specific "
               "reason here and in the notification. Recalled is the submitter "
               "withdrawing before review, not a rejection."),
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
    note="ONE mapping for both Power Apps filtering and Power BI RLS. Nobody is "
         "provisioned for their own base: CAC identifies the user, the GAL gives "
         "their installation, and anyone at that installation may view and edit "
         "its EOM submissions regardless of unit. Installation is the unit of "
         "access.\n\n"
         "WARNING: this list drives APP filtering. Power Apps Visible and Filter() "
         "are NOT an access-control boundary — see docs/security-open-issue.md. "
         "The data layer must enforce the same scope independently.",
    columns=(
        c("Security_ID", "Text", req=True, indexed=True),
        c("UPN", "Text", req=True, indexed=True),
        c("Scope_Type", "Choice", req=True, choices=SCOPE_TYPE, indexed=True),
        c("Portfolio_ID", "Text", indexed=True),
        c("Installation_ID", "Text", indexed=True),
        c("Facility_ID", "Text", indexed=True),
        c("Role", "Choice", req=True, choices=ROLE,
          note="BASE_USER is automatic from CAC and the GAL. PORTFOLIO_MANAGER is "
               "granted. Two roles, not six — users can hold two in their heads."),
        c("Job_Title", "Text", note="From the GAL. Display only, never authorization."),
        c("Can_QC", "Boolean", req=True,
          note="Defaults on for PORTFOLIO_MANAGER: reviewing is the core of the role."),
        c("Can_Submit_On_Behalf", "Boolean", req=True,
          note="Records the true origin of an emailed document instead of "
               "misattributing it to AFSVC."),
        c("Can_Edit_Requirements", "Boolean", req=True,
          note="Defaults OFF. Reviewing a 1119 and changing what a 1119 IS are "
               "different jobs; configuration is policy."),
        c("Can_Grant_Access", "Boolean", req=True,
          note="Defaults OFF, and settable only by an Enterprise-scope holder. "
               "Stops the role self-propagating — without this, one grant makes "
               "the population monotonically increasing."),
        c("Grant_Scope", "Choice", req=True, choices=GRANT_SCOPE,
          note="Portfolio = own portfolio only. Enterprise = anywhere, and that is "
               "two or three people, not a default. Limits blast radius."),
        c("Grant_Type", "Choice", req=True, choices=GRANT_TYPE,
          note="GAL derived, Requested or Manual. Distinguishes what identity gave "
               "someone from what a human granted them."),
        c("Granted_By", "Text"),
        c("Granted_Date", "DateTime"),
        c("Expires_Date", "DateTime", indexed=True,
          note="REQUESTED ACCESS EXPIRES. Sixty days by default. Someone who PCS'd "
               "but still owes their losing base a package needs a handover window, "
               "not permanent rights to a base they left."),
        c("Developer_Flag", "Boolean", req=True,
          note="Never granted by a role. Unlocks the diagnostic surface."),
        c("Tester_Flag", "Boolean", req=True),
        c("Active_Flag", "Boolean", req=True, indexed=True,
          note="Revocation without deletion, so the audit trail survives."),
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
        c("Scope_Confidence", "Text",
          note="A Proposed grain should be visibly provisional in the COP as well "
               "as in the app."),
        c("Routing_Org", "Text",
          note="ANG EOY submissions route to NGB/A1X. A COP that cannot show "
               "routing cannot answer 'where did they go'."),
        c("Component", "Text", note="Active, ANG or AFRC."),
        c("Required_Flag", "Boolean", req=True),
        c("Nominal_Due_Date", "DateTime", req=True,
          note="Leadership reporting uses the nominal dates, so 'the 5th' stays "
               "the 5th in a brief."),
        c("Effective_Due_Date", "DateTime", req=True,
          note="What the status was evaluated against."),
        c("Nominal_Final_Call_Date", "DateTime"),
        c("Effective_Final_Call_Date", "DateTime"),
        c("Due_Date_Adjusted", "Boolean"),
        c("Received_Flag", "Boolean", req=True),
        c("Initial_Submitted_DateTime", "DateTime"),
        c("Initial_Submission_On_Time", "Boolean",
          note="What the base is told."),
        c("Final_Evidence_On_Time", "Boolean",
          note="What leadership is told. Never show these two as bare booleans; "
               "translate them into a sentence."),
        c("Version_No", "Number"),
        c("QC_Status", "Text"),
        # C8. V3 carried Final_Status AND a duplicate Status_Semantic. Two columns
        # that must always agree are a defect waiting to happen.
        c("Final_Status", "Text", req=True, indexed=True,
          note="The semantic string, copied verbatim from the item. This is the ONLY "
               "semantic column: Power BI labels with it and never re-derives it."),
        c("Status_Code", "Number", req=True, indexed=True,
          note="0 Gray, 1 Red, 2 Yellow, 3 Green, 4 Blue, 5 Amber. Copied verbatim "
               "from the item. Power BI conditionally formats the whole COP matrix "
               "off this column and reproduces none of the logic."),
        c("Action_Owner", "Text", req=True),
        c("Action_Required", "Boolean", req=True),
        c("Package_State", "Text", req=True, choices=(),
          note="Facility-level rollup: ACTION_REQUIRED | IN_REVIEW | COMPLETE | "
               "IN_PROGRESS | NOT_APPLICABLE. Computed over semantic statuses, never "
               "over colour codes — a colour rollup calls [ACCEPTED, NOT_DUE, NOT_DUE] "
               "Complete when it is IN_PROGRESS."),
        c("Days_Late", "Number", note="Magnitude. Amber and Red share an owner."),
        c("Current_File_URL", "URL"),
        c("Generated_DateTime", "DateTime", req=True),
    ),
)



# ==========================================================================
# Scheduling, access and notification
# ==========================================================================

MF_Non_Duty_Day = ListDef(
    name="MF_Non_Duty_Day",
    title="MF Non Duty Day",
    grain="One row per non-duty date",
    volume_estimate=2000,
    unique_key=("Non_Duty_ID",),
    note="Federal holidays and wing down days. Resolves Nominal to Effective "
         "dates under NonDutyDay_Policy. A nominal suspense landing on a Saturday "
         "cannot be the date someone is held to, and a weekend suspense with no "
         "rule produces a monthly argument.",
    columns=(
        c("Non_Duty_ID", "Text", req=True, indexed=True),
        c("Date", "DateTime", req=True, indexed=True),
        c("Name", "Text", req=True, note="Independence Day, wing down day, and so on."),
        c("Scope_Type", "Choice", req=True, choices=("Enterprise", "Portfolio", "Installation"),
          note="A federal holiday is Enterprise. A wing down day is one installation."),
        c("Scope_ID", "Text", indexed=True, note="Null when Scope_Type is Enterprise."),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_Calendar_Event = ListDef(
    name="MF_Calendar_Event",
    title="MF Calendar Event",
    grain="One row per authored calendar entry",
    volume_estimate=20000,
    unique_key=("Event_ID",),
    note="Authored events only. Every expected item is ALREADY a dated event and "
         "is projected onto the calendar from MF_EOM_Item — duplicating them here "
         "would create two sources of truth for the same suspense. This list "
         "carries what the checklist cannot: assessments, data calls, reminders.",
    columns=(
        c("Event_ID", "Text", req=True, indexed=True),
        c("Event_Type", "Choice", req=True, choices=CALENDAR_EVENT_TYPE),
        c("Title", "Text", req=True),
        c("Event_Date", "DateTime", req=True, indexed=True),
        c("End_Date", "DateTime"),
        c("All_Day", "Boolean", req=True),
        c("Scope_Type", "Choice", req=True, choices=SCOPE_TYPE),
        c("Scope_ID", "Text", indexed=True),
        c("Linked_Item_ID", "Text",
          note="EOM_Item_ID where the event annotates a real obligation."),
        c("Status_Code", "Number", req=True,
          note="Copied from the linked item where there is one, so the calendar "
               "colours with the same six states as everything else."),
        c("Created_By", "User", req=True),
        c("Created_DateTime", "DateTime", req=True),
        c("Active_Flag", "Boolean", req=True, indexed=True),
    ),
)

MF_Access_Request = ListDef(
    name="MF_Access_Request",
    title="MF Access Request",
    grain="One row per request for access to an installation the requester is not posted to",
    volume_estimate=5000,
    unique_key=("Request_ID",),
    note="Modelled on how Teams handles a request to join. Someone who PCS'd but "
         "still owes their losing base a package requests that installation, with "
         "a justification and an expiry. The exception path to the GAL-derived "
         "model, not a parallel provisioning system.",
    columns=(
        c("Request_ID", "Text", req=True, indexed=True),
        c("Requester_UPN", "Text", req=True, indexed=True,
          note="Resolved identity, never a typed name."),
        c("Requester_Name", "Text", req=True, note="Display only."),
        c("Home_Installation", "Text", note="From the GAL. What identity already says."),
        c("Requested_Installation_ID", "Text", req=True, indexed=True),
        c("Justification", "Note", req=True,
          note="Required. A request with no reason cannot be judged."),
        c("Requested_Until", "DateTime",
          note="Sixty days by default. A handover window, not permanent rights."),
        c("Status", "Choice", req=True, choices=ACCESS_REQUEST_STATUS, indexed=True),
        c("Decided_By", "Text", note="Must hold Can_Grant_Access."),
        c("Decided_Date", "DateTime"),
        c("Decision_Comment", "Note"),
    ),
)

MF_Notification_Rule = ListDef(
    name="MF_Notification_Rule",
    title="MF Notification Rule",
    grain="One row per notification trigger",
    volume_estimate=100,
    unique_key=("Rule_ID",),
    note="Notifications are a LIST, not code. Every rule has an Enabled toggle and "
         "a Digest flag, and the toggles are on an admin screen rather than inside "
         "a flow. Two rules ship enabled; everything else is tuned once the queue "
         "behaves.",
    columns=(
        c("Rule_ID", "Text", req=True, indexed=True),
        c("Trigger_Event", "Choice", req=True, choices=NOTIFICATION_TRIGGER, indexed=True),
        c("Recipient_Type", "Choice", req=True, choices=NOTIFICATION_RECIPIENT,
          note="An org box, a role or the submitter. A named person's mailbox is "
               "never a rule target."),
        c("Recipient_Address", "Text",
          note="Resolved from MF_Installation.Org_Box_Email where the type is an "
               "org box."),
        c("Enabled", "Boolean", req=True, indexed=True),
        c("Digest", "Boolean", req=True,
          note="ON by default for anything recurring. One message per recipient per "
               "run listing everything they owe. Per-item mail across 103 "
               "installations is how a notification system gets muted in week one."),
        c("Cadence_Days", "Number", note="Null means once."),
        c("Subject_Template", "Text"),
        c("Notes", "Note"),
    ),
)


MF_Document_Destination = ListDef(
    name="MF_Document_Destination",
    title="MF Document Destination",
    grain="One row per portfolio per document domain",
    volume_estimate=20,
    unique_key=("Destination_ID",),
    note="THE FOUR PORTFOLIOS ARE FOUR SEPARATE SITE COLLECTIONS, not four "
         "channels in one team and not four folders in one library. Every "
         "earlier document in this programme assumed one site; that assumption "
         "was wrong and it invalidated every single-site provisioning plan. "
         "Site, library and root folder are configured per portfolio and never "
         "derived: Portfolio 2's site slug carries a 'Legacy_' prefix the other "
         "three do not, so a URL built by pattern 404s on exactly one "
         "portfolio — three work and one is a mystery, which is the worst "
         "failure shape there is. EOM-02 fails closed on an unbound, "
         "unverified or inactive row.",
    columns=(
        c("Destination_ID", "Text", req=True, indexed=True, note="PORT2-EOM"),
        c("Portfolio_ID", "Text", req=True, indexed=True),
        c("Document_Domain", "Choice", req=True, choices=DOCUMENT_DOMAIN, indexed=True,
          note="EOY shares the EOM destination unless a row says otherwise."),
        c("Site_URL", "Text",
          note="BLANK IN SOURCE, ALWAYS. Bound at import from the environment "
               "variable for this portfolio. A .mil site URL committed to "
               "source is a destination leak and the pre-release scan blocks "
               "it. Never a literal in Power Fx."),
        c("Library_Name", "Text", req=True,
          note="Assumed 'Shared Documents'. Verify per site — assumption is "
               "how this breaks on the first real upload."),
        c("Root_Folder", "Text", req=True,
          note="All four differ: 'Legacy_Portfolio 1/H. Monthly Data Call', "
               "'Legacy_Portfolio 2/5. Monthly Data Call', and two without a "
               "prefix. The 'H.' and '5.' are sort-order prefixes. No rule "
               "derives these; they are configuration."),
        c("Folder_Template", "Text", req=True,
          note="{FiscalYearShort}/{MonthFolder}. These are the names of "
               "folders that ALREADY EXIST and are matched, never rendered "
               "into a path and created. EOM-02 resolves the tokens; the app "
               "never sees them."),
        c("Create_Missing_Folders", "Boolean", req=True,
          note="FALSE, permanently. The FY and month folders are curated by "
               "hand. A flow that creates folders will eventually produce "
               "'Aug 26' beside someone's 'August 2026' and nobody notices for "
               "a month. The column exists so the decision is visible and "
               "auditable, not so it can be flipped."),
        c("Fallback_Policy", "Choice", req=True, choices=FALLBACK_POLICY,
          note="FIND_OR_ROOT for R1. See the vocabulary note above."),
        c("Month_Folder_Pattern_Note", "Text",
          note="THE ONE FIELD NOBODY WILL GUESS RIGHT. What the month folders "
               "inside FY26 are actually called on this site — 'Aug 26', "
               "'August 2026', '08. August' are all plausible. Recorded by the "
               "person who walks the site, for the next person who has to "
               "debug a file at root."),
        c("Site_Note", "Text",
          note="Which site collection this portfolio lives on, in words."),
        c("Verified_By", "Text",
          note="Who opened this site and read its real structure. Blank means "
               "nobody has, and EOM-02 will not write here."),
        c("Verified_Date", "DateTime"),
        c("Active_Flag", "Boolean", req=True,
          note="FALSE until verified. An unverified site cannot silently "
               "receive files."),
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
    MF_Non_Duty_Day,
    MF_Calendar_Event,
    MF_Access_Request,
    MF_Notification_Rule,
    MF_Document_Destination,
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
                     "Authority_Status", "Action_Required",
                     "Effective_Due_Date", "Effective_Final_Call_Date"):
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

    # Status evaluation uses EFFECTIVE dates; reporting uses NOMINAL ones.
    # Losing either pair collapses the distinction and produces a monthly
    # argument about weekend suspenses.
    for pair in (("Nominal_Due_Date", "Effective_Due_Date"),
                 ("Nominal_Final_Call_Date", "Effective_Final_Call_Date")):
        for col in pair:
            if col not in by_name:
                errs.append(f"MF_EOM_Item is missing {col}; the nominal/effective "
                            "pair is what keeps 'the 5th' the 5th in a brief while "
                            "the base is held to a date they can meet")

    # LATE and RETURNED are produced by the decision order. A choice column that
    # rejects them would make the flow fail on a state the engine can reach.
    for produced in ("LATE", "RETURNED"):
        if produced not in by_name["Final_Status"].choices:
            errs.append(f"MF_EOM_Item.Final_Status cannot store {produced}, which "
                        "the decision order in docs/status-calculation.md produces")

    # Amber. Six states, not five.
    if 5 not in STATUS_CODE_VALUES:
        errs.append("Status_Code 5 (Amber) is missing: without it, a base past the "
                    "first suspense and one past the final call look identical")

    # On-time is two questions, shown to two audiences.
    for col in ("Initial_Submission_On_Time", "Final_Evidence_On_Time"):
        if col not in by_name:
            errs.append(f"MF_EOM_Item is missing {col}")

    # The fact carries exactly one semantic column.
    fact_cols = {c.name for c in LISTS_BY_NAME["MF_EOM_Status"].columns}
    if "Status_Semantic" in fact_cols:
        errs.append("MF_EOM_Status carries both Final_Status and Status_Semantic; "
                    "two columns that must always agree are a defect waiting to happen")

    # Routing. The app supplies logical identifiers; EOM-02 resolves the rest.
    dest = LISTS_BY_NAME["MF_Document_Destination"]
    dest_by_name = {c.name: c for c in dest.columns}

    # Site_URL must be nullable or the seed cannot ship blank, and a seed that
    # cannot ship blank is a seed somebody fills in with a real .mil URL.
    if dest_by_name["Site_URL"].required:
        errs.append("MF_Document_Destination.Site_URL must be nullable: it ships "
                    "BLANK and is bound at import from an environment variable. "
                    "A required column invites a committed destination")

    # Three independent facts have to be true before a file is written, and all
    # three default to 'no'. Losing any one of them turns fail-closed into
    # fail-into-whatever-row-was-seeded.
    for gate in ("Active_Flag", "Verified_By", "Site_URL"):
        if gate not in dest_by_name:
            errs.append(f"MF_Document_Destination is missing {gate}; EOM-02 fails "
                        "closed on all three and cannot check one that is absent")

    sub_by_name = {c.name: c for c in LISTS_BY_NAME["MF_EOM_Submission"].columns}

    # The GUID is the durable handle. Under FIND_OR_ROOT files are moved by
    # design, so a build that stored only the URL would lose the audit trail on
    # exactly the files a human had to rescue.
    if "SharePoint_Unique_ID" not in sub_by_name:
        errs.append("MF_EOM_Submission is missing SharePoint_Unique_ID; the URL "
                    "does not survive the move that FIND_OR_ROOT plans for")

    # A misfiled document nobody can count is worse than an upload that failed.
    nf = sub_by_name.get("Needs_Filing")
    if nf is None:
        errs.append("MF_EOM_Submission is missing Needs_Filing")
    elif not nf.indexed:
        errs.append("MF_EOM_Submission.Needs_Filing must be indexed — Admin "
                    "filters on it and the list crosses the delegation ceiling")

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
            "DOCUMENT_DOMAIN": list(DOCUMENT_DOMAIN),
            "FALLBACK_POLICY": list(FALLBACK_POLICY),
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
