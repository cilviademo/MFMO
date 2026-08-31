# Reconciliation record

Three inputs govern this repository, and they do not all agree. This file says
which wins where, and why. It is the decision record — if you think a choice
below is wrong, change it here first, then change the code.

| Input | What it is | Held in |
|---|---|---|
| **MASTER** | The consolidated project handoff. Broadest scope, the full data model, the UX direction, the pilot and acceptance criteria. | `docs/handoffs/MASTER_HANDOFF.md` |
| **CODEX** | The build handoff written against the V3 repo. Narrower, later, and explicitly corrects two MASTER conclusions. | `docs/handoffs/CODEX_BUILD_HANDOFF.md` |
| **V3** | The artifacts as actually built. The implemented schema, the prototype, the flow specs. | `reference/v3/` |

## Precedence

**V3 for what exists. CODEX for what to do next. MASTER for everything neither
covers.**

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

## Still open

Unchanged from both handoffs, and neither design nor code can close them:

1. Which government cloud — GCC, GCC High or DoD.
2. Whether PAC CLI is authorized against the tenant.
3. The authority reference for all twelve requirements. Every one is
   `UNVERIFIED`, so not one of them can currently drive a Red status. That is
   the intended behaviour, not a gap in the build.
4. MASTER §42's remaining seventeen information items, none of which are schema
   blockers.
