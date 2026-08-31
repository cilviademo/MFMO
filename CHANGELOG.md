# Changelog

Semantic versions. `MAJOR` is a schema change requiring a provisioning run,
`MINOR` a screen, flow or requirement change, `PATCH` a fix with no schema or
contract change.

Rollback is importing the previous ZIP from `dist/`. A rollback across a
MAJOR boundary needs the matching provisioning run and is documented in that
release's entry; there is no automatic down-migration.

---

## [Unreleased] — R1 source complete, not yet built in a tenant

Everything below exists as reviewable source and passes the local suite. **No
Power Platform environment has been touched.** `dist/` holds no ZIP, because
one cannot honestly be produced without an environment to export from.

### Schema

- `scripts/eom_schema.py` at version **2.0**: 12 lists, 164 columns, the
  single source of truth. Validated by assertion rather than by convention —
  the list count, the column count, the index declarations, `Facility_ID`
  nullability and the ban on stored percentages all fail the build if broken.
- `docs/data-model.md` generated from it; a stale copy fails validation.
- `provisioning/Provision-MFOpsLists.ps1` consumes the generated JSON and
  declares nothing of its own. It refuses to run against a schema version it
  does not expect, and throws rather than continuing if an index cannot be
  created.

### Status

- One engine, one evaluation, returning
  `{status, code, label, actionOwner, actionRequired}`.
- Eleven codes over five visual states. Blue separates *not due yet* from
  *not applicable*.
- `PROVISIONAL_OVERDUE` (Gray, owner **Program**) so an unverified
  requirement past its suspense date never drives Red. With all twelve seeded
  requirements `UNVERIFIED`, this is the default path today.
- Reference implementation in Python; transliterations in
  `StatusEngine.fx`, `flows/EOM03-StatusFact` and the HTML prototype. The
  tests hold all four in agreement, including the **evaluation order**, which
  is behaviour and not style.
- Rollups run over semantic status: `[ACCEPTED, NOT_DUE, NOT_DUE]` is 100%
  complete, and a zero denominator reads "Nothing due" rather than 0% or 100%.

### Data and configuration

- Twelve seeded requirements, **all UNVERIFIED**, three inactive. Each states
  in its `Authority_Reference` that it is provisional and what is missing —
  an empty citation on an unverified row tells a reader nothing.
- All three requirement scopes and the Annual (EOY) frequency are exercised
  by the seed.
- `MF_App_Config` ships `TenantCloud` and `PacCliAuthorized` as `UNKNOWN`,
  the kill switch off, and `SiteUrl` as `SET_AT_DEPLOY`.
- `EnableDocumentContentAI` and `EnableAIBuilder` ship `False` in both value
  and default, and no code path behind either exists in R1.

### EOM-01

- Idempotent on the compound `EOM_Item_Key`; a second run creates nothing and
  changes no `EOM_Item_ID`, and never resets a submission, a QC decision or a
  suspense date a return moved.
- Installation- and Contract-scope rows carry a **null** `Facility_ID`. The
  field is absent from the flow's create body rather than written as `''`.
- The operating-model filter is evaluated per facility and only at facility
  scope, so one base running a legacy DFAC and a Food 2.0 café generates two
  different requirement sets.

### App

- 10 screens, 4 components, Fluent 2 modern controls, auto-layout containers
  throughout.
- Upload via `EOM05-AppUpload` to the document library. The Attachments
  control is not used and is not present in the source.
- Named formulas over a bloated OnStart; OnStart reduced to telemetry and
  session state.
- Every query touching a high-volume list lives in `Delegation.fx`, filters
  `Reporting_Period_ID` first, and sorts on an indexed column.
- `scrDiagnostics` gated twice — a feature flag **and** `Developer_Flag` — and
  its `OnVisible` bounces anyone who reaches it another way.
- Maintenance and read-only modes: the app disables write affordances and
  `EOM-04` / `EOM-05` refuse independently. The disabled control is a
  courtesy; the flow check is the control.

### Flows

- `EOM-02` binds at **library** level. A folder-level trigger silently misses
  every folder created after the flow was authored, and Portfolio FY folders
  are created annually by people who do not know a flow exists.
- No flow has a path that creates an `MF_EOM_Item` from a file — asserted by
  a test, not by intention.
- `EOM-04` refuses a QC return without both a comment and a new suspense
  date, and writes the new date onto the item as well as the submission.
- Notifications ship disabled and log what they would have sent, so a full
  cycle can be inspected before anyone's inbox is involved.

### Validation

- `scripts/validate_solution.py` fails the build on: a delegation
  anti-pattern, a query reaching a high-volume list from outside
  `Delegation.fx`, a hard-coded URL, GUID or list-name string literal, a
  positive `TabIndex`, an interactive control with no `AccessibleLabel`, a
  soft-gated feature flag defaulting `True`, a stale `data-model.md`, or a
  flow that does not read its site from a parameter.
- `--reconcile-fact` compares the app's rows against `MF_EOM_Status` field by
  field, for every row rather than a sample.
- 82 tests in `tests/`, all passing.

### Known gaps

These are honest, not deferred quietly:

- **The PowerShell is unverified against a live tenant.** No PowerShell
  runtime was available where this was written, so the three scripts are
  reviewed source, not executed source. Run each with `-WhatIf` first.
- **Every tenant-side acceptance test is outstanding**, including all
  thirteen accessibility gates, RLS with two scopes, delegation at 5,000+
  rows, and index verification. `docs/DEPLOYMENT.md` carries the list.
- **No release ZIP.** `dist/` is empty of artifacts and says so.
- Requirement offsets are expressed in calendar days. `Due_Rule` records the
  intent (`EOM+5BD`) but business-day arithmetic is not implemented; if the
  programme needs true business days, that is a schema-compatible change to
  the engine and a `MINOR` release.
