# EOM-03 — Nightly Reconciliation

**Trigger:** Recurrence, nightly 02:00 local.

The only writer of `Final_Status` and `Status_Code` outside the app's QC
action. Implements `docs/status-calculation.md` exactly. **If the two ever
disagree, this flow is wrong, not the document.**

## Steps

1. **Recalculate item status** for the open period and the two prior periods,
   applying the ten-rule decision order in one evaluation per row. Older
   periods are closed history and are not touched.

   All four fields are written together — `Final_Status`, `Status_Code`,
   `Action_Owner`, `Action_Required`. A flow that writes one without the others
   has derived it somewhere else.

2. **Sync `Current_Submission_ID`** to the `Is_Current` submission, and
   `Received_Flag` / `Received_DateTime` with it. Repair stale pointers: a
   failed app patch can leave one dangling.

3. **Set the two on-time facts and `Days_Late`** here rather than in DAX, and
   stamp `Last_Reconciled_DateTime`.

   ```
   Initial_Submitted_DateTime      first version, never overwritten by a resubmission
   Initial_Submission_On_Time      by Effective_Due_Date        -> told to the base
   Acceptable_Evidence_DateTime    when an accepted version first existed
   Final_Evidence_On_Time          by Effective_Final_Call_Date -> told to leadership
   ```

   Uploaded 4 Sep, returned 9 Sep, accepted 12 Sep is *submitted on time* AND
   *final evidence late*. Both are true and both are stored, because they
   answer different people's questions.

   `Days_Late` measures against the final call. Amber and Red share an owner;
   this carries the difference in degree.

   System Health flags anything not reconciled within
   `MF_App_Config.ReconciliationStaleHours` — stale reconciliation looks
   exactly like a quiet month.

4. **Detect orphan submissions.** Any submission whose `EOM_Item_ID` does not
   resolve gets an audit row and an `MF Unmatched File` entry. Never delete.

5. **Detect duplicate current versions.** More than one `Is_Current` row per
   item is a defect; keep the newest, demote the rest, and audit it.

6. **Rebuild `MF_EOM_Status`** — one flat row per `MF_EOM_Item`, joined to
   installation, facility and requirement. Copy `Final_Status` and
   `Status_Code` **verbatim**; Power BI colours on the code and labels with the
   semantic string, and reconstructs no workflow logic of its own.

   Compute `Package_State` here too, over semantic statuses.

7. **Write the run summary** to `MF_EOM_Audit`: items evaluated, status
   changes, orphans, duplicates, duration.

## The rule that matters

An item whose requirement is `Authority_Status = 'UNVERIFIED'` and has not been
received is `PENDING_VALIDATION`, **`Status_Code = 4`** — Blue, informational,
owner `Admin`. It is never 1, and it is not 0 either.

> V3's spec said `Status_Code = 0` here. That was the four-state model, before
> Blue existed to separate *not due yet* from *not applicable*. Corrected —
> see `docs/handoffs/RECONCILIATION.md` C2.

All twelve seeded requirements are `UNVERIFIED`, so this is the default path,
not an edge case. An unconfirmed requirement must not turn a base red.

## Package state, over semantic statuses

```
any OVERDUE, RETURNED, NOT_SATISFIED or LATE        ACTION_REQUIRED
else any RECEIVED_PENDING_QC                        IN_REVIEW
else every applicable non-provisional item ACCEPTED COMPLETE
else anything applicable remains                    IN_PROGRESS
else                                                NOT_APPLICABLE
```

Never over colour codes. The naive colour rollup sees `[3, 4, 4]`, finds no 1
and no 2, and marks the package Complete. It is `IN_PROGRESS`: two requirements
have not been filed.

## Verification

After the run, the app and `MF_EOM_Status` must agree on **every** row, not a
sample:

```bash
python3 scripts/validate_solution.py --reconcile-fact \
    --items items_export.json --fact fact_export.json
```

A disagreement means something derived a status independently of the semantic
string, which is the failure the one-engine rule exists to prevent.
