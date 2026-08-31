# EOM-04 — Notifications and Escalation

**Trigger:** Recurrence, daily 07:00 local.

Decides nothing. Reads what EOM-03 and the app already wrote, and **reads its
own rules from `MF_Notification_Rule`** — notifications are a list, not code.
Every rule has an `Enabled` toggle and a `Digest` flag, and the toggles are on
an admin screen rather than inside this flow.

**Two rules ship enabled**, because they are the two that stop somebody
watching a folder:

| Rule | Trigger | To | Why |
|---|---|---|---|
| NR-001 | `SubmissionCreated` | portfolio org box | Reviewers learn something arrived |
| NR-002 | `StatusChanged` | the submitter | A base learns their document came back |

Everything else ships disabled and is tuned once the queue behaves.

The remaining triggers, all seeded disabled:

| Trigger | Recipient | Note |
|---|---|---|
| `DueSoon` | Installation POC | |
| `FirstSuspensePassed` | Installation POC | **The one that matters most** — the only week in the cycle where a reminder still changes the outcome |
| `FinalSuspensePassed` | Portfolio Manager | Escalation after `EscalationDaysOverdue` |
| `CorrectionSuspensePassed` | Submitter | |
| `PendingReviewAging` | Portfolio Manager | Review throughput is a real metric, because Accept means opening the file |
| `AccessRequested` | a holder of `Can_Grant_Access` | |

An org box or a role is a recipient. **A named person's mailbox is never a rule
target** — it breaks the moment they PCS.

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
