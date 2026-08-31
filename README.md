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

Single GCC / GCC High / DoD environment. No Dataverse, no premium connectors,
no AI Builder, no Pipelines.

---

## Where this build came from

Three inputs, and they do not all agree. **`docs/handoffs/RECONCILIATION.md` is
the decision record** — read it before changing anything load-bearing.

| Input | What it is |
|---|---|
| [`docs/handoffs/MASTER_HANDOFF.md`](docs/handoffs/MASTER_HANDOFF.md) | The consolidated project handoff. Broadest scope. |
| [`docs/handoffs/CODEX_BUILD_HANDOFF.md`](docs/handoffs/CODEX_BUILD_HANDOFF.md) | The build handoff written against V3. Later, and corrects two MASTER conclusions. |
| [`reference/v3/`](reference/) | The V3 artifacts as delivered. Prior art, not live source. |

**Precedence: V3 for what exists, CODEX for what to do next, MASTER for
everything neither covers.** Where V3's code disagreed with V3's own
documentation, the documentation won — three such defects are corrected here
and listed as C1–C3 in the record.

## Read these first

| | |
|---|---|
| [`docs/status-calculation.md`](docs/status-calculation.md) | One engine, one evaluation. Eight semantic statuses over five visual codes. |
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
Schema version            3.0  (12 lists, 172 columns)   validated
Requirement seed          12 rows, all UNVERIFIED, 3 inactive
Status engine             reference + Power Fx + prototype, held in agreement
EOM-01                    reference implementation, idempotency proven
Canvas app source         10 screens, 4 components, .pa.yaml
Flows                     5 implementation specs
Local test suite          99 tests, passing
Power Platform build      NOT STARTED
Solution import tested    NO
PAC CLI authorized        UNKNOWN  — verify
Tenant cloud              UNKNOWN  — GCC, GCC High or DoD, confirm
```

**Two answers gate everything**: which government cloud this tenant is in, and
whether PAC CLI may run against it. Neither changes the design; both change the
deployment scripts. Do not guess either one.

---

## Layout

```
scripts/eom_schema.py             single source of truth. Nothing else declares a list.
scripts/status_engine.py          the reference status engine
scripts/generate_expected_items.py  EOM-01 reference implementation
scripts/validate_solution.py      pre-release gate

docs/                             settled decisions, runbook, prototype
docs/handoffs/                    the two handoffs and the reconciliation record
configuration/                    seeds: requirements, config, flags, sample dimensions
provisioning/                     PowerShell: gates, lists and indexes, seeding
canvas-app/formulas/              App.Formulas, StatusEngine, Cascade, Delegation
canvas-app/src/                   .pa.yaml — the app. This is the code.
flows/                            five implementation specs
powerbi/                          semantic model, measures, RLS
solution/                         packaging envelope and connection references
reference/v3/                     the V3 build as delivered. Not live source.
tests/                            99 tests. bash tests/run_tests.sh
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
12. **An unverified requirement cannot create an adverse status.**

## Status, in one paragraph

`Final_Status` is the semantic string, `Status_Code` is the numeric visual code
0–4. Both are stored, written together by one evaluation, and neither derived
from the other. Five codes, not four: Blue separates *not due yet* from *not
applicable*. A provisional requirement past its due date is Blue, owned by the
programme — and since all twelve seeded requirements are `UNVERIFIED`, that is
the default path today. Package rollups run over semantic statuses, never over
colour: `[ACCEPTED, NOT_DUE, NOT_DUE]` is **In progress**, not Complete. There
is no colour picker anywhere.

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
