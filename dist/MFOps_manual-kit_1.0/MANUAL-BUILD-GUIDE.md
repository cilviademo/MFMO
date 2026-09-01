# MANUAL BUILD GUIDE — Mission Feeding Operations pilot, entirely by hand

Everything here happens in SharePoint, Power Apps Studio and the Power
Automate designer. **No solution import. No Dataverse. No CLI. No
temporary provisioning flow.** Work the phases in order; every step ends
in something you can SEE, and the next phase assumes you saw it.

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.


## Phase 1 — create the 17 lists

Work `LIST-BUILD-SHEETS/` in file order (01 → 17); the order is
dependency order. Do not skip ahead: transactional lists come last for a
reason.

- [ ] All 17 lists exist, named exactly as the sheets print them.
  **Verify:** Site Contents shows 17 new lists.

## Phase 2 — columns

Each sheet's column table, top to bottom, typing internal names exactly.

- [ ] Every sheet's column count matches.
  **Verify:** each sheet's VERIFY block, ticked.

## Phase 3 — indexes, while every list is still empty

- [ ] Every sheet's index list created, counts matching.
  **Verify:** sign `VERIFICATION.md` -- every row PASS, then and only
  then: `SAFE TO LOAD CONFIGURATION: YES`.

Per-list totals (derived from the schema; the suite fails if this table
drifts):

| # | List | Columns | Indexes |
|---:|---|---:|---:|
| 01 | `MF App Config` | 6 | 2 |
| 02 | `MF Feature Flags` | 7 | 1 |
| 03 | `MF Installation` | 18 | 4 |
| 04 | `MF Facility` | 19 | 5 |
| 05 | `MF EOM Requirement` | 23 | 4 |
| 06 | `MF Document Destination` | 15 | 3 |
| 07 | `MF Non Duty Day` | 6 | 4 |
| 08 | `MF Notification Rule` | 9 | 3 |
| 09 | `MF Security Mapping` | 20 | 8 |
| 10 | `MF Access Request` | 11 | 4 |
| 11 | `MF Calendar Event` | 13 | 4 |
| 12 | `MF EOM Item` | 32 | 13 |
| 13 | `MF EOM Submission` | 33 | 13 |
| 14 | `MF Unmatched File` | 13 | 4 |
| 15 | `MF EOM Status` | 39 | 8 |
| 16 | `MF EOM Audit` | 9 | 4 |
| 17 | `MF App Event Log` | 13 | 6 |
| | **TOTAL** | **286** | **90** |

## Phase 4 — CSV seeds (only after VERIFICATION.md says YES)

Follow `CSV-IMPORT/IMPORT-ORDER.md` -- grid-view paste only, **never
"New list → From Excel"**, row-count check after every paste.

- [ ] Config, flags, installations, facilities, requirements,
  destinations, notification rules pasted; counts match.
- [ ] `expected-items-2026-08-09.csv` pasted into `MF EOM Item`:
  **737 rows**, statuses as generated (737 × NOT_DUE, as of 2026-09-01).
  These do NOT refresh on their own in the manual pilot (EOM-03 is
  deferred); EOM-02 updates a row when a submission lands.
  **Verify:** the list shows 737 items.

## Phase 5 — your security row

- [ ] Create YOUR row in `MF Security Mapping` (UPN = your account,
  scope and role per the sample CSV's column layout -- the sample rows
  themselves are never pasted).
  **Verify:** after Phase 6, the app opens onto Home, not No Access.

## Phase 6 — canvas app (standalone Path C)

`CANVAS-MANUAL/PASTE-RUNBOOK.md`, sections 1–4. The Submit path stays
red until Phase 7 -- expected.

- [ ] 18 data sources, 4 formula files, 6 components, 16 screens, each
  screen's visible check ticked.

## Phase 7 — the EOM-02 flow, then attach it

`FLOW-BUILD/EOM-02-manual.md`, click by click, expressions verbatim.
EOM-01/03/04 are deferred (one page each in `FLOW-BUILD/` says what
replaces them: the CSV; manual review; nothing, deliberately).

- [ ] Flow built and the synthetic-submission test at the end of the
  manual passed: one row, one file, and the replay attempt returned the
  first result instead of duplicating.
- [ ] Flow attached in Studio (runbook section 5); Submit resolves.

## Phase 8 — pilot checks

- [ ] Save, publish, icon/description, Accessibility checker
  (runbook section 6).
- [ ] Share: app → security group as User; flow → Run-only, "Use this
  connection"; SharePoint permissions granted separately.
- [ ] A base-scoped tester sees Home / My Package / Calendar only, and
  their own installation's items only.
- [ ] One real pilot upload lands where `deployment` worksheets say it
  should. NOT TESTABLE LOCALLY -- only your tenant answers this.
