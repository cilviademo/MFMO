# The COP semantic model

**`MF_EOM_Status` is the canonical fact. The COP reconstructs no workflow
logic.**

Every workflow decision is resolved before Power BI sees a row: the code, the
semantic label, the visual state, the action owner and the two rollup flags.
No measure below re-derives a status, and no report author needs to know what
`RETURNED` means or which codes count toward completeness.

If a rule appears in DAX that also appears in `docs/status-calculation.md`,
that is a second engine and it is a defect.

---

## Tables

| Table | Source | Role |
|---|---|---|
| `MF_EOM_Status` | SharePoint list | Fact. One row per item per snapshot. |
| `MF_Requirement` | SharePoint list | Dimension |
| `MF_Facility` | SharePoint list | Dimension |
| `MF_Installation` | SharePoint list | Dimension |
| `MF_Reporting_Period` | SharePoint list | Dimension |
| `MF_Security_Mapping` | SharePoint list | **RLS bridge** — hidden |
| `Date` | generated | Marked as the date table, joined on `Snapshot_Date` |

Relationships are single-direction, many-to-one, from the fact outward.
Bi-directional filtering is off: it makes RLS leak, and this model carries
facility-level security.

`Facility_ID` is **null** on Installation- and Contract-scope rows. Do not
replace it with a blank string in Power Query — the RLS expression below
depends on the distinction, and a blank string would attach those rows to a
facility that does not exist.

---

## Measures

Two booleans and some division. That is the entire completeness model.

```dax
Items in scope =
    COUNTROWS ( MF_EOM_Status )

Items due =
    CALCULATE ( COUNTROWS ( MF_EOM_Status ), MF_EOM_Status[Is_In_Denominator] = TRUE )

Items accepted =
    CALCULATE ( COUNTROWS ( MF_EOM_Status ), MF_EOM_Status[Is_Complete] = TRUE )

-- Blank, never zero and never one, when nothing is due. "0% of nothing" is a
-- figure a manager will act on.
Completeness =
    DIVIDE ( [Items accepted], [Items due] )

Completeness label =
    IF ( ISBLANK ( [Completeness] ), "Nothing due", FORMAT ( [Completeness], "0%" ) )

Action required =
    CALCULATE ( COUNTROWS ( MF_EOM_Status ), MF_EOM_Status[Action_Required] = TRUE )

-- Owned by the programme, not the facility: an unverified requirement past
-- its suspense date. This is currently the majority of the estate.
Provisional past suspense =
    CALCULATE (
        COUNTROWS ( MF_EOM_Status ),
        MF_EOM_Status[Status_Code] = "PROVISIONAL_OVERDUE"
    )

Genuinely overdue =
    CALCULATE ( COUNTROWS ( MF_EOM_Status ), MF_EOM_Status[Status_Code] = "OVERDUE" )
```

`Genuinely overdue` counts only `OVERDUE`, which only a `VERIFIED` requirement
can produce. **Do not add `PROVISIONAL_OVERDUE` to it.** The two are different
facts with different owners, and a single "overdue" number that merges them
tells a commander that facilities are in breach of requirements nobody has
confirmed exist.

### Latest snapshot

The fact is a daily snapshot, so an unfiltered sum counts every day at once.

```dax
Latest snapshot = CALCULATE ( MAX ( MF_EOM_Status[Snapshot_Date] ), ALL ( MF_EOM_Status ) )

Completeness today =
    CALCULATE ( [Completeness], MF_EOM_Status[Snapshot_Date] = [Latest snapshot] )
```

Every current-state visual filters to the latest snapshot. Trend visuals use
month-end snapshots, which are exempt from the retention purge.

---

## Row-level security

**One security mapping serves app filtering and Power BI RLS.**
`MF_Security_Mapping` is the same list the app reads; the roles are generated
from `Scope_Type` and `Scope_ID` rather than hand-maintained, so a user added
to a facility in the app is filtered correctly in the report on the next
refresh with no separate action.

Define one role, `MissionFeedingScope`, on `MF_EOM_Status`:

```dax
VAR me = USERPRINCIPALNAME ()
VAR isGlobal =
    NOT ISEMPTY (
        FILTER ( ALL ( MF_Security_Mapping ),
            MF_Security_Mapping[Principal_UPN] = me
                && MF_Security_Mapping[Scope_Type] = "Global"
                && MF_Security_Mapping[Is_Active] = TRUE ) )
RETURN
    isGlobal
    || MF_EOM_Status[Facility_ID] IN
        SELECTCOLUMNS ( FILTER ( ALL ( MF_Security_Mapping ),
            MF_Security_Mapping[Principal_UPN] = me
                && MF_Security_Mapping[Scope_Type] = "Facility"
                && MF_Security_Mapping[Is_Active] = TRUE ), "s", MF_Security_Mapping[Scope_ID] )
    || MF_EOM_Status[Installation_ID] IN
        SELECTCOLUMNS ( FILTER ( ALL ( MF_Security_Mapping ),
            MF_Security_Mapping[Principal_UPN] = me
                && MF_Security_Mapping[Scope_Type] = "Installation"
                && MF_Security_Mapping[Is_Active] = TRUE ), "s", MF_Security_Mapping[Scope_ID] )
    || MF_EOM_Status[Portfolio_ID] IN
        SELECTCOLUMNS ( FILTER ( ALL ( MF_Security_Mapping ),
            MF_Security_Mapping[Principal_UPN] = me
                && MF_Security_Mapping[Scope_Type] = "Portfolio"
                && MF_Security_Mapping[Is_Active] = TRUE ), "s", MF_Security_Mapping[Scope_ID] )
```

`Is_Active` matters: access is revoked by setting it false, not by deleting
the row, so the audit trail survives.

A user scoped to one facility sees only that facility's rows — **including
the installation-scope rows for their installation**, because those carry
`Installation_ID` and a null `Facility_ID`, and the installation clause
matches only if they hold an installation-scope mapping. A facility user does
not see their installation's certification row, which is correct: it is not
their obligation.

### The rollup rule the report must not break

**A facility user must not receive an installation figure derived from their
neighbours.** RLS narrows the fact, so an "installation completeness" card
shown to a facility-scoped user is silently computed over their own rows only
— a correct number with a wrong label, which is worse than an error.

Every visual whose title names a scope wider than the viewer's carries the
qualifier:

```dax
Scope qualifier =
VAR me = USERPRINCIPALNAME ()
VAR widest =
    CALCULATE ( MAX ( MF_Security_Mapping[Scope_Type] ),
        ALL ( MF_Security_Mapping ),
        MF_Security_Mapping[Principal_UPN] = me,
        MF_Security_Mapping[Is_Active] = TRUE )
RETURN
    IF ( widest = "Facility",
         "Covers your assigned facilities only, not the whole installation.",
         BLANK () )
```

Test RLS with at least two scopes before release — a facility user and an
installation manager — and confirm their totals differ in the way the mapping
says they should.

---

## Refresh

Scheduled refresh, twice daily, at least an hour after EOM-03. Import mode,
not DirectQuery: DirectQuery against a SharePoint list at this volume is
slower than the refresh window it replaces, and the fact is a daily snapshot,
so live data would not be more current anyway.

Incremental refresh on `Snapshot_Date`: 14 days refreshed, 400 days archived.

---

## Report pages

| Page | Grain | Note |
|---|---|---|
| Portfolio | Portfolio × period | Completeness, action required, provisional count kept separate from genuinely overdue |
| Installation | Installation × period | Includes installation- and contract-scope rows |
| Facility | Facility × requirement | The same `Requirement · Scope · Due · Status · Action` row as the app |
| Provisional requirements | Requirement | The programme's own backlog: what is unverified and how much is riding on it |
| Trend | Month-end snapshots | Monthly, not daily |

Every chart carries a text summary and a data-table alternative
(`docs/accessibility.md`, gate A6). Status is shown with its label, never by
colour alone — a Power BI chart is subject to the same rule as a chip in the
app.
