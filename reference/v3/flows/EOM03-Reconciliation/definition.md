# EOM-03 — Nightly Reconciliation

**Trigger:** Recurrence, nightly 02:00 local.

The only writer of `Final_Status` and `Status_Code` outside the app's QC action.
Implements `docs/status-calculation.md` exactly. If the two ever disagree, this
flow is wrong, not the app.

## Steps

1. **Recalculate item status** for the open period and the two prior periods,
   applying the nine-rule decision order. Older periods are closed history and
   are not touched.

2. **Sync Current_Submission_ID** to the `Is_Current` submission. Repair stale
   pointers — a failed app patch can leave one dangling.

3. **Detect orphan submissions.** Any submission whose EOM_Item_ID does not
   resolve → audit row plus an MF Unmatched File entry. Never delete.

4. **Rebuild `MF_EOM_Status`** — one flat row per MF_EOM_Item joined to
   installation, facility and requirement. Write both `Status_Code` and
   `Status_Semantic`; Power BI colours on the first and labels with the second,
   and reconstructs no workflow logic of its own. Also set `Days_Late` and
   `On_Time_Flag` here rather than in DAX.

5. **Write the run summary** to MF EOM Audit: items evaluated, status changes,
   orphans, duration.

## The rule that matters

An item whose requirement is `Authority_Status = 'UNVERIFIED'` and has not been
received stays at `Status_Code = 0`, never 1. An unconfirmed requirement must not
turn a base red. All twelve seeded requirements are currently UNVERIFIED, so this
is the default path, not an edge case.
