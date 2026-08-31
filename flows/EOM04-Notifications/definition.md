# EOM-04 — Notifications and Escalation

**Trigger:** Recurrence, daily 07:00 local.
**Gated by `mfops_MF_NotificationsEnabled`. Ships FALSE. Enable after UAT.**

Decides nothing. Reads what EOM-03 and the app already wrote.

| Condition | Recipient | Cadence |
|---|---|---|
| Due in 3 days, not received | Facility manager | Once |
| Due today, not received | Facility manager + MFM | Once |
| `OVERDUE` | Facility manager + MFM | Every 3 days |
| Overdue > `EscalationDaysOverdue` | Portfolio Manager | Once, then weekly |
| `CORRECTION_REQUIRED` | Original uploader | Once, then at suspense |
| Correction suspense passed | Uploader + Portfolio Manager | Once |
| `RECEIVED_PENDING_QC` > 5 days | Portfolio Manager | Every 3 days |

## A provisional requirement never generates a nag

`PENDING_VALIDATION` is excluded from every row above. The action sits with the
programme, not the facility, and mailing a base about an obligation nobody has
confirmed exists is exactly the behaviour the Blue state prevents on screen.

## Anti-spam

Record `Notified_DateTime` per item per notification type in `MF_EOM_Audit`
(`Action = 'Notification Sent'`) and check before sending. Without it, the
daily recurrence mails the same person about the same missing 1119 thirty
times.

**Digest, not per-item.** One message per recipient per run, listing everything
they owe. Thirty separate emails is how a notification system gets muted in
week one.

## Test before enabling

Run with the flag FALSE for a full cycle, writing every intended send to
`MF_EOM_Audit` as `Action = 'Notification Suppressed'` with the recipient and
the reason. **Read the log.** Then enable.

A notification system switched on untested is how a programme teaches several
hundred people to filter its mail to a folder.
