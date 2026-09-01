# Government environment compatibility mode

The solution must not require Managed Environments, Power Platform Pipelines,
premium or custom connectors, AI Builder, PCF components, service principals,
app registrations, the HTTP or Graph connectors, Dataverse, or more than one
Power Platform environment.

It must deploy into a **single government production environment** by manual
solution import, or by PAC CLI where the tenant authorizes it.

---

## The cloud is DoD. It is not GCC High.

The SharePoint tenant is `usaf.dps.mil` and Teams resolves to
`dod.teams.microsoft.us`. That is the **DoD** cloud.

This was open for most of the programme and several documents guessed GCC High
while it was. **Every GCC High endpoint in a document dated before 31 Aug 2026
is wrong for this deployment.** The table below is kept complete because the
solution supports all three clouds and hard-codes none — but only one column
applies here.

```
Maker   make.apps.appsplatform.us
Flow    flow.appsplatform.us
Admin   admin.appsplatform.us
```

**Confirm the Power Platform environment sits in the same tenant as the
SharePoint sites.** Same cloud does not guarantee same tenant, and a
cross-tenant connection fails in a way that reads like a permissions problem
for a week.

### One answer still gates the build

| Question | Status | Recorded in |
|---|---|---|
| Which government cloud? | **DoD** — `UsGovDod` | `MF_App_Config.TenantCloud` |
| May the build run PAC CLI against the tenant? | **UNKNOWN — verify** | `MF_App_Config.PacCliAuthorized` |

Neither changes the design; both change the deployment scripts.
`Provision-MFOpsLists.ps1` takes the cloud as a mandatory parameter for exactly
this reason: a script pointed at the wrong cloud's endpoints fails in ways that
look like a permissions problem.

Microsoft supports PAC CLI in GCC, GCC High and DoD. **Local governance may
still forbid it**, and Microsoft availability does not equal local DAF
authorization.

### Endpoints by cloud — the DoD column is the one that applies

| | GCC | GCC High | DoD |
|---|---|---|---|
| SharePoint admin | `*-admin.sharepoint.com` | `*-admin.sharepoint.us` | `*-admin.dps.mil` | <!-- prerelease: allow CLD-03 the endpoint table IS the policy that forbids the commercial host -->
| Power Platform API | `api.gov.powerplatform.microsoft.us` | `api.high.powerplatform.microsoft.us` | `api.appsplatform.us` |
| PAC CLI `--cloud` | `UsGov` | `UsGovHigh` | **`UsGovDod`** |
| PnP `-AzureEnvironment` | `USGovernment` | `USGovernmentHigh` | **`USGovernmentDoD`** |
| Login authority | `login.microsoftonline.com` | `login.microsoftonline.us` | `login.microsoftonline.us` |

### If PAC CLI is not authorized

Nothing in the design depends on it.

* Lists are provisioned by `Provision-MFOpsLists.ps1` over PnP PowerShell, or
  by the REST payloads the same script emits with `-EmitRestOnly`.
* The app is authored in the maker portal and exported as an `.msapp`, which is
  unpacked to `.pa.yaml` on any workstation — unpacking is an offline operation
  on the exported file and does not touch the tenant.
* The solution ZIP is exported from the maker portal and committed to `dist/`.

**The `.pa.yaml` is the code.** The `.msapp` and the solution ZIP are build
artifacts. If they ever disagree, the YAML wins and the artifact is rebuilt.

---

## Why single-environment safety is a design constraint, not a caveat

Federal Power Platform tenants commonly grant one environment for everything —
apps, flows, Dataverse, agents — with no DEV or TEST tier. **Publishing *is*
deploying.** Every safety mechanism has to live inside the app.

That is why this repo contains `MF_App_Config`, `MF_Feature_Flags`,
`MF_App_Event_Log` and `Developer_Flag` / `Tester_Flag`. They are not
nice-to-haves; they are the substitute for an environment tier.

| Constraint | Our mechanism |
|---|---|
| No DEV environment | `Developer_Flag` + feature flags |
| No staged release | `Enabled_Testers` → `Enabled_Prod` |
| No rollback pipeline | Packaged semantic releases in `dist/` |
| Publishing is deploying | `MaintenanceMode` / `ReadOnlyMode` kill switch |
| No environment monitoring | `MF_App_Event_Log` |
| Two builds in one app | `App_Version` stamped on every event |

**Do not copy the common workaround** of hand-renaming old and new screens.
Ship both behind a flag and flip a checkbox.

---

## Capability gate register

Nothing below is assumed. Each is verified against **this tenant** — new
connectors are disabled by default in GCC High and DoD until an administrator
reviews them.

```powershell
pwsh provisioning/Verify-MFOpsCapabilities.ps1 -SiteUrl <site> -TenantCloud <cloud>
```

Writes one `MF_App_Config` row per gate, keyed `Capability.<Name>`, and throws
if any blocker is unavailable.

| Capability | MVP dependency | If unavailable |
|---|---|---|
| SharePoint Online connector | **Yes** | **Blocker.** Stop. |
| Power Apps canvas | **Yes** | **Blocker.** Stop. |
| Power Automate | **Yes** | **Blocker.** Stop. |
| Power BI, gov endpoint | **Yes** | **Blocker.** Confirm the service URL. |
| Office 365 Users connector | Preferred | Fallback: UPN text only |
| Solutions | Preferred | Fallback: unmanaged component export |
| PAC CLI | No | Fallback: manual export |
| Environment variables | Preferred | Fallback: `MF_App_Config` rows |
| Fluent 2 modern controls | Preferred | Fallback: classic, recorded as a variance |
| AI Builder | **No** | Feature-flagged tier 3 only. Ships `False`. |
| PCF / Creator Kit | **No** | Native modern controls first |
| Code Apps | **No** | Requires admin enablement |
| Custom connectors | **No** | Not used |
| HTTP / Graph | **No** | Not used |
| Dataverse | **No** | Not used |
| Power Platform Pipelines | **No** | **Not used by design.** Requires Managed Environments and premium licensing. |

AI Builder deserves restating: **it must never become a dependency whose
availability could block the app.** It is behind `EOM_AI_BUILDER`, which ships
`Enabled_Prod FALSE` and `Enabled_Testers FALSE`, and the code path behind it
is absent from R1 entirely.

If environment variables are unavailable, every value in
`configuration/environment-variables.json` has a matching `MF_App_Config` row.
The app reads config first and falls back to the variable, **so neither path is
load-bearing alone.**

---

## Kill switch

Two config keys, read as named formulas so they re-evaluate rather than going
stale in an OnStart:

| Key | Effect |
|---|---|
| `MaintenanceMode` = `True` | Everyone except developers and admins lands on `scrMaintenance`, before any business data source is opened |
| `ReadOnlyMode` = `True` | The app loads, every write affordance is disabled and visibly labelled, and EOM-04 and EOM-02 refuse to write |

`ReadOnlyMode` matters more than it looks. When something is wrong but not
broken, people still need to see where their package stands. Locking writes
while leaving status readable is far safer than pulling the app.

Both are enforced twice — the disabled control is a courtesy; **the flow check
is the control.** Both default `False` in the app's fallback, so a
configuration outage neither locks everyone out nor silently unlocks writes.

Turning either on requires no deployment. That is the point.

## Developer and tester surfaces

`Developer_Flag` and `Tester_Flag` live on `MF_Security_Mapping` and are never
granted by a role. `Developer_Flag` unlocks `scrDiagnostics` — the resolved
config, the capability register, the configuration health checks, the flag
resolution and the last twenty events. `Tester_Flag` lets a user see
`Enabled_Testers` features without altering the production default.

`scrDiagnostics` is gated twice: the flag **and** `Developer_Flag`. A normal
user must not reach it by any navigation, deep link or keyboard route. This is
an acceptance test.

---

## No hard-coded URLs, site GUIDs or list names

Anywhere. Not in Power Fx, not in a flow spec, not in a script.

* The app's site and library paths come from environment variables, with
  `MF_App_Config` as the fallback.
* Flows read the same keys in their first action.
* `provisioning/*.ps1` take the site URL as a mandatory parameter and never
  default it.
* `scripts/validate_solution.py` greps the tree for `https://*.sharepoint.*`,
  bare GUIDs and list names as string literals, and fails the build on a hit.

The unavoidable exception is the connection reference in the exported solution,
which carries an environment-specific id. It is parameterised in
`configuration/connection-references.json` and supplied at import time, never
edited in place.

---

## Release discipline

No Pipelines. Semantic versions, packaged, tagged and reversible.

```
v0.1.0  scaffold
v0.2.0  requirement engine
v0.3.0  facility security
v0.4.0  document ingestion
v0.5.0  QC workflow
v0.6.0  reconciled build (this one)
v0.9.0  UAT
v1.0.0  operational release
```

Every release produces `dist/MissionFeedingOperations_vX.Y.Z.zip`, a
`CHANGELOG.md` entry, and the deployment settings for that environment.
**Canonical source lives in this repo, not inside Power Apps.** Even if the
tenant forces an import-as-new-app pattern, any release can be recreated
exactly.

Export daily during active development.

**Rollback is importing the previous ZIP from `dist/`,** and it is tested as
part of the release rather than assumed. A rollback across a schema change
needs the matching provisioning run and is documented per release; there is no
automatic down-migration and none is pretended. Schema changes are additive —
a retired column is marked unused, never deleted, because deleting a SharePoint
column destroys its data irreversibly.

**Do not promise zero-touch deployment.** Tenant-specific SharePoint rebinding
after import is a real manual step and `docs/DEPLOYMENT.md` says so.
