# Flows

Five flows. Between them they own every write that matters, because the app
enforces nothing on its own: a disabled button is a courtesy, and the check
inside the flow is the control.

| Flow | Trigger | Owns |
|---|---|---|
| `EOM01-GenerateExpectedItems` | Recurrence, nightly | Creating the persistent checklist rows |
| `EOM02-FileIntake` | SharePoint, **library level** | Discovering folder drops, routing strays to Needs Classification |
| `EOM03-StatusFact` | Recurrence, nightly after EOM-01 | Writing `MF_EOM_Status`, the canonical Power BI fact |
| `EOM04-QCDecision` | Power Apps (V2) | QC accept and return, and the flag-gated notifications |
| `EOM05-AppUpload` | Power Apps (V2) | The front door: writing the file to the library and the submission row |

## Rules every flow follows

1. **First action reads `MF_App_Config`.** No URL, site GUID or list name is
   hard-coded in a flow definition. The site and library paths come from
   configuration at run time.
2. **`ReadOnlyMode` is checked server-side.** `EOM04` and `EOM05` terminate
   with a friendly failure if it is on, regardless of what the app allowed.
3. **The status engine is applied in one place per flow**, in the order
   defined in `docs/status-calculation.md`. No flow derives a label or a
   colour independently of the code.
4. **Never invent a requirement.** `EOM02` has no path that creates an
   `MF_EOM_Item`.
5. **Never overwrite a file, never duplicate a checklist row.** `EOM05`
   increments `Version_Number` and flips `Is_Current_Version`; it never
   patches over an existing file or row.
6. **Every run writes to `MF_App_Event_Log`** with the `correlationId` the
   app passed, so an app action and its flow runs are one story.
7. **Idempotency is by business key, not by run history.** Re-running a flow
   after a partial failure is always safe.

## Importing

The definitions here are the reviewable source. They carry
`$connections` placeholders rather than environment-specific connection ids;
those are supplied by the deployment settings file at import time and are
never edited in place. See `docs/DEPLOYMENT.md`.
