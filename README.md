# MissionFeedingOperations

A government-compatible, source-controlled Power Platform solution. Release 1
is the end-of-month and end-of-year document requirement, discovery,
classification, versioning, QC and COP workflow for mission feeding
facilities.

Target: a single Power Platform environment in a US Government cloud.
SharePoint, Power Apps, Power Automate, Power BI and Entra identity only.
Everything else degrades behind a feature flag.

---

## Read these first

Three files hold decisions that are already settled. Do not re-derive them.

| | |
|---|---|
| [`docs/status-calculation.md`](docs/status-calculation.md) | One engine, one evaluation. Eleven codes, five visual states, and why an unverified requirement never goes Red. |
| [`docs/government-environment-mode.md`](docs/government-environment-mode.md) | Cloud endpoints, the capability gate register, the kill switch, feature flags, releases and rollback. |
| [`docs/accessibility.md`](docs/accessibility.md) | Section 508 as an acceptance gate, not a review comment. |

Then [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the build order and the
acceptance tests, and [`docs/data-model.md`](docs/data-model.md) — generated,
never hand-edited — for the schema.

`docs/mf-operations-prototype.html` is a live prototype: it runs the real
engine rather than mocking it up. Open it in a browser, change the date, and
watch the rows re-evaluate.

---

## Build state

```
Schema version            2.0  (12 lists, 164 columns)   validated
Requirement seed          12 rows, all UNVERIFIED, 3 inactive
Status engine             reference + Power Fx + flow, held in agreement
EOM-01                    reference implementation, idempotency proven
Canvas app source         10 screens, 4 components, .pa.yaml
Flows                     5 flows, 6 definitions
Local test suite          82 tests, passing
Power Platform build      NOT STARTED
Solution import tested    NO
PAC CLI authorized        UNKNOWN  — verify
Tenant cloud              UNKNOWN  — GCC, GCC High or DoD, confirm
```

**Two answers gate everything**: which government cloud this tenant is in, and
whether you may run PAC CLI against it. Neither changes the design; both
change the deployment scripts. Both currently read `UNKNOWN` in
`configuration/app_config.csv`. Do not guess either one.

---

## Layout

```
scripts/eom_schema.py            single source of truth. Nothing else declares a list or a column.
scripts/status_engine.py         the reference status engine
scripts/generate_expected_items.py   EOM-01 reference implementation
scripts/validate_solution.py     pre-release gate

docs/                            the settled decisions, the deployment runbook, the prototype
configuration/                   seeds: requirements, config, flags, sample dimensions
provisioning/                    PowerShell: capability gates, lists and indexes, seeding
canvas-app/formulas/             App.Formulas, StatusEngine, Delegation
canvas-app/src/                  .pa.yaml — the app. This is the code.
flows/                           five flows; the READMEs carry the logic
powerbi/                         semantic model, measures and RLS
solution/                        packaging envelope and connection references
tests/                           82 tests. bash tests/run_tests.sh
dist/                            release ZIPs. Rollback imports from here.
```

---

## Run the checks

```bash
bash tests/run_tests.sh
```

Covers the schema, the status engine, EOM-01's three properties, the seeds,
the delegation and accessibility static checks, and that the Power Fx, the
flows and the prototype still agree with the reference implementation.

It does **not** cover anything that needs a tenant: delegation at 5,000+ rows,
index verification, RLS, the keyboard and screen-reader passes, and the
maintenance and read-only tests are in `docs/DEPLOYMENT.md`. Passing locally
is necessary, not sufficient.

---

## The shape of the thing

**The app is the front door for submissions, and folder drops keep working.**
Users pick their facility and document, then drop the file. Installation,
facility, document type and reporting period are declared at upload, so the
file needs no classification and its filename is never read for meaning.
Files placed directly in a Portfolio FY folder are discovered by flow and
routed to a small Needs Classification queue.

Upload goes through a flow to the document library, **not** through the Power
Apps Attachments control — which binds to a Form, targets lists rather than
libraries, and behaves badly on Teams and mobile. That is a reason not to use
the control, not a reason to stop people uploading through the app.

Obligations are modelled as Facility / Installation / Contract × Requirement ×
Reporting Period. Each uploaded file is a child submission version. Every
version is preserved.

`MF_EOM_Item` is persistent; `MF_EOM_Submission` is versioned. The checklist
row is never duplicated on resubmission and no file is ever overwritten.

The operating model lives on the **facility**, not the installation: one base
can run a legacy DFAC and a Food 2.0 café, and requirements follow the
facility. Installation- and contract-scope requirements carry a null
`Facility_ID` — null, not empty string.

---

## Non-negotiables

These are load-bearing. Each is enforced by a test, a validator check, or
both.

1. **Never store a percentage or a computed status the app must recompute.**
   `Status_Code` is stored precisely so `Filter()` on it delegates.
2. **`Operating_Model` lives on the facility.**
3. **`Requirement_Scope` is Facility | Installation | Contract.**
4. **`MF_EOM_Item` is persistent; `MF_EOM_Submission` is versioned.**
5. **`Facility_ID` is null, not empty string,** at installation and contract
   scope.
6. **An UNVERIFIED requirement never drives a Red status.** All twelve seeded
   requirements are provisional today, so this is the default path.
7. **Status is calculated, never chosen.** No colour picker exists anywhere.
8. **Status is never colour-only.** Every chip carries text.
   1. **One status engine, one evaluation**, returning
      `{status, code, label, actionOwner, actionRequired}`. Never a second
      function deriving the label independently of the code.
   2. **`Final_Status` and `Status_Code` are independent.** Five visual
      states, not four — Blue separates *not due yet* from *not applicable*.
   3. **Rollups run over semantic statuses and over what the viewer may see.**
   4. **No sign-in.** CAC resolves identity before the app loads.
9. **Filenames are never authoritative.**
10. **The list row is truth; the file path is convenience.** Store
    `SharePoint_File_ID`, not just the URL.
11. **One security mapping** serves app filtering and Power BI RLS.
12. **Do not invent a requirement.** An upload with no matching expected item
    goes to Needs Classification, never creates a tracker row.

---

## Delegation

A non-delegable query returns the first 500 rows — 2,000 at most — and reports
success. No error, no warning, no log entry. A Portfolio Manager sees "3
overdue" when there are eleven, and nobody finds out until an inspection.

`MF_EOM_Item` passes that ceiling in the first quarter. Every production query
filters server-side on indexed columns with `Reporting_Period_ID` first, and
they all live in `canvas-app/formulas/Delegation.fx` so the set is reviewable.
`scripts/validate_solution.py` fails the build on an anti-pattern or on a
query that reaches a high-volume list from outside that file.

**Indexes must exist before a list crosses 5,000 items — you cannot add them
afterward.** The provisioning script creates and verifies them, and throws if
one is missing.

---

## What R1 deliberately does not do

FMAT, SAIIT, training, equipment, contracts and Five-Year Plans. The shell is
built so that `Requirement · Scope · Due · Status · Action` is the same row in
every later module, and R2–R4 reuse it without new UX.

Also out of scope: content-based classification, AI Builder, backfill of prior
periods, PCF components, Code Apps, Pipelines, and any composite readiness
score.
