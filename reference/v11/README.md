# Mission Feeding Operations

Power Platform solution for End-of-Month submission tracking and QC. Release 1
of a shell that FMAT, Training, Equipment and Five-Year modules will reuse.

```
Power App        Mission Feeding Manager front end, all human interaction and QC
SharePoint       Storage: 8 lists + the evidence document tree
Power Automate   Background only: generation, intake, reconciliation, notification
Power BI         COP / leadership snapshot, formatted from Status_Code alone
```

## The design decision that makes this work

**The app is the front door.** When a DFAC manager selects their facility and
drops a file into the requirement box, installation, facility, document type and
reporting period are *declared* at upload. Nothing has to classify the file, and
no naming convention exists or is needed.

The upload goes through a Power Automate flow to the document library, **not**
through the Power Apps Attachments control — that control binds to a Form,
targets lists rather than libraries, and behaves badly on Teams and mobile.

Folder drops still work and land in a small Needs Classification queue that a
human resolves in the app. Content classification and AI Builder exist as
feature-flagged tiers, both shipping off, and neither may become a dependency.

## No sign-in

CAC identifies the user before the app loads. Identity, scope and permissions
resolve from `MF_Security_Mapping` on open. There is no login screen anywhere in
the design, and a user with no mapping gets a route to fix that rather than an
empty app.

## Built for one environment

A DAF tenant may grant a single Power Platform environment for everything.
Publishing is deploying, so every safety mechanism lives inside the app:
feature flags, maintenance and read-only modes, developer/tester surfaces,
version stamping and structured telemetry. See
`docs/government-environment-mode.md`.

## Locked design decisions

1. **`Operating_Model` lives on the facility**, not the installation. One base
   can run a legacy DFAC and a Food 2.0 café; requirements follow the facility.
2. **`Requirement_Scope` is Facility | Installation | Contract.** Portfolio is
   reserved, not implemented. A contractor invoice may cover several facilities
   under one CLIN and must not be forced to facility grain.
3. **`MF_EOM_Item` is persistent; `MF_EOM_Submission` is versioned.** A
   correction attaches v2 to the same item. The checklist row is never
   duplicated.
4. **`Facility_ID` is nullable** on the item, for installation and contract scope.
5. **Unresolved form applicability is configuration, never code.** All twelve
   seeded requirements are `UNVERIFIED`, and an unverified requirement never
   drives a Red status.
6. **Status is calculated, never chosen.** No colour picker anywhere.
   `docs/status-calculation.md` is the one definition; Power Fx and DAX are
   mechanical translations of it.
7. **One security mapping** serves both app filtering and Power BI RLS.
8. **Status is never colour-only.** `Status_Semantic` accompanies every code —
   Section 508.
9. **Every data-source query must delegate.** A non-delegable query returns the
   first 500 rows and reports success; it produces wrong answers, not slow ones.
10. **The list row is truth; the path is convenience.** Store
    `SharePoint_File_ID`, not just a URL.

## Repository

```
CODEX_BUILD_HANDOFF.md           the execution prompt
docs/
  build-notes.md                 READ FIRST — programme answers, overrides everything
  MF_EOM_Data_Dictionary.csv     12 lists, 164 columns
  government-environment-mode.md single-environment safety, capability gates
  accessibility.md               Section 508 acceptance gates
  design-system.md               Fluent + Cognos, calendar spec, routing notes
  figma-prompt.md                first-pass generation prompt
  figma-prompt-v2.md             improvement pass — use this one
  powerapps-translation.md       React prototype patterns -> Canvas equivalents
  prototype-notes.md             what the prototype proves and what changed
  mf-operations-prototype.html   working prototype — open it in a browser
  status-calculation.md          THE status definition — read before changing anything
  DEPLOYMENT.md                  provisioning, build, export, acceptance tests
provisioning/
  Provision-MFOpsLists.ps1       PnP, idempotent, sets indexes
configuration/
  requirements.csv               12 seeded rows, all UNVERIFIED
  app-config.csv                 kill switch and capability toggles
  feature-flags.csv              8 flags, unreleased work shipped safely
  environment-variables.json     13 variables — no hard-coded URLs anywhere
  connection-references.json
canvas-app/
  formulas/                      App.Formulas (named formulas), OnStart,
                                 Cascade, Upload, QC, Delegation
  screens/                       7 screens with layouts
  components/                    8 reusable components
  data-sources/                  delegation rules that actually matter at scale
flows/                           4 specs — EOM-01 through EOM-04
solution/MissionFeedingOperations/   unpacked solution source (populated after first export)
dist/                            the exported package (produced by pac, not by hand)
```

## Release path

| Release | Domain | Reuses |
|---|---|---|
| R1 | EOM submission, QC, missing, correction | — |
| R2 | FMAT: finding → owner → due → action → validation | same shell |
| R3 | Training: requirement → completion → expiration | same shell |
| R4 | Equipment: asset → NMC → work order → aging → close | same shell |

`Requirement · Scope · Due · Status · Action` is the same row in every one.

## Status

Nothing here has been imported into a Power Platform environment. Build in DEV
against these specs, export through `pac`, commit the result. See
`docs/DEPLOYMENT.md`.
