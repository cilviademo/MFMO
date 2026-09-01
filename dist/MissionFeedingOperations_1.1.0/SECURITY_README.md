# Security verification — Phase 5

`scripts/prerelease_scan.py` returns **PASS**, 0 failures, 3 warnings. Below are
the checks the scanner cannot make, done by hand, plus what the warnings are.

**This checks the PACKAGE. It says nothing about the tenant.** DLP, tenant
isolation, Conditional Access, SharePoint permissions, Purview retention, the
records schedule, privacy review, STIG applicability and RMF authorisation are
all deployment-side. **Import success is not authorisation to operate.**

## The scan

```
30 content rules + 11 manifest assertions + 7 required-artifact checks
PASS — no blocking findings. 3 warning(s).
```

All 11 manifest assertions verified true against the repository.

The three warnings are `IDN-01` on `configuration/security-mapping.sample.csv`
— placeholder accounts at `example.mil` in a file named `.sample`. They are
warnings by design: the file exists to be loaded into a test tenant with
`-IncludeSampleData`, and the scan's job is to make sure nobody forgets that.
They must not reach production, and `Seed-MFOpsConfiguration.ps1` prints a
warning before loading them.

One inline exception is in force and is reported on every run:

```
[CLD-03] docs/government-environment-mode.md
         the endpoint table IS the policy that forbids the commercial host
```

Every inline exception now requires a reason string of substance; an
unexplained one fails the scan as `EXC-01`.

## Manual checks

| Check | Result | Evidence |
|---|---|---|
| No commercial endpoint anywhere | PASS | zero matches for the commercial Power Apps, Flow, SharePoint, Power BI, Azure Websites or Graph hosts across every `.fx`, `.yaml`, `.json`, `.csv`, `.ps1`, `.xml` |
| Cloud is DoD, not GCC High | PASS | `MF_App_Config.TenantCloud = UsGovDod`; `cloud.target: DOD` in the manifest |
| Every environment-specific value is an environment variable | PASS | 18 variables, **every one with a blank default** |
| No hardcoded destination | PASS | all four `Site_URL` blank; `URL-01` now watches `.dps.mil` as well as `.sharepoint.us` |
| Connectors limited to the allowlist | **FIXED** | see below |
| Each conditional connector degrades gracefully | PASS | every conditional entry declares a fallback, checked by test |
| No stale connection reference | **FIXED** | see below |
| Dev, mock, debug, role-simulator and AI flags all FALSE | PASS | `EOM_AI_BUILDER`, `EnableAIBuilder`, `EnableDocumentContentAI`, `EOM_WAIVERS` all FALSE; `MaintenanceMode` and `ReadOnlyMode` False; no mock or role-simulator flag exists |
| Developer flag cannot be self-assigned | PASS | `Developer_Flag` lives in `MF_Security_Mapping` and is patched by no screen |
| No screen writes a role, scope or capability | PASS | zero patch sites for `Role`, `Scope_Type`, `Can_QC`, `Can_Grant_Access`, `Grant_Scope`, `Active_Flag`, `Expires_Date` |
| Manifest claims match reality | **ONE CORRECTED** | see below |
| Required artifacts exist **and are non-empty** | PASS | 7 artifacts, smallest 1,760 bytes, threshold 200 |

## Two things fixed

**A stale Teams connection reference.** `connection-references.json` declared
four connectors; `shared_teams` was on none of the allowlist's three lists and
nothing in the build used it — notifications are Outlook, and escalation is a
notification rule rather than a Teams post. It is removed.

An unused connection reference is not free. It prompts at import, it needs its
own DLP conversation with the tenant admin, and it widens the app's declared
surface for no behaviour. `tests/test_hardening.py` now fails if a declared
connector is not on the allowlist.

**One manifest claim was stronger than the deployment.** The manifest carried
`user_may_edit_audit_author: false`. The app writes `Actor_UPN` and
`Uploaded_By` as `User().Email`, which Power Apps derives from the signed-in
session and which a user **cannot forge from inside the app** — but nothing
stops a user with direct write access to `MF_EOM_Audit` from setting it to
anything.

That is the same gap as installation scope, on the same lists, and it closes
the same way. The manifest now says both things separately:

```
audit_author_is_authenticated_identity: true
audit_author_enforced_at_data_layer:    false
```

Claiming a control the deployment does not have is worse than recording the
gap, because the gap then never gets closed.

## The open issue is still open

`docs/security-open-issue.md`. **The data layer does not enforce installation
scope.** `security-manifest.yaml` carries
`data_layer_permissions_verified: false`, and it stays false until a
SharePoint-side change is made.

It is **narrowed, not closed**: the four portfolios turned out to be four
separate site collections, so a portfolio boundary is now a site boundary that
SharePoint enforces natively. What remains is installation scope *within* a
portfolio site.

```
portfolio_boundary_enforced_by_site:       true
installation_scope_enforced_at_data_layer: false
```

Nothing in this pass closed it in documentation. It cannot be closed in
documentation.
