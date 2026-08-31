> **ARCHIVED 31 Aug 2026. Superseded by `reference/v14/CLAUDE_CODE_HANDOFF.md`
> and, above it, `reference/v14/ACTION_DOCUMENT.md`.**
>
> Two of its statements are now known wrong and must not be followed:
>
> * It records the tenant cloud as "UNKNOWN — GCC High or DoD". It is **DoD**
>   (`usaf.dps.mil` / `dod.teams.microsoft.us`).
> * It describes "one Teams site, four portfolio channels, access granted at
>   the channel". The four portfolios are **four separate SharePoint site
>   collections**. See `deployment/site-bindings.md`.
>
> Kept because its statement of the data-layer scope problem is the clearest
> written anywhere, and `docs/security-open-issue.md` descends from it.

# CLAUDE CODE HANDOFF — Mission Feeding Operations

**Repo:** `mission-feeding-operations-v10.zip`
**Date:** 31 Aug 2026
**Supersedes:** everything before it. Where a document in this repo disagrees
with this file, this file wins.

---

## BUILD STATE

```
Schema                     15 SharePoint lists, 212 columns
Requirements               13 rows, 8 active, authority and scope tracked apart
Registry                   103 installations, 154 facilities, seeded from the QRG
R1 scope                   43 installations, 67 Legacy facilities
Status engine              6 visual states, one evaluation, action ownership
Suspense                   5 calendar days + 10th, nominal and effective dates
Security scan              PASS, 0 warnings
Power Platform build       NOT STARTED
Solution import tested     NO — verify you are permitted before building
PAC CLI authorised         UNKNOWN
Tenant cloud               UNKNOWN — GCC High or DoD
Data-layer permissions     NOT ENFORCED — see the blocker below
```

---

## THE BLOCKER — read before anything else

**The app's installation scope is presentational until SharePoint enforces it.**

Power Apps `Visible` and `Filter()` are not access control. Microsoft is
explicit: hiding a record in the app does not remove the user's permission to
the underlying data.

The confirmed structure is one Teams site, four portfolio channels, access
granted at the channel. Every base user who can reach a portfolio channel can
reach every other installation's documents in it — through Teams, SharePoint,
Explorer sync, any client. The app will show a Lackland manager only Lackland.
SharePoint will still serve them Creech's 1119.

`security/security-manifest.yaml` carries `data_layer_permissions_verified:
false` and it stays false until this is closed. Three options and a
recommendation are in `docs/security-open-issue.md`.

**This does not block the build.** Every app-layer control is correct
regardless. It is a deployment dependency to raise with the SharePoint
administrator now, so it is resolved before the pilot rather than during the
ISSM review.

---

## WHAT CHANGED IN THE LAST FIVE ITERATIONS

### 1. The requirement set is real and sourced

From the AFSVC *End of Month/Year Procedures* deck, Required Documents slide.
Eleven of thirteen rows now carry citations.

| Code | Scope | Confidence | Frequency |
|---|---|---|---|
| 1119 | Facility | **High** | Monthly |
| 1119-1 (Field feeding) | Facility | Medium | **Conditional** |
| SF 1080 | Installation | **Proposed** | Monthly |
| SAIIT | Facility | **High** | Monthly |
| GPC Bank Statement | Installation | **Proposed** | Monthly |
| 1038 | Installation | **Low** | Quarterly |
| EOY MFR | Facility | Medium | Annual, Sep |
| EOY inventory last page | Facility | Medium | Annual, Sep |

**SIK is retired** — absent from the authoritative list, kept inactive as a
record of the decision. DAF Form 79 likewise.

**The 1119-1 is field feeding, not a 1119 continuation.** It is seeded
`Conditional`, `Required_Flag = FALSE`, and **EOM-01 must not generate it**.
Auto-generating it would put a permanent red row on every DFAC that ran no field
feeding — the exact false-overdue that teaches people to ignore a dashboard. The
base or reviewer adds it when it applies.

**Authority and scope are separate columns.** The deck confirms which documents
exist. It says nothing about the grain each is filed at. `Authority_Status`
answers the first; `Scope_Confidence` and `Scope_Basis` answer the second.
Marking a scope guess VERIFIED because the document is verified turns a proposal
into policy by accident.

### 2. Two suspense dates, four date fields

**5 calendar days after month end, final call the 10th.** CALENDAR is the
baseline — the source says "within 5 days" and never says duty days.

The two have different standing: the 5 days is VERIFIED from procedure language,
the 10th is a **MANAGEMENT_RULE** from the programme. Labelling the 10th as
source-verified would be a small lie that becomes load-bearing the first time
someone challenges it.

Every item carries `Nominal_Due_Date`, `Effective_Due_Date`,
`Nominal_Final_Call_Date`, `Effective_Final_Call_Date`, with
`NonDutyDay_Policy = NEXT_DUTY_DAY` resolved against `MF_Non_Duty_Day`.

**Status evaluation always uses effective dates. Reporting uses nominal.**
Leadership sees "the 5th"; the base sees `Due 5 Sep (Mon 8 Sep)`.

### 3. Six status states, and colour carries ownership

```
Blue    Not due — submission window open        nobody acts yet
Amber   Late — past initial, before final call  BASE acts, has runway
Red     Overdue, or returned for correction     BASE acts, out of runway
Yellow  Awaiting AFSVC review                   AFSVC acts
Green   Accepted                                done
Gray    Not required this period                nothing
```

**Amber and yellow must be different hues.** The Figma build maps both to the
same amber, which tells a DFAC manager that a document they filed on time and
one they never sent are the same kind of problem. Amber means time risk; yellow
means somebody else has it.

Six is the ceiling. A seventh stops being scannable.

**One engine, one evaluation.** `itemStatus()` returns
`{status, code, label, actionOwner, actionRequired}` in a single pass. Never
write a second function that derives the label independently — that is how a
status engine starts lying.

**Rollups run over semantic statuses, never colour codes.**
`[ACCEPTED, NOT_DUE, NOT_DUE]` is IN PROGRESS, not Complete. And rollups compute
over what the viewer may see — a facility user must not receive an installation
figure derived from their neighbours.

**Wrong document is not permanently red.** It means the requirement is unmet;
urgency depends on the suspense. Before the final call it is NOT_SATISFIED
(amber), after it is OVERDUE (red). A submission-level QC verdict never becomes
the parent item's status directly.

### 4. Registry seeded from the real QRG

`configuration/installations.csv` · `facilities.csv` · `qrg-data-quality.csv`,
generated by `scripts/gen_registry.py` from `data/QRG__Scrubbed_.csv`.

**261 rows is not 261 facilities.** 107 rows are byte-identical duplicates —
Fairchild's Ross DFAC four times, Andersen's DFAC three times. Deduplicated:
**154 facilities across 103 installations.**

**R1 scope is 43 installations and 67 facilities.** Only 43 have any Legacy row.

**Four bases are split into two installation strings** by program —
`MINOT AFB (2.0)` / `MINOT AFB (MAF)`, same at Malmstrom and FE Warren, plus
`EGLIN AFB (2.0)`. The generator normalises them to one physical installation
and keeps both source strings in `Source_Installation_String`.

That split is the enterprise encoding "one base, two operating models" into the
installation name because the QRG has nowhere else to put it.
`MF_Facility.Operating_Model` is that place. It is also why the file appears to
show zero installations with mixed feeding types when the enterprise plainly has
them.

**Six joint bases are stored surname-first**: `CHARLESTON, JB`,
`ELMENDORF, JB`, `HICKAM, JBP`, `LANGLEY, JB`, `MCCHORD, JBL`, `MCGUIRE, JB`.
Search must match both forms.

**JB Charleston is now JB Lindsey Graham.** It is Food 2.0, so out of R1 scope —
the rename matters for the directory and search only. Carry the former name as a
searchable alias.

**One open question:** are those 107 duplicates a flattened export of something
with finer grain — one row per POS terminal, per meal period? If so, collapsing
them permanently loses information. Worth one look before the pipeline is
trusted. `qrg-data-quality.csv` lists all 151 issues found, including every
duplicate, so nothing is silently discarded.

### 5. Generation is enabled per installation

`MF_Installation.Generation_Enabled` gates EOM-01. All 103 rows ship **FALSE**.

This is what stops the missing enterprise facility registry from blocking R1.
Onboarding is: populate the base's facilities and operating models → validate →
flip the flag → the next generation run picks it up. A base with the flag FALSE
reads as *not yet onboarded*, never as compliant.

`Registry_Validated_By` and `Registry_Validated_Date` record who signed off.

### 6. Roles collapsed to two, capability moved to flags

`MF_Security_Mapping.Role` is now `BASE_USER | PORTFOLIO_MANAGER`. Everyone is
BASE_USER automatically from CAC and GAL; PORTFOLIO_MANAGER is granted.

Capability lives in flags, not in the role: `Can_QC`, `Can_Submit_On_Behalf`,
`Can_Edit_Requirements`, `Can_Grant_Access`, `Grant_Scope`.

**`Can_Grant_Access` defaults FALSE even for Portfolio Managers.** If every PM
could grant PM, the role self-propagates — one grant and the population can only
grow, with no holder needing anyone's approval to expand it. That is a privilege
escalation path.

`Grant_Scope` limits blast radius: Portfolio means a PM grants only inside their
own portfolio; Enterprise is two or three people at AFSVC.

Two roles in the interface, four capability decisions underneath, and splitting
review from configuration later is a flag change rather than a schema change.
Full implementation in `docs/access-management.md`.

### 7. Security hardening

`scripts/prerelease_scan.py` is an executable gate — 30 content rules plus 11
manifest assertions. Exit 1 blocks the export. **Currently PASS, 0 warnings.**

It found one hit on its first run: `app-config.csv` contained the string
`app.powerbi.com` inside a description warning against hardcoding it. The rule
working as intended — a scanner that reasons about intent can be talked into a
pass. The description was reworded rather than the rule weakened.

Full directive in `security/SECURITY_PROMPTS.md`. The load-bearing parts:

- **No hardcoded destinations.** Every environment-specific value is an
  environment variable with a BLANK default. No commercial endpoint anywhere.
  Support GCC High and DoD; hard-code neither.
- **Do not build authentication.** No login screen, no password field, no
  "select a user". Identity comes from Entra Government via CAC. The QRG POC
  column is a display name — never an identity, never a permission, never an
  email source.
- **Deny by default, fail closed.** No mapping → NO ACCESS with a request route.
  Scope unresolvable → ACCESS_SCOPE_UNRESOLVED. Config missing →
  CONFIGURATION_REQUIRED. Never downgrade a security failure into permissive
  behaviour.
- **System-derived fields.** A user may never write UPN, role, authorisation,
  reviewer identity, status, version, or any audit author or timestamp.
- **Connectors:** SharePoint, conditionally Office 365 Users, Outlook, Power BI.
  Everything else prohibited. New connectors are disabled by default in GCC High
  and DoD, so conditional connectors must degrade gracefully.
- **CUI framework, not CUI assumption.** `CUI_Flag` defaults false. Protected
  fields exist as nullable columns and ship blank.
- **Not 800-171, not CMMC.** Those govern CUI in nonfederal systems and the
  Defense Industrial Base. The chain here is FISMA → DoDI 8500.01 → 8510.01 →
  RMF / 800-53 → DISA SRGs and STIGs → DAF and local AO.
- **Import success is not authorisation to operate.**

### 8. Design and the Figma prototype

`docs/powerapps-translation.md` maps every prototype pattern to its Canvas
equivalent, and names the four with none: sticky positioning, CSS transitions,
custom scrollbars, arbitrary hover.

**The Figma build is a design reference, not an import artifact.** Nothing in
its `src/` uploads to Power Platform. The importable artifact is the solution
package from `pac`.

Three defects in the current Figma build to carry forward as fixes:

1. Placeholder content throughout — Ramstein, Aviano, Spangdahlem, 86th AW,
   "AAFES Contractor-Operated", nine fictional requirements. Replace from the
   QRG.
2. The amber/yellow collision described above.
3. Admin health invents four things a Canvas app cannot know: database
   heartbeat, Entra service reachability, Teams bot webhook, storage quota.
   Replace with observable configuration health, and split the screen into
   APPLICATION HEALTH and TENANT SECURITY where tenant rows read "Requires
   tenant admin verification" and never "Healthy".

**External fonts are a release blocker.** The build loads Inter from Google
Fonts. That CDN may be blocked on .mil and it is a supply-chain dependency.
Production font is Segoe UI Variable; Inter is a Figma substitute only. The
scanner enforces this.

**Landing screen:** AFSVC shield, "AFSVC Mission Feeding", one Enter button, and
a panel showing the current cycle's three dates and package counts. **No role
tiles** — a role selector on the front door is an access bypass wearing a
friendly face. **No FOUO marking** — a legacy marking superseded by the CUI
programme, and nothing here has been designated CUI.

**Hover may refine. Hover must never reveal.** Anything reachable only by
hovering is unreachable in the built app, on touch, and by keyboard.

---

## FILE MAP

```
CLAUDE_CODE_HANDOFF.md          this file — read first
CODEX_BUILD_HANDOFF.md          the execution prompt and gates
README.md

data/
  QRG__Scrubbed_.csv            source of record for the registry

configuration/
  installations.csv             103 installations, Generation_Enabled all FALSE
  facilities.csv                154 facilities, 67 flagged In_R1_Scope
  qrg-data-quality.csv          151 issues — duplicates, blanks, split bases
  requirements.csv              13 rows with authority and scope confidence
  app-config.csv                kill switch and capability toggles
  feature-flags.csv             8 flags, unreleased work shipped dark
  environment-variables.json    13 variables, all blank defaults
  connection-references.json

docs/
  build-notes.md                programme answers + two addenda. Read second.
  status-calculation.md         THE status definition. Arbitrates all disputes.
  access-management.md          two roles, capability flags, grant/revoke/expiry
  security-open-issue.md        the data-layer gap
  government-environment-mode.md single-environment safety, capability gates
  powerapps-translation.md      prototype patterns -> Canvas
  accessibility.md              Section 508 gates
  design-system.md              Fluent + Cognos, calendar, routing
  figma-prompt-v2.md            UI improvement pass
  figma-prompt-registry.md      real data integration pass
  prototype-notes.md            what the HTML prototype proves
  mf-operations-prototype.html  working prototype — open in a browser
  DEPLOYMENT.md                 provisioning, build, export, acceptance tests
  MF_EOM_Data_Dictionary.csv    15 lists, 212 columns

security/
  SECURITY_PROMPTS.md           the directive. Read third.
  security-manifest.yaml        machine-verified claims
  connector-allowlist.yaml      R1 connectors with fallbacks
  role-matrix.csv               7 roles x 11 capabilities

canvas-app/
  formulas/  App.Formulas · App.OnStart · Cascade · Upload · QC · Delegation
  screens/ components/ data-sources/   layout and delegation specs

flows/  EOM01 · EOM02 · EOM03 · EOM04   implementation specs, not JSON
provisioning/Provision-MFOpsLists.ps1   PnP, idempotent, sets indexes

scripts/
  eom_schema.py                 SINGLE SOURCE OF TRUTH — edit here only
  gen_eom_artifacts.py          dictionary, provisioning, requirements, config
  gen_registry.py               QRG -> installations, facilities, data quality
  prerelease_scan.py            the release gate
```

**Regenerate:**
```
python3 scripts/gen_eom_artifacts.py && python3 scripts/gen_registry.py
python3 scripts/prerelease_scan.py
```

Edit `scripts/eom_schema.py`, never the generated CSVs.

---

## NON-NEGOTIABLES

1. Never store a percentage or a status the app must recompute. `Status_Code` is
   stored and indexed so `Filter()` on it delegates.
2. `Operating_Model` lives on the **facility**, not the installation.
3. `Requirement_Scope` is Facility | Installation | Contract.
4. `MF_EOM_Item` is persistent; `MF_EOM_Submission` is versioned. Never
   duplicate the checklist row. Never overwrite a file.
5. `Facility_ID` is **null**, not empty string, for installation and contract
   scope.
6. An UNVERIFIED requirement never drives Red.
7. Status is calculated, never chosen. No colour picker exists anywhere.
8. Status is never colour-only. Every chip carries text.
9. One status engine, one evaluation, five properties returned together.
10. Rollups run over semantic statuses and over what the viewer may see.
11. Filenames are never authoritative.
12. The list row is truth; the path is convenience. Store `SharePoint_File_ID`.
13. One security mapping serves the app and Power BI RLS.
14. Every data-source query must delegate. A non-delegable query returns the
    first 500 rows and reports success — a wrong answer, not a slow one.
15. No sign-in. CAC resolves identity before the app loads.
16. Do not invent a requirement. An upload with no matching expected item goes
    to Needs Classification.

---

## THE RECURRING FAILURE — check every new rule against this

Five times a rule has fired at the wrong grain and flooded the queue:

| Rule | Naive | Fixed | Fix |
|---|---|---|---|
| TRN-02 expired certs | 1,195 | 360 | aggregate to facility + type |
| EQP-04 calibration | 305 | 85 | aggregate + coverage gate |
| SAIIT-02 variance | 396 | 108 | tighten distribution |
| FND-01 execution pace | 730 | 30 | current period only |
| 1119-1 field feeding | every DFAC | conditional | do not auto-generate |

Before any rule enters the queue:

1. **Grain** — is this the level at which someone acts?
2. **Recency** — current work item or historical fact?
3. **Coverage** — is the source tested at this installation? If not, suppress.
4. **Suppression** — what makes this rule meaningless?
5. **Deduplication** — does another domain already report this same problem?

The exception queue is the product. If it is noisy, nothing else matters.

---

## BUILD ORDER

**Gate 0 — safety**
- [ ] `data/` and any real export in `.gitignore`
- [ ] Record the known-good commit
- [ ] `python3 scripts/prerelease_scan.py` returns PASS

**Gate 1 — capability**
- [ ] Confirm cloud: GCC High or DoD
- [ ] Confirm you may import a solution
- [ ] Confirm PAC CLI authorisation
- [ ] Confirm SharePoint, Power Apps, Power Automate available
- [ ] Raise the data-layer permission question with the SharePoint admin

**Stop if any of the first four is unresolved.**

**Gate 2 — provision**
- [ ] Run `Provision-MFOpsLists.ps1` against DEV
- [ ] Confirm indexes were created — you cannot index past 5,000 items
- [ ] Import `requirements.csv`, `app-config.csv`, `feature-flags.csv`
- [ ] Import `installations.csv` and `facilities.csv`
- [ ] Confirm all `Generation_Enabled` are FALSE

**Gate 3 — pilot registry**
- [ ] Pick 3-5 Legacy installations. Andersen (1 facility) and JBSA Lackland
      (6 facilities) cover both shapes.
- [ ] Validate their facilities and operating models
- [ ] Set `Generation_Enabled = TRUE` and record the validator

**Gate 4 — EOM-01**
- [ ] Generate for the open period
- [ ] Installation-scope rows have `Facility_ID` **null**, not empty
- [ ] Contract-scope rows carry `Contract_ID`
- [ ] The 1119-1 generated **nothing**
- [ ] Re-run: row count unchanged
- [ ] Nominal and effective dates both populated; a weekend suspense rolled

**Verify this before building any screen.** Every UI decision downstream depends
on the shape of that data.

**Gate 5 — shell**
App.Formulas, OnStart, containers, `cmpStatusBadge`, `cmpRequirementRow`,
`cmpMetricStrip`, `cmpFilterToolbar`, then scrHome, scrMaintenance, scrNoAccess.

**Gate 6 — flows** EOM-03 first, then the app and the status view agree on every
row. Then EOM-02 and the classification queue. EOM-04 last, notifications off.

**Gate 7 — acceptance** `docs/DEPLOYMENT.md`, `docs/accessibility.md`,
`security/SECURITY_PROMPTS.md` §15. Then export, unpack, tag, commit.

---

## RULINGS STILL NEEDED

1. **Scope of SF 1080, GPC and 1038.** All Proposed. Facility scope on a
   three-DFAC base means three uploads; installation means one. Changing this
   after items exist means regenerating a period.
2. **Is the 5-day suspense programme policy or derived from DAFMAN 7.14.4?** If
   derived, the EOY suspense should key off 30 September, not month end.
3. **Are the 5th and 10th calendar or duty days?** Currently CALENDAR with
   NEXT_DUTY_DAY. A weekend suspense with no rule produces a monthly argument.
4. **Is the 1119-1 conditional or monthly?** Seeded conditional. If it is a
   monthly companion to the 1119, set `Frequency = Monthly` and
   `Required_Flag = TRUE`.
5. **Are the 107 duplicate QRG rows real?** See above.
6. **Which data-layer permission option?** See `docs/security-open-issue.md`.

---

## DO NOT

- Store a percentage as a column
- Fuzzy-match identity inside Power Apps
- Put person-grain personnel data in the model
- Treat absence from a feed as compliance
- Auto-generate the 1119-1
- Invent DAF policy, thresholds, form requirements or system names
- Invent an installation name that is not in the QRG
- Fabricate DoDAAC, DoDAAD, org boxes or any protected value
- Populate an "N/A" as if it were data
- Declare a Data Call field retired without a validated replacing source
- Claim the package is compliant, STIG-compliant or authorised
- Build another monolithic dashboard
