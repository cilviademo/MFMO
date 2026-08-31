# Deployment

Read `docs/government-environment-mode.md` first. Two answers gate everything:
**which government cloud this tenant is in**, and **whether you may run PAC
CLI against it**. Neither changes the design; both change these steps.

Both currently read `UNKNOWN` in `configuration/app_config.csv`. Do not guess
either one.

---

## Build order

Do not reorder this. Step 4 in particular: **do not build screens before
EOM-01 produces correct rows.** Every UI decision downstream depends on the
shape of that data, and a gallery built against rows with the wrong
`Facility_ID` semantics gets rebuilt, not adjusted.

### 1. Verify the capability gates

```powershell
pwsh provisioning/Verify-MFOpsCapabilities.ps1 `
    -SiteUrl <site> -TenantCloud <UsGov|UsGovHigh|UsGovDod>
```

Writes one `MF_App_Config` row per gate. **Stop if any of gates 1-5 is not
GREEN.** SharePoint, Power Apps and Power Automate are hard requirements with
no fallback; everything else degrades behind a flag.

### 2. Provision the lists

```powershell
python3 scripts/eom_schema.py --json > provisioning/schema.generated.json
pwsh provisioning/Provision-MFOpsLists.ps1 -SiteUrl <site> -TenantCloud <cloud> -WhatIf
pwsh provisioning/Provision-MFOpsLists.ps1 -SiteUrl <site> -TenantCloud <cloud>
```

**Confirm the indexes were created.** The script verifies them and throws if
any is missing. This is not a formality: SharePoint refuses to add an index to
a list that has already crossed the 5,000-item threshold, and `MF_EOM_Item`
passes it in the first quarter. An index missed here cannot be added later.

Expected: 12 lists, 164 columns, the evidence library with versioning on.

### 3. Seed configuration

```powershell
pwsh provisioning/Seed-MFOpsConfiguration.ps1 -SiteUrl <site> -TenantCloud <cloud>
```

Seeds `MF_App_Config`, `MF_Feature_Flags` and the twelve requirements. Then
load the **real** installation, facility, contract and security rows — the
`*.sample.csv` files are for a test tenant and are seeded only with
`-IncludeSampleData`.

Set `SiteUrl`, `EvidenceLibraryPath`, `PortfolioRootPath` and `SupportContact`
to real values. Leave `MaintenanceMode` and `ReadOnlyMode` `false`.

### 4. Build EOM-01 and run it

Import `flows/EOM01-GenerateExpectedItems`. Run it for the open period. Then,
**before building any UI**, verify in the tenant:

- [ ] Row count matches `python3 scripts/generate_expected_items.py` for the
      same seed data.
- [ ] `Facility_ID` is genuinely empty on every Installation- and
      Contract-scope row. Create two views — one filtered `Facility_ID is
      empty`, one filtered `Requirement_Scope is Installation or Contract` —
      and confirm the counts agree exactly. A mismatch means empty strings got
      written and every downstream filter is wrong.
- [ ] Run it a second time. Zero rows created, no `EOM_Item_ID` changed.
- [ ] A facility with a legacy DFAC and a Food 2.0 café shows different
      requirement sets on the two facilities.
- [ ] Every row past its suspense date is Gray, not Red.

### 5. Build the app shell

`App.Formulas` (both `.fx` files), `App.OnStart`, the containers, the four
components, then `scrHome`, `scrMaintenance`, `scrNoAccess`.

### 6. Build `scrUpload`

Import `flows/EOM05-AppUpload` first. **Test with an arbitrary filename** —
something like `Copy of copy FINAL(2).xlsx`. It must upload correctly, because
the declaration classified it and the filename was never read.

### 7. Build `scrInstallation` and `scrReview`

Import `flows/EOM04-QCDecision`. Test the correction cycle end to end:
submit → return with comment and new suspense → resubmit → accept. Confirm v1
survives with its QC comment intact.

### 8. Build EOM-03 and reconcile

```bash
python3 scripts/validate_solution.py --reconcile-fact \
    --items items_export.json --fact fact_export.json
```

**Every row, not a sample.** A disagreement means something derived a status
independently of the code, which is the failure the single-engine rule exists
to prevent.

### 9. Build EOM-02 and `scrUnmatched`

Drop a file directly into a Portfolio FY folder. Confirm it appears in the
queue with a suggestion, that the suggestion is *not* applied, and that no
`MF_EOM_Item` was created.

### 10. Build EOM-04 with notifications disabled

Leave `EnableNotifications` `FALSE`. **Read `MF_App_Event_Log` for a full
cycle** — the flow records every notification it would have sent, with
recipient and reason — before enabling anything.

### 11. Run the acceptance tests

Below, plus every gate in `docs/accessibility.md`.

### 12. Export, unpack, tag, commit

```bash
bash tests/run_tests.sh
pac canvas unpack --msapp MissionFeedingOperations.msapp --sources canvas-app/src
# export the solution as managed for production, unmanaged as the source of truth
cp MissionFeedingOperations_managed.zip dist/MissionFeedingOperations_v1.0.0.zip
git tag -a v1.0.0
```

The YAML is the code. If the unpacked YAML differs from what is committed,
review the diff before accepting it — a maker-portal edit that never reaches
the repository is a change nobody can review or roll back.

---

## Acceptance tests

Every one of these is run in the tenant. The local suite (`tests/run_tests.sh`)
is necessary and not sufficient.

### Data

| # | Test | Pass |
|---|---|---|
| D1 | EOM-01 is idempotent: second run creates nothing | |
| D2 | Installation- and Contract-scope rows have null `Facility_ID`, verified by the two-view count comparison | |
| D3 | A base running a legacy DFAC and a Food 2.0 café generates both requirement sets | |
| D4 | The EOY (`FiscalYear`) period generates `REQ-011` at installation scope | |
| D5 | An inactive requirement generates nothing | |

### Submission

| # | Test | Pass |
|---|---|---|
| S1 | Upload works with an arbitrary filename, via the flow, not the Attachments control | |
| S2 | Resubmission creates v2 and retains v1 with its file and QC comment | |
| S3 | Exactly one submission per item has `Is_Current_Version` true | |
| S4 | A file dropped in a Portfolio folder reaches Needs Classification | |
| S5 | An upload with no matching expected item is refused and creates no tracker row | |
| S6 | A tier 1 folder hint is displayed as a suggestion and is not applied | |

### QC and status

| # | Test | Pass |
|---|---|---|
| Q1 | A return without a comment is refused **by the flow**, not just by the disabled button | |
| Q2 | A return without a new suspense date is refused the same way | |
| Q3 | A return moves the item's `Suspense_Date` to the new date | |
| Q4 | A provisional requirement past suspense stays Gray, action owner Program | |
| Q5 | Verifying a requirement on `scrAdminRequirements` lets a past-suspense item go Red on the next run | |
| Q6 | An accepted item stays Green after its suspense date passes | |

### Rollups and the COP

| # | Test | Pass |
|---|---|---|
| R1 | Facility, installation and portfolio rollups are correct | |
| R2 | `[ACCEPTED, NOT_DUE, NOT_DUE]` reports 100%, not 33% | |
| R3 | A period with nothing due shows "Nothing due", not 0% or 100% | |
| R4 | `MF_EOM_Status` matches the app for **every** row | |
| R5 | RLS tested with at least two scopes: a facility user and an installation manager see different totals, and the facility user's installation figure is labelled as narrowed | |

### Delegation

| # | Test | Pass |
|---|---|---|
| G1 | Every query verified delegable at 5,000+ rows in `MF_EOM_Item` | |
| G2 | No blue-underline delegation warning in the maker portal on any screen | |
| G3 | A gallery over a 5,000-row period shows the correct total, and `scrDiagnostics` reports no truncation | |
| G4 | Every index declared in the schema exists on the list | |

**How to test G1 properly:** seed `MF_EOM_Item` past 5,000 rows for one
period before testing. A query that looks fine at 400 rows is the one that
lies at 5,000, and it lies without an error.

### Single-environment safety

| # | Test | Pass |
|---|---|---|
| E1 | `MaintenanceMode` true sends a normal user to `scrMaintenance` before any data loads | |
| E2 | A `Developer_Flag` holder still gets in | |
| E3 | `ReadOnlyMode` true disables every write affordance | |
| E4 | `ReadOnlyMode` true makes EOM-04 and EOM-05 **refuse**, tested by calling them directly, not through the app | |
| E5 | A normal user cannot reach `scrDiagnostics` by navigation, deep link or keyboard | |
| E6 | Turning `EnableUnmatchedQueue` off removes the destination from the nav for a normal user | |
| E7 | Telemetry writes on app open, upload and QC decision | |
| E8 | `MF_App_Config` unreachable: the app still loads and no optional dependency turns on | |

### Accessibility

Every gate A1-A13 in `docs/accessibility.md`. A1, A2, A4 and A10 are the ones
this app is most likely to fail.

---

## Rollback

Import the previous ZIP from `dist/`. This is tested as part of each release,
not assumed.

A rollback across a MAJOR version boundary needs the matching provisioning
run and is documented per release in the CHANGELOG. There is no automatic
down-migration and none is pretended: schema changes are additive within a
MAJOR version, and a retired column is marked unused rather than deleted —
deleting a SharePoint column destroys its data irreversibly.

---

## Troubleshooting

**"3 overdue" when there are eleven.** Delegation. Open `scrDiagnostics` and
compare the row count against the warning threshold. Then check the index on
the column being filtered — an index that was never created cannot be added
once the list passed 5,000 items, and the fix is a new list plus a migration.

**Blank columns everywhere after an import.** Schema mismatch. `scrDiagnostics`
compares `MF_App_Config.SchemaVersion` against what the app expects and warns.

**A facility's items stopped generating.** Check `Is_Active` on the facility,
the requirement's effective dates, and whether the requirement's
`Applies_To_Operating_Model` still includes that facility's model. A facility
that switched from `Legacy_DFAC` to `Food_2_0` legitimately stops generating
some requirements and starts generating others.

**Files in the library but not in the app.** EOM-02 runs every five minutes.
If they are older than that, check the trigger is bound at library level and
not to a folder — a folder-level trigger silently misses every folder created
after the flow was authored.

**Everything is Gray.** That is correct today. All twelve requirements are
`UNVERIFIED` and cannot drive Red. Verify one on `scrAdminRequirements`, with
a citation, and it will.
