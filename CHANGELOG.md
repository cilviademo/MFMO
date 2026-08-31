# Changelog

Semantic versions. Rollback is importing the previous ZIP from `dist/`, tested
as part of the release rather than assumed. Schema changes are additive; a
retired column is marked unused, never deleted.

---

## [0.6.0] — Reconciled build. Source complete, not yet built in a tenant.

Rebases this repository onto the **V3 artifacts** and reconciles the two
handoffs against each other. `docs/handoffs/RECONCILIATION.md` is the decision
record and lists every conflict and how it was resolved.

**No Power Platform environment has been touched.** `dist/` holds no ZIP.

### Corrected — the earlier commit on this branch was wrong

That commit was written before the V3 artifacts were available and
reconstructed the design from the build handoff alone. Several load-bearing
choices did not survive contact with the real thing:

- **`Final_Status` and `Status_Code` were inverted.** `Final_Status` is the
  semantic string; `Status_Code` is the numeric visual code 0–4. It had them
  the other way round.
- **The semantic vocabulary was invented.** The real eight are
  `NOT_APPLICABLE`, `NOT_DUE`, `PENDING_VALIDATION`, `OVERDUE`,
  `NOT_SATISFIED`, `CORRECTION_REQUIRED`, `RECEIVED_PENDING_QC`, `ACCEPTED`.
- **The rollup answer was wrong.** `[ACCEPTED, NOT_DUE, NOT_DUE]` is
  `IN_PROGRESS`, not "100% complete". Two documents have not been filed. There
  is no completion ratio; the COP counts packages by state.
- **The requirement catalogue was fictional.** The real twelve are AF Form
  1119, 1119-1, SIK, SF 1080, DAF 79, AF 1038, the contractor invoice and
  SAIIT, across Legacy/APF, Food 2.0 and MAFFO/MAF.
- **The schema was a guess.** The real one is `MF_EOM_Requirement`,
  `MF_Unmatched_File` and `MF_EOM_Audit` — not the invented `MF_Contract` and
  `MF_Reporting_Period`, and the unmatched queue is its own list rather than a
  state on the submission.
- **The flow JSON was fabricated.** Removed. V3 ships Markdown implementation
  specs for a stated reason, and that reasoning holds: an export that has never
  been imported is a drawing of source, not source.

### Corrections applied to V3

V3's own artifacts disagreed with each other in three places. The prototype and
the decision table were right; the Power Fx had drifted.

| # | Fixed |
|---|---|
| C1 | `StatusLabel()`, `StatusColor()` and `StatusSemantic()` — three parallel switches over one code — replaced by one evaluation returning the whole record |
| C2 | Power Fx returned `0` for a not-due item and had no Blue branch; now five states, `4` for not-due and informational |
| C3 | `MFRollup()` and the `Package Status Code` DAX were colour rollups, on the page below V3's own prose calling that wrong; now semantic |
| C4 | `MF_EOM_Item` gains `Authority_Status` — decision rule 2 reads it and a lookup would not delegate |
| C5 | `MF_EOM_Item` gains `Received_DateTime`, which V3's own DAX referenced and which did not exist |
| C6 | `MF_EOM_Item` gains `Days_Late` and `On_Time_Flag`, per EOM-03's own spec |
| C7 | `MF_EOM_Item` gains `Last_Reconciled_DateTime`, so the stale-reconciliation health check has something to check |
| C8 | `MF_EOM_Status` carried both `Final_Status` and a duplicate `Status_Semantic`; now one semantic column |
| C9 | `Final_Status` is indexed as well as `Status_Code` |
| C10 | The requirement seed gains the two declared columns it never carried |

### Schema

- **12 lists, 172 columns**, schema version 3.0, validated by assertion:
  the list set, index declarations, `Facility_ID` nullability, the two status
  fields and the ban on stored percentages all fail the build if broken.
- `docs/data-model.md` and `docs/MF_EOM_Data_Dictionary.csv` generated from it;
  a stale copy fails validation.
- The provisioning script consumes the generated JSON and declares nothing of
  its own. The lists are deliberately **not** solution components.

### Status

- One engine, one evaluation, returning
  `{ status, code, label, actionOwner, actionRequired }`.
- Ported from the V3 prototype's `itemStatus()` and `packageState()`, which
  were the most current V3 artifacts. The tests assert the Python, the Power Fx
  and the prototype agree on every status, code, label, owner and action flag,
  **including the evaluation order**, which is behaviour.
- A wrong document is `NOT_SATISFIED` before the due date and `OVERDUE` after —
  it does not stay Red forever.
- A provisional requirement is Blue and owned by the programme. With all twelve
  seeded requirements `UNVERIFIED`, that is the default path.

### Data and configuration

- The real twelve requirements, all `UNVERIFIED`, three inactive. Each records
  what is unresolved rather than leaving the citation blank.
- Sample dimension data with Lackland running both a legacy DFAC and a Food 2.0
  cafe, so the operating-model split is exercised by the tests.
- `TenantCloud` and `PacCliAuthorized` ship `UNKNOWN`; the kill switch ships
  off; AI flags ship off in prod **and** for testers.
- Every environment variable has a matching `MF_App_Config` row, so neither
  path is load-bearing alone.

### App

- 10 screens. `scrHistory` became `scrActivity` — business events and the audit
  trail, stamped with the app version.
- Navigation is role-shaped and feature-flagged: three destinations for a
  facility user, six for an admin.
- Home filters on **action ownership**, not colour, and separates *needs your
  attention* from *waiting on AFSVC*.
- `MF_VisibleItems` applies scope server-side before anything is counted, so a
  facility user never receives a figure derived from their neighbours'
  packages.
- On-behalf submission records both the uploader and the target location.
- `scrDiagnostics` is gated twice and carries the configuration health checks —
  facilities with no requirement set, stale reconciliation, unmatched backlog.

### Flows

Five Markdown implementation specs. EOM-02 binds at **library** level; no flow
has a path that creates an `MF_EOM_Item` from a file; EOM-04 ships disabled and
logs what it would have sent; EOM-05 is the new app-upload flow.

### Validation

`validate_solution.py` fails the build on a delegation anti-pattern, an inline
query against a high-volume list, a hard-coded URL or GUID, a list name as a
string literal, a positive `TabIndex`, absolute positioning, a missing
`AccessibleLabel`, an AI flag left on, stale generated docs, fabricated flow
JSON, or a missing reconciliation correction. **99 tests pass.**

### Known gaps

- **The PowerShell is reviewed, not executed.** No PowerShell runtime was
  available. Run each script with `-WhatIf` first.
- **Every tenant-side acceptance test is outstanding** — accessibility gates,
  RLS with two scopes, delegation at 5,000+ rows, index verification.
- **No release ZIP**, and none can honestly be produced without an environment.
- `MF_Document_Location` from the master handoff is deferred to R2; EOM-02
  reads path segments through configuration keys so adding it later is a flow
  change, not a migration.
- All twelve requirements remain `UNVERIFIED`. That is the programme's open
  question, not a gap in the build.

---

## [0.5.0] and earlier — V3 and before

Preserved unmodified in `reference/v3/`. Scaffold, requirement engine, facility
security, document ingestion and the QC workflow, per the release ladder in
`docs/government-environment-mode.md`.
