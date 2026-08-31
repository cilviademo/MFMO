# Status calculation

**Settled. Do not re-derive.** `scripts/status_engine.py` is the reference
implementation; `canvas-app/formulas/StatusEngine.fx` and
`flows/EOM03-StatusFact` are transliterations of it, held in agreement by
`tests/test_status_engine.py`.

---

## The shape of the answer

There is one engine and one evaluation. It takes the row and the date and
returns a single record:

```
{ status, code, label, actionOwner, actionRequired }
```

`code` is `Status_Code` — stored, indexed, and the only thing a production
`Filter()` ever tests. `status` is `Final_Status` — one of five visual
states. `label` is `Status_Semantic` — the human-readable string stored beside
the code so a screen reader, an export and a Power BI card all say the same
words.

**Never write a second function that derives the label independently of the
code.** If a screen needs a label, it reads `Status_Semantic`. If a report
needs a colour, it reads `Final_Status`. Neither recomputes.

---

## Five visual states, eleven codes

`Final_Status` and `Status_Code` are independent. Several codes map to one
visual state, and the mapping is not reversible — which is the point. Four
states would force *not due yet* and *not applicable* into the same bucket,
and those are different facts about the world: one is an obligation that has
not arrived, the other is an obligation that does not exist.

| Code | Visual | Label | Action owner | Action required |
|---|---|---|---|:-:|
| `NOT_DUE` | **Blue** | Not due yet | Facility | no |
| `DUE_SOON` | **Amber** | Due soon | Facility | yes |
| `SUBMITTED` | **Amber** | Submitted - awaiting review | Reviewer | yes |
| `IN_REVIEW` | **Amber** | In review | Reviewer | yes |
| `RETURNED` | **Amber** | Returned for correction | Facility | yes |
| `ACCEPTED` | **Green** | Accepted | None | no |
| `OVERDUE` | **Red** | Overdue | Facility | yes |
| `PROVISIONAL_OVERDUE` | **Gray** | Past suspense - requirement unverified | Program | yes |
| `WAIVED` | **Gray** | Waived | None | no |
| `NOT_APPLICABLE` | **Gray** | Not applicable | None | no |
| `SUPERSEDED` | **Gray** | Superseded | None | no |

Status is never colour-only. Every chip carries its label text, and the
label is what an assistive technology announces. See `docs/accessibility.md`.

Status is calculated, never chosen. **No colour picker exists anywhere in
this solution**, and no screen, flow or report may write `Final_Status`
except by copying what the engine returned.

---

## Evaluation order

The order is total and the first match wins. Reordering it changes
behaviour, so it is asserted by the tests.

```
1.  requirement inactive, retired, or not applicable to this
    facility's operating model              -> NOT_APPLICABLE   Gray
2.  waived                                  -> WAIVED           Gray
3.  superseded by another row               -> SUPERSEDED       Gray

    A current-version submission exists; its QC state is the item's state:
4.  QC = ACCEPTED                           -> ACCEPTED         Green
5.  QC = RETURNED                           -> RETURNED         Amber
6.  QC = IN_REVIEW                          -> IN_REVIEW        Amber
7.  QC = PENDING                            -> SUBMITTED        Amber

    Nothing submitted. Time decides, verification decides the colour:
8a. as_of > Suspense_Date and requirement VERIFIED   -> OVERDUE  Red
8b. as_of > Suspense_Date and not VERIFIED  -> PROVISIONAL_OVERDUE  Gray
8c. Suspense_Date - as_of <= DueSoonWindowDays       -> DUE_SOON Amber
8d. otherwise                               -> NOT_DUE          Blue
```

Only the **current version** submission is consulted. A rejected v1 under an
accepted v2 does not make the item Amber; that is what `Is_Current_Version`
is for.

### Why an UNVERIFIED requirement never goes Red

All twelve seeded requirements are `UNVERIFIED`. Not one of them yet has a
confirmed regulation, contract clause or policy memo behind it. Turning a
facility's tile Red on the authority of a requirement the programme has not
verified would be telling a manager they are in breach of something nobody
can cite. Step 8b exists so that the provisional state is visible and owned
by the **Program**, not by the facility — the action required is *verify the
requirement*, not *submit the document*.

This is the default path today, not an edge case. A requirement leaves it by
having `Verification_Status` set to `VERIFIED` with an `Authority_Reference`
and a `Verification_Date`, which is a deliberate administrative act on
`scrAdminRequirements`.

---

## Rollups

Two rules, both easy to get wrong.

### Roll up over semantic status, not over colour

A colour rollup counts `[ACCEPTED, NOT_DUE, NOT_DUE]` as one green out of
three and reports 33% complete. It is 100% complete: two of those
obligations are not due yet and belong in neither the numerator nor the
denominator.

```
numerator   = count(Status_Code = ACCEPTED)
denominator = count(Status_Code not in
              {NOT_DUE, WAIVED, NOT_APPLICABLE, SUPERSEDED})
```

`MF_EOM_Status` carries these as `Is_Complete` and `Is_In_Denominator` so
the COP sums two booleans and reconstructs no workflow logic. When the
denominator is zero the answer is *nothing due*, displayed as such — **not
0% and not 100%**.

**No percentage is ever stored.** Storing one guarantees a stale figure the
app must recompute, and `scripts/eom_schema.py --validate` fails the build
if a column name suggests otherwise.

### Roll up over what the viewer may see

A facility user must not receive an installation figure derived from their
neighbours' rows. The visibility filter is applied *before* the aggregation,
not after, and it is the same mapping the app and Power BI RLS both use
(`MF_Security_Mapping`). `rollup()` takes a `visible_predicate` for exactly
this reason.

An installation figure shown to someone scoped to one facility is either
suppressed or labelled as covering their scope only. It is never silently
narrowed and presented as the installation total.

---

## Dates

`Due_Date` and `Suspense_Date` are both offsets in days from
`Reporting_Period.Period_End`, taken from the requirement:

```
Due_Date      = Period_End + Requirement.Due_Offset_Days
Suspense_Date = Period_End + Requirement.Suspense_Offset_Days
```

`Suspense_Offset_Days >= Due_Offset_Days` is enforced. `Due_Rule`
(`"EOM+5BD"`) is documentation of where the offsets came from; it is never
parsed at runtime.

A QC return writes `New_Suspense_Date` onto the submission and back onto the
item's `Suspense_Date`. **A return without both a comment and a new suspense
date is rejected by the flow** — a returned document with no deadline is how
items disappear.

`DueSoonWindowDays` is a config key, default 7.

---

## What each screen is allowed to do

| Surface | May read | May write |
|---|---|---|
| `scrHome`, galleries | `Status_Code`, `Status_Semantic`, `Final_Status` | nothing |
| `cmpStatusBadge` | the engine's record | nothing |
| `scrReview` (QC) | submission QC fields | `QC_Status`, `QC_Comment`, `New_Suspense_Date` via flow |
| `flows/EOM01` | requirement + period | item status fields, from the engine |
| `flows/EOM03` | item | `MF_EOM_Status`, copied verbatim |
| Power BI | `MF_EOM_Status` | nothing |

QC decisions are the only human input to status, and they are inputs to the
engine — not statuses themselves.
