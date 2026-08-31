"""Emit everything downstream of eom_schema.py."""
import csv, os, sys, json

sys.path.insert(0, os.path.dirname(__file__))
from eom_schema import LISTS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ------------------------------------------------------------ data dictionary
rows = []
for lname, l in LISTS.items():
    for col in l["columns"]:
        rows.append([lname, l["title"], l["grain"], col["name"], col["type"],
                     "Y" if col["required"] else "N",
                     "Y" if col["indexed"] else "N",
                     "; ".join(col["choices"]), col["note"], l.get("note", "")])
p = os.path.join(ROOT, "docs", "MF_EOM_Data_Dictionary.csv")
with open(p, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["List", "Display_Title", "Grain", "Column", "Type", "Required", "Indexed",
                "Choices", "Column_Note", "List_Note"])
    w.writerows(rows)
print(f"{len(LISTS)} lists, {len(rows)} columns -> docs/MF_EOM_Data_Dictionary.csv")

# --------------------------------------------------- PnP provisioning template
TYPEMAP = {"Text": "Text", "Note": "Note", "Number": "Number", "Currency": "Currency",
           "DateTime": "DateTime", "Boolean": "Boolean", "Choice": "Choice",
           "URL": "URL", "User": "User", "Lookup": "Lookup", "Calculated": "Calculated"}

ps = ['# Provision Mission Feeding Operations lists.',
      '# PnP.PowerShell. Run against the DEV site first.',
      '#   Connect-PnPOnline -Url $SiteUrl -Interactive',
      '# GCC High note: use -AzureEnvironment USGovernmentHigh on Connect-PnPOnline.',
      '',
      'param([Parameter(Mandatory=$true)][string]$SiteUrl)',
      '',
      'Connect-PnPOnline -Url $SiteUrl -Interactive -AzureEnvironment USGovernmentHigh',
      '']
for lname, l in LISTS.items():
    ps.append(f'# --- {lname} : {l["grain"]}')
    ps.append(f'$list = Get-PnPList -Identity "{l["title"]}" -ErrorAction SilentlyContinue')
    ps.append('if ($null -eq $list) {')
    ps.append(f'    $list = New-PnPList -Title "{l["title"]}" -Template GenericList -OnQuickLaunch')
    ps.append('}')
    for col in l["columns"]:
        t = TYPEMAP[col["type"]]
        args = [f'-List "{l["title"]}"', f'-DisplayName "{col["name"]}"',
                f'-InternalName "{col["name"]}"', f'-Type {t}']
        if col["required"]:
            args.append("-Required")
        if col["choices"]:
            ch = ",".join(f'"{x}"' for x in col["choices"])
            args.append(f'-Choices {ch}')
        ps.append(f'Add-PnPField {" ".join(args)} -ErrorAction SilentlyContinue | Out-Null')
    idx = [col["name"] for col in l["columns"] if col["indexed"]]
    if idx:
        ps.append(f'# Index before the list crosses 5,000 items. You cannot index after.')
        for i in idx:
            ps.append(f'Set-PnPField -List "{l["title"]}" -Identity "{i}" '
                      f'-Values @{{Indexed=$true}} -ErrorAction SilentlyContinue | Out-Null')
    ps.append('')
ps.append('Write-Host "Provisioning complete." -ForegroundColor Green')
with open(os.path.join(ROOT, "provisioning", "Provision-MFOpsLists.ps1"), "w",
          encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(ps))
print("provisioning/Provision-MFOpsLists.ps1")

# ------------------------------------------------------- requirement seed data
# Working scope matrix. UNVERIFIED items are generated as inactive configuration,
# never as hard-coded logic, and never drive a Red status.
REQ = [
    # ========================================================================
    # Source: AFSVC "End of Month/Year Procedures", Required Documents.
    # Supporting: DAFMAN 34-131 ch 7.14; DFAC Manager Handbook 1.7.5;
    # Storeroom Handbook 5.3.4.
    #
    # Authority_Status answers "does this requirement exist".
    # Scope_Confidence answers "at what grain is it filed".
    # These are DIFFERENT claims and the deck answers only the first.
    # ========================================================================
    # ID, Code, Name, Model, Scope, ScopeConf, ScopeBasis, FacTypes, Freq, Required,
    #   DueDay, FinalDay, QC, Authority, Status, Sort, Active
    ("REQ-001", "1119", "AF Form 1119 Feeding Summary", "Legacy/APF", "Facility", "High",
     "The 1119 initialises one facility and one month; SAIIT requires 1119 sales to match "
     "CrunchTime and Aloha per operation.",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Monthly", 1, 5, 10, 1,
     "AFSVC EOM/EOY Procedures, Required Documents.", "VERIFIED", 10, 1),

    ("REQ-002", "1119-1", "AF Form 1119-1 (Field feeding)", "Legacy/APF", "Facility", "Medium",
     "Follows the 1119's grain if it is filed alongside it.",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Conditional", 0, 5, 10, 1,
     "AFSVC EOM/EOY Procedures names this FIELD FEEDING. OPEN RULING: seeded Conditional and "
     "not auto-generated, because auto-generating it would red-flag every DFAC that ran no "
     "field feeding. If it is in fact a monthly companion to the 1119, set Frequency=Monthly "
     "and Required_Flag=TRUE.", "VERIFIED", 20, 1),

    ("REQ-003", "SF1080", "SF 1080 Voucher for Transfers", "Legacy/APF", "Installation", "Proposed",
     "Reimbursement is normally consolidated. NOT supported by the deck either way.",
     "", "Monthly", 1, 5, 10, 1,
     "AFSVC EOM/EOY Procedures, Required Documents. Scope PROPOSED.", "VERIFIED", 30, 1),

    ("REQ-004", "SAIIT", "SAIIT review (Sales, Adjustments, Invoices, Inventory, Transfers)",
     "Legacy/APF", "Facility", "High",
     "Written around DFAC and storeroom management: inventory review, sales, adjustments, "
     "invoices, transfers between operations at one installation.",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Monthly", 1, 5, 10, 1,
     "AFSVC EOM/EOY Procedures. DFAC Manager Handbook 1.7.5.3 — SAIIT review within 24 hours of "
     "storeroom review, completed NLT 5 days after the inventory date.", "VERIFIED", 40, 1),

    ("REQ-005", "GPC", "Bank Statement (GPC purchases)", "Legacy/APF", "Installation", "Proposed",
     "Installation initially, deliberately NOT facility. If an installation has multiple "
     "cardholders this may need an account/cardholder grain, and hard-wiring it to facility "
     "now would make that a schema change instead of a configuration change.",
     "", "Monthly", 1, 5, 10, 1,
     "AFSVC EOM/EOY Procedures, Required Documents. Scope PROPOSED.", "VERIFIED", 50, 1),

    ("REQ-006", "1038", "AF Form 1038", "Legacy/APF", "Installation", "Low",
     "Administrative rather than operational. Weakest scope evidence of the six.",
     "", "Quarterly", 1, 5, 10, 1,
     "AFSVC EOM/EOY Procedures, Required Documents — QUARTERLY. Generates Dec/Mar/Jun/Sep only. "
     "Scope PROPOSED.", "VERIFIED", 60, 1),

    # ------------------------------------------------------------------ EOY
    # PARTIALLY defined. Additional September evidence, not a second package.
    ("REQ-020", "EOY-MFR", "EOY disinterested party memorandum (MFR)", "Legacy/APF", "Facility",
     "Medium", "The MFR is prepared by the DFAC manager for that facility's inventory.",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Annual", 1, 5, 10, 1,
     "DAFMAN 34-131 7.14.5 via AFSVC EOM/EOY Procedures. DFAC manager prepares an MFR "
     "identifying inventory officers, outlining inventory and physical value; FSO/FSSC signs; "
     "copy to the Food Service Accountant.", "VERIFIED", 70, 1),

    ("REQ-021", "EOY-INV", "EOY inventory — signed last page", "Legacy/APF", "Facility", "Medium",
     "Follows the inventory, which is conducted per operation.",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Annual", 1, 5, 10, 1,
     "DAFMAN 34-131 7.14.5. Last page of the inventory to AFSVC/VMF; ANG to NGB/A1X — see "
     "MF_Installation.Component. EOY physical inventory 30 September, Inventory Officer from "
     "outside Food Service (7.14; Storeroom Handbook 5.3.4).", "VERIFIED", 80, 1),

    # ---------------------------------------------------- retired / not in scope
    ("REQ-007", "SIK", "Subsistence-in-Kind Bill", "Legacy/APF", "Installation", "Proposed", "",
     "", "Monthly", 0, 5, 10, 1,
     "Not listed in the current AFSVC EOM/EOY Required Documents procedure; retain inactive "
     "pending contrary authority.", "RETIRED_OR_NOT_APPLICABLE", 90, 0),

    ("REQ-008", "DAF79", "DAF Form 79", "All", "Installation", "Proposed", "",
     "", "Monthly", 0, 5, 10, 1,
     "Not listed in the current AFSVC EOM/EOY Required Documents procedure.",
     "UNVERIFIED", 91, 0),

    # ---------------------------------------------------------------- deferred
    ("REQ-010", "CONTRACTOR-INV", "Contractor invoice / Food 2.0 support", "Food 2.0", "Contract",
     "Proposed", "One invoice may cover several facilities under one CLIN.",
     "", "Monthly", 0, 5, 15, 1,
     "DEFERRED pending the Food 2.0 handbook. Aramark/Sodexo breakdowns reorganise into "
     "Portfolios 1-4 in October.", "UNVERIFIED", 95, 0),

    ("REQ-011", "SAIIT", "SAIIT review", "Food 2.0", "Facility", "Medium", "",
     "Main DFAC;Contract Cafe;MAF", "Monthly", 0, 5, 15, 1,
     "DEFERRED with the Food 2.0 package.", "UNVERIFIED", 96, 0),

    ("REQ-012", "MIDMONTH-INV", "Mid-month inventory review", "Legacy/APF", "Facility", "High",
     "Same grain as the month-end inventory.",
     "Main DFAC;MAF", "Monthly", 0, 20, 25, 0,
     "OUT OF SCOPE for v1. DFAC Manager Handbook 1.7.5.3: inventories are completed on the 15th "
     "AND the last day of every month. Only the month-end cycle is an EOM submission today.",
     "VERIFIED", 97, 0),
]
p = os.path.join(ROOT, "configuration", "requirements.csv")
with open(p, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["Requirement_ID", "Document_Code", "Document_Name", "Applicable_Model",
                "Requirement_Scope", "Scope_Confidence", "Scope_Basis",
                "Applicable_Facility_Types", "Frequency", "Required_Flag",
                "Due_Day", "Due_Basis", "Final_Due_Day", "Final_Due_Basis",
                "NonDutyDay_Policy", "QC_Required", "Authority_Reference",
                "Authority_Status", "Sort_Order", "Active_Flag"])
    for r in REQ:
        w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8],
                    "TRUE" if r[9] else "FALSE", r[10], "CALENDAR", r[11], "CALENDAR",
                    "NEXT_DUTY_DAY", "TRUE" if r[12] else "FALSE",
                    r[13], r[14], r[15], "TRUE" if r[16] else "FALSE"])
unver = sum(1 for r in REQ if r[14] == "UNVERIFIED")
inactive = sum(1 for r in REQ if not r[16])
print(f"configuration/requirements.csv — {len(REQ)} rows, {unver} UNVERIFIED, "
      f"{inactive} seeded INACTIVE pending applicability confirmation")

# ------------------------------------------------- environment variables
ENV = [
    ("MF_SharePointSiteURL", "String", "DEV site collection URL for the MF Operations lists"),
    ("MF_FileIntakeLibrary", "String", "Document library where FY folders live"),
    ("MF_EvidenceRootPath", "String", "Server-relative root for the managed evidence tree"),
    ("MF_RequirementList", "String", "MF EOM Requirement"),
    ("MF_ItemList", "String", "MF EOM Item"),
    ("MF_SubmissionList", "String", "MF EOM Submission"),
    ("MF_UnmatchedList", "String", "MF Unmatched File"),
    ("MF_SecurityList", "String", "MF Security Mapping"),
    ("MF_AuditList", "String", "MF EOM Audit"),
    ("MF_PowerBIReportURL", "String", "COP report deep link for the Home screen button"),
    ("MF_CurrentFiscalYear", "String", "FY2027"),
    ("MF_NotificationsEnabled", "Boolean", "Master switch. Ship FALSE; enable after UAT."),
    ("MF_EscalationDaysOverdue", "Number", "Days past suspense before escalation. Default 5."),
]
with open(os.path.join(ROOT, "configuration", "environment-variables.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"environmentVariables": [
        {"schemaName": f"mfops_{n}", "displayName": n, "type": t, "description": d,
         "defaultValue": "", "required": True} for n, t, d in ENV]}, fh, indent=2)

with open(os.path.join(ROOT, "configuration", "connection-references.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"connectionReferences": [
        {"schemaName": "mfops_sharepointonline", "connectorId":
         "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
         "displayName": "MF Ops - SharePoint"},
        {"schemaName": "mfops_office365users", "connectorId":
         "/providers/Microsoft.PowerApps/apis/shared_office365users",
         "displayName": "MF Ops - Office 365 Users"},
        {"schemaName": "mfops_office365", "connectorId":
         "/providers/Microsoft.PowerApps/apis/shared_office365",
         "displayName": "MF Ops - Outlook (notifications)"},
        {"schemaName": "mfops_teams", "connectorId":
         "/providers/Microsoft.PowerApps/apis/shared_teams",
         "displayName": "MF Ops - Teams (escalation)"}]}, fh, indent=2)
print("configuration/environment-variables.json, connection-references.json")
