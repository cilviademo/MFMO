# EOM-03 — Status fact

Writes `MF_EOM_Status`, the canonical Power BI fact.

## The point

**The COP reconstructs no workflow logic.** Every workflow decision is
resolved before Power BI sees it: the code, the semantic label, the visual
state, the action owner, and the two rollup flags. No DAX measure in the
report may re-derive a status, and no report author needs to know what
`RETURNED` means or which codes count toward completeness.

If a question about a row can be answered by the report at all, it is
answered from a column that already exists here.

## Grain

One row per `MF_EOM_Item` per snapshot date:

```
Title (Fact_Key) = "<EOM_Item_Key>|<Snapshot_Date>"
```

Idempotent on that key. A re-run on the same day updates rather than
duplicates, which matters because this flow is the one most likely to be
re-run after a partial failure.

## Rollup flags

```
Is_Complete       = Status_Code = "ACCEPTED"
Is_In_Denominator = Status_Code not in
                    ("NOT_DUE", "WAIVED", "NOT_APPLICABLE", "SUPERSEDED")
```

Both booleans, both computed here, neither stored as a percentage. A colour
rollup would call `[ACCEPTED, NOT_DUE, NOT_DUE]` 33% complete; summing these
two flags gives 100%, which is the truth. When the denominator sums to zero
the answer is *nothing due* — the report shows that, not 0% and not 100%.

**No percentage is ever stored**, here or anywhere. `scripts/eom_schema.py
--validate` fails the build on a column name that suggests one.

## Verification

Step 8 of the build order: after this flow runs, the app and `MF_EOM_Status`
must agree on **every** row, not a sample.

```bash
python3 scripts/validate_solution.py --reconcile-fact \
    --items items_export.json --fact fact_export.json
```

The reconciliation compares `Status_Code`, `Final_Status`, `Status_Semantic`,
`Action_Owner_Role`, `Is_Complete` and `Is_In_Denominator` per
`EOM_Item_ID` for the latest snapshot, and fails on the first disagreement.
A disagreement means one of them derived a value independently of the code,
which is the failure the single-engine rule exists to prevent.

## Security

The fact carries `Portfolio_ID`, `Installation_ID` and `Facility_ID` so
Power BI RLS filters on the same keys the app filters on. **One security
mapping serves both** — `MF_Security_Mapping` is loaded into the model as the
RLS bridge, and the roles are generated from `Scope_Type` and `Scope_ID`
rather than hand-maintained. See `powerbi/MF_EOM_Status.md`.

A facility-scoped viewer must not receive an installation figure derived from
their neighbours' rows: RLS narrows the fact, and the report labels a figure
whose scope was narrowed rather than presenting it as a total.

## Retention

A daily snapshot of every item is the largest table in the solution — roughly
three million rows in year one. `SnapshotRetentionDays` (default 400, one
fiscal year plus a month) governs the purge, which runs at the end of this
flow and deletes by indexed `Snapshot_Date`. Month-end snapshots are exempt
from the purge; the trend a COP needs is monthly, not daily.
