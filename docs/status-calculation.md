# Status calculation — ONE definition, three runtimes

The Power App, the reconciliation flow and Power BI must never disagree about
what colour a base is. This file is the single definition; the Power Fx, the
flow spec and the DAX are mechanical translations of it. **Change the rules
here first, then change all three.**

Reference implementation: `scripts/status_engine.py`.
Held in agreement by: `tests/test_status_engine.py`.

**Nothing about status is ever stored by a human.** There is no "set this to
yellow" control anywhere in the app, and no colour picker.

---

## Two fields, both stored, neither derived from the other

| | |
|---|---|
| `Final_Status` | the **semantic** string — nine values |
| `Status_Code` | the **numeric visual** code — 0 to 5 |

Both are written by one evaluation. Power BI conditionally formats the entire
COP matrix off `Status_Code` alone and labels with `Final_Status`; no DAX in the
report reproduces any of the logic below.

`Status_Code` is stored, and indexed, precisely so `Filter()` delegates. A
computed comparison would silently return the first 500 rows.

### The six visual codes

| Code | Colour | Meaning | Who acts next |
|---|---|---|---|
| 0 | Gray | Not applicable, waived, not required this period | nobody |
| 1 | Red | Past the final call, or returned for correction | **the base**, urgently |
| 2 | Yellow | Received, awaiting AFSVC review | **AFSVC** |
| 3 | Green | Accepted | nobody |
| 4 | Blue | Not due — the submission window is open | nobody yet |
| 5 | Amber | Past the initial suspense, final call not reached | **the base** |

**Colour carries OWNERSHIP and time risk, not severity.** For a DFAC manager
opening the app once a month under time pressure, *which rows are my problem*
is the first question, and this answers it without reading a single label.

```
Blue    nobody yet
Amber   the base, with runway
Red     the base, out of runway
Yellow  AFSVC
Green   nobody
Gray    nobody
```

**The amber/yellow split is the point.** Amber means *time risk*: the 5th has
passed, the base has until the 10th, nothing is wrong yet. Yellow means
*somebody else has it*: the file arrived and AFSVC owes a decision. Collapsing
them tells a DFAC manager that a document they submitted on time and a document
they have not sent are the same kind of problem.

**Four states were not enough either.** Collapsing "not applicable" and "not
due yet" into Gray made an installation whose requirements had simply not come
due display as *Not applicable*, which is false.

Six is the ceiling. A seventh would stop being scannable.

The trade is that Late and Overdue share a colour. Acceptable — both are the
base's action, the label distinguishes them, and `Days_Late` carries magnitude.
The alternative mixes ownership and severity in one channel and forces the user
to read every row.

> Every version of the Power Fx up to v11 returned `0` for a not-due item and
> had no Blue branch at all, contradicting the decision table in the same
> document. Corrected — `handoffs/RECONCILIATION.md` C2.

---

## One engine, one evaluation

The engine returns a **state object**, not a code:

```
{ status, code, label, actionOwner, actionRequired }
```

Label, colour and ownership come from a single pass. Two parallel functions —
one for the code, one for the label — invite divergence, and divergence in a
status engine is a silent wrong answer.

> V3 shipped *three*: `StatusLabel()`, `StatusColor()` and `StatusSemantic()`,
> each switching independently over the numeric code, and they had already
> drifted from the decision table. Corrected — `handoffs/RECONCILIATION.md` C1.

---

## Two suspense dates, and two versions of each

**First suspense: 5 calendar days after month end. Final call: the 10th.**

Between them an item is **LATE** (amber), not overdue. That middle window is
the only week in the cycle where a reminder still changes the outcome;
collapsing it into one red state throws that away.

The two have different standing and the model records it:

| | Source | `Authority_Status` |
|---|---|---|
| 5 days after month end | procedure language | `VERIFIED` |
| the 10th | programme decision | `MANAGEMENT_RULE` |

Labelling the 10th as source-verified would be a small lie that becomes
load-bearing the first time someone challenges it.

**`CALENDAR` is the baseline.** The source says "within 5 days" and does not
say duty days, business days or workdays. Do not infer duty days without a
citation.

> Three different five-day clocks exist in the source documents and only one is
> this. DAFMAN 34-131 7.14.4 is a fiscal-year *posting* rule; DFAC Manager
> Handbook 1.7.5.3 is an internal inventory-*review* deadline. The one
> configured in `Due_Day` is the programme's submission suspense — worth
> confirming that is a policy the programme sets rather than something derived
> from 7.14.4, because if it is derived, the EOY suspense should key off
> 30 September rather than month end.

### Nominal and effective

A nominal suspense that lands on a Saturday cannot be the date someone is held
to, and burying that adjustment in a formula produces a monthly argument. Every
item carries four dates:

```
Nominal_Due_Date              the policy date — "the 5th" stays the 5th
Effective_Due_Date            after NonDutyDay_Policy — what a person owes
Nominal_Final_Call_Date
Effective_Final_Call_Date
```

`NonDutyDay_Policy` defaults to `NEXT_DUTY_DAY` and resolves against
`MF_Non_Duty_Day` — federal holidays and wing down days, scoped enterprise,
portfolio or installation.

**Status evaluation always uses the effective dates. Reporting uses the nominal
ones.** Leadership still sees "the 5th"; the base sees:

```
1119        Due 5 Sep (Mon 8 Sep)
```

`Due_Date_Adjusted` is TRUE where they differ, and the package screen shows
both.

Both `Due_Day` and `Final_Due_Day` come from the requirement row, never from a
flow. Changing the 5th to the 7th is a list edit. A `Due_Day` of 31 in a
30-day month clamps to the last day rather than rolling into the next.

A QC return sets `Correction_Due` on the item. It does **not** move the
suspense dates: the original is what the on-time facts are measured against,
and rewriting it would erase the fact that the first attempt was late.

---

## On-time is two questions, not one

```
Initial_Submitted_DateTime      when the first version arrived
Initial_Submission_On_Time      by Effective_Due_Date
Acceptable_Evidence_DateTime    when an accepted version first existed
Final_Evidence_On_Time          by Effective_Final_Call_Date
```

Uploaded 4 Sep, returned 9 Sep, corrected and accepted 12 Sep: the base
submitted on time and AFSVC did not have usable evidence on time. **Both are
true.** Show the first to the base and the second to leadership.

**Never render these as two booleans.** Translate:

> Submitted 4 Sep — on time
> Accepted 12 Sep — final evidence after suspense

---

## Item status — decision order, first match wins

```
 1. Waived_Flag or not Required_Flag        NOT_APPLICABLE       0  nobody
 2. Requirement UNVERIFIED or PROPOSED,
    and not received                        PENDING_VALIDATION   4  Admin,    no action
 3. QC = Accepted                           ACCEPTED             3  nobody
 4. QC = Not Applicable                     NOT_APPLICABLE       0  nobody
 5. QC = Recalled                           by date              -  Facility
 6. QC in {Correction Required, Incomplete,
      Wrong Reporting Period, Wrong Facility}
                                            RETURNED             1  Facility, action
 7. QC = Wrong Document, past final call    OVERDUE              1  Facility, action
 8. QC = Wrong Document, before final call  NOT_SATISFIED        1  Facility, action
 9. Received, QC pending                    RECEIVED_PENDING_QC  2  Reviewer, action
10. Not received, before first suspense     NOT_DUE              4  Facility, no action
11. Not received, past first, before final  LATE                 5  Facility, action
12. Not received, past the final call       OVERDUE              1  Facility, action
```

Only the **current version** submission is consulted. A superseded version
never influences the item; that is what `Is_Current` is for.

**Rule 2 — a provisional requirement is informational, never adverse.** The
base has nothing to do and nothing is wrong, and the action sits with the
Admin: *verify the requirement*, not *file the document*.

Eleven of thirteen requirements are now `VERIFIED` against the AFSVC procedures
deck, so **this rule now applies to almost nothing.** A missed 1119 turns red
as it should. It still matters for the two deferred Food 2.0 placeholders, and
it is what stops a requirement nobody has confirmed from turning a base red.

**Rule 5 — a recall is the submitter withdrawing before review**, not a
rejection. The item reverts to its date-based state and the withdrawn version
stays in history as superseded.

**Rule 6 collapses four verdicts into one status but keeps the reason.**
`Final_Status` is `RETURNED`; `QC_Status` on the current submission carries the
specific verdict — Incomplete, Wrong Reporting Period, Wrong Facility — and
that is what the base reads on their dashboard and in the notification. The
engine does not need four states to say "it came back"; the submitter needs
four reasons to know what to fix.

**Rules 7 and 8 — a wrong document does not stay Red forever.** It means the
requirement is still *unmet*, and whether that is urgent depends on the
suspense date rather than on the reviewer's verdict. A submission-level QC
result must never become the parent item's status directly.

**Rules 10 to 12 keep the matrix calm at the start of a month.** Everything is
Blue on the 1st, amber after the first suspense, red only after the final call.

---

## Action ownership

`Status_Code` alone cannot answer *"is this mine?"* — which is why the engine
returns the owner in the same pass. Home filters on ownership.

| Status | Code | Owner | Action required |
|---|:-:|---|:-:|
| `OVERDUE` | 1 Red | Facility | yes |
| `RETURNED` | 1 Red | Facility | yes |
| `NOT_SATISFIED` | 1 Red | Facility | yes |
| `LATE` | 5 Amber | Facility | yes |
| `RECEIVED_PENDING_QC` | 2 Yellow | Reviewer | yes |
| `NOT_DUE` | 4 Blue | Facility | no |
| `PENDING_VALIDATION` | 4 Blue | Admin | no |
| `ACCEPTED` | 3 Green | none | no |
| `NOT_APPLICABLE` | 0 Gray | none | no |

A submitter's *needs your attention* list must not include documents sitting in
AFSVC's review queue. Those belong under **Waiting on AFSVC**.

---

## QC means the reviewer opened the file

Accept means the reviewer **opened the document** — in Teams or downloaded —
and verified it is the right one, complete and correct. This is substantive
review, not presence checking. Two consequences:

- Review takes real time, so bulk accept is valuable but **must never be the
  default action**. It is an explicit multi-select, never a "select all"
  button.
- Review throughput is a real metric. `PendingReviewAging` matters.

---

## Package rollup — over semantic statuses, never over colour codes

The naive colour rollup sees `[3, 4, 4]`, finds no 1 and no 2, and marks the
package **Complete**. That is wrong: two requirements have not been filed yet.
**It is `IN_PROGRESS`.**

```
any OVERDUE, RETURNED, NOT_SATISFIED or LATE        ACTION_REQUIRED   1
else any RECEIVED_PENDING_QC                        IN_REVIEW         2
else every applicable non-provisional item ACCEPTED COMPLETE          3
else anything applicable remains                    IN_PROGRESS       4
else                                                NOT_APPLICABLE    0
```

A provisional requirement neither completes a package nor blocks it: it is
excluded from the "every item accepted" test but still counted as applicable.

> V3's `MFRollup()` and its `Package Status Code` DAX were both that naive
> colour rollup — on the page below V3's own prose calling it wrong. Corrected
> — `handoffs/RECONCILIATION.md` C3.

**No completion percentage is stored anywhere.** A ratio quietly treats "not
yet due" as either done or failing, and neither is true. The COP counts
packages by state.

### Rollups run over what the viewer may see

**Installation is the unit of access.** Nobody is provisioned for their own
base: CAC identifies the user, the GAL gives their installation, and anyone at
that installation may view and edit its EOM submissions regardless of unit.
That simplifies the earlier design and dissolves the facility-rollup leak — a
facility-scoped rollup is no longer something to defend, because facility is
not the access boundary.

What remains, and matters more: a user must not receive a figure derived from
*installations* they may not see. Scope is applied server-side, in the query,
before anything is counted.

**And the app-layer filter is not the boundary.** Power Apps `Visible` and
`Filter()` do not remove a user's permission to the underlying SharePoint data.
The data layer must enforce the same scope independently — see
`security-open-issue.md`, which is unresolved.

---

## Who may write what

| Surface | May read | May write |
|---|---|---|
| galleries, `cmpStatusBadge` | `Final_Status`, `Status_Code` | nothing |
| `scrReview` (QC) | submission QC fields | `QC_Status`, `QC_Comment`, `Correction_Due`, and the four status fields **from one evaluation** |
| `scrUnmatched` | unmatched queue | a submission against an **existing** item, and the same four fields |
| EOM-01 | requirement + period + registry | the item's dates and status fields, at creation |
| EOM-03 | item + current submission | all four fields, the on-time facts, `MF_EOM_Status` |
| Power BI | `MF_EOM_Status` | nothing |

QC decisions are the only human input to status, and they are **inputs to the
engine**, not statuses themselves.

---

## Power Fx and DAX

`canvas-app/formulas/StatusEngine.fx` — `MF_EvaluateStatus()` is the
branch-for-branch transliteration of the decision order above; `MF_Status()` is
the lookup a gallery uses to render a row whose status is already stored.

`powerbi/MF_EOM_Status.md` — the measures aggregate; they never recompute item
status, and `Package_State` is materialized by EOM-03 rather than re-derived.

**Neither is reproduced in this file.** Earlier versions of this document
carried a Power Fx block that drifted from the decision table four sections
above it and stayed wrong across four releases. The code lives in one place and
the tests hold it to this table.
