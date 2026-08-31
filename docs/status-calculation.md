# Status calculation — ONE definition, three runtimes

The Power App, the reconciliation flow and Power BI must never disagree about
what colour a base is. This file is the single definition; the Power Fx, the
flow spec and the DAX are mechanical translations of it. **Change the rules
here first, then change all three.**

Reference implementation: `scripts/status_engine.py`.
Executable specification: `docs/mf-operations-prototype.html`.
Held in agreement by: `tests/test_status_engine.py`.

**Nothing about status is ever stored by a human.** There is no "set this to
yellow" control anywhere in the app, and no colour picker exists.

---

## Two fields, both stored, neither derived from the other

| | |
|---|---|
| `Final_Status` | the **semantic** string — eight values |
| `Status_Code` | the **numeric visual** code — 0 to 4 |

Both are written by one evaluation. Power BI conditionally formats the entire
COP matrix off `Status_Code` alone and labels with `Final_Status`; no DAX in
the report reproduces any of the logic below.

`Status_Code` is stored, and indexed, precisely so `Filter()` delegates. A
computed comparison would silently return the first 500 rows.

### The five visual codes

| Code | Colour | Meaning |
|---|---|---|
| 0 | Gray | Not applicable, or waived |
| 1 | Red | Required, missing and past suspense |
| 2 | Amber | Received awaiting review, correction needed, or not satisfied |
| 3 | Green | Accepted |
| 4 | Blue | Not due yet, or informational (provisional requirement) |

**Four states were not enough.** Collapsing "not applicable" and "not due yet"
into Gray made an installation whose requirements had simply not come due
display as *Not applicable*, which is false. Blue separates "in progress,
nothing wrong" from "does not apply".

> The V3 Power Fx returned `0` for a not-due item and had no Blue branch at
> all, contradicting the decision table in the same document. That is corrected
> here — see `handoffs/RECONCILIATION.md` C2.

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
> drifted from the table below. Corrected — `handoffs/RECONCILIATION.md` C1.

## Item status — decision order, first match wins

```
 1. Waived_Flag or not Required_Flag        NOT_APPLICABLE       0  none
 2. Authority UNVERIFIED and not received   PENDING_VALIDATION   4  Admin,    no action
 3. QC = Accepted                           ACCEPTED             3  none
 4. QC = Not Applicable                     NOT_APPLICABLE       0  none
 5. QC = Correction Required                CORRECTION_REQUIRED  2  Facility, action
 6. QC = Wrong Document, past due           OVERDUE              1  Facility, action
 7. QC = Wrong Document, before due         NOT_SATISFIED        2  Facility, action
 8. Received, QC pending                    RECEIVED_PENDING_QC  2  Reviewer, action
 9. Not received, before due                NOT_DUE              4  Facility, no action
10. Not received, past due                  OVERDUE              1  Facility, action
```

Only the **current version** submission is consulted. A rejected v1 under an
accepted v2 does not make the item Amber; that is what `Is_Current` is for.

**Rules 6 and 7 replace a bug.** A wrong document does not stay Red forever. It
means the requirement is still *unmet*; whether that is urgent depends on the
suspense date, not on the reviewer's verdict. A submission-level QC result must
never become the parent item's status directly.

**Rule 2 is why an unverified requirement is Blue, not Gray and not Red.** It
is informational: the base has nothing wrong and nothing to answer for. Until
the authority is confirmed, an unfiled document is not a finding, and the
action sits with the **Admin** — verify the requirement — rather than with the
facility.

All twelve seeded requirements are `UNVERIFIED`, so **rule 2 is the default
path today, not an edge case.** A requirement leaves it by being marked
`Verified` on `scrAdminRequirements`, with a citation, which is a deliberate
administrative act.

**Rule 9 keeps the matrix calm at the start of a month.** Everything is Blue on
the 1st and turns Red only after suspense passes — not Amber, which would make
the whole enterprise look at-risk every month.

---

## Action ownership

`Status_Code` alone cannot answer *"is this mine?"*. Amber covers both
*correction needed* (the facility's action) and *awaiting review* (AFSVC's).
Home filters on ownership, not colour.

| Status | Owner | Action required |
|---|---|:-:|
| `OVERDUE` | Facility | yes |
| `CORRECTION_REQUIRED` | Facility | yes |
| `NOT_SATISFIED` | Facility | yes |
| `RECEIVED_PENDING_QC` | Reviewer | yes |
| `NOT_DUE` | Facility | no |
| `PENDING_VALIDATION` | Admin | no |
| `ACCEPTED` / `NOT_APPLICABLE` | none | no |

A submitter's *needs your attention* list must not include documents sitting in
AFSVC's review queue. Those belong under **Waiting on AFSVC**.

---

## Package rollup — over semantic statuses, never over colour codes

The naive colour rollup marks `[ACCEPTED, NOT_DUE, NOT_DUE]` **Complete**,
because it sees `[3, 4, 4]` and finds no 1 and no 2. That is wrong: two
requirements have not been filed yet. **It is `IN_PROGRESS`.**

```
any OVERDUE, CORRECTION_REQUIRED or NOT_SATISFIED   ACTION_REQUIRED   1
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

A user scoped to one DFAC must not receive an installation figure derived from
their neighbours' packages — that leaks across a security boundary even when no
names appear on screen, because the numbers themselves are the disclosure.

Scope is applied **server-side, in the query, before anything is counted**
(`MF_VisibleItems` in `Delegation.fx`). A facility user's own package rolls
their facility's items plus the installation- and contract-scope items that
genuinely belong to them.

A facility package rolls its own items. An installation package rolls its
facility packages **plus** its Installation-scope and Contract-scope items —
those have `Facility_ID` null and belong to the installation directly, not to
any one DFAC. A portfolio rolls its installation packages.

A contract-scope item is visible only when the contract actually covers a
facility in the viewer's scope.

Any figure whose scope is narrower than its label implies says so, in text.

---

## Dates

```
Due_Date = date( Reporting_Period + Due_Offset_Months , Due_Day )
```

Both values come from the requirement row, never from a flow. Changing the
10th to the 15th is a list edit. A `Due_Day` of 31 in a 30-day month clamps to
the last day of that month rather than rolling into the next.

`Reporting_Period` is `YYYY-MM`. Dates are `YYYY-MM-DD`. Datetimes carry a time
part — parse to a day before comparing, so a timestamp never leaks into a day
comparison.

A QC return sets `Correction_Due` on the item. It does not move `Due_Date`:
the original suspense is what `Days_Late` and `On_Time_Flag` are measured
against, and rewriting it would erase the fact that the first attempt was late.

---

## Who may write what

| Surface | May read | May write |
|---|---|---|
| galleries, `cmpStatusBadge` | `Final_Status`, `Status_Code` | nothing |
| `scrReview` (QC) | submission QC fields | `QC_Status`, `QC_Comment`, `Correction_Due`, and the four status fields **from one evaluation** |
| `scrUnmatched` | unmatched queue | a submission against an **existing** item, and the same four fields |
| EOM-01 | requirement + period | the item's status fields, at creation |
| EOM-03 | item + current submission | all four fields, plus `MF_EOM_Status` |
| Power BI | `MF_EOM_Status` | nothing |

QC decisions are the only human input to status, and they are **inputs to the
engine**, not statuses themselves.

---

## Power Fx

`canvas-app/formulas/StatusEngine.fx`. `MF_EvaluateStatus()` is the branch-for-
branch transliteration of the decision order above; `MF_Status()` is the
lookup a gallery uses to render a row whose status is already stored.

## DAX

`powerbi/MF_EOM_Status.md`. The measures aggregate; they never recompute item
status, and `Package_State` is materialized by EOM-03 rather than re-derived.
