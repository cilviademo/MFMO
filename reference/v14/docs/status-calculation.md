# Status calculation — ONE definition, two runtimes

The Power App and Power BI must never disagree about what colour a base is.
This file is the single definition; the Power Fx and DAX below are mechanical
translations of it. Change the rules here first, then both.

**Nothing about status is ever stored by a human.** There is no "set this to
yellow" control anywhere in the app. `Final_Status` and `Status_Code` are
written by flow EOM-03 and recalculated on every QC action.

---

## Status codes

| Code | Colour | Meaning | Who acts next |
|---|---|---|---|
| 0 | Gray | Not applicable, waived, not required this period | nobody |
| 1 | Red | Past the final call, or returned for correction | **the base**, urgently |
| 2 | Yellow | Received, awaiting AFSVC review | **AFSVC** |
| 3 | Green | Accepted | nobody |
| 4 | Blue | Not due — the submission window is open | nobody yet |
| 5 | Amber | Past the initial suspense, final call not reached | **the base** |

**Six states, and the amber/yellow split is the point.**

Amber means **time risk**: the 5th has passed, the base still has until the
10th, and nothing is wrong yet. Yellow means **somebody else has it**: the file
arrived and AFSVC owes a decision.

Those are different situations for different people and they must not look
alike. Collapsing them into one warning colour tells a DFAC manager that a
document they submitted on time and a document they have not sent are the same
kind of problem.

Colour still resolves ownership at a glance:

```
Blue    nobody yet
Amber   the base, with runway
Red     the base, out of runway
Yellow  AFSVC
Green    nobody
Gray     nobody
```

Six is the ceiling. A seventh state would stop being scannable.

**Four states were not enough.** Collapsing "not applicable" and "not due yet"
into Gray made an installation whose requirements simply had not come due
display as *Not applicable*, which is false. Blue separates "in progress,
nothing wrong" from "does not apply".

`Status_Code` is the visual code. `Final_Status` is the semantic string. Never
derive one from the other — they are both written by the status engine in a
single evaluation.

Power BI conditionally formats the entire COP matrix off `Status_Code` alone.
No DAX in the report reproduces any of the logic below.

---

## One engine, one evaluation

The engine returns a **state object**, not a code:

```
{ status, code, label, actionOwner, actionRequired }
```

Label, colour and ownership come from a single pass. Two parallel functions —
one for the code, one for the label — invite divergence, and divergence in a
status engine is a silent wrong answer.

## Two suspense dates, and two versions of each

**First suspense: 5 calendar days after month end. Final call: the 10th.**

`CALENDAR` is the baseline. The source says "within 5 days" and does not say
duty days, business days or workdays. Do not infer duty days without a citation.

The two have different standing and the model records that:

| | Source | `Authority_Status` |
|---|---|---|
| 5 days after month end | procedure language | VERIFIED |
| the 10th | programme decision | MANAGEMENT_RULE |

Between them an item is **LATE** (amber), not overdue. That is the only week in
the cycle where a reminder still changes the outcome.

### Nominal and effective

A nominal suspense that lands on a Saturday cannot be the date someone is held
to, and burying that adjustment in a formula produces a monthly argument. Every
item therefore carries four dates:

```
Nominal_Due_Date              the policy date — "the 5th" stays the 5th
Effective_Due_Date            after NonDutyDay_Policy — what a person owes
Nominal_Final_Call_Date
Effective_Final_Call_Date
```

`NonDutyDay_Policy` defaults to `NEXT_DUTY_DAY` and is configuration, resolved
against `MF_Non_Duty_Day` (federal holidays, wing down days).

**Status evaluation uses the effective dates, always.** Reporting and leadership
views use the nominal ones, so "the 5th" remains the 5th in a brief. Where they
differ, `Due_Date_Adjusted` is TRUE and the package screen shows both:

```
1119        Due 5 Sep (Mon 8 Sep)
```

## On-time is two questions, not one

```
Initial_Submitted_DateTime            when the first version arrived
Initial_Submission_On_Time            by Effective_Due_Date
Current_Acceptable_Evidence_DateTime  when an accepted version existed
Final_Evidence_On_Time                by Effective_Final_Call_Date
```

Uploaded 4 Sep, returned 9 Sep, corrected and accepted 12 Sep: the base
submitted on time and AFSVC did not have usable evidence on time. Both are true.

**Never show these as two booleans.** Translate:

> Submitted 4 Sep — on time
> Correction accepted 12 Sep — final evidence after suspense

## Item status — decision order, first match wins

```
1.  Waived_Flag or not Required_Flag       NOT_APPLICABLE       0  no owner
2.  Requirement UNVERIFIED, not received   PENDING_VALIDATION   4  Admin, no action
3.  QC = Accepted                          ACCEPTED             3  no owner
4.  QC = Not Applicable                    NOT_APPLICABLE       0  no owner
5.  QC = Recalled                          NOT_DUE / OVERDUE    by date, Facility
6.  QC in {Correction Required, Incomplete,
      Wrong Reporting Period, Wrong Facility}
                                           RETURNED             1  Facility, action
7.  QC = Wrong Document, past final due    OVERDUE              1  Facility, action
8.  QC = Wrong Document, before final due  NOT_SATISFIED        1  Facility, action
9.  Received, QC pending                   RECEIVED_PENDING_QC  2  Reviewer, action  (yellow)
10. Not received, before first suspense    NOT_DUE              4  Facility, no action
11. Not received, past first, before final LATE                 5  Facility, action
12. Not received, past final suspense      OVERDUE              1  Facility, action
```

**Rule 6 collapses four verdicts into one status but keeps the reason.**
`Final_Status` is RETURNED; `QC_Status` on the current submission carries the
specific verdict — Incomplete, Wrong Reporting Period, Wrong Facility — and that
is what the base reads on their dashboard and in the notification. The status
engine does not need four states to say "it came back"; the submitter needs four
reasons to know what to fix.

**Rule 5.** A recall is the submitter withdrawing before review, not a
rejection. The item reverts to its date-based state and the withdrawn version
stays in history as superseded.



**Rules 6 and 7 replace a bug.** A wrong document does not stay Red forever.
It means the requirement is still *unmet*; whether that is urgent depends on
the suspense date, not on the reviewer's verdict. A submission-level QC result
must never become the parent item's status directly.

**Rule 2 is why an unverified requirement is Blue, not Gray.** It is
informational — the base has nothing to do and nothing is wrong.

## Action ownership

`Status_Code` alone cannot answer "is this mine?". Amber covers both
*correction needed* (the facility's action) and *awaiting review* (AFSVC's
action). Home filters on ownership, not colour:

| Status | Owner | Action required |
|---|---|---|
| OVERDUE | Facility | yes |
| CORRECTION_REQUIRED | Facility | yes |
| NOT_SATISFIED | Facility | yes |
| RECEIVED_PENDING_QC | Reviewer | yes |
| NOT_DUE | Facility | no |
| PENDING_VALIDATION | Admin | no |
| ACCEPTED / NOT_APPLICABLE | none | no |

A submitter's "needs your attention" list must not include documents sitting in
AFSVC's review queue. Those belong under *Waiting on AFSVC*.

Rule 3 is the important one. Until AFSVC confirms whether SF 1080 applies to
Food 2.0, an unverified requirement must not turn a base red. The box still
appears in the app so people can upload against it, but its absence is not a
finding.

Rule 8 keeps the matrix clean at the start of a month. Everything is gray on
the 1st and turns red only after suspense passes — not yellow, which would make
the whole enterprise look at-risk every month.

---

## Package rollup — over semantic statuses, never over colour codes

The naive colour rollup marks `[ACCEPTED, NOT_DUE, NOT_DUE]` as **Complete**,
because it sees `[3,0,0]` and no 1 or 2. That is wrong: two requirements have
not been filed yet.

```
if any OVERDUE, CORRECTION_REQUIRED or NOT_SATISFIED   ACTION_REQUIRED   1
else if any RECEIVED_PENDING_QC                        IN_REVIEW         2
else if every applicable non-provisional item ACCEPTED COMPLETE          3
else if anything applicable remains                    IN_PROGRESS       4
else                                                   NOT_APPLICABLE    0
```

**Rollups are computed over what the viewer may see**, never over the full
installation. A user scoped to one DFAC must not receive an installation figure
derived from their neighbours' packages — that leaks information across a
security boundary even when no names appear on screen. A contract-scope item is
visible only when the contract actually covers a facility in the viewer's
scope.

A facility package rolls its own items. An installation package rolls its
facility packages **plus** its Installation-scope and Contract-scope items —
those have `Facility_ID` null and belong to the installation directly, not to
any one DFAC. A portfolio rolls its installation packages.

---

## Power Fx — `formulas/StatusCalculation.fx`

```
// Item status. Called from the tracker gallery and after every QC patch.
// varToday is set in App.OnStart so the whole session agrees on the date.

MFItemStatusCode(
    Waived: Boolean, Required: Boolean, AuthorityStatus: Text,
    Received: Boolean, QCStatus: Text, DueDate: DateTime
): Number =
    If( Waived Or Not(Required), 0,
        AuthorityStatus = "UNVERIFIED" And Not(Received), 0,
        QCStatus = "Accepted", 3,
        QCStatus = "Wrong Document", 1,
        QCStatus = "Correction Required", 2,
        Received, 2,
        varToday <= DueDate, 0,
        1
    );

MFItemStatusLabel(
    Waived: Boolean, Required: Boolean, AuthorityStatus: Text,
    Received: Boolean, QCStatus: Text, DueDate: DateTime
): Text =
    If( Waived Or Not(Required), "Not Applicable",
        AuthorityStatus = "UNVERIFIED" And Not(Received), "Not Due",
        QCStatus = "Accepted", "Accepted",
        QCStatus = "Wrong Document", "Wrong Document",
        QCStatus = "Correction Required", "Correction Required",
        Received, "Pending Review",
        varToday <= DueDate, "Not Due",
        "Overdue"
    );

// Rollup over any table with a Status_Code column.
MFRollup( items: Table ): Number =
    If( CountRows(Filter(items, Status_Code = 1)) > 0, 1,
        CountRows(Filter(items, Status_Code = 2)) > 0, 2,
        CountRows(Filter(items, Status_Code = 3)) > 0, 3,
        0
    );

MFStatusColor( code: Number ): Color =
    Switch( code,
        3, ColorValue("#5C9E6B"),
        2, ColorValue("#C8A44D"),
        1, ColorValue("#C0564B"),
        ColorValue("#5F6B78")
    );
```

---

## DAX — `powerbi/EOMStatus.dax`

Power BI reads `Status_Code` as stored by EOM-03. These measures only aggregate
and rollup; they never recompute item status.

```
EOM Items = COUNTROWS ( MF_EOM_Item )

EOM Accepted = CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] = 3 )
EOM Pending  = CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] = 2 )
EOM Missing  = CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] = 1 )
EOM Applicable =
CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] IN { 1, 2, 3 } )

EOM Complete % = DIVIDE ( [EOM Accepted], [EOM Applicable] )

// Same rollup as Power Fx MFRollup, in DAX.
Package Status Code =
SWITCH (
    TRUE (),
    CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] = 1 ) > 0, 1,
    CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] = 2 ) > 0, 2,
    CALCULATE ( [EOM Items], MF_EOM_Item[Status_Code] = 3 ) > 0, 3,
    0
)

Package Status Color =
SWITCH ( [Package Status Code],
    3, "#5C9E6B", 2, "#C8A44D", 1, "#C0564B", "#5F6B78" )

Package Status Label =
SWITCH ( [Package Status Code],
    3, "Complete", 2, "In review", 1, "Action required", "Not applicable" )

// Days late, for the aging view. Uses the current submission only.
EOM Days Late =
AVERAGEX (
    FILTER ( MF_EOM_Item, MF_EOM_Item[Received_Flag] = TRUE () ),
    DATEDIFF ( MF_EOM_Item[Due_Date], MF_EOM_Item[Received_Date], DAY )
)
```

---

## The Power BI status view

Flow EOM-03 maintains a flat view for the COP. Installation × Facility ×
Reporting_Period × Requirement, one row per `MF_EOM_Item`:

```
Installation_ID · Installation_Name · Facility_ID · Facility_Name
Operating_Model · Reporting_Period · Document_Code · Requirement_Scope
Required · Received · Received_Date · Due_Date
QC_Status · Final_Status · Status_Code · Evidence_URL
```

`Facility_ID` and `Facility_Name` are null on Installation- and Contract-scope
rows. The COP matrix collapses to installation level without losing the detail
underneath, because the rollup is the same function at every level.
