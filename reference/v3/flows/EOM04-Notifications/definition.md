# EOM-04 — Notifications and Escalation

**Trigger:** Recurrence, daily 07:00 local.
**Gated by `mfops_MF_NotificationsEnabled`. Ship FALSE. Enable after UAT.**

Decides nothing. Reads what EOM-03 and the app already wrote.

| Condition | Recipient | Cadence |
|---|---|---|
| Due in 3 days, not received | Facility manager | Once |
| Due today, not received | Facility manager + MFM | Once |
| Overdue | Facility manager + MFM | Every 3 days |
| Overdue > `MF_EscalationDaysOverdue` | Portfolio Manager | Once, then weekly |
| Correction Required | Original uploader | Once, then at suspense |
| Correction suspense passed | Uploader + Portfolio Manager | Once |
| Pending Review > 5 days | Portfolio Manager | Every 3 days |

## Anti-spam

Record `Notified_DateTime` per item per notification type in MF EOM Audit and
check before sending. Without it, the daily recurrence mails the same person
about the same missing 1119 thirty times.

**Digest, not per-item.** One message per recipient per run, listing everything
they owe. Thirty separate emails is how a notification system gets muted in
week one.

## Test before enabling
Run with the flag FALSE, writing intended sends to MF EOM Audit for a full
cycle. Read the log. Then enable.
