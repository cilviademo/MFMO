# Mission Feeding Operations — R1

**Version 1.0.0 · Schema 5.0 · DoD cloud (`UsGovDod`)**

Automates the End-of-Month document requirement, discovery, classification,
versioning, QC and common operational picture for Air Force mission feeding
facilities.

**Recommended target: DEV or PILOT only.** Not production. Tenant validation has
not occurred and the data-layer scope issue is open.

---

## What this release is

A consolidation, not a feature release. The build was correct in most places and
carried three kinds of incoherence: a second live upload architecture, a stale
generator whose output no longer matched the code, and package references to
things that had been renamed. All three are the sort of thing that imports
cleanly and fails on the first real day.

## Before you import

Read, in order:

1. `deployment/DEPENDENCY_MANIFEST.md` — **66 destination-side resources.
   16 MUST ALREADY EXIST. Importing the ZIP creates none of them.**
2. `deployment/site-bindings.md` — the four site collections, and the ten
   minutes of somebody's time that everything downstream depends on.
3. `docs/DEPLOYMENT.md` — the gates, in order. Do not reorder them.

## The one thing most likely to go wrong

```
"The ZIP imported"
      is not
"all 17 SharePoint lists exist, with the exact internal column names the
 formulas reference, on four correctly bound site collections, with the
 libraries and pre-existing FY and month folders in place"
```

A successful import is not a working deployment. `deployment/DEPENDENCY_MANIFEST.md`
exists to make that distinction explicit.

## What is in the box

| | |
|---|---|
| Canvas app | 12 screens, 4 components, `.pa.yaml` |
| Flows | 5 specifications — EOM-01, EOM-02, EOM-02b, EOM-03, EOM-04 |
| Schema | 17 SharePoint lists, 284 columns, internal names fixed at creation |
| Registry | 103 installations, 154 facilities, from the QRG |
| Requirements | 13 rows, 8 active, authority and scope tracked separately |
| Destinations | 4 rows, all unbound, unverified and inactive |
| Power BI | semantic model, measures, RLS |

## What ships switched off, on purpose

* **All 103 installations have `Generation_Enabled = FALSE`.** EOM-01 generates
  nothing until a base is onboarded. A base with the flag FALSE reads as *not
  yet onboarded*, never as compliant.
* **All four document destinations are unbound, unverified and inactive.**
  EOM-02 fails closed on all three until somebody walks each site.
* **Six of eight notification rules are disabled.** Two ship enabled.
* **Every flow imports off.** Enable them in the order in `docs/DEPLOYMENT.md`.
* **AI Builder and document-content classification are FALSE and have no code
  path.**

None of these is an incomplete build. Each is a decision.

## What is verified, and what is not

```
346 unit tests                      OK
 14 solution validations            0 warnings, 0 failures
    pre-release security scan       PASS, 3 warnings
    routing dry run, four sites     PASS
    EOM-01 dry run                  32 rows across the 5-base pilot
    release gate, 18 stop conditions NOT BLOCKED
```

**Ten things are NOT TESTABLE LOCALLY** and are listed with an owner in
`docs/TEST_MATRIX.md`. None of them is reported as passing. The most important:
PAC CLI validation, solution import, the Power Apps Accessibility Checker, real
SharePoint writes, tenant DLP, and **the real month folder naming on each of the
four sites**.

## Known limitations

`KNOWN_LIMITATIONS.md`. The two that matter:

* **The data layer does not enforce installation scope.** Narrowed by the
  four-site finding — a portfolio boundary is now a site boundary SharePoint
  enforces natively — but not closed. An ISSM will ask.
* **The four site bindings do not exist yet.** Until somebody opens each
  portfolio site and records what is actually there, EOM-02 files everything at
  the Monthly Data Call root and looks broken on day one.

## Rollback

`ROLLBACK.md`. Response order is ReadOnlyMode → MaintenanceMode → feature flag →
disable flow → import the previous ZIP. **A solution rollback does not undo
SharePoint columns, data, configuration rows or status values.**
