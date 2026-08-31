# Flows — four, and only four

The Power App handles all human interaction and all QC writes. Power Automate
does only what the app cannot: scheduled generation, background discovery,
recalculation, and notification.

**The separate "Portfolio QC Flow" from the earlier design is deleted.** When a
Portfolio Manager clicks Accept, the app patches the list directly. EOM-04 only
notices the resulting state change.

| Flow | Trigger | Purpose |
|---|---|---|
| EOM-01 Expected Package Generator | Recurrence, 1st of month 0500 | Create the expected MF_EOM_Item rows |
| EOM-02 Submission | Called from the app | Authorise, resolve destination, place the file, record the submission |
| EOM-02b Legacy Intake | When a file is created in the FY library | Folder drops the app didn't create. Exception path only. |
| EOM-03 Reconciliation | Recurrence, nightly 0200 | Recalculate Final_Status and Status_Code |
| EOM-04 Notifications | Recurrence, daily 0700 | Suspense reminders and escalation |

Each subfolder holds a `definition.md` written as an implementation spec, not a
hand-authored `definition.json`. Flow definitions are environment-bound; a
wrong-environment export is worse than none. Build these in the DEV environment
against these specs, then export the solution through `pac` and commit the
result to `dist/`.
