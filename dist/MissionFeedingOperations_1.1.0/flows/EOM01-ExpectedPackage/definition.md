# EOM-01 — Expected Package Generator

**Trigger:** Recurrence, 1st of each month, 05:00 local.
**Idempotent.** Safe to re-run; never creates a duplicate item.

Reference implementation: `scripts/generate_expected_items.py`.
Tests: `tests/test_eom01.py`.

**Build order: this runs before any screen is built.** Every UI decision
downstream depends on the shape of this data, and a gallery built against rows
with the wrong `Facility_ID` semantics gets rebuilt, not adjusted.

## Schema compatibility — checked before any write

```
expected = the schema version this flow was authored against   (a literal)
deployed = MF_App_Config.SchemaVersion

if expected <> deployed:
        return CONFIGURATION_REQUIRED
        log SCHEMA_MISMATCH with both versions
        stop before any write
```

**Every flow makes this comparison independently.** The app disabling its own
submit button is not a control — a flow can be invoked directly, and a flow run
on a schedule has no app in front of it at all.

A newer flow writing against an older schema patches columns that do not exist
yet. SharePoint does not error on that; it writes nothing. A document then reads
as submitted while nothing was recorded, which is the failure this whole build
exists to prevent.

`docs/SHAREPOINT_SCHEMA_MANIFEST.md` is the contract being checked.

## Logic

```
period        = format(addToTime(utcNow(), -1, 'Month'), 'yyyy-MM')
activeReqs    = MF EOM Requirement where Active_Flag = true
installations = MF Installation    where Active_Flag = true
                                     AND Generation_Enabled = true   <-- the gate
facilities    = MF Facility        where Active_Flag = true
                                     AND Installation_ID in installations

for each requirement in activeReqs:

    if requirement.Frequency does not fall in this period: skip
       Monthly     always
       Quarterly   period month in {12, 3, 6, 9}
       Semiannual  {3, 9}
       Annual      {9}
       Annual      Applicable_Period_Month (9 for EOY)
       Conditional NEVER auto-generated

    switch requirement.Requirement_Scope:

      FACILITY:
        targets = facilities where
                    ( Operating_Model = requirement.Applicable_Model
                      OR requirement.Applicable_Model = 'All' )
                    AND ( Applicable_Facility_Types is blank
                          OR Facility_Type in Applicable_Facility_Types )
        -> one item per facility; Facility_ID set, Contract_ID null

      INSTALLATION:
        targets = installations having AT LEAST ONE active facility whose
                  Operating_Model matches (or the requirement is 'All')
        -> one item per installation; Facility_ID NULL, Contract_ID null

      CONTRACT:
        targets = distinct Contract_ID across active facilities whose
                  Operating_Model matches
        -> one item per contract; Facility_ID NULL, Contract_ID set,
           Installation_ID = installation of the first facility on that contract
```

The model filter is applied at **facility scope only**. An installation has no
operating model, and a contract may span facilities running different ones.

## The onboarding gate

**`MF_Installation.Generation_Enabled` decides whether a base generates at
all.** A base with it FALSE reads as *not yet onboarded*, never as compliant,
and never as having nothing due.

The canonical installation/facility registry is the critical R1 configuration
dependency — CrunchTime, Aloha Enterprise and Teams all differ and none tracks
what EOM needs. It is built by hand in `MF_Installation` and `MF_Facility` and
becomes the authoritative EOM operational registry until an enterprise source
supersedes it.

Onboarding is therefore: **populate the base's facilities and operating models
→ validate → flip the flag → the next run picks it up.** `Registry_Validated_By`
and `Registry_Validated_Date` record who signed off. Everything else in the app
can be built and tested against the pilot bases meanwhile.

This is a dependency, not a blocker.

## Conditional requirements are never generated

The 1119-1 is **field feeding**, not a 1119 continuation. The source names it
"1119-1 (Field feeding)" and it is required only where field feeding actually
occurred in the period.

Auto-generating it would put a permanent red row on every DFAC that never ran a
field feeding exercise — precisely the kind of false overdue that teaches
people to ignore the dashboard.

The base or the reviewer adds it when it applies, through the *Add a
requirement for this period* action, which is scoped to conditional
requirements only.

## An unknown facility type generates rather than disappearing

The QRG carries no `Facility_Type`. A requirement scoped to
`Main DFAC;Flight Kitchen;Satellite;MAF` would therefore match nothing, and a
base with no expected rows is indistinguishable from a base with nothing due —
the exact failure the expected checklist exists to prevent.

So an unknown type **matches**, and the run reports those facilities as needing
a type confirmed. A false expected row is visible and a reviewer can waive it;
a missing one is invisible until an inspection.

## Facility_ID must be null, not empty string

For Installation and Contract scope the field is **absent from the create
payload**, not written as `''`. SharePoint stores absent as null. The Power BI
relationship and the app's `LookUp` both depend on it, and the two look
identical in a gallery while behaving differently in every `Filter()`.

Do not add the field back with `''` to make the payload look uniform.

## Four dates, not one

```
Nominal_Due_Date          = date(period + Due_Offset_Months, Due_Day)        the 5th
Nominal_Final_Call_Date   = date(period + Due_Offset_Months, Final_Due_Day)  the 10th
Effective_*               = resolved against NonDutyDay_Policy and MF_Non_Duty_Day
Due_Date_Adjusted         = TRUE where a nominal and its effective differ
```

Every value comes from the requirement row, never from the flow. Changing the
5th to the 7th is a list edit. A day of 31 in a 30-day month clamps to the last
day rather than rolling into the next.

Non-duty days are resolved **per installation and portfolio**, because a wing
down day belongs to one base while a federal holiday does not.

**Status evaluation uses the effective dates. Reporting uses the nominal
ones** — leadership still sees "the 5th"; the base sees "Due 5 Sep (Mon 8
Sep)".

## Row written

```
EOM_Item_ID      = period | coalesce(Facility_ID, Contract_ID, Installation_ID) | Requirement_ID
EOM_Item_Key     = LACKLAND|BLDG1234|2026-08|1119     (human-readable)
Authority_Status = requirement.Authority_Status        (denormalized — rule 2 reads it)
Requirement_Scope= requirement.Requirement_Scope       (denormalized for filtering)
Required_Flag    = requirement.Required_Flag
Received_Flag    = false
Current_Submission_ID = null
```

Plus `Routing_Org` from the requirement, **overridden to `NGB/A1X` where
`MF_Installation.Component` is `ANG`** — DAFMAN 34-131 7.14.5 is explicit that
ANG DFAC managers provide the inventory last page to NGB/A1X. Without this the
EOY requirement routes ANG submissions to the wrong organisation and nobody
notices until someone asks where they went.

Then the status engine runs **once** and writes all four status fields
together. Eleven of thirteen requirements are now `VERIFIED` against the AFSVC
procedures deck, so a new row past its final call is genuinely `OVERDUE` —
rule 2 no longer catches most of the estate.

The deterministic `EOM_Item_ID` is what makes this idempotent: check the key
before creating.

## What a re-run must never do

Reset a submission, a QC decision, a waiver, or a correction suspense that a
review moved. A row that already exists is left alone; EOM-03 owns
recalculation, not this flow.

## Configuration health

Three different reports, because they are three different problems and must
not read as one:

| Reported | Meaning |
|---|---|
| Installations awaiting onboarding | `Generation_Enabled` FALSE. Not asked yet. |
| Facilities with no operating model | The NO_DFAC registry rows. A record, not a fault. |
| Facilities with no confirmed type | Generating, but every type-scoped requirement applies until the type is set. |
| Onboarded facilities with no applicable requirements | A genuine configuration gap. |

Report any onboarded active facility that generated **no** items. A facility with no
applicable requirement set is a configuration gap, not a facility with nothing
to do, and it otherwise sits silently green forever. Write it to
`MF_EOM_Audit` and surface it on System Health.

## Audit

One `MF_EOM_Audit` row per run: `Action = 'Generated'`, `Detail` = counts by
scope plus the uncovered-facility list.

## Test

Re-run for a period that already has items. **The row count must not change.**
Then confirm with two views — one filtered `Facility_ID is empty`, one filtered
`Requirement_Scope is Installation or Contract` — that the counts agree exactly.
A mismatch means empty strings were written and every downstream filter is
wrong.
