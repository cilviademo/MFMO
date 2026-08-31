# Changelog

Semantic versions. Rollback is importing the previous ZIP from `dist/`, tested
as part of the release rather than assumed. Schema changes are additive; a
retired column is marked unused, never deleted.

---

## [0.7.0] — v7-v11 integration. The programme's answers, and the AFSVC deck.

Integrates four later solution snapshots, the programme's answers to twenty
questions, and the AFSVC End of Month/Year Procedures deck. The domain model
changes substantially; `docs/handoffs/RECONCILIATION.md` records every decision
and `docs/build-notes.md` carries the programme's own rulings.

**No Power Platform environment has been touched.** `dist/` holds no ZIP.

### Six visual states, and colour now means ownership

```
Blue   4  not due, window open           nobody yet
Amber  5  past the first suspense        the base, with runway
Red    1  past the final call, returned  the base, out of runway
Yellow 2  received, awaiting review      AFSVC
Green  3  accepted                       nobody
Gray   0  not applicable                 nobody
```

Amber means *time risk*; yellow means *somebody else has it*. Collapsing them
tells a DFAC manager that a document they filed on time and one they never sent
are the same kind of problem.

### Two suspense dates, four date columns

First suspense 5 days after month end, final call the 10th, `LATE` between —
the only week in the cycle where a reminder still changes the outcome. The 5th
is `VERIFIED` from the procedure language; the 10th is a `MANAGEMENT_RULE` from
the programme, and the model records the difference.

Every item carries `Nominal_*` and `Effective_*` pairs resolved against the new
`MF_Non_Duty_Day` list. **Status evaluates against effective; reporting uses
nominal**, so "the 5th" stays the 5th in a brief while the base is held to a
date they can meet.

### On-time is two questions

`Initial_Submission_On_Time` and `Final_Evidence_On_Time`. Uploaded 4 Sep,
returned 9 Sep, accepted 12 Sep is *submitted on time* **and** *evidence late*.
Both stored, shown to different audiences, never rendered as two bare booleans.

### Installation is the unit of access

CAC identifies the user, the GAL gives their installation, and anyone there may
view and edit its submissions regardless of unit. Two roles, not six. This
**dissolves the facility rollup leak** recorded against V3 — facility is no
longer the access boundary.

`MF_Access_Request` is the exception path for someone who PCS'd and still owes
their losing base a package. **Requested access expires**, sixty days by
default, and `MF_LiveScope` honours the expiry in the app rather than waiting
for a cleanup job.

### Seven QC verdicts plus Recalled

Four collapse into one `RETURNED` status; the specific reason stays on the
submission, because the engine does not need four states to say "it came back"
and the submitter needs four reasons to know what to fix. A recall reverts the
item to its date-based state.

Accept means the reviewer **opened the file**. Bulk accept is therefore an
explicit multi-select, never a select-all button.

### The real catalogue and the real registry

Thirteen requirements — 1119, SF 1080, SAIIT, GPC, 1119-1, 1038, and two EOY
documents. **Eleven moved to `VERIFIED` with citations**, so rule 2 of the
status engine now applies to almost nothing and a missed 1119 turns red.

`Authority_Status` and `Scope_Confidence` are separate claims: the deck
confirms *which* documents are in the package, not *at what grain* each is
filed. Four grains remain `Proposed`.

The 1119-1 is **field feeding** and is `Conditional` — never auto-generated,
because a permanent red row on every DFAC that ran none is the false overdue
that teaches people to ignore the dashboard.

103 installations and 154 facilities from the Mission Feeding QRG, with five
pilot bases onboarded. `Generation_Enabled` is the onboarding gate: a base with
it FALSE reads as *not yet asked*, never as compliant.

### Security is evidenced

`security/` carries the manifest, connector allowlist and role matrix;
`scripts/prerelease_scan.py` is wired into `tests/run_tests.sh` as a release
gate. It now supports an **auditable inline exception** so a document that
names a prohibited string in order to prohibit it does not require skipping the
whole file — every exception is reported on every run.

`ROLLBACK.md` written, including the part that gets missed: a solution import
does not revert SharePoint columns, data, or status values already written.

### Corrections applied to v11

v11's artifacts disagree with each other in the same way V3's did — the
decision table is current, the code is stale. Ten further corrections, C11–C20,
each held by a test. The three that would have been silent failures:

- **C16** — the registry says `Legacy`, the requirements say `Legacy/APF`.
  Unmapped, EOM-01 would have generated **zero** facility rows and every base
  would have read as having nothing due.
- **C17** — requirements filter on `Facility_Type`, which the QRG never
  populates. Excluding on it drops every facility from every type-scoped
  requirement. Unknown now matches and is reported: a false expected row is
  visible, a missing one is not.
- **C11** — `Final_Status` could not store `LATE` or `RETURNED`, both of which
  v11's own decision order produces.

### Known gaps

- **The data layer does not enforce installation scope.** `security-open-issue.md`
  is the most important open item here: Power Apps `Visible` and `Filter()` are
  not an access boundary, and an ISSM will find it. Not a reason to delay the
  build; a deployment dependency to raise with the SharePoint administrator now.
- Four requirement grains remain `Proposed`. **Confirm before the first
  generation run** — changing scope after items exist means regenerating a
  period.
- Whether the 1119-1 is conditional is an open ruling, not a silent decision.
- EOY is **partially** defined: the documents and citations are settled; the
  row grain, QC checklist and closeout rules are not.
- The PowerShell is reviewed, not executed. Every tenant-side acceptance test
  is outstanding. No release ZIP, and none can honestly be produced without an
  environment.

**134 local tests pass.**

---

## [0.6.0] — Reconciled build against the V3 artifacts.

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

## [0.5.0] and earlier — V3 through v11

Preserved unmodified in `reference/v3/` and `reference/v11/`. Scaffold,
requirement engine, facility security, document ingestion and the QC workflow,
per the release ladder in `docs/government-environment-mode.md`.
