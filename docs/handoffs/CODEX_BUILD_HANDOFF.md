# MISSION FEEDING POWER APPS — CODEX BUILD HANDOFF

**Solution:** `MissionFeedingOperations`
**Release 1 scope:** EOM requirement, evidence, versioning, QC, and COP status
**Target:** a single GCC/GCC High Power Platform environment
**Repo:** this one. `scripts/eom_schema.py` is the single source of truth.

Read `docs/status-calculation.md`, `docs/government-environment-mode.md` and
`docs/accessibility.md` before writing anything. Those three files contain the
decisions that are already settled.

---

## BUILD STATE

```
Schema version:            2.0  (12 lists, 164 columns)
Requirement seed:          12 rows, all UNVERIFIED, 3 inactive
Status logic:              defined and prototyped
HTML prototype:            v2 — docs/mf-operations-prototype.html
Status engine:             one evaluation, five visual states, action ownership
Power Platform build:      NOT STARTED
Solution import tested:    NO — verify you are permitted before building
PAC CLI authorized:        UNKNOWN — verify
Tenant cloud:              UNKNOWN — GCC High or DoD, confirm
```

**Two answers gate everything:** which government cloud this tenant is in, and
whether you may run PAC CLI against it. Neither changes the design; both change
the deployment scripts.

---

## The instruction

Build `MissionFeedingOperations` as a government-compatible, source-controlled
Power Platform solution whose MVP is the EOM document requirement, discovery,
classification, versioning, QC and COP workflow.

**The app is the front door for submissions, and folder drops keep working.**
Users pick their facility and document, then drop the file. Installation,
facility, document type and reporting period are declared at upload, so the file
needs no classification. Files placed directly in a Portfolio FY folder are
discovered by flow and routed to a small Needs Classification queue.

Model expected obligations as Facility / Installation / Contract × Requirement ×
Reporting Period. Model each uploaded file as a child submission version.
Preserve every version.

Operating model and security are at facility grain. Installation- and
contract-scope requirements carry a null `Facility_ID`.

Filenames are never authoritative and never a classification method.

Use only SharePoint, Power Apps, Power Automate, Power BI and Entra identity for
MVP. Everything else degrades gracefully behind a feature flag.

Build with Fluent 2 native modern controls, auto-layout containers, and Section
508 conformance as an acceptance gate.

All Power Fx touching a data source must be delegable at production scale.

No hard-coded URLs, site GUIDs or list names anywhere.

Generate `MF_EOM_Status` as the canonical Power BI fact so the COP reconstructs
no workflow logic.

Include feature flags, maintenance and read-only modes, app version, structured
telemetry, and a protected developer surface.

Produce `.pa.yaml` source, flow definitions, configuration seeds, deployment
docs, validation scripts and test fixtures. The YAML is the code; the `.msapp`
and solution ZIP are build artifacts.

---

## Two corrections to earlier research

**1. "Don't make Power Apps the document repository" is right about the
mechanism and wrong about the conclusion.**

The Power Apps *Attachments control* is genuinely limited — it binds to a Form,
targets lists and Dataverse rather than libraries, and behaves badly on Teams
and mobile. That is a reason not to use the Attachments control. It is not a
reason to stop people uploading through the app.

**Upload via Power Automate to the document library instead.** The app collects
the file and the declared metadata, calls a flow, and the flow writes to the
library and the lists. No Attachments control, no friction, and the declaration
that makes classification unnecessary is preserved.

Reverting to folder-drop-only would reintroduce the exact classification risk
that the front-door decision removed. Both paths stay; the app is preferred.

**2. Layered content classification is a tier-2 fallback, not the production
baseline.**

The confidence pipeline (folder context → metadata → file type → content →
signatures → filename as weak evidence → manual) is a sound design for a system
that must infer. This system mostly doesn't have to.

```
Tier 0  Declared at upload      production baseline, ~95% of volume
Tier 1  Folder + uploader hint  strays; suggestion only, never applied
Tier 2  Document content        feature-flagged, optional
Tier 3  AI Builder              feature-flagged, off by default
Tier 4  Human classification    the queue
```

Build tier 0 and tier 1. Leave tiers 2 and 3 behind `EnableDocumentContentAI`
and `EnableAIBuilder`, both shipping `False`. Do not build a classifier the
architecture no longer needs, and never let AI Builder become a dependency
whose availability could block the app.

Everything else in the research is adopted as written.

---

## Adopted from the research

| Change | Where |
|---|---|
| Single-environment safety as a first-class feature | `MF_App_Config`, `MF_Feature_Flags`, `Developer_Flag`, `Tester_Flag` |
| Kill switch: maintenance and read-only modes | `MF_App_Config`, `App.Formulas.fx` |
| Structured business telemetry | `MF_App_Event_Log` |
| Canonical Power BI fact | `MF_EOM_Status` |
| Semantic status string beside the code | `Status_Semantic` on item and fact |
| Compound human-readable key | `EOM_Item_Key` |
| Portfolio denormalized for delegation | `MF_EOM_Item.Portfolio_ID` |
| Classification method and error state | `MF_EOM_Submission` |
| Named formulas over a bloated OnStart | `App.Formulas.fx` |
| Delegation patterns and anti-patterns | `Delegation.fx` |
| Library-level trigger, not folder-level | `flows/EOM02b-LegacyIntake` |
| Capability gate register | `docs/government-environment-mode.md` |
| Section 508 acceptance gates | `docs/accessibility.md` |
| Semantic releases with packaged rollback | `docs/government-environment-mode.md` |
| No Pipelines dependency | throughout |

---

## Non-negotiables

1. **Never store a percentage or a computed status the app must recompute.**
   `Status_Code` is stored precisely so `Filter()` on it delegates.
2. **`Operating_Model` lives on the facility.** One base can run a legacy DFAC
   and a Food 2.0 café; requirements follow the facility.
3. **`Requirement_Scope` is Facility | Installation | Contract.** A contractor
   invoice may cover several facilities under one CLIN.
4. **`MF_EOM_Item` is persistent; `MF_EOM_Submission` is versioned.** Never
   duplicate the checklist row on resubmission. Never overwrite a file.
5. **`Facility_ID` is null, not empty string,** for installation and contract
   scope.
6. **An UNVERIFIED requirement never drives a Red status.** All twelve seeded
   requirements are provisional today, so this is the default path.
7. **Status is calculated, never chosen.** No colour picker exists anywhere.
8. **Status is never colour-only.** Every chip carries text.
8a. **One status engine, one evaluation.** It returns
    `{status, code, label, actionOwner, actionRequired}`. Never write a second
    function that derives the label independently of the code.
8b. **`Final_Status` and `Status_Code` are independent.** Five visual states,
    not four — Blue separates *not due yet* from *not applicable*.
8c. **Rollups run over semantic statuses and over what the viewer may see.**
    A colour rollup calls `[ACCEPTED, NOT_DUE, NOT_DUE]` Complete. A facility
    user must not receive an installation figure derived from their neighbours.
8d. **No sign-in.** CAC resolves identity before the app loads.
9. **Filenames are never authoritative.**
10. **The list row is truth; the file path is convenience.** Files get moved and
    renamed. Store `SharePoint_File_ID`, not just the URL.
11. **One security mapping** serves app filtering and Power BI RLS.
12. **Do not invent a requirement.** An upload with no matching expected item
    goes to Needs Classification, never creates a tracker row.

---

## Delegation — the failure that doesn't announce itself

A non-delegable query returns the first 500 rows (2,000 maximum) and reports
success. A Portfolio Manager sees "3 overdue" when there are eleven, and nobody
finds out until an inspection.

`MF EOM Item` at 89 installations × facilities × requirements × 12 months × the
first year of versions passes that ceiling comfortably. Every query filters
server-side on indexed columns, `Reporting_Period` first.

The anti-patterns are enumerated in `canvas-app/formulas/Delegation.fx`. The
provisioning script indexes the required columns. **Indexes must exist before a
list crosses 5,000 items — you cannot add them afterward.**

---

## Naming

```
Screens      scrHome scrUpload scrInstallation scrReview scrUnmatched
             scrHistory scrAdminRequirements scrMaintenance scrNoAccess
             scrDiagnostics (developer only)
Containers   conRoot conHeader conBody conNav conContent conFooter
Galleries    galMyWork galRequirements galFacilities galVersions
Controls     cmbInstallation cmbFacility cmbPeriod btnReview btnAccept
             lblFacilityName
Components   cmpStatusBadge cmpEOMItem cmpMetricCard cmpEmptyState
Globals      gblCurrentUser gblCurrentFacility gblRole gblAppVersion
Locals       locSelectedItem locDialogOpen
Collections  colNavigation
```

Prefer `With()` for scoped subformulas over chains of `Set()`. Avoid nested
`ForAll` — that work belongs in EOM-01.

---

## Build order

1. **Verify the capability gates.** `docs/government-environment-mode.md`.
   Stop if SharePoint, Power Apps or Power Automate are unavailable.
2. **Provision lists.** `provisioning/Provision-MFOpsLists.ps1`. Confirm the
   indexes were created.
3. **Seed configuration.** `configuration/requirements.csv`, then `MF_App_Config`,
   `MF_Feature_Flags`, and the real installation, facility and security rows.
4. **Build EOM-01** and run it for the open period. Verify idempotency and null
   `Facility_ID` on installation-scope rows before building any UI.
5. **Build the app shell:** App.Formulas, OnStart, containers, components,
   scrHome, scrMaintenance, scrNoAccess.
6. **Build scrUpload** with the flow-based upload. Test with an arbitrary
   filename.
7. **Build scrInstallation and scrReview.** Test the correction cycle end to end.
8. **Build EOM-03**, then verify the app and `MF_EOM_Status` agree on every row.
9. **Build EOM-02 and scrUnmatched.**
10. **Build EOM-04** with notifications disabled; read the log for a full cycle
    before enabling.
11. **Run the acceptance tests** in `docs/DEPLOYMENT.md` and
    `docs/accessibility.md`.
12. **Export, unpack, tag, commit.**

Do not build screens before EOM-01 produces correct rows. Every UI decision
downstream depends on the shape of that data.

---

## Definition of done for R1

- [ ] Capability gates verified and recorded
- [ ] Lists provisioned, indexes confirmed
- [ ] EOM-01 idempotent; installation-scope rows have null `Facility_ID`
- [ ] A facility with a legacy DFAC and a Food 2.0 café generates both
      requirement sets
- [ ] Upload works with an arbitrary filename via the flow, not the Attachments
      control
- [ ] Resubmission creates v2 and retains v1
- [ ] QC blocks return without comment and suspense
- [ ] Provisional requirement past suspense stays Gray
- [ ] Rollups correct at facility, installation and portfolio
- [ ] `MF_EOM_Status` matches the app for every row
- [ ] RLS tested with at least two scopes
- [ ] Every query verified delegable at 5,000+ rows
- [ ] Accessibility checker clean; keyboard-only pass complete
- [ ] Maintenance and read-only modes tested
- [ ] A feature flag demonstrably hides a screen from a normal user
- [ ] Telemetry writes on open, upload and QC
- [ ] `dist/MissionFeedingOperations_v1.0.0.zip` + CHANGELOG committed

---

## What R1 deliberately does not do

FMAT, SAIIT, training, equipment, contracts and Five-Year Plans. Build the shell
correctly; `Requirement · Scope · Due · Status · Action` is the same row in
every later module, and R2–R4 reuse it without new UX.

Also out of scope: content-based classification, AI Builder, backfill of prior
periods, PCF components, Code Apps, Pipelines, and any composite readiness
score.
