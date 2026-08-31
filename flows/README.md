# Flows — five

The Power App handles all human interaction and all QC writes. Power Automate
does only what the app cannot: scheduled generation, background discovery,
recalculation, notification, and the one write the app is not allowed to make
directly.

**The separate "Portfolio QC Flow" from the earliest design stays deleted.**
When a Portfolio Manager clicks Accept, the app patches the list. EOM-04 only
notices the resulting state change.

| Flow | Trigger | Purpose |
|---|---|---|
| EOM-01 Expected Package Generator | Recurrence, 1st of month 05:00 | Create the expected `MF_EOM_Item` rows |
| EOM-02 Submission | Called by `scrUpload` | Resolve the destination, place the file, write the submission row |
| EOM-02b Legacy Intake | File created in a portfolio library | Catch folder drops the app did not create |
| EOM-03 Reconciliation | Recurrence, nightly 02:00 | Recalculate `Final_Status` / `Status_Code`, rebuild `MF_EOM_Status` |
| EOM-04 Notifications | Recurrence, daily 07:00 | Suspense reminders and escalation. Ships disabled. |

EOM-02 was `EOM-05 App Upload` and EOM-02b was `EOM-02 File Intake`; they were
renamed to match the programme handoff when the app became the front door.

**EOM-02b is deployed four times, once per portfolio.** The four portfolios are
four separate SharePoint **site collections**, and a SharePoint trigger binds to
one site. There is no single instance that covers all four, and a build that
assumed otherwise would have discovered folder drops in Portfolio 1 only.
`deployment/site-bindings.md` carries the bindings.

## Why these are Markdown specs and not `definition.json`

Flow definitions are environment-bound. A hand-written export that has never
been imported, never validated against a connector and never run is not
source — it is a drawing of source, and its fidelity is implied rather than
real. A wrong-environment export is worse than none.

So each subfolder holds a `definition.md` written as an implementation spec.
Build these in the tenant against these specs, then export the solution and
commit the artifact to `dist/`. The spec stays the reviewable source; the
export is the build output.

An earlier commit on this branch shipped fabricated Logic Apps JSON for these
flows. It was removed — see `docs/handoffs/RECONCILIATION.md` §8.

## Rules every flow follows

1. **First action reads `MF_App_Config`.** No site URL, GUID or list name is
   literal in a flow. Environment variables where the tenant supports them,
   `MF_App_Config` rows where it does not; neither path is load-bearing alone.
2. **`ReadOnlyMode` is checked server-side.** EOM-04 and EOM-02 refuse to
   write when it is on, regardless of what the app allowed. The disabled
   control is a courtesy; this is the control.
3. **The status engine is applied in one place per flow**, in the order in
   `docs/status-calculation.md`. No flow derives a label or a colour
   independently of the semantic status.
4. **Never invent a requirement.** No flow has a path that creates an
   `MF_EOM_Item` from a file.
5. **Never overwrite a file, never duplicate a checklist row.**
6. **Every run writes to `MF_EOM_Audit`**, and business events to
   `MF_App_Event_Log`, stamped with `App_Version`.
7. **Idempotency is by deterministic business key**, not by run history.
   Re-running after a partial failure is always safe.
