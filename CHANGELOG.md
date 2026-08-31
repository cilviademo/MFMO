# Changelog

Semantic versions. Rollback is importing the previous ZIP from `dist/`, tested
as part of the release rather than assumed. Schema changes are additive; a
retired column is marked unused, never deleted.

---

## [1.0.0] — R1 release consolidation.

The consolidation pass. No new features; everything here makes the existing
build coherent, correct and importable. `docs/DECISION_LOG.md` records what was
superseded, `docs/DUPLICATION_AUDIT.md` what was consolidated, and
`docs/CORRECTNESS_VERIFICATION.md` the defects found and fixed.

**No Power Platform environment has been touched.** Tenant validation has not
occurred and the data-layer scope issue is open. Recommended target is **DEV or
PILOT only**.

### A second live upload architecture was removed

The build carried two. R1 writes evidence directly into each portfolio's own
authoritative destination — and it *also* still provisioned a central
`Mission Feeding Evidence` library, with `EOM_Root_Path` and
`EvidenceRootPath` telling an intake flow which subtree to watch and which to
ignore.

That is not a stale document. It was a second write target, created by the
provisioning script on every run. Removed from the script, the config, the
environment variables, the canvas formulas and the solution package in the same
commit that records the decision; only the explanation survives, in
`docs/DECISION_LOG.md` D-01.

### Seven correctness defects

| Defect | Why it mattered |
|---|---|
| `Delegation.fx` sorted three item queries on `Due_Date` | A column that stopped existing at the four-date split. `SortByColumns` against a missing column does not error — the list renders unsorted and nobody notices |
| `gen_registry.py` had gone stale | It emitted the raw QRG operating model and no `Facility_Type`, while the committed CSVs carried both. **Regenerating would have silently reintroduced the defect that cost a month** |
| The pilot onboarding was a hand edit to a *generated* file | And it was lost, in this pass, by running the generator — which is exactly how the generator went stale in the first place. Now `configuration/pilot-onboarding.csv` |
| No submission request idempotency | A user pressing Submit twice after a timeout — the normal case on a government network, not the edge case — got two files and two submission rows |
| The schema version check was a warning on a diagnostics screen, pinned to a stale `3.0` | A newer app writing against an older schema patches columns that do not exist, which writes nothing rather than erroring. A document reads as submitted while nothing was recorded |
| The fallback ceiling was implied by construction, not asserted | A file above the approved root looks like it worked: it is in SharePoint, the upload returned success, and it is somewhere nobody will look |
| `EOM_Folder_URL` described as the installation's folder root | A second answer to "where do this installation's documents live" is how two answers diverge |

### Orphaned package references

`Solution.xml` still declared `mfops_EOM02FileIntake` and
`mfops_EOM05AppUpload` — flows renamed two releases ago — and
`Customizations.xml` still defined the two retired environment variables while
knowing nothing of the four site bindings. An orphaned root component fails the
import with a message naming the missing component and nothing else useful, at
the worst possible moment.

A stale Teams connection reference went with them. Nothing used it, and an
unused connection reference is not free: it prompts at import, it needs its own
DLP conversation with the tenant admin, and it widens the declared surface for
no behaviour.

### One security claim was stronger than the deployment

The manifest carried `user_may_edit_audit_author: false`. The app writes
`Actor_UPN` as `User().Email`, which Power Apps derives from the signed-in
session and which a user cannot forge from inside the app — but nothing stops a
user with direct write access to the audit list. Recorded now as two separate
facts:

```
audit_author_is_authenticated_identity: true
audit_author_enforced_at_data_layer:    false
```

Claiming a control the deployment does not have is worse than recording the
gap, because the gap then never gets closed. It is the same exposure as
installation scope, on the same lists, and it closes the same way.

### Requirement applicability was implemented twice

`Cascade.fx` filtered the requirement dropdown with an inline predicate while
`generate_expected_items.py` decided what EOM-01 generates. The inline version
got the unknown-facility-type case right **by accident** — Power Fx `in` is
substring containment and the empty string is a substring of everything — and
got a real type that is a substring of another wrong: `MAF` matched a list
containing `MAFFO`. Both are now named functions matching on a delimited exact
term, held to the Python predicate by test.

### New gates

* `scripts/release_gate.py` — the 18 stop conditions. Exit 1 blocks the build.
* `scripts/routing_dryrun.py` — all four site collections, seven failure paths,
  proving no folder is created and no fallback rises above its approved root.
* `docs/SHAREPOINT_SCHEMA_MANIFEST.md` — internal names for 17 lists and 286
  columns, reconciled against every formula and flow in the three positions
  where a wrong name reads blank instead of erroring.
* `deployment/DEPENDENCY_MANIFEST.md` — 66 destination-side resources, each
  with an owner and a provisioning path. **16 MUST ALREADY EXIST**, 7 need
  manual `.mil` configuration, and importing the ZIP creates none of them.
* `docs/REPOSITORY_INVENTORY.md`, `docs/DECISION_LOG.md`,
  `docs/DUPLICATION_AUDIT.md`, `docs/CORRECTNESS_VERIFICATION.md`,
  `docs/SECURITY_VERIFICATION.md`, `docs/TEST_MATRIX.md`.

Three superseded documents were archived to `docs/archive/` with headers naming
what replaced them. Documentation is archived; executable code is removed.

346 tests, up from 248.

---

## [0.8.0] — The routing finding. Four site collections, not four channels.

Integrates v12, v13 and v14 with their action document, and the Figma design
build. One structural finding invalidates an assumption every earlier document
was built on; the rest is hardening the two failure shapes that keep recurring.

`docs/handoffs/RECONCILIATION.md` C21–C35 records every decision.

**No Power Platform environment has been touched.** `dist/` holds no ZIP.

### The four portfolios are four separate SharePoint site collections

Not four channels in one team. Every prior document assumed one site, and that
assumption invalidated every single-site provisioning plan built on it.

```
1  DAFMissionFeeding-Portfolio1          Legacy_Portfolio 1/H. Monthly Data Call
2  DAFMissionFeeding-Legacy_Portfolio2   Legacy_Portfolio 2/5. Monthly Data Call
3  DAFMissionFeeding-Portfolio3          Legacy_Portfolio 3/Monthly Data Call
4  DAFMissionFeeding-Portfolio4          Legacy_Portfolio 4/Monthly Data Call
```

Three things there break a naive build. **Portfolio 2's slug carries `Legacy_`
and the others do not** — a URL built by pattern 404s on exactly one portfolio,
which is the worst failure shape there is: three work and one is a mystery.
**All four root folder names differ**, two with sort prefixes no rule derives.
And **this is the DoD cloud, not GCC High**.

New list `MF_Document_Destination` (17 lists, 286 columns), one row per
portfolio, every one shipping `Site_URL` blank, `Verified_By` blank and
`Active_Flag` FALSE. EOM-02 fails closed on all three.
`deployment/site-bindings.md` is the walkthrough, and it is now a required
release artifact.

One thing got easier: a portfolio boundary is now a **site** boundary, which
SharePoint enforces natively. The data-layer scope gap is narrowed to
installation scope *within* a portfolio site. Not closed —
`data_layer_permissions_verified` stays false.

### Find, never create

`Create_Missing_Folders` is FALSE permanently, with `FIND_OR_ROOT` as the
fallback. The FY and month folders are curated by hand; the flow matches them.

A flow that creates folders will eventually produce `Aug 26` beside someone's
`August 2026`. Both look right, half the submissions go to each, and nobody
notices for a month.

`scripts/folder_resolver.py` matches `FY26` / `FY 26` / `FY2026`, then the
month by full name, three-letter form and two-digit number in that order,
rejecting a folder that states the wrong year. When nothing matches, the file
lands at the Monthly Data Call root with `Needs_Filing` and a note saying what
was searched for. **A submission that lands somewhere findable beats one that
fails** — the base did their part, and the mess is ours, visibly.

The v14 spec said the opposite in the same snapshot as the action document, and
also failed closed on `Channel_Type`, a column that snapshot's own schema no
longer defines. A spec that fails closed on an absent column fails open.

### A filter that matches nothing must say so

Twice a generator filtered on a vocabulary the data does not use and reported
"created 0" as success — first `Legacy/APF` against a registry saying `Legacy`,
then facility types the QRG does not carry at all.

`scripts/vocabulary_guard.py` runs before any row is generated and separates the
two zeroes: a term the data contains **nowhere** raises; a real term that no
currently-onboarded row happens to carry is reported, not raised. Failing the
second would make onboarding one base at a time impossible; passing the first
cost a month.

And the corollary, now tested: **an empty filter column means "no constraint",
never "no match"**. Under-generating is worse than over-generating.

### The release gate checks content, not just paths

`ROLLBACK.md` once shipped as a zero-byte file and passed a check that only
asked whether the path resolved — the exact shape of failure the scan exists to
prevent, occurring in the scan itself. Required artifacts are now checked for
substance.

Inline scanner exceptions now **require a reason string**. An exception nobody
explained silences a rule and leaves nothing to review.

`URL-01` was written for GCC High and watched `.sharepoint.us`. This tenant is
DoD, so it watched the one host a leak could not occur on and missed the one it
could. It now watches both, and `URL-02` catches a portfolio slug used as a
path.

### Amber and yellow are finally different colours

They were `#8A5300` and `#6B5300` — **1.16:1 apart**, two near-identical browns
under a model whose entire point is that colour carries ownership. Amber says
the base still owes it and has runway; yellow says AFSVC has it.

Now `#944800` on `#FFF3E6` and `#5A5800` on `#FDFAE0`: ΔE2000 25, 41° of hue,
each above 6:1 on its own background, and still 14–18 ΔE apart under
deuteranopia, protanopia and tritanopia.

The build note asked for 3:1 between the two text colours. **That test cannot be
passed and should not be attempted** — WCAG contrast is a luminance ratio, two
colours differing only in hue sit at 1.0:1, and forcing 3:1 makes one fail 4.5:1
against its own tint. `docs/accessibility.md` gives the measure that does answer
the question.

The obvious fix has a second trap: amber pushed toward orange lands near red,
and red-versus-amber is the *no runway* / *has runway* distinction. The first
candidate scored ΔE 30 against yellow and 14.5 against red. The shipped amber
holds 19.5 against red, and the tests hold both distances at once.

### Configuration, not code

`ReviewAgeHighlightDays` is new, and the review-age bands are **derived** from
it rather than listed beside it — four hardcoded buckets next to a separately
hardcoded threshold is two facts that must agree with nothing making them.

Upload size, accepted file types and both suspense days already lived in
configuration. The suspense days stay on the requirement row, never as a default
in the date code: the 5th and the 10th do not have the same standing, and a
shared default makes both unchallengeable.

### Any percentage states its denominator

**A not-onboarded installation is not compliant. It has not been asked.** All
103 ship `Generation_Enabled = FALSE` and contribute no rows, so a percentage
over existing rows reports 100% while the enterprise has barely started.

```
43 of 43 onboarded installations complete
60 installations not yet onboarded
```

Never one number. In the Power BI measures as well as the tests.

### Also

- `docs/native-visuals.md`: build in-app visuals from containers and
  `FillPortions`, not the chart controls — ~50-row cap, no theming, poor
  screen-reader support. At 103 installations a portfolio comparison silently
  shows part of the data and reports success.
- `EOM-05 App Upload` is now `EOM-02 Submission`; `EOM-02 File Intake` is now
  `EOM-02b Legacy Intake`. EOM-02b is deployed **four times**, once per site.
- `SharePoint_Unique_ID` is the durable handle. Under FIND_OR_ROOT files get
  moved by design, and a build storing only the URL would lose the audit trail
  on exactly the submissions somebody had to rescue.
- `Seed-MFOpsConfiguration.ps1` pointed at `installations.sample.csv` and
  `facilities.sample.csv`, renamed two releases ago. Fixed, with the real
  registry behind `-IncludeRegistry`.
- The Figma build's other two defects — a hardcoded four-month period selector
  and zero accessible names across 31 buttons — do not exist in the canvas
  source. Both now have regression tests so they cannot appear.
- 248 tests, up from 134.

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
