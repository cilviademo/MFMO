# Government Environment Compatibility Mode

The solution must not require Managed Environments, Power Platform Pipelines,
premium or custom connectors, AI Builder, PCF components, service principals,
app registrations, the HTTP or Graph connectors, Dataverse, or more than one
Power Platform environment.

It must deploy into a **single GCC/GCC High production environment** by manual
solution import, or by PAC CLI where the tenant authorizes it.

---

## Why this is a design constraint, not a caveat

Federal Power Platform tenants commonly grant one environment for everything —
apps, flows, Dataverse, agents — with no DEV or TEST tier. Publishing *is*
deploying. Every safety mechanism has to live inside the app.

That is why this repo contains `MF_App_Config`, `MF_Feature_Flags`,
`MF_App_Event_Log` and `Developer_Flag`/`Tester_Flag`. They are not
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

Nothing below is assumed. Each is verified against **this tenant**, not against
Microsoft's published availability — new connectors are disabled by default in
GCC High and DoD until an administrator reviews them.

| Capability | MVP dependency | Status | Action |
|---|---|---|---|
| SharePoint Online connector | **Yes** | Verify | Blocker if absent |
| Power Apps canvas | **Yes** | Verify | Blocker if absent |
| Power Automate | **Yes** | Verify | Blocker if absent |
| Power BI (gov endpoint) | **Yes** | Likely core | Confirm service URL |
| Office 365 Users connector | Yes | Verify | Fallback: UPN text only |
| Solutions | Preferred | Verify | Fallback: unmanaged component export |
| PAC CLI | No | Verify authorization | Fallback: manual export |
| Environment variables | Preferred | Verify | Fallback: `MF_App_Config` rows |
| AI Builder | **No** | Verify | Feature-flagged tier 2 only |
| PCF / Creator Kit | **No** | Avoid initially | Native modern controls first |
| Code Apps | **No** | Future | Requires admin enablement |
| Custom connectors | **No** | Avoid | — |
| HTTP / Graph | **No** | Avoid | — |
| Dataverse | **No** | Not used | — |
| Power Platform Pipelines | **No** | Avoid | Requires Managed Environments + premium licensing |

If environment variables are unavailable, every value in
`configuration/environment-variables.json` has a matching `MF_App_Config` row.
The app reads config first and falls back to the variable, so neither path is
load-bearing alone.

**Two questions to answer before the final deployment scripts are written:**
are you in GCC High or DoD, and are you permitted to run PAC CLI against the
tenant? Microsoft supports PAC CLI in GCC and GCC High, but local governance may
still forbid it.

---

## Kill switch

`MF_App_Config` carries:

```
MaintenanceMode        False    App locked except developers and admins
ReadOnlyMode           False    Status visible, no writes accepted
CurrentAppVersion      0.5.0
OpenReportingPeriod    2026-08
SupportMessage                  Shown on the maintenance screen
MinimumSupportedVersion 0.4.0
CurrentFiscalYear      FY2027
EnableAIBuilder        False
EnableDocumentContentAI False
RequireQC              True
```

`ReadOnlyMode` matters more than it looks. When something is wrong but not
broken, people still need to see where their package stands. Locking writes
while leaving the COP readable is far safer than pulling the app.

---

## Release discipline

```
v0.1.0  scaffold
v0.2.0  requirement engine
v0.3.0  facility security
v0.4.0  document ingestion
v0.5.0  QC workflow
v0.9.0  UAT
v1.0.0  operational release
```

Every release produces `dist/MissionFeedingOperations_vX.Y.Z.zip`,
`CHANGELOG.md`, and `deployment-config.json`. Canonical source lives in this
repo, not inside Power Apps. Even if the tenant forces an import-as-new-app
pattern, any release can be recreated exactly.

Export daily during active development. `.pa.yaml` is the code; the `.msapp`
and the solution ZIP are build artifacts.
