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
    # ID, Code, Name, Model, Scope, FacTypes, Freq, Required, DueDay, QC, Authority, Status, Sort, Active
    ("REQ-001", "1119", "AF Form 1119 Daily Feeding Summary", "Legacy/APF", "Facility",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Monthly", 1, 10, 1,
     "DAFMAN 34-131 - CONFIRM paragraph", "UNVERIFIED", 10, 1),
    ("REQ-002", "1119-1", "AF Form 1119-1 Continuation", "Legacy/APF", "Facility",
     "Main DFAC;Flight Kitchen;Satellite;MAF", "Monthly", 1, 10, 1,
     "Accompanies the facility 1119 - CONFIRM applicability", "UNVERIFIED", 20, 1),
    ("REQ-003", "SIK", "Subsistence-in-Kind Bill", "Legacy/APF", "Installation",
     "", "Monthly", 1, 10, 1,
     "SCOPE UNRESOLVED - may be consolidated installation billing rather than per DFAC",
     "UNVERIFIED", 30, 1),
    ("REQ-004", "1119", "AF Form 1119 Daily Feeding Summary", "MAFFO/MAF", "Facility",
     "MAF;Main DFAC", "Monthly", 1, 10, 1, "CONFIRM", "UNVERIFIED", 10, 1),
    ("REQ-005", "1119-1", "AF Form 1119-1 Continuation", "MAFFO/MAF", "Facility",
     "MAF;Main DFAC", "Monthly", 1, 10, 1, "CONFIRM", "UNVERIFIED", 20, 1),
    ("REQ-006", "SIK", "Subsistence-in-Kind Bill", "MAFFO/MAF", "Installation",
     "", "Monthly", 1, 10, 1, "SCOPE UNRESOLVED", "UNVERIFIED", 30, 1),
    ("REQ-007", "SF1080", "SF 1080 Voucher for Transfers", "Food 2.0", "Installation",
     "", "Monthly", 0, 10, 1,
     "APPLICABILITY UNRESOLVED - depends on the reimbursement/billing workflow",
     "UNVERIFIED", 40, 0),
    ("REQ-008", "DAF79", "DAF Form 79", "All", "Installation",
     "", "Monthly", 0, 10, 1, "APPLICABILITY UNRESOLVED - do not assume",
     "UNVERIFIED", 50, 0),
    ("REQ-009", "1038", "AF Form 1038", "All", "Installation",
     "", "Monthly", 0, 10, 1, "FREQUENCY AND SCOPE UNRESOLVED", "UNVERIFIED", 60, 0),
    ("REQ-010", "CONTRACTOR-INV", "Contractor invoice / Food 2.0 support", "Food 2.0", "Contract",
     "", "Monthly", 1, 15, 1,
     "Contract scope - one invoice may cover several facilities under one CLIN",
     "UNVERIFIED", 70, 1),
    ("REQ-011", "SAIIT", "SAIIT inventory accountability", "Food 2.0", "Facility",
     "Main DFAC;Contract Cafe;MAF", "Monthly", 1, 15, 1,
     "Inventory accountability is tied to the individual operation", "UNVERIFIED", 80, 1),
    ("REQ-012", "SAIIT", "SAIIT inventory accountability", "Legacy/APF", "Facility",
     "Main DFAC;MAF", "Monthly", 1, 15, 1, "CONFIRM", "UNVERIFIED", 80, 1),
]
p = os.path.join(ROOT, "configuration", "requirements.csv")
with open(p, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["Requirement_ID", "Document_Code", "Document_Name", "Applicable_Model",
                "Requirement_Scope", "Applicable_Facility_Types", "Frequency", "Required_Flag",
                "Due_Day", "QC_Required", "Authority_Reference", "Authority_Status",
                "Sort_Order", "Active_Flag"])
    for r in REQ:
        w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                    "TRUE" if r[7] else "FALSE", r[8], "TRUE" if r[9] else "FALSE",
                    r[10], r[11], r[12], "TRUE" if r[13] else "FALSE"])
unver = sum(1 for r in REQ if r[11] == "UNVERIFIED")
inactive = sum(1 for r in REQ if not r[13])
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
