# Mission Feeding Operations — RELEASE V1

**Programme release V1 · Schema 5.0 · DoD cloud (`UsGovDod`)**

**V1 is the programme label for this culmination.** It does not renumber
the internal artifacts — their numbers are load-bearing: Artifact 1 is
**1.0.0** by build provenance, and the assembled canvas candidate is
**1.1.0** because the version bump is one of the assembler's nine gates.
V1 wraps them: Artifact 1 + canvas source + assembly pipeline + REFERENCE
msapp + the Figma parity contract + runbooks. Read 1.0.0/1.1.0 as parts
of V1, not as contradicting it.

Automates the End-of-Month document requirement, discovery, classification,
versioning, QC and common operational picture for Air Force mission feeding
facilities.

**Recommended target: DEV or PILOT only.** Not production. Tenant validation has
not occurred and the data-layer scope issue is open.

---

## Four artifacts, and they are not the same kind of thing

| Artifact | What it is |
|---|---|
| **Artifact 1** — `MissionFeedingOperations_1.0.0.zip` | Backend bootstrap: 5 flows (disabled), 24 blank env vars, 3 connection refs. **Canvas app present in solution: NO — by design.** Built reproducibly from a tag by `scripts/build_release.sh`; same tag, same bytes. |
| **`MissionFeedingOperations_REFERENCE_ONLY.msapp`** | Sanitized engineering artifact: schema-validated source packed by pac 2.11.2 over neutralised scaffolding. **Never a deployment artifact.** |
| **Assembled 1.1.0 candidate** | Produced tenant-side by `assemble_full_solution.sh` from the operator's own wrapper export, through nine fail-closed gates. A candidate, not the release. |
| **Platform re-export** | Studio's own export after import → open → zero errors → Accessibility Checker → publish. **The canonical DEV/PILOT release artifact**, promoted only by `validate_final_export.sh`. |

V1 ships the first two plus the means to produce the last two. The
re-export's provenance is different in kind and must not be reported as
the same. It is hashed *after* validation, not before:

```
python3 scripts/validate_solution.py --export MissionFeedingOperations_1.1.0.zip
sha256sum MissionFeedingOperations_1.1.0.zip
```

The validator asserts exactly one canvas app, the approved screen set, every
data source in the schema, every flow reference resolving, and — the one place
a URL legitimately appears, because Studio embeds the bound dataset — that any
embedded site URL resolves through an environment variable rather than being a
literal. A literal means the app was bound by hand and the binding will not
travel to the next environment.

Structural only. Nothing in it runs the app.

## Pushing the tag — a human step

No agent in this build can create a tag ref; the push returns HTTP 403. Artifact
1 cannot be rebuilt from a tag that does not resolve, so this runs first:

```
git tag v1.0.0 <build-commit>
git push origin v1.0.0
```

The build commit is named in `FINAL_RELEASE_REPORT.md` under **Build**. Do not
build until `git ls-remote --tags origin` shows it.

## What this release is

A consolidation, not a feature release. The build was correct in most places and
carried three kinds of incoherence: a second live upload architecture, a stale
generator whose output no longer matched the code, and package references to
things that had been renamed. All three are the sort of thing that imports
cleanly and fails on the first real day.

## Before you import

Read, in order:

1. `deployment/DEPENDENCY_MANIFEST.md` — **72 destination-side resources.
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
| Canvas app | 16 screens, 6 components, `.pa.yaml` + generated Studio-dialect source, plus the REFERENCE `.msapp` |
| Design parity | `configuration/figma-canvas-map.json` + `docs/FIGMA_CANVAS_PARITY.md`, machine-checked against the vendored Figma build |
| Flows | 5 specifications — EOM-01, EOM-02, EOM-02b, EOM-03, EOM-04 |
| Schema | 17 SharePoint lists, 286 columns, internal names fixed at creation |
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
* **`EOM_PREVIEW_AS` ships ON for portfolio managers with `Can_QC`.** A
  manager can open any in-scope installation through the base user's own
  screens, read-only — the submit screen refuses while previewing, and the
  flow authenticates the real caller regardless. Turn the flag off to
  remove the affordance entirely.

None of these is an incomplete build. Each is a decision.

## What is verified, and what is not

```
560 unit tests                      OK  (247 behavioural / 173 structural / 140 policy)
    solution validation             0 failures
    pre-release security scan       PASS, 4 warnings (each explained in the report)
    design parity gate              PASS (16 screens, 6 components, 19 tokens)
    routing dry run, four sites     PASS
    EOM-01 expectation              737 rows across the pilot window (verified in-tenant)
    release gate                    NOT BLOCKED — every stop condition clears
```

**Ten things are NOT TESTABLE LOCALLY** and are listed with an owner in
`docs/TEST_MATRIX.md`. None of them is reported as passing. The most important:
PAC CLI validation, solution import, the Power Apps Accessibility Checker, real
SharePoint writes, tenant DLP, and **the real month folder naming on each of the
four sites**.

## Open by design — pilot validation items, not missing build work

These are intentionally unresolved locally and move to the tenant:
actual import/open behaviour; real SharePoint writes; EOM-01 runtime in
the tenant; EOM-02 upload/routing against the real sites; EOM-02b
post-import duplication and binding; the actual Studio render (the
Studio-open visual gate in `CANVAS_APP_ASSEMBLY.md` is the decisive
human checkpoint); Accessibility Checker results; tenant DLP and
security enforcement; installation-level data isolation.

Repository status: **READY FOR PATH A ASSEMBLY.** The successful pilot
outcome is **DEV/PILOT RELEASE CANDIDATE**. Neither is rounded up.

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
