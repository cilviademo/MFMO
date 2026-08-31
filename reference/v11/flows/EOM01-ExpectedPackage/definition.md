# EOM-01 — Expected Package Generator

**Trigger:** Recurrence, 1st of each month, 05:00 local.
**Idempotent.** Safe to re-run; never creates a duplicate item.

## Logic

```
period        = format(addToTime(utcNow(), -1, 'Month'), 'yyyy-MM')
activeReqs    = MF EOM Requirement where Active_Flag = true
facilities    = MF Facility where Active_Flag = true
installations = MF Installation where Active_Flag = true

for each requirement in activeReqs:

    if requirement.Frequency does not fall in this period: skip
       (Monthly = always; Quarterly = period month in {12,3,6,9};
        Semiannual = {3,9}; Annual = {9}; Conditional = never auto-generate)

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
                  Operating_Model matches (or requirement is 'All')
        -> one item per installation; Facility_ID NULL, Contract_ID null

      CONTRACT:
        targets = distinct Contract_ID across active facilities whose
                  Operating_Model matches
        -> one item per contract; Facility_ID NULL, Contract_ID set,
           Installation_ID = installation of the first facility on that contract
```

**Facility_ID must be null, not empty string,** for Installation and Contract
scope. The Power BI relationship and the app's LookUp both depend on it.

## Due date

```
Due_Date = date( period + Due_Offset_Months , Due_Day )
```

Both values come from the requirement row, never from the flow. Changing the
10th to the 15th is a list edit.

## Row written

```
EOM_Item_ID       = period & '|' & coalesce(Facility_ID, Contract_ID, Installation_ID)
                              & '|' & Requirement_ID
Required_Flag     = requirement.Required_Flag
Requirement_Scope = requirement.Requirement_Scope     (denormalized for filtering)
Received_Flag     = false
Current_Submission_ID = null
Final_Status      = 'Not Due'
Status_Code       = 0
```

The deterministic `EOM_Item_ID` is what makes this idempotent — check the key
before creating.

## Audit
One MF EOM Audit row per run: Action = 'Generated', Detail = counts by scope.

## Test
Re-run for a period that already has items. Row count must not change.
