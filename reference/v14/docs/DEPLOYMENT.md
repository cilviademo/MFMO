# Deployment

**Read this first:** nothing in this repo has been imported into a Power
Platform environment. The canvas app source, flow specs and solution structure
follow current Power Platform conventions, but Microsoft has been changing the
canvas packing workflow and older `pac canvas pack` commands are being
deprecated.

**Therefore: this repo is the source of truth for the design, and the DEV
environment is the source of truth for the package.** Build in DEV against these
specs, export through `pac`, commit the result to `dist/`. Do not treat a
hand-authored `.msapp` as authoritative.

---

## 0. Prerequisites

- Power Platform DEV environment with a Dataverse database
- **Confirm you can import a solution.** Some DAF tenants restrict solution
  import to environment admins. Find out before building.
- **Confirm premium connector licensing.** SharePoint and Office 365 Users are
  standard; scheduled flows in a solution generally are not a licensing problem,
  but confirm for your tenant.
- PnP.PowerShell, and `pac` (Power Platform CLI)
- GCC High: `Connect-PnPOnline -AzureEnvironment USGovernmentHigh`

## 1. Provision the lists

```powershell
.\provisioning\Provision-MFOpsLists.ps1 -SiteUrl "https://<tenant>.sharepoint.us/sites/<site>"
```

Idempotent. Creates eight lists, adds columns, sets indexes.

**Indexes are not optional.** `MF EOM Item` crosses 5,000 rows inside a year and
you cannot index a list after it passes the threshold without admin help.

## 2. Seed configuration

Import `configuration/requirements.csv` into **MF EOM Requirement**.

Twelve rows, all `Authority_Status = UNVERIFIED`, three seeded inactive. That is
deliberate: an unconfirmed requirement generates an item and shows a drop box,
but never drives a Red status. Activate rows as AFSVC confirms applicability.

Then populate **MF Installation**, **MF Facility** and **MF Security Mapping**
from your real roster. `Operating_Model` goes on the facility, not the
installation.

## 3. Build in DEV

1. Create the solution `MissionFeedingOperations`
2. Add the environment variables from
   `configuration/environment-variables.json`
3. Add the connection references from
   `configuration/connection-references.json`
4. Create the canvas app `MF Operations`; build the seven screens per
   `canvas-app/screens/README.md`, the components per
   `canvas-app/components/README.md`, and paste the Power Fx from
   `canvas-app/formulas/`
5. Build the four flows per `flows/*/definition.md`
6. **Leave `MF_NotificationsEnabled` FALSE.**

## 4. Export

```
pac auth create --environment <DEV>
pac solution export --path ./dist --name MissionFeedingOperations --managed false
pac solution unpack --zipfile ./dist/MissionFeedingOperations.zip \
    --folder ./solution/MissionFeedingOperations --processCanvasApps
```

Commit the unpacked source. That round trip — build in DEV, export, unpack,
commit — is what makes the repo authoritative going forward.

## 5. Import to TEST

```
Power Apps → Solutions → Import → MissionFeedingOperations.zip
```

Map at import: the SharePoint connection, the connection references, and every
environment variable. Nothing is hard-coded, so DEV/TEST/PROD differ only in
these values.

---

## Acceptance tests

Run all of these in TEST before anyone sees it.

**Generation**
- [ ] EOM-01 creates facility-scope items for every matching facility
- [ ] Installation-scope items have `Facility_ID` **null**, not empty string
- [ ] Contract-scope items carry `Contract_ID` and null `Facility_ID`
- [ ] Re-running EOM-01 for the same period changes no row count
- [ ] A facility whose model doesn't match a requirement gets no item
- [ ] An installation with a legacy DFAC and a Food 2.0 cafe generates both
      requirement sets

**Upload**
- [ ] A DFAC manager with one facility sees no dropdowns
- [ ] A manager with two facilities sees a facility dropdown only
- [ ] Requirements filter by the **facility's** operating model
- [ ] A file with an arbitrary name uploads and classifies correctly
- [ ] Resubmission creates v2, sets v1 `Is_Current = false`, keeps both files
- [ ] "On behalf of" is visible only to MFM/PM/Admin and records the target

**QC**
- [ ] Accept sets `Status_Code = 3` on the item
- [ ] Correction Required without a comment is blocked
- [ ] Correction Required without a suspense date is blocked
- [ ] Wrong Document sets `Status_Code = 1`
- [ ] Every QC action writes an audit row

**Status**
- [ ] Not received, before suspense → 0 Gray, not Red
- [ ] Not received, after suspense → 1 Red
- [ ] Unverified requirement, not received, after suspense → **0 Gray**
- [ ] Facility package rolls up correctly
- [ ] Installation package includes installation- and contract-scope items
- [ ] Power BI `Status_Code` matches the app for the same row

**Security**
- [ ] DFAC manager sees only their facility
- [ ] MFM sees their installation
- [ ] Portfolio Manager sees their portfolio and can QC
- [ ] DFAC manager cannot see the QC controls
- [ ] Non-admin cannot open the requirements admin screen

**Intake**
- [ ] A file dropped directly in the FY folder lands in Needs Classification
- [ ] A file uploaded via the app does **not** create an unmatched row
- [ ] Classifying an unmatched file creates a real submission

**Notifications**
- [ ] With the flag FALSE, intended sends are logged and nothing mails
- [ ] Digest format: one message per recipient, not per item

## Known open items

- Requirement applicability is UNVERIFIED across the board. SIK and SF 1080
  scope in particular (installation vs facility) is a configuration value, not a
  code change — that was the point of `Requirement_Scope`.
- No content-based classification. Not needed while the app is the front door.
- No backfill. Tracking starts fresh next month by decision.
- Facility-level requirement waivers exist on the item but have no admin UI yet.

---

## Government single-environment addendum

If the tenant grants one environment, read `docs/government-environment-mode.md`
before step 3. Publishing is deploying. Additional gates:

- [ ] `MF_App_Config` and `MF_Feature_Flags` seeded before the first publish
- [ ] `MaintenanceMode` toggles and locks non-developers out
- [ ] `ReadOnlyMode` blocks writes while status stays visible
- [ ] A flag with `Enabled_Prod = FALSE, Enabled_Testers = TRUE` is invisible to
      a normal user and visible to a tester
- [ ] `Developer_Flag` reveals `scrDiagnostics`; nobody else can reach it
- [ ] Telemetry writes on open, upload and QC, stamped with `App_Version`
- [ ] `dist/` holds the tagged release and CHANGELOG before you publish
- [ ] Rollback rehearsed: import the prior release ZIP and confirm it works

If environment variables are unavailable, confirm every value resolves from
`MF_App_Config` instead. Neither path may be load-bearing alone.
