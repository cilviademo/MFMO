# EOM-01 — Expected Package Generator

**Trigger:** Recurrence, 1st of each month, 05:00 local.
**Idempotent.** Safe to re-run; never creates a duplicate item.

Reference implementation: `scripts/generate_expected_items.py`.
Tests: `tests/test_eom01.py`.

**Build order: this runs before any screen is built.** Every UI decision
downstream depends on the shape of this data, and a gallery built against rows
with the wrong `Facility_ID` semantics gets rebuilt, not adjusted.

## Logic

```
period        = format(addToTime(utcNow(), -1, 'Month'), 'yyyy-MM')
activeReqs    = MF EOM Requirement where Active_Flag = true
facilities    = MF Facility        where Active_Flag = true
installations = MF Installation    where Active_Flag = true

for each requirement in activeReqs:

    if requirement.Frequency does not fall in this period: skip
       Monthly     always
       Quarterly   period month in {12, 3, 6, 9}
       Semiannual  {3, 9}
       Annual      {9}
       Conditional never auto-generated

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

## Facility_ID must be null, not empty string

For Installation and Contract scope the field is **absent from the create
payload**, not written as `''`. SharePoint stores absent as null. The Power BI
relationship and the app's `LookUp` both depend on it, and the two look
identical in a gallery while behaving differently in every `Filter()`.

Do not add the field back with `''` to make the payload look uniform.

## Due date

```
Due_Date = date( period + Due_Offset_Months , Due_Day )
```

Both values come from the requirement row, never from the flow. Changing the
10th to the 15th is a list edit. A `Due_Day` of 31 in a 30-day month clamps to
the last day of that month rather than rolling into the next.

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

Then the status engine runs **once** and writes all four status fields
together. With every seeded requirement `UNVERIFIED`, a new row is
`PENDING_VALIDATION` / `Status_Code 4` / owner `Admin` — informational, never
adverse. That is the default path today, not an edge case.

The deterministic `EOM_Item_ID` is what makes this idempotent: check the key
before creating.

## What a re-run must never do

Reset a submission, a QC decision, a waiver, or a correction suspense that a
review moved. A row that already exists is left alone; EOM-03 owns
recalculation, not this flow.

## Configuration health

Report any active facility that generated **no** items. A facility with no
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
