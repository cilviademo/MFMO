# MissionFeedingOperations

A government-compatible, source-controlled Power Platform solution. Release 1
is the End-of-Month document requirement, discovery, reconciliation,
versioning, QC and COP workflow for Air Force mission feeding.

```
Teams / SharePoint   document repository and front door
Power Apps           human workflow and QC
Power Automate       generation, discovery, reconciliation, notification
Power BI             leadership COP
SharePoint Lists     configuration, workflow state, security, audit
```

Single **DoD** government environment — SharePoint tenant `usaf.dps.mil`, Teams
`dod.teams.microsoft.us`. Not GCC High. No Dataverse, no premium connectors,
no AI Builder, no Pipelines.

The four portfolios are **four separate SharePoint site collections**, not four
channels in one team. `deployment/site-bindings.md`.

---

## Where this build came from

Three inputs, and they do not all agree. **`docs/handoffs/RECONCILIATION.md` is
the decision record** — read it before changing anything load-bearing.

| Input | What it is |
|---|---|
| [`docs/build-notes.md`](docs/build-notes.md) | **The programme's own answers**, plus the AFSVC procedures deck and two addenda. The current domain truth. |
| [`reference/v11/`](reference/) | The latest solution snapshot as delivered. |
| [`docs/handoffs/`](docs/handoffs/) | Four handoffs — CODEX, MASTER, and two later revisions. |
| [`reference/v3/`](reference/) | The earliest snapshot. Kept because some decisions still trace to it. |

**Precedence: v11 and the build notes for the domain, CODEX for engineering
discipline, MASTER for what neither covers.**

**Every snapshot has the same defect: the decision table is current and the
code is stale.** V3 shipped three parallel status functions that had already
diverged from its own table; v11 still carries a four-state Power Fx block
underneath a twelve-rule, six-state decision order in the same file. That is
why this repository keeps one reference implementation and a test suite that
holds every transliteration to it. **Twenty corrections, C1–C20, each held by a
test.**

## Read these first

| | |
|---|---|
| [`docs/status-calculation.md`](docs/status-calculation.md) | One engine, one evaluation. Nine semantic statuses over six visual codes, two suspense dates, two on-time facts. |
| [`docs/build-notes.md`](docs/build-notes.md) | The programme's answers, the AFSVC deck, and what is still open. |
| [`docs/security-open-issue.md`](docs/security-open-issue.md) | The data layer does not enforce installation scope. Unresolved. |
| [`docs/access-management.md`](docs/access-management.md) | CAC, the GAL, and how access is actually granted. |
| [`docs/government-environment-mode.md`](docs/government-environment-mode.md) | Cloud endpoints, capability gates, the kill switch, releases and rollback. |
| [`docs/accessibility.md`](docs/accessibility.md) | Section 508 as a build gate, not a review step. |

Then [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the build order and
acceptance tests, and [`docs/data-model.md`](docs/data-model.md) — generated,
never hand-edited.

`docs/mf-operations-prototype.html` is the executable specification: it runs
the real engine. Open it in a browser.

---

## Build state

```
Schema version            5.0  (17 lists, 286 columns)   validated
Requirement seed          13 rows, 8 active, authority and scope tracked apart
Registry                  103 installations, 154 facilities, from the QRG
Status engine             reference + Power Fx + prototype, held in agreement
EOM-01                    reference implementation, idempotency proven
EOM-02                    find-never-create folder resolution, tested
Canvas app source         12 screens, 4 components, .pa.yaml
Flows                     5 implementation specs
Local test suite          185 tests, passing
Power Platform build      NOT STARTED
Solution import tested    NO
PAC CLI authorized        UNKNOWN  — verify
Tenant cloud              DoD (UsGovDod)  — confirmed
Installations onboarded   0 of 103   (Generation_Enabled ships FALSE)
Document destinations     4 rows, all unbound, unverified and inactive
Data-layer permissions    NOT ENFORCED  — docs/security-open-issue.md
```

**One answer still gates deployment**: whether PAC CLI may run against the
tenant. It does not change the design, only the deployment scripts.

**Four gate the first generation run**: the grain of SF 1080, GPC and 1038, and
whether the 1119-1 is conditional. Changing scope after items exist means
regenerating a period.

**One gates the first upload**: somebody has to open each of the four portfolio
sites and record what is actually there — the site URL, the library, the exact
root folder, and above all how the month folders inside FY26 are named. Four
sites, about ten minutes. Without it EOM-02 files everything at the Monthly Data
Call root and looks broken on day one.

---

## Layout

```
scripts/eom_schema.py             single source of truth. Nothing else declares a list.
scripts/status_engine.py          the reference status engine
scripts/generate_expected_items.py  EOM-01 reference implementation
scripts/validate_solution.py      delegation, accessibility and staleness gate
scripts/prerelease_scan.py        security gate. A FAIL means do not export.
scripts/folder_resolver.py        EOM-02 destination resolution. Find, never create.
scripts/vocabulary_guard.py       a filter that matches nothing must say so

docs/                             settled decisions, runbook, prototype
docs/handoffs/                    the handoffs and the reconciliation record
deployment/site-bindings.md       the four site collections. Walk them before the first upload.
configuration/                    the real registry, requirements, config, flags, rules
data/                             the scrubbed QRG the registry was built from
security/                         manifest, connector allowlist, role matrix
provisioning/                     PowerShell: gates, lists and indexes, seeding
canvas-app/formulas/              App.Formulas, StatusEngine, Cascade, Delegation
canvas-app/src/                   .pa.yaml — the app. This is the code.
flows/                            five implementation specs
powerbi/                          semantic model, measures, RLS
solution/                         packaging envelope and connection references
reference/                        v3, v11, v14 and the Figma build, as delivered. Not live source.
tests/                            248 tests + the release gate. bash tests/run_tests.sh
dist/                             release ZIPs. Rollback imports from here.
```

## Run the checks

```bash
bash tests/run_tests.sh
```

Covers the schema and its generated artifacts, the status engine and its three
transliterations, EOM-01's three properties, the seeds, the flow specs, the
delegation and accessibility static checks, and that the ten reconciliation
corrections stayed applied.

It does **not** cover anything needing a tenant. Delegation at 5,000+ rows,
index verification, RLS, the keyboard and screen-reader passes and the
maintenance/read-only tests are in `docs/DEPLOYMENT.md`. Passing locally is
necessary, not sufficient.

---

## The shape of the thing

**Documents normally go into the Portfolio Teams FY folder, and the app is the
preferred front door.** Both paths stay open. Uploading through the app
declares installation, facility, requirement and period, so the file needs no
classification at all — that declaration is what keeps the stray queue small.
Files dropped straight into a folder are discovered by EOM-02 and routed to a
small Needs Classification queue.

Upload goes through a flow to the document library, **not** through the Power
Apps Attachments control, which binds to a Form, targets lists rather than
libraries, and behaves badly on Teams and mobile. That is a reason not to use
that control, not a reason to stop people uploading through the app.

Obligations are Facility / Installation / Contract × Requirement × Reporting
Period. `MF_EOM_Item` is the persistent expected row; `MF_EOM_Submission` is
the versioned evidence. The checklist row is never duplicated on resubmission
and no file is ever overwritten.

`Operating_Model` lives on the **facility**, not the installation: Lackland
runs a legacy DFAC and a Food 2.0 cafe, and they generate different requirement
sets. Installation- and Contract-scope requirements carry a **null**
`Facility_ID` — null, not empty string.

---

## Prime directives

1. Do not build another giant dashboard or monolithic SharePoint list.
2. Do not make Power Apps the *required* document repository. Folder drops keep
   working.
3. **Filenames are never authoritative** and are never a classification method,
   at any tier.
4. **Never silently ignore an unmatched file.**
5. Do not hard-code Legacy / Food 2.0 / MAFFO requirements in app formulas.
   Requirements are configuration.
6. Do not hard-code "due by the 10th" — `Due_Day` is a list column.
7. Do not assume Food 2.0 requirements equal Legacy requirements.
8. Do not let Power BI reconstruct workflow logic from raw submissions.
9. **Retain every version.** Nothing is overwritten or deleted.
10. No AI Builder, Dataverse, Graph, custom connectors, PCF, premium pipelines
    or multiple environments in MVP.
11. **Do not expose data outside the viewer's scope through rollups.**
12. **An unverified requirement cannot create an adverse status.** Eleven of
    thirteen are now verified, so this protects the exceptions rather than the
    estate.
13. **A base that is not onboarded reads as *not yet asked*, never as
    compliant.**
14. **Requested access expires.**

## Status, in one paragraph

`Final_Status` is the semantic string, `Status_Code` the numeric visual code
0–5. Both stored, written together by one evaluation, neither derived from the
other. **Six codes, and colour carries ownership**: Blue nobody yet, Amber the
base with runway, Red the base out of runway, Yellow AFSVC, Green nobody, Gray
nobody. Two suspense dates with a LATE window between them — the only week
where a reminder still changes the outcome. Every date exists as nominal and
effective, so "the 5th" stays the 5th in a brief while the base is held to a
date they can meet. Package rollups run over semantic statuses, never colour:
`[ACCEPTED, NOT_DUE, NOT_DUE]` is **In progress**, not Complete. There is no
colour picker anywhere.

## Delegation

A non-delegable query silently returns the first 500 rows and reports success.
A Portfolio Manager sees "3 overdue" when there are eleven, and nobody finds
out until an IG does.

`MF_EOM_Item` passes that ceiling inside the first year. Every production query
lives in `canvas-app/formulas/Delegation.fx`, filters server-side on indexed
columns with `Reporting_Period` first, and `validate_solution.py` fails the
build on an anti-pattern or an inline query.

**Indexes must exist before a list crosses 5,000 items — SharePoint will not
add them afterward.**

---

## Out of scope for R1

FMAT, SAIIT automation, Go for Green, ServSafe/training, equipment, contracts
and the Five-Year Plan. The shell is built so `Requirement · Scope · Due ·
Status · Action` is the same row in every later module.

Also out: content-based classification, AI Builder, historical backfill, PCF
components, Code Apps, Pipelines, and any composite readiness score.
