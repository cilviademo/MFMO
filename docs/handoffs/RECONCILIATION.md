# Reconciliation record

Three inputs govern this repository, and they do not all agree. This file says
which wins where, and why. It is the decision record — if you think a choice
below is wrong, change it here first, then change the code.

| Input | What it is | Held in |
|---|---|---|
| **MASTER** | The consolidated project handoff. Broadest scope, the full data model, the UX direction, the pilot and acceptance criteria. | `docs/handoffs/MASTER_HANDOFF.md` |
| **CODEX** | The build handoff written against the V3 repo. Narrower, later, and explicitly corrects two MASTER conclusions. | `docs/handoffs/CODEX_BUILD_HANDOFF.md` |
| **V3** | The artifacts as first delivered. | `reference/v3/` |
| **v7–v11** | Four later solution snapshots, plus the programme's answers to twenty questions and the AFSVC procedures deck. **v11 is the current domain truth.** | `reference/v11/` |
| **BUILD NOTES** | The programme answers and three addenda that settle the suspense model, the security model, the QC verdicts and the requirement catalogue. | `docs/build-notes.md` |

## Precedence

**ACTION_DOCUMENT for anything it touches. v14 for the domain. CODEX for
engineering discipline. MASTER for what neither covers. V3 only where nothing
later contradicts it.**

`reference/v14/ACTION_DOCUMENT.md` is the latest and is explicitly a delta: it
carries the routing finding, the rulings on the previous build's findings, and
the Figma actions. Where it and the v14 handoff disagree — they do, on whether
the four portfolios are channels or site collections — the action document
wins, and the handoff's own header says so.

v14 and `build-notes.md` carry the programme's own rulings, so they win on
every question of *what the system must do*. CODEX still governs
*how the repository is built* — one engine, delegable queries, no fabricated
artifacts — because nothing later revisits those.

MASTER §40 claims to supersede earlier artifacts; CODEX is later still and was
written with V3 in front of it. Where CODEX explicitly reasons about a MASTER
position — it does so twice, under "Two corrections to earlier research" — CODEX
wins, because it is an argued correction rather than an oversight.

Where V3's *code* disagrees with V3's *own documentation*, the documentation
wins: the stale Power Fx is a known defect, called out below.

---

## Resolved conflicts

### 1. Is the app a place to upload from? — CODEX wins

MASTER prime directive 2 and §34.1 say do not make Power Apps the document
repository, demote Upload, normal intake is Teams/SharePoint.

CODEX correction 1 accepts the mechanism and rejects the conclusion: the
Power Apps **Attachments control** is the problem — it binds to a Form, targets
lists rather than libraries, and behaves badly on Teams and mobile. That is a
reason not to use that control. It is not a reason to stop people uploading
through the app, because reverting to folder-drop-only reintroduces the exact
classification risk the declaration removes.

**Resolution.** The app collects the file and the declared metadata and calls a
flow; the flow writes the library and the lists. No Attachments control. Folder
drops keep working through EOM-02. Both paths stay; the app is preferred.

V3's prototype had already landed here independently: "Upload is no longer a
top-level destination… It still declares installation, facility, requirement and
period at upload, so an attached document needs no classification — that
decision stands."

### 2. Classification tiers — CODEX wins

MASTER §5 specifies a ten-signal confidence pipeline. CODEX correction 2 calls
that a sound design for a system that must infer, and observes that this system
mostly does not have to.

**Resolution.** Tier 0 `Declared at upload` is the production baseline. Tier 1
is a folder/uploader hint, shown as a suggestion and never applied. Tiers 2 and
3 exist as vocabulary and feature flags shipping `False`, with no code path in
R1. AI Builder must never become a dependency whose absence blocks the app.

### 3. Which status vocabulary? — V3 wins

MASTER §10 lists twelve semantic statuses. V3 implements eight, and its decision
order produces exactly those eight.

**Resolution.** V3's eight. The MASTER extras map in rather than disappearing:

| MASTER status | Where it lives now |
|---|---|
| `MISSING` | `OVERDUE` — a required document past suspense |
| `IN_PROGRESS` | a **package** state, not an item state |
| `WRONG_DOCUMENT` | a QC verdict on the submission; the item becomes `NOT_SATISFIED` before suspense, `OVERDUE` after |
| `NEEDS_CLASSIFICATION` | `MF_Unmatched_File.Resolution_Status` — never an item status, because no item exists yet |
| `SOURCE_MISSING` | not modelled in R1; the evidence library is the source and its absence is an outage, not a row state |
| `PENDING_REQUIREMENT_VALIDATION` | `PENDING_VALIDATION` |

V3's treatment of Wrong Document is a deliberate bug fix and is kept: a wrong
document does not stay Red forever. It means the requirement is still unmet, and
whether that is urgent depends on the suspense date, not on the reviewer's
verdict.

### 4. Which field carries the colour? — V3 and MASTER agree; the earlier build in this repo had it inverted

`Final_Status` is the **semantic string**. `Status_Code` is the **numeric visual
code**, 0–4. Both are stored, written together by one evaluation, and neither is
derived from the other.

An earlier commit on this branch had these reversed — `Status_Code` holding the
semantic string and `Final_Status` holding a colour name. That was a
reconstruction made before the V3 artifacts were available, and it is corrected.

### 5. Five visual states — CODEX and the V3 prototype win over the V3 Power Fx

`0` Gray not applicable · `1` Red overdue · `2` Amber needs attention ·
`3` Green accepted · `4` Blue not due or informational.

V3's `status-calculation.md` decision table assigns `4` to both `NOT_DUE` and
`PENDING_VALIDATION`, and V3's prototype implements exactly that. But V3's Power
Fx in the same document returns `0` for a not-due item and has **no Blue branch
at all**, and `App.Formulas.fx` likewise switches over four states. The prose
"everything is gray on the 1st" is left over from the four-state model.

**Resolution.** Five states. The prototype and the decision table are right; the
Power Fx was stale. Same for `flows/EOM03` whose spec said an unverified
unreceived item "stays at `Status_Code = 0`" — it is `4`.

### 6. The rollup — V3 wins, and the earlier build in this repo was wrong

CODEX 8c says a colour rollup calls `[ACCEPTED, NOT_DUE, NOT_DUE]` Complete,
and that this is the failure to avoid. It does not say what the right answer is.
The earlier build here read it as "the right answer is 100% complete". It is
not.

**Resolution.** V3's package rollup: that package is `IN_PROGRESS`. Two
documents have not been filed. A package is `COMPLETE` only when every
applicable, non-provisional item is `ACCEPTED`.

```
any OVERDUE, CORRECTION_REQUIRED or NOT_SATISFIED   ACTION_REQUIRED
else any RECEIVED_PENDING_QC                        IN_REVIEW
else every applicable non-provisional item ACCEPTED COMPLETE
else anything applicable remains                    IN_PROGRESS
else                                                NOT_APPLICABLE
```

Completeness counting still exists for the COP, but it is a count of packages by
state, not a ratio that quietly treats "not yet due" as "done".

### 7. Screen names — CODEX names, MASTER structure

CODEX names the screens. MASTER §21 renames History to Activity and V3's
prototype notes confirm it: "History became Activity — business events, stamped
with the app version."

**Resolution.** CODEX's names, with `scrHistory` → `scrActivity`, which both
MASTER and the V3 prototype ask for and CODEX does not argue against. Navigation
is role-shaped per V3: three destinations for a facility user, six for an admin.

### 8. Flow artifacts — V3 wins

The earlier build here committed hand-written Logic Apps `definition.json` for
five flows. V3 deliberately ships `definition.md` implementation specs instead,
and gives the reason: "Flow definitions are environment-bound; a wrong-environment
export is worse than none."

That reasoning holds, and the fabricated JSON was worse than it looked — it had
never been imported, never validated against a connector, and its fidelity was
implied rather than real.

**Resolution.** Specs in Markdown, authored to be built against. The exported
solution ZIP carries the real definitions once a tenant exists.

### 9. `MF_Document_Location` — deferred, not dropped

MASTER §8 defines a location-mapping list. V3 does not implement it, and both
CODEX and V3 describe EOM-02 resolving portfolio and fiscal year positionally
from the folder path.

**Resolution.** Not added in R1 — a thirteenth list neither of the two later
inputs asks for. The path segments EOM-02 reads are configuration keys rather
than constants, so introducing the list later is a flow change and a seed, not a
schema migration. Recorded as an R2 item.

---

## Corrections applied to V3

These are changes to V3, not merely adoptions of it. Each fixes something the
V3 artifacts get wrong or leave out.

| # | V3 as delivered | Corrected to | Why |
|---|---|---|---|
| C1 | `App.Formulas.fx` has `StatusLabel()`, `StatusColor()` and `StatusSemantic()` — three parallel switches over the code | one evaluation returning the whole record | CODEX 8a. Three functions over one input is how a status engine starts lying, and V3's already disagree with V3's own decision table |
| C2 | Power Fx returns `0` for not-due; no Blue branch | five states, `4` for not-due and informational | CODEX 8b, V3's own decision table, V3's prototype |
| C3 | `MFRollup()` and the `Package Status Code` DAX are colour rollups | semantic package rollup | CODEX 8c, and V3's own prose calls the colour rollup wrong on the page above |
| C4 | `MF_EOM_Item` has no `Authority_Status` | denormalized onto the item | Decision rule 2 reads it. A join does not delegate, so without this the app cannot evaluate its own second rule |
| C5 | `MF_EOM_Item` has no `Received_DateTime` | added | V3's own DAX references `MF_EOM_Item[Received_Date]`, which does not exist |
| C6 | `MF_EOM_Item` has no `Days_Late` / `On_Time_Flag` | added | EOM-03's spec says to set them there rather than in DAX, and the fact carries them |
| C7 | `MF_EOM_Item` has no `Last_Reconciled_DateTime` | added | MASTER §36's "stale reconciliation" health check has nothing to check without it |
| C8 | `MF_EOM_Status` carries both `Final_Status` and a duplicate `Status_Semantic` | one semantic column, `Final_Status` | Two columns that must always agree are a defect waiting to happen. The accessibility doc's `Status_Semantic` reference is updated |
| C9 | `MF_EOM_Item.Status_Code` indexed but `Final_Status` not | both indexed | The app filters on the semantic status; MASTER §26 lists `Final_Status` as an index |
| C10 | Requirement seed has 14 of the 16 declared columns | all 16 | `Due_Offset_Months` and `Accepted_File_Types` were declared and never seeded |

---

# Integration 2 — v7 to v11, 31 Aug 2026

The versioning archive supersedes the V3 rebase in several load-bearing ways.
Where an earlier entry in this file conflicts with the table below, the table
below is current.

## What changed, and why

### 1. Six visual states, not five

```
Blue   4  not due, window open           nobody yet
Amber  5  past the first suspense        the base, WITH RUNWAY
Red    1  past the final call, returned  the base, OUT OF RUNWAY
Yellow 2  received, awaiting review      AFSVC
Green  3  accepted                       nobody
Gray   0  not applicable                 nobody
```

**Colour now carries ownership and time risk, not severity.** For a DFAC
manager opening the app once a month under time pressure, *which rows are my
problem* is the first question and this answers it without reading a label.

Amber means time risk; yellow means somebody else has it. Collapsing them tells
a manager that a document they filed on time and one they never sent are the
same kind of problem.

### 2. Two suspense dates, and a LATE window

First suspense 5 days after month end, final call the 10th. Between them an
item is `LATE` (amber), not overdue — **the only week in the cycle where a
reminder still changes the outcome.**

The two carry different standing and the model records it: the 5th is
`VERIFIED` from the procedure language, the 10th is a `MANAGEMENT_RULE` from
the programme. Labelling the 10th as source-verified would be a small lie that
becomes load-bearing the first time someone challenges it.

### 3. Nominal and effective dates

`CALENDAR` is the baseline — the source says "within 5 days" and does not say
duty days. But a nominal suspense landing on a Saturday cannot be the date
someone is held to, so every item carries four dates and `NonDutyDay_Policy`
resolves them against the new `MF_Non_Duty_Day` list.

**Status evaluates against effective; reporting uses nominal.** Leadership
still sees "the 5th"; the base sees "Due 5 Sep (Mon 8 Sep)".

### 4. On-time is two questions

`Initial_Submission_On_Time` and `Final_Evidence_On_Time`. Uploaded 4 Sep,
returned 9 Sep, accepted 12 Sep is *submitted on time* and *evidence late*, and
both are true. Shown to different audiences, and **never rendered as two bare
booleans.**

### 5. Installation is the unit of access

Nobody is provisioned for their own base: CAC identifies the user, the GAL
gives their installation, and anyone there may view and edit its submissions
regardless of unit. Two roles, not six.

**This dissolves the facility rollup leak** recorded against V3 — facility is
no longer the access boundary, so a facility-scoped rollup is not something to
defend. `MF_Access_Request` is the exception path, and **requested access
expires**.

### 6. Seven QC verdicts plus Recalled

Four of them collapse into one `RETURNED` status. The engine does not need four
states to say "it came back"; the submitter needs four reasons to know what to
fix, and those live on the submission.

A **recall** is the submitter withdrawing before review, not a rejection: the
item reverts to its date-based state.

### 7. The requirement catalogue is real now

1119, SF 1080, SAIIT, GPC bank statement, 1119-1 and 1038 quarterly, plus two
EOY documents. **Eleven of thirteen moved from `UNVERIFIED` to `VERIFIED` with
citations**, so rule 2 of the status engine now applies to almost nothing and a
missed 1119 turns red as it should.

SIK and DAF 79 are retired against the procedures deck and kept as a record of
the decision. The 1119-1 is **field feeding** and is `Conditional` — never
auto-generated.

**Authority and scope are separate claims.** `Authority_Status` answers *does
this requirement exist*; `Scope_Confidence` and `Scope_Basis` answer *at what
grain is it filed*, and four of the six are still `Proposed`.

### 8. Notifications are a list, not code

`MF_Notification_Rule`, with two rules shipping enabled and digest on by
default for anything recurring. Per-item mail across 103 installations is how a
notification system gets muted in week one.

### 9. The onboarding gate

`MF_Installation.Generation_Enabled`. EOM-01 generates only where it is TRUE,
so a base that is not yet onboarded reads as **not yet asked**, never as
compliant. The registry is the critical R1 configuration dependency — a
dependency, not a blocker: five pilot bases are seeded onboarded and everything
else can be built against them.

### 10. Security is now evidenced

`security/security-manifest.yaml`, `connector-allowlist.yaml`,
`role-matrix.csv` and `scripts/prerelease_scan.py`, wired into
`tests/run_tests.sh` as a release gate.

**`docs/security-open-issue.md` is unresolved and is the most important open
item in the repository:** Power Apps `Visible` and `Filter()` are not an access
boundary, and the evidence library does not yet enforce installation scope.
The app's scope claim is presentational until it does.

## Corrections applied to v11

As with V3, v11's own artifacts disagree with each other. The pattern is
identical: the decision table is current, the code is stale.

| # | v11 as delivered | Corrected to | Why |
|---|---|---|---|
| C11 | `Final_Status` choices omit `LATE` and `RETURNED` | both added | v11's own twelve-rule decision order produces both. The flow would have written a value the column rejects. |
| C12 | `Current_Acceptable_Evidence_DateTime` | `Acceptable_Evidence_DateTime` | 35 characters, over SharePoint's 32-character internal name limit |
| C13 | `Status_Code` has no value 5 in the schema | six values declared | Without Amber, a base past the first suspense and one past the final call look identical |
| C14 | Feature-flag `Minimum_Role` still uses the six-role vocabulary | `BASE_USER`, `PORTFOLIO_MANAGER`, `DEVELOPER` | The role model collapsed to two and the flags were not updated |
| C15 | `status-calculation.md` still carries the four-state Power Fx | removed; the code lives in one place | The same block has contradicted the decision table in the same file across four releases |
| C16 | Registry `Operating_Model` is `Legacy`; requirements say `Legacy/APF` | normalised on import, with the map in the schema | **Unmapped, nothing would ever match**: EOM-01 would generate zero facility rows and every base would read as having nothing due |
| C17 | Requirements filter on `Facility_Type`, which the QRG never populates | unknown type MATCHES, and is reported | Excluding on it drops every facility from every type-scoped requirement. A false expected row is visible; a missing one is not. |
| C18 | `Applicable_Period_Month`, `Routing_Org` and `Accepted_File_Types` declared but never seeded | seeded | The build notes state EOY carries month 9 and that `Routing_Org` exists for ANG; neither reached the data |
| C19 | `Operating_Model` required, but 20 registry rows are NO_DFAC | nullable, and reported separately | A base with no feeding facility is a record worth keeping, not a validation failure |
| C20 | `CHANGELOG.md` and `ROLLBACK.md` are empty files | written | The pre-release scan requires both, and a rollback nobody wrote down is not a rollback |

## Corrections applied to v14

| # | v14 says | Live tree | Why |
|---|---|---|---|
| C21 | `EOM02-Submission` builds the path from `{FiscalYear}/{ReportingPeriod}/{InstallationName}/{RequirementCode}` and creates missing folders | folders are **matched**, never constructed; `{FiscalYearShort}/{MonthFolder}` | The same snapshot's `ACTION_DOCUMENT.md` and `document-destinations.csv` both say find-never-create with `Create_Missing_Folders = FALSE`. The action document wins. A flow that creates folders eventually produces `Aug 26` beside someone's `August 2026` |
| C22 | The flow fails closed on `Channel_Type = 'Unverified'` | fails closed on `Active_Flag`, `Verified_By` and `Site_URL` | `Channel_Type` is not in that snapshot's own schema — it went away with the four-channels-in-one-team model. **A spec that fails closed on an absent column fails open** |
| C23 | Four portfolio channels in one Teams site | four separate **site collections**, one destination row and one env var each | The routing finding. Portfolio 2's slug carries a `Legacy_` prefix the others do not, so a URL built by pattern 404s on exactly one portfolio — three work and one is a mystery |
| C24 | Tenant cloud GCC High (or UNKNOWN) | **DoD**, `UsGovDod` | `usaf.dps.mil` / `dod.teams.microsoft.us`. Every GCC High endpoint written before 31 Aug 2026 is wrong for this deployment |
| C25 | `prerelease_scan` rule URL-01 watches `.sharepoint.us` | watches `.sharepoint.us` **and** `.dps.mil` | Written when the cloud was assumed GCC High, so it watched the one host a leak could not occur on and missed the one it could |
| C26 | Required release artifacts checked for existence | checked for **content** | `ROLLBACK.md` shipped as a zero-byte file and passed. That is the shape of failure this whole scan exists to prevent, occurring in the scan itself |
| C27 | Inline scanner exceptions need only a rule id | a **reason string is required**, minimum length enforced | An exception nobody explained silences a rule and leaves nothing to review |
| C28 | Vocabulary filters are checked by inspection | `scripts/vocabulary_guard.py` asserts every filter matched something, before any row is generated | Twice a filter matched nothing and reported success. A term the data never contains raises; a real term with no selected rows is a legitimate zero and is reported |
| C29 | Amber `#8A5300`, yellow `#6B5300` — 1.16:1 apart | `#944800` on `#FFF3E6` and `#5A5800` on `#FDFAE0` | Two near-identical browns under a model whose whole point is that colour carries ownership. Also **ΔE 19.5 from red**: the obvious "make amber more orange" fix trades the yellow collision for a red one |
| C30 | "Verify at least 3:1 between the two text colours" | ΔE2000 ≥ 20 and ≥ 30° of hue, each chip ≥ 4.5:1 on its own background, verified under three CVD simulations | **The 3:1 test cannot be passed.** WCAG contrast is a luminance ratio; two colours differing only in hue sit at 1.0:1, and forcing 3:1 between two chip texts makes one fail 4.5:1 against its own tint. 3:1 is also 1.4.11 Non-text Contrast, which governs *adjacent* colour, not two foregrounds that never touch |
| C31 | Review age bands `0-1 / 2-3 / 4-5 / 6+` beside a separate "aged 4 days or more" | bands **derived** from `MF_App_Config.ReviewAgeHighlightDays` | Two facts that must agree, with nothing making them agree. Change the threshold to 3 and the queue contradicts its own legend |
| C32 | Completion shown as a single percentage | every completion figure states its denominator | A not-onboarded installation is not compliant — it has not been asked. All 103 ship `Generation_Enabled = FALSE` and contribute no rows, so a percentage over existing rows reports 100% while the enterprise has barely started |
| C33 | `EOM-02b Legacy Intake` deduplicates on path | deduplicates on `SharePoint_Unique_ID` | Under FIND_OR_ROOT a file is moved *by design* by the human who files it. A path check would rediscover it as a stray on the day somebody tidied up |
| C34 | `MF_EOM_Submission` stores `SharePoint_File_ID` | stores `SharePoint_Unique_ID` as the durable handle, `File_ID` alongside | The GUID survives a rename and a move between libraries; the list item ID does not, and moves are now part of the design |
| C35 | `MF_EOM_Data_Dictionary.csv` reports 15 lists / 212 columns | regenerated: 17 lists, 282 columns | A generated file committed before its generator ran |

## Still open

Unchanged from both handoffs, and neither design nor code can close them:

1. **The data layer does not enforce installation scope.** Still the single
   most important item — `docs/security-open-issue.md` — but **narrowed**. The
   four portfolios turned out to be four separate site collections, so the
   portfolio boundary is now a site boundary that SharePoint enforces natively.
   What remains is installation scope *within* a portfolio site. Smaller, and
   still the thing an ISSM will ask about.
2. Whether PAC CLI is authorized against the tenant. *(The cloud question is
   closed: DoD, `UsGovDod`.)*
3. **The four site bindings.** Somebody has to open each of the four portfolio
   site collections and record the site URL, the library, the exact root folder
   and — the item nobody will guess right — **how the month folders inside FY26
   are actually named**. Four sites, about ten minutes.
   `deployment/site-bindings.md`. Without it EOM-02 files everything at the
   Monthly Data Call root and looks broken on day one.
4. **Scope confirmation for SF 1080, GPC and 1038**, all still `Proposed`, and
   confirmation of the three facility-grain proposals. Getting these wrong is
   not cosmetic: facility scope on a three-DFAC base means three expected rows
   and three uploads. **Confirm before the first generation run**, because
   changing scope after items exist means regenerating a period.
5. **Is the 1119-1 conditional?** Seeded `Conditional` and not auto-generated,
   because the deck names it "1119-1 (Field feeding)". If it is in fact a
   monthly companion to the 1119, set `Frequency = Monthly` and
   `Required_Flag = TRUE`. The note is on the row and the decision has not been
   made silently.
6. **Is the 5-day suspense a programme policy or derived from DAFMAN 34-131
   7.14.4?** If derived, the EOY suspense should key off 30 September rather
   than month end. Three different five-day clocks exist in the source.
7. **Are the 5th and the 10th calendar days?** Seeded `CALENDAR` with
   `NEXT_DUTY_DAY` adjustment, which is the defensible reading, but a weekend
   suspense with no confirmed rule produces a monthly argument.
8. The registry itself: facilities and operating models per base, validated,
   before `Generation_Enabled` is flipped. Five pilot bases are seeded.
9. EOY is **partially** defined. The two documents and their citations are
   settled; the expected-row grain, the QC checklist, whether count sheets are
   retained or submitted, and the closeout rules are not. Do not implement a
   complete EOY workflow until they are.
10. MASTER §42's remaining information items, none of which are schema
    blockers.
