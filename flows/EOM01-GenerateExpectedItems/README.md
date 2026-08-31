# EOM-01 — Generate expected items

**Reference implementation: `scripts/generate_expected_items.py`.** The flow is
a transliteration of it. `tests/test_eom01.py` runs the reference against
fixtures and asserts the properties below.

**Build order: this runs before any screen is built.** Every UI decision
downstream depends on the shape of this data, and a gallery built against
rows with the wrong `Facility_ID` semantics has to be rebuilt, not adjusted.

## What it does

For each reporting period in state `OPEN`, expand the active requirement
catalogue across the active installations, facilities and contracts, and
upsert one `MF_EOM_Item` per obligation.

```
for period in periods where Period_State = "OPEN":
  for requirement in requirements where Is_Active:
    if FREQUENCY_TO_PERIOD_TYPE[requirement.Frequency] != period.Period_Type: skip
    if period.Period_End outside requirement effective dates:            skip

    Due_Date      = period.Period_End + requirement.Due_Offset_Days
    Suspense_Date = period.Period_End + requirement.Suspense_Offset_Days

    targets = by requirement.Requirement_Scope:
      Facility      -> active facilities whose Operating_Model is in
                       Applies_To_Operating_Model (empty means all)
      Installation  -> active installations          Facility_ID = null
      Contract      -> active contracts              Facility_ID = null

    for target in targets:
      key = "<Scope>|<ScopeID>|<Requirement_Code>|<Period_ID>"
      if MF_EOM_Item has key: re-evaluate status only, keep everything else
      else:                   create the row
```

Frequency selects the period type. Nothing is inferred from a period's name.

| Frequency | Period_Type |
|---|---|
| `Monthly` | `Month` |
| `Quarterly` | `Quarter` |
| `SemiAnnual` | `Quarter` |
| `Annual` | `FiscalYear` — the EOY path |

## The three properties that are tested

**Idempotent.** Identity is `EOM_Item_Key`, and generation is an upsert keyed
on it. A second run creates nothing and changes no `EOM_Item_ID`. The
checklist row is persistent; only submissions are versioned. A run never
resets a submission, a QC decision, or a suspense date a QC return moved.

**Null, not empty string.** Installation- and Contract-scope rows carry
`Facility_ID = null`. The flow writes the field as absent, not as `''`. An
empty string looks identical in a gallery and behaves differently in every
`Filter()`, and `IsBlank()` does not delegate — so the app asks about
`Requirement_Scope` instead, which is why that column is denormalized here.

**Requirements follow the facility.** The operating-model filter is evaluated
per facility and only for Facility-scope requirements. Fort Liberty in the
sample data runs a legacy DFAC (`FAC-FTLIB-01`) and a Food 2.0 café
(`FAC-FTLIB-02`); `REQ-002` applies to `Legacy_DFAC;Contractor_Operated` and
`REQ-012` to `Food_2_0;Hybrid`, so the two facilities generate different
requirement sets on the same installation. An installation has no operating
model, and a contract may span facilities running different ones, so the
filter is not applied at those scopes.

## Status at generation

Every new row is evaluated by the status engine once, at creation. With all
twelve requirements `UNVERIFIED`, a row created after its suspense date is
`PROVISIONAL_OVERDUE` / Gray, not `OVERDUE` / Red — and its action owner is
`Program`, not the facility. This is the default path today, not an edge case.

## Verify before building any UI

```bash
python3 scripts/generate_expected_items.py --as-of 2026-09-20
python3 -m pytest tests/test_eom01.py -v
```

Then in the tenant, after the first run:

1. Row count matches the reference for the same seed data.
2. `Facility_ID` is genuinely empty (not `''`) on every Installation- and
   Contract-scope row — check with a view filtered `Facility_ID is empty` and
   compare against a `Requirement_Scope = Installation` filter. The two counts
   must agree.
3. Run it a second time. Created count is zero and no `EOM_Item_ID` changed.
4. `FAC-FTLIB-01` and `FAC-FTLIB-02` have different requirement sets.

## Scale

At 89 installations the nightly run touches hundreds of thousands of rows
over a year. It pages the SharePoint source with `$top` and a `$filter` on
indexed columns, and it never issues a per-row `Get item` — the existing-key
lookup is one paged read of the period's rows into a keyed object, then an
in-memory check per candidate.
