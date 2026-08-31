# Government environment mode

**Settled. Do not re-derive.**

This solution targets a single Power Platform environment in a US
Government cloud. Two facts about that environment gate everything, and
neither changes the design — both change the deployment scripts.

---

## The two gating answers

| Question | Status | Where it is recorded |
|---|---|---|
| Which government cloud is this tenant in — GCC, GCC High, or DoD? | **UNKNOWN — confirm before provisioning** | `configuration/app_config.csv` key `TenantCloud` |
| May the build run PAC CLI against it? | **UNKNOWN — verify authorization** | `configuration/app_config.csv` key `PacCliAuthorized` |

Do not guess either one. `provisioning/Provision-MFOpsLists.ps1` refuses to
run until `TenantCloud` is set to a real value, because the SharePoint and
Graph endpoints differ per cloud and a script pointed at the commercial
endpoints from a GCC High tenant fails in ways that look like a permissions
problem.

### Endpoints by cloud

| | GCC | GCC High | DoD |
|---|---|---|---|
| SharePoint admin | `*-admin.sharepoint.com` | `*-admin.sharepoint.us` | `*-admin.dps.mil` |
| Graph | `graph.microsoft.com` | `graph.microsoft.us` | `dod-graph.microsoft.us` |
| Power Platform API | `api.gov.powerplatform.microsoft.us` | `api.high.powerplatform.microsoft.us` | `api.appsplatform.us` |
| PAC CLI `--cloud` | `UsGov` | `UsGovHigh` | `UsGovDod` |
| Login authority | `login.microsoftonline.com` | `login.microsoftonline.us` | `login.microsoftonline.us` |

### If PAC CLI is not authorized

Nothing in the design depends on it. The fallback path is fully supported:

* Lists are provisioned by `Provision-MFOpsLists.ps1` over PnP PowerShell or,
  if PnP is also unavailable, by the REST payloads the same script emits with
  `-EmitRestOnly`.
* The canvas app is authored in the maker portal and exported as an `.msapp`,
  which is unpacked to `.pa.yaml` by `pac canvas unpack` **or** by the Power
  Apps Language Tooling in any environment that has it — including a
  developer workstation outside the tenant, because unpacking is an offline
  operation on the exported file.
* The solution ZIP is exported from the maker portal and committed to
  `dist/`.

**The YAML is the code.** The `.msapp` and the solution ZIP are build
artifacts. If the two ever disagree, the YAML wins and the artifact is
rebuilt.

---

## Capability gate register

Verify each gate before build step 1 and record the result in
`MF_App_Config`. **Stop the build if any of the first five is red.**

| # | Capability | Required for | Gate | If unavailable |
|---|---|---|---|---|
| 1 | SharePoint Online, custom list creation | everything | **HARD** | Stop. No fallback. |
| 2 | SharePoint document library, versioning on | evidence storage | **HARD** | Stop. |
| 3 | Power Apps canvas apps | the app | **HARD** | Stop. |
| 4 | Power Automate, SharePoint connector | all five flows | **HARD** | Stop. |
| 5 | Entra ID, `Office365Users` connector | identity, no sign-in screen | **HARD** | Stop. |
| 6 | Power BI service, gov region | the COP | soft | App still correct; COP deferred. `MF_EOM_Status` still written. |
| 7 | Office 365 Outlook connector | EOM-04 notifications | soft | Flag `EnableNotifications` False. Log rows still written. |
| 8 | Power Apps modern (Fluent 2) controls | UI | soft | Classic controls with the same accessible names. Record as a variance. |
| 9 | AI Builder | tier 3 classification | soft | Flag `EnableAIBuilder` **ships False**. Never a dependency. |
| 10 | Premium connectors / Dataverse | nothing in R1 | n/a | Not used. R1 is standard-connector only. |
| 11 | Power Platform Pipelines | nothing | n/a | **Not used by design.** Releases are ZIP + tag. |
| 12 | Custom connectors | nothing in R1 | n/a | Not used. |
| 13 | Power Apps Component Framework | nothing in R1 | n/a | Out of scope. |
| 14 | Teams embedding | convenience | soft | App runs in browser. |

Gate 9 deserves restating: **AI Builder must never become a dependency whose
availability could block the app.** It is behind `EnableAIBuilder`, which
ships `False`, and the code path behind it is absent from R1 entirely.

### Recording the result

```powershell
pwsh provisioning/Verify-MFOpsCapabilities.ps1 -TenantCloud UsGovHigh -Verbose
```

Writes one `MF_App_Config` row per gate, keyed `Capability.<n>.<name>`, with
`Config_Value` of `GREEN`, `SOFT_FAIL` or `RED`, plus the date and the
identity that verified it. A `Requires_Capability` value on a feature flag
names one of these keys; the app refuses to honour a flag whose capability
gate is not GREEN.

---

## Single-environment safety

There is one environment. Dev, test and production are the same tenant, the
same lists and the same app. That is not an ideal to be argued with; it is
the constraint, and it is handled as a first-class feature rather than by
convention.

### Kill switch

Two config keys, read at app start and re-read on every navigation:

| Key | Effect |
|---|---|
| `MaintenanceMode` = `true` | Every user except Developer_Flag holders lands on `scrMaintenance`. No data source is opened. |
| `ReadOnlyMode` = `true` | The app loads normally, all write affordances are disabled and visibly labelled, and the upload and QC flows refuse to run. |

`ReadOnlyMode` is enforced twice: the controls disable, **and** the flows
check the same key before writing. A disabled button is a courtesy; the flow
check is the control.

Turning either on requires no deployment. That is the point.

### Developer and tester surfaces

`Developer_Flag` and `Tester_Flag` live on `MF_Security_Mapping` and are
never granted by a role. `Developer_Flag` unlocks `scrDiagnostics`, which
shows the resolved config, the capability register, the last twenty
telemetry rows and the delegation warnings for the current screen.
`Tester_Flag` allows a user to receive flags scoped to testers without
altering the production default.

A normal user must not be able to reach `scrDiagnostics` by any navigation,
deep link or keyboard route. This is an acceptance test.

### Feature flags

Every capability outside the R1 core is behind a flag with a `False`
default. The default is what the app uses if `MF_Feature_Flags` is
unreachable — so an outage never turns an optional dependency on.

| Flag | Ships | Gate |
|---|:-:|---|
| `EnableDocumentContentAI` | `False` | Capability 9 |
| `EnableAIBuilder` | `False` | Capability 9 |
| `EnableNotifications` | `False` | Capability 7 |
| `EnablePowerBIEmbed` | `False` | Capability 6 |
| `EnableUnmatchedQueue` | `True` | Capability 4 |
| `EnableAppUpload` | `True` | Capability 4 |
| `EnableFolderDropIntake` | `True` | Capability 4 |
| `EnableDiagnosticsScreen` | `True` | — (still requires `Developer_Flag`) |
| `EnableEOYModule` | `True` | — |

---

## No hard-coded URLs, site GUIDs or list names

Anywhere. Not in Power Fx, not in a flow, not in a script.

* The app's SharePoint connections are added by name at author time; the
  **site path and library path** come from `MF_App_Config`
  (`SiteUrl`, `EvidenceLibraryPath`, `PortfolioRootPath`).
* Flows read the same keys from `MF_App_Config` in their first action.
* `provisioning/*.ps1` take the site URL as a parameter and never default it.
* `scripts/validate_solution.py` greps the whole tree for
  `https://*.sharepoint.*`, bare GUIDs and literal `MF_` list names outside
  `scripts/eom_schema.py` and fails the build on a hit.

The one unavoidable exception is the connection reference in the exported
solution, which carries an environment-specific id. It is parameterised in
`solution/src/Other/Customizations.xml` and supplied at import time by a
deployment settings file, never edited in place.

---

## Releases and rollback

No Pipelines. Semantic versions, packaged, tagged and reversible.

```
v<MAJOR>.<MINOR>.<PATCH>

MAJOR  a schema change that requires a provisioning run
MINOR  a screen, flow or requirement change
PATCH  a fix with no schema or contract change
```

Each release:

1. `python3 scripts/eom_schema.py --validate && python3 scripts/validate_solution.py`
2. `bash tests/run_tests.sh`
3. Export the solution as **managed** for production, **unmanaged** for the
   source of truth. Commit the unpacked YAML; commit the managed ZIP to
   `dist/MissionFeedingOperations_v<version>.zip`.
4. Update `CHANGELOG.md`.
5. `git tag -a v<version>`.

**Rollback is importing the previous ZIP from `dist/`.** It is tested as
part of the release, not assumed. A rollback across a MAJOR boundary
requires the matching provisioning run and is documented per release in the
CHANGELOG; there is no automatic down-migration and none is pretended.

Schema changes are additive only within a MAJOR version. A column is
retired by setting it unused and documenting it, never by deletion —
deleting a SharePoint column destroys its data irreversibly.
