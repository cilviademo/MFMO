# The 17 lists — what they are, and why you don't build them by hand

## They are not folders

A SharePoint **List** is a table — rows and typed columns, like a spreadsheet
that lives in SharePoint. It is not a folder and it holds no files.

```
SharePoint List          a table of records      MF EOM Item, MF Facility
Document Library         a place files live      Shared Documents
Folder                   inside a library        FY26/August 2026
```

Your Monthly Data Call folders are the second and third of those. The 17 lists
are the first — they are the application's database. The documents stay where
they are; the lists record what was expected, what arrived, who reviewed it and
what happened.

## You don't create them manually

`provisioning/Provision-MFOpsLists.ps1` creates all 17, adds all 286 columns
with the exact internal names the formulas depend on, and sets the indexes.

Building them by hand would take a day and produce internal column names that
silently break the app — a column typed as `Installation ID` becomes
`Installation_x0020_ID` internally, and every formula referencing
`Installation_ID` then fails with no error message.

One command:

```powershell
.\Provision-MFOpsLists.ps1 -SiteUrl "https://<tenant>/sites/<your-ops-site>"
```

## What each one holds

| # | List | Cols | What it is |
|---|---|---|---|
| 1 | MF Installation | 10 | The 103 installations. Portfolio, MAJCOM, onboarding flag. |
| 2 | MF Facility | 7 | The 154 facilities. **Operating model lives here**, not on the installation. |
| 3 | MF EOM Requirement | 24 | The requirement catalogue. Change a suspense day here, not in the app. |
| 4 | MF EOM Item | 29 | **The core table.** One persistent row per expected submission per period. |
| 5 | MF EOM Submission | 28 | One row per uploaded file version. v1 and v2 both live here. |
| 6 | MF Unmatched File | 13 | Files found in a folder that couldn't be matched. Should stay near empty. |
| 7 | MF Security Mapping | 20 | Who can see and do what. Drives the app and Power BI RLS. |
| 8 | MF EOM Audit | 9 | Every state change. |
| 9 | MF App Config | 6 | The kill switch and the tunable values. |
| 10 | MF Feature Flags | 7 | Ship a screen dark, flip a checkbox to release it. |
| 11 | MF App Event Log | 13 | Business telemetry. |
| 12 | MF EOM Status | 32 | The flat fact table Power BI reads. Rebuilt nightly. |
| 13 | MF Calendar Event | 13 | Dates a Portfolio Manager authors. |
| 14 | MF Access Request | 11 | The PCS / TDY access request path. |
| 15 | MF Notification Rule | 9 | Notification triggers. All off for pilot. |
| 16 | MF Non Duty Day | 6 | Holidays and down days. Feeds the effective-date calculation. |
| 17 | MF Document Destination | 13 | Where files go. Four rows, one per portfolio. |

## The two that matter operationally

**MF EOM Item** is the checklist. It answers "what is missing", which is the
whole point of the application. Without it you can see what was submitted but
not what was not.

**MF EOM Submission** is the evidence. One row per version, nothing overwritten.

The other 15 support those two.

## What you create manually

Only what the CSVs cannot carry:

- The site itself, if you go with a dedicated one
- Your own row in `MF Security Mapping` so you can get in
- The four `Site_URL` values in `MF Document Destination`, after discovery

Everything else imports from `configuration/`.
