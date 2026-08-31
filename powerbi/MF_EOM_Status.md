# The COP semantic model

**`MF_EOM_Status` is the canonical fact. Power BI reconstructs no workflow
logic.**

Every workflow decision is resolved by EOM-03 before the report sees a row: the
semantic status, the numeric colour code, the action owner, and the package
state. **Power BI colours on `Status_Code` and labels with `Final_Status`.**

If a rule appears in DAX that also appears in `docs/status-calculation.md`,
that is a second engine and it is a defect.

---

## Tables

| Table | Source | Role |
|---|---|---|
| `MF_EOM_Status` | SharePoint list | Fact. One flat row per `MF_EOM_Item`. |
| `MF_EOM_Requirement` | SharePoint list | Dimension |
| `MF_Facility` | SharePoint list | Dimension |
| `MF_Installation` | SharePoint list | Dimension |
| `MF_Security_Mapping` | SharePoint list | **RLS bridge** — hidden |
| `Period` | generated from `Reporting_Period` | `YYYY-MM`, marked as the date table |

Relationships are single-direction, many-to-one, from the fact outward.
**Bi-directional filtering is off**: it makes RLS leak, and this model carries
facility-level security.

`Facility_ID` is **null** on Installation- and Contract-scope rows. Do not
replace it with a blank string in Power Query — the RLS expression depends on
the distinction, and a blank string would attach those rows to a facility that
does not exist.

---

## Measures

The fact already carries everything. These aggregate; they never recompute.

```dax
EOM Items = COUNTROWS ( MF_EOM_Status )

-- Colour codes as stored by EOM-03.
--   0 Gray  1 Red  2 Yellow  3 Green  4 Blue  5 Amber
EOM Accepted      = CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] = 3 )
EOM Out of runway = CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] = 1 )
EOM With runway   = CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] = 5 )
EOM Awaiting AFSVC= CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] = 2 )
EOM Not due       = CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] = 4 )

-- Applicable excludes Gray. It does NOT exclude Blue: a not-due requirement
-- is still an obligation, it simply has not arrived.
EOM Applicable =
CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] IN { 1, 2, 3, 4, 5 } )

-- The base owes something now: Red AND Amber. Amber is not "fine".
EOM Base owes = CALCULATE ( [EOM Items], MF_EOM_Status[Status_Code] IN { 1, 5 } )
```

### Provisional is not overdue

```dax
-- Only a Verified requirement can produce OVERDUE.
Genuinely overdue =
CALCULATE ( [EOM Items], MF_EOM_Status[Final_Status] = "OVERDUE" )

Provisional =
CALCULATE ( [EOM Items], MF_EOM_Status[Final_Status] = "PENDING_VALIDATION" )
```

**Do not add `Provisional` to `Genuinely overdue`.** They are different facts
with different owners, and a single "overdue" number that merges them tells a
commander that bases are in breach of requirements nobody has confirmed exist.
Report them as separate figures, and label the second one as the programme's
own backlog.

### Package state — materialized, not re-derived

`Package_State` is written by EOM-03 over semantic statuses. The report reads
it.

```dax
Packages complete =
CALCULATE (
    DISTINCTCOUNT ( MF_EOM_Status[Facility_ID] ),
    MF_EOM_Status[Package_State] = "COMPLETE"
)

Packages action required =
CALCULATE (
    DISTINCTCOUNT ( MF_EOM_Status[Facility_ID] ),
    MF_EOM_Status[Package_State] = "ACTION_REQUIRED"
)

### Every completion figure states its denominator

**A not-onboarded installation is not compliant. It has not been asked.**

All 103 installations ship `Generation_Enabled = FALSE`. EOM-01 generates
nothing for them, so they contribute no rows to `MF_EOM_Status` — and a
percentage computed over the rows that exist reports 100% while most of the
enterprise has never been brought into the system. That is not a rounding
problem. It is a card that says the programme is finished when it has barely
started.

The fix is not a caveat in a tooltip. It is two measures, and the report shows
both:

```dax
-- Every package the onboarded population owes this period. Not "packages we
-- have rows for" -- MF_EOM_Status only holds rows for onboarded installations,
-- which is precisely why the denominator has to be named rather than inferred
-- from the fact table's row count.
Packages expected =
CALCULATE (
    DISTINCTCOUNT ( MF_EOM_Status[Facility_ID] ),
    MF_EOM_Status[Required_Flag] = TRUE ()
)

Installations onboarded =
CALCULATE ( COUNTROWS ( MF_Installation ),
            MF_Installation[Generation_Enabled] = TRUE (),
            MF_Installation[Active_Flag]        = TRUE () )

Installations not yet onboarded =
CALCULATE ( COUNTROWS ( MF_Installation ),
            MF_Installation[Generation_Enabled] = FALSE (),
            MF_Installation[Active_Flag]        = TRUE () )

-- The percentage, with the denominator it was computed over stated in the
-- same string. A caller cannot use this number without also carrying the
-- population it describes.
Completion statement =
VAR Onboarded = [Installations onboarded]
VAR Waiting   = [Installations not yet onboarded]
VAR Done      = [Packages complete]
VAR Expected  = [Packages expected]
RETURN
    IF ( Expected = 0,
         "No packages expected — " & Onboarded & " installations onboarded",
         FORMAT ( DIVIDE ( Done, Expected ), "0%" )
           & " of " & Expected & " packages across "
           & Onboarded & " onboarded installations"
           & IF ( Waiting > 0,
                  " · " & Waiting & " installations not yet onboarded", "" ) )
```

Rendered:

```
84% of 180 packages across 43 onboarded installations
60 installations not yet onboarded
```

**Never one number.** A card visual has room for exactly one figure, which is
exactly why the temptation is strongest here — put the second line in the card's
subtitle rather than dropping it.

The same rule governs the in-app visuals. `docs/native-visuals.md`.

Package Status Color =
SWITCH ( SELECTEDVALUE ( MF_EOM_Status[Package_State] ),
    "COMPLETE",        "#0E700E",
    "IN_REVIEW",       "#5A5800",   -- yellow: AFSVC holds it
    "ACTION_REQUIRED", "#A4262C",
    "IN_PROGRESS",     "#0F548C",
    "#424242" )
```

> V3's DAX contained `Package Status Code` as a naive colour rollup — the same
> "any 1 then 1, any 2 then 2, any 3 then 3, else 0" that marks
> `[ACCEPTED, NOT_DUE, NOT_DUE]` Complete. It is removed. The rollup is
> computed once, server-side, over semantic statuses. See
> `docs/handoffs/RECONCILIATION.md` C3.

### Timeliness — two rates, not one

`Days_Late` and both on-time flags are set by EOM-03, not computed here.

```dax
Average days late =
AVERAGEX ( FILTER ( MF_EOM_Status, MF_EOM_Status[Received_Flag] ),
           MF_EOM_Status[Days_Late] )

-- What the BASE is told: did the first version arrive by the first suspense.
Submission on-time rate =
DIVIDE (
    CALCULATE ( [EOM Items], MF_EOM_Status[Initial_Submission_On_Time] = TRUE () ),
    CALCULATE ( [EOM Items], MF_EOM_Status[Received_Flag] = TRUE () )
)

-- What LEADERSHIP is told: did usable evidence exist by the final call.
Evidence on-time rate =
DIVIDE (
    CALCULATE ( [EOM Items], MF_EOM_Status[Final_Evidence_On_Time] = TRUE () ),
    CALCULATE ( [EOM Items], MF_EOM_Status[Received_Flag] = TRUE () )
)
```

**Report both, and never merge them.** Uploaded 4 Sep, returned 9 Sep, accepted
12 Sep is *submitted on time* and *evidence late* — a single rate hides which
half of the process is slow, and they have different owners.

### Nominal, not effective, on a leadership view

`Nominal_Due_Date` is what a brief says. `Effective_Due_Date` is what the
status was evaluated against. A COP that reports against the effective date
quietly tells leadership the suspense moved, which is true for the base and
misleading in aggregate. Use nominal, and surface `Due_Date_Adjusted` where
somebody asks why a row is not late.

**No completion percentage is stored** in the fact. A ratio quietly treats
"not yet due" as either done or failing. Where the COP needs one it is computed
here, from `Status_Code = 3` over `EOM Applicable`, and only within a closed
period.

---

## Row-level security

**One security mapping serves app filtering and Power BI RLS.**
`MF_Security_Mapping` is the same list the app reads, so a user added to a
facility is filtered correctly in the report on the next refresh with no
separate action. Do not maintain two permission models.

One role, `MissionFeedingScope`, on `MF_EOM_Status`:

```dax
VAR me = USERPRINCIPALNAME ()
VAR mine =
    FILTER ( ALL ( MF_Security_Mapping ),
             MF_Security_Mapping[UPN] = me
             && MF_Security_Mapping[Active_Flag] = TRUE () )
VAR isEnterprise =
    NOT ISEMPTY ( FILTER ( mine, MF_Security_Mapping[Scope_Type] = "Enterprise" ) )
RETURN
    isEnterprise
    || MF_EOM_Status[Portfolio_ID] IN
        SELECTCOLUMNS ( FILTER ( mine, MF_Security_Mapping[Scope_Type] = "Portfolio" ),
                        "s", MF_Security_Mapping[Portfolio_ID] )
    || MF_EOM_Status[Installation_ID] IN
        SELECTCOLUMNS ( FILTER ( mine, MF_Security_Mapping[Scope_Type] = "Installation" ),
                        "s", MF_Security_Mapping[Installation_ID] )
    || MF_EOM_Status[Facility_ID] IN
        SELECTCOLUMNS ( FILTER ( mine, MF_Security_Mapping[Scope_Type] = "Facility" ),
                        "s", MF_Security_Mapping[Facility_ID] )
```

`Active_Flag` matters: access is revoked by setting it false, not by deleting
the row, so the audit trail survives.

### The leak this is guarding against

A facility-scoped user must not receive an installation figure derived from
their neighbours' packages. RLS narrows the fact, so an "installation
completeness" card shown to a facility-scoped user is silently computed over
their own rows only — **a correct number with a wrong label**, which is worse
than an error.

Every visual whose title names a scope wider than the viewer's carries a
qualifier, matching `MF_ScopeQualifier()` in the app:

```dax
Scope qualifier =
VAR me = USERPRINCIPALNAME ()
VAR isFacilityOnly =
    ISEMPTY ( FILTER ( ALL ( MF_Security_Mapping ),
        MF_Security_Mapping[UPN] = me
        && MF_Security_Mapping[Active_Flag] = TRUE ()
        && MF_Security_Mapping[Scope_Type] IN { "Enterprise", "Portfolio", "Installation" } ) )
RETURN
    IF ( isFacilityOnly,
         "Covers your facility and this installation's shared obligations, not the whole base.",
         BLANK () )
```

A facility-scoped user does see their installation's Installation-scope rows —
those are shared obligations of the base, carried with a null `Facility_ID` —
but not another DFAC's facility rows. Test RLS with **at least two scopes**
before release and confirm the totals differ the way the mapping says they
should.

---

## Refresh

Scheduled refresh twice daily, at least an hour after EOM-03. Import mode, not
DirectQuery: DirectQuery against a SharePoint list at this volume is slower
than the refresh window it replaces, and the fact is rebuilt nightly anyway.

The gov Power BI service URL differs by cloud. It comes from
`MF_App_Config.PowerBIReportURL`; never hard-code the commercial service URL. <!-- prerelease: allow CLD-02 naming the prohibited host in the sentence prohibiting it -->

---

## Report pages

| Page | Grain | Note |
|---|---|---|
| Portfolio | Portfolio × period | Packages by state. Provisional shown separately from overdue. |
| Installation | Installation × facility | The matrix, conditionally formatted from `Status_Code` |
| Facility | Facility × requirement | The same `Requirement · Scope · Due · Status · Action` row as the app |
| Provisional | Requirement | The programme's own backlog: what is unverified, and what grain is still Proposed |
| Onboarding | Installation | `Generation_Enabled` — who is not yet asked, which is not the same as compliant |
| Timeliness | Period | `Days_Late`, `On_Time_Flag`, aging |

Conditional formatting comes from `Status_Code` — six values. Use the app's
tokens verbatim so a chip and a report cell for the same item are the same
colour:

```
0 Gray    #424242 on #F5F5F5     not required
1 Red     #A4262C on #FDF3F4     base owes it, no runway
2 Yellow  #5A5800 on #FDFAE0     AFSVC owes it
3 Green   #0E700E on #F1FAF1     accepted
4 Blue    #0F548C on #EFF6FC     not due
5 Amber   #944800 on #FFF3E6     base owes it, has runway
```

**Amber and yellow must stay 48 degrees apart in hue**; they were two
near-identical browns 1.16:1 apart, which is a split nobody can read at a
glance. Do not let a report theme "harmonise" them back together. The label
beside it comes from `Final_Status`. **Status is never colour-only in the report either** — a green
square with no text fails the same gate in Power BI as it does in the app.
Every chart carries a text summary and a data-table alternative.
