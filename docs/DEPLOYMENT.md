# Deployment

Read `government-environment-mode.md` first. **Two answers gate everything:**
which government cloud this tenant is in, and whether PAC CLI is authorized
against it. Both currently read `UNKNOWN` in `configuration/app-config.csv`.

**Do not promise zero-touch deployment.** Tenant-specific SharePoint rebinding
after import is a real manual step and is listed below.

---

## Build order

Do not reorder this. **Do not build screens before EOM-01 produces correct
rows** — every UI decision downstream depends on the shape of that data, and a
gallery built against rows with the wrong `Facility_ID` semantics gets rebuilt,
not adjusted.

### 1. Verify the capability gates

```powershell
pwsh provisioning/Verify-MFOpsCapabilities.ps1 `
    -SiteUrl <site> -TenantCloud <UsGov|UsGovHigh|UsGovDod>
```

**Stop if any MVP dependency is unavailable.** SharePoint, Power Apps, Power
Automate and gov Power BI have no fallback; everything else degrades behind a
flag.

### 2. Provision the lists

```powershell
python3 scripts/eom_schema.py --json > provisioning/schema.generated.json
pwsh provisioning/Provision-MFOpsLists.ps1 -SiteUrl <site> -TenantCloud <cloud> -WhatIf
pwsh provisioning/Provision-MFOpsLists.ps1 -SiteUrl <site> -TenantCloud <cloud>
```

Expected: **16 lists, 263 columns**, plus the evidence library with versioning
on.

**Confirm the indexes were created.** The script verifies them and throws if
one is missing. This is not a formality: SharePoint refuses to add an index to
a list that has already crossed the 5,000-item threshold, and `MF_EOM_Item`
passes it inside the first year. An index missed here cannot be added later —
the fix is a new list and a migration.

### 2a. Close the data-layer scope gap

**Do this before the pilot, not during the ISSM review.**
`docs/security-open-issue.md` records that the app's installation scope is
presentational until the evidence library enforces it independently. Option 1 —
item-level permissions per installation folder, driven by Entra groups — is the
recommendation and needs SharePoint administrator support.

The app build does not wait on this. The deployment does.

### 3. Seed configuration

```powershell
pwsh provisioning/Seed-MFOpsConfiguration.ps1 -SiteUrl <site> -TenantCloud <cloud>
```

Seeds `MF_App_Config`, `MF_Feature_Flags` and the twelve requirements. Then
load the **real** installation, facility and security rows — the `*.sample.csv`
files are for a test tenant and only load with `-IncludeSampleData`.

Set `PowerBIReportURL`, `SupportContact`, `EOM_Root_Path`, `EvidenceRootPath`
and `CurrentFiscalYear` to real values. Leave the kill switch off.

### 3a. Build the registry and onboard the pilot

`MF_Installation` and `MF_Facility` are the authoritative EOM operational
registry — no enterprise source tracks what EOM needs. For each pilot base:
populate its facilities and operating models, validate them, set
`Registry_Validated_By` and `Registry_Validated_Date`, then set
`Generation_Enabled = TRUE`.

**Nothing generates for a base until that flag is set**, and a base with it
FALSE reads as *not yet onboarded*, never as compliant. Expect the first
version to be wrong at a handful of bases.

### 4. Build EOM-01 and run it

Then, **before building any UI**, verify in the tenant:

- [ ] Row count matches `python3 scripts/generate_expected_items.py --period <p>`
      for the same seed data.
- [ ] `Facility_ID` is genuinely empty on every Installation- and
      Contract-scope row. Create two views — one filtered `Facility_ID is
      empty`, one filtered `Requirement_Scope is Installation or Contract` —
      and confirm the counts agree **exactly**. A mismatch means empty strings
      were written and every downstream filter is wrong.
- [ ] Re-run it. **Zero rows created**, no `EOM_Item_ID` changed.
- [ ] A base running both a legacy DFAC and a Food 2.0 cafe shows different
      requirement sets on the two facilities.
- [ ] Only onboarded installations generated anything.
- [ ] A weekend or holiday suspense produced a different `Effective_Due_Date`
      from its `Nominal_Due_Date`, with `Due_Date_Adjusted` TRUE.
- [ ] The 1119-1 generated **nothing** — it is conditional.
- [ ] The four health reports are distinguishable: awaiting onboarding, no
      operating model, no confirmed facility type, no applicable requirements.

### 5. Build the app shell

`App.Formulas` (all four `.fx` files), `App.OnStart`, the containers, the four
components, then `scrHome`, `scrMaintenance`, `scrNoAccess`.

### 6. Build `scrUpload` and EOM-05

**Test with an arbitrary filename** — `Copy of copy FINAL(2).xlsx`. It must
upload correctly, because the declaration classified it and the filename was
never read.

### 7. Build `scrInstallation` and `scrReview`

Test the correction cycle end to end: submit → return with comment and suspense
→ resubmit → accept. Confirm v1 survives with its QC comment.

Then test Wrong Document **before** and **after** the due date and confirm the
item shows `NOT_SATISFIED` then `OVERDUE` — not permanently Red.

### 8. Build EOM-03 and reconcile

```bash
python3 scripts/validate_solution.py --reconcile-fact \
    --items items_export.json --fact fact_export.json
```

**Every row, not a sample.**

### 9. Build EOM-02 and `scrUnmatched`

Drop a file straight into a Portfolio FY folder. Confirm it appears in the
queue with a suggestion, that the suggestion is **not** applied, and that no
`MF_EOM_Item` was created.

### 10. Build EOM-04 with notifications disabled

Leave the flag FALSE. **Read `MF_EOM_Audit` for a full cycle** — every intended
send is recorded as `Notification Suppressed` — before enabling anything.

### 11. Run the acceptance tests

Below, plus every gate in `accessibility.md`.

### 12. Export, unpack, tag, commit

```bash
bash tests/run_tests.sh
pac canvas unpack --msapp MissionFeedingOperations.msapp --sources canvas-app/src
cp MissionFeedingOperations_managed.zip dist/MissionFeedingOperations_v1.0.0.zip
git tag -a v1.0.0
```

If the unpacked YAML differs from what is committed, review the diff before
accepting it — a maker-portal edit that never reaches the repository is a
change nobody can review or roll back.

---

## Manual steps after import

These are real and are not automated away:

1. **SharePoint list rebinding.** Canvas data sources bind to list IDs. After
   import into a tenant whose lists were provisioned separately, each data
   source is re-pointed once in the maker portal.
2. **Connection references.** Supplied at import from the deployment settings
   file. The Outlook connection may be left empty while notifications ship off.
3. **Flow ownership and enablement.** Imported flows arrive off; enable them in
   the build order above, not all at once.
4. **Power BI dataset credentials and the RLS role membership.**

---

## Acceptance tests

Every one is run in the tenant. The local suite is necessary and not
sufficient.

### Data

| # | Test |
|---|---|
| D1 | EOM-01 is idempotent: a second run creates nothing |
| D2 | Installation- and Contract-scope rows have null `Facility_ID`, verified by the two-view count comparison |
| D3 | A base running a legacy DFAC and a Food 2.0 cafe generates both requirement sets |
| D4 | An inactive requirement generates nothing |
| D5 | A facility with no applicable requirement set is surfaced, not silently green |
| D6 | Quarterly and Annual requirements expand only in their months |

### Submission

| # | Test |
|---|---|
| S1 | Upload works with an arbitrary filename, via the flow, not the Attachments control |
| S2 | Resubmission creates v2 and retains v1 with its file and QC comment |
| S3 | Exactly one submission per item has `Is_Current` true |
| S4 | A file dropped in a Portfolio folder reaches Needs Classification |
| S5 | An upload with no matching expected item is refused and creates no tracker row |
| S6 | A folder hint is displayed as a suggestion and is never auto-applied |
| S7 | On-behalf submission records both the uploader and the target location |

### QC and status

| # | Test |
|---|---|
| Q1 | A return without a comment is refused |
| Q2 | A correction return without a suspense date is refused |
| Q3 | Wrong Document before due shows `NOT_SATISFIED`; after due, `OVERDUE` |
| Q4 | A provisional requirement past suspense stays Blue, owner Admin — never Red |
| Q7 | An item between the two suspenses is `LATE` / Amber, not Overdue |
| Q8 | A `Recalled` submission reverts the item to its date-based state |
| Q9 | Each of the four returning verdicts yields `RETURNED`, and the base sees the specific reason |
| Q10 | Both on-time facts are recorded independently on a returned-then-accepted item |
| Q5 | Marking a requirement Verified lets a past-suspense item go Red on the next run |
| Q6 | An accepted item stays Green after its due date passes |

### Rollups and the COP

| # | Test |
|---|---|
| R1 | Facility, installation and portfolio rollups are correct |
| R2 | `[ACCEPTED, NOT_DUE, NOT_DUE]` reports **In progress**, not Complete |
| R3 | An installation package includes its Installation- and Contract-scope items |
| R4 | `MF_EOM_Status` matches the app for **every** row |
| R5 | RLS tested with at least two scopes; a facility user does not receive a figure derived from their neighbours, and any narrowed figure is labelled |

### Delegation

| # | Test |
|---|---|
| G1 | Every query verified delegable at 5,000+ rows in `MF_EOM_Item` |
| G2 | No delegation warning in the maker portal on any screen |
| G3 | A gallery over a 5,000-row period shows the correct total; `scrDiagnostics` reports no truncation |
| G4 | Every index declared in the schema exists on the list |

**How to test G1 properly:** seed `MF_EOM_Item` past 5,000 rows for one period
first. A query that looks fine at 400 rows is the one that lies at 5,000, and
it lies without an error.

### Single-environment safety

| # | Test |
|---|---|
| E1 | `MaintenanceMode` sends a normal user to `scrMaintenance` before any data loads |
| E2 | A `Developer_Flag` holder still gets in |
| E3 | `ReadOnlyMode` disables every write affordance |
| E4 | `ReadOnlyMode` makes EOM-04 and EOM-05 **refuse**, tested by calling them directly, not through the app |
| E5 | A normal user cannot reach `scrDiagnostics` by navigation, deep link or keyboard |
| E6 | Turning a feature flag off removes the destination from the nav |
| E7 | Telemetry writes on app open, upload and QC decision |
| E8 | `MF_App_Config` unreachable: the app still loads and no optional dependency turns on |
| E9 | An expired `Expires_Date` removes access without a cleanup job running |
| E10 | A `PORTFOLIO_MANAGER` without `Can_Grant_Access` cannot grant the role |
| E11 | `Generation_Enabled` FALSE shows "not yet onboarded", not an empty compliant package |

### Accessibility

Every gate in `accessibility.md`.

---

## Pilot

Three to five locations covering Legacy/APF, Food 2.0 and MAFFO/MAF, all three
requirement scopes, normal folder upload, app upload, on-behalf intake,
correction and versioning, wrong document, unmatched, overdue, an unverified
requirement, facility security, and portfolio QC.

**Target: at least 95% of clearly identifiable pilot files reconciled
automatically, and 100% of unresolved files routed visibly to Needs
Classification.** Nothing is silently ignored.

---

## Troubleshooting

**"3 overdue" when there are eleven.** Delegation. Open `scrDiagnostics` and
compare the row count against the threshold, then check the index on the
filtered column.

**Blank columns after an import.** Schema mismatch. `scrDiagnostics` compares
`MF_App_Config.SchemaVersion` against what the app expects and warns.

**A facility's items stopped generating.** Check `Active_Flag`, the
requirement's `Applicable_Model` against that facility's `Operating_Model`, and
`Applicable_Facility_Types`. A facility that switched from Legacy/APF to
Food 2.0 legitimately stops generating some requirements and starts others.

**Files in the library but not in the app.** Check the EOM-02 trigger is bound
at **library** level, not to a folder — a folder-scoped trigger does not fire
recursively and silently misses every folder created after it was authored.

**Everything is Blue.** That is correct today. All twelve requirements are
`UNVERIFIED` and cannot drive an adverse status. Verify one on
`scrAdminRequirements`, with a citation, and it will.
