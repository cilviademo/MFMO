# Final release report — Mission Feeding Operations R1

## Result

**PARTIAL** — a real solution ZIP with **five implemented flows**, three
connection references and twenty-four environment variables. The canvas app is
assembled in Studio.

**READY WITH DEPLOYMENT-SIDE REQUIREMENTS**, for **DEV or PILOT only.**

### Per-list index counts — verified before anything else

**No list exceeds the SharePoint cap of 20. The maximum is 13.**

| List | Columns | Indexed | | List | Columns | Indexed |
|---|---:|---:|---|---|---:|---:|
| MF_EOM_Item | 32 | **13** | | MF_App_Event_Log | 13 | 6 |
| MF_EOM_Submission | 33 | **13** | | MF_Facility | 19 | 5 |
| MF_Security_Mapping | 20 | 8 | | MF_Installation | 18 | 4 |
| MF_EOM_Status | 39 | 8 | | MF_EOM_Requirement | 23 | 4 |
| MF_Unmatched_File | 13 | 4 | | MF_EOM_Audit | 9 | 4 |
| MF_Non_Duty_Day | 6 | 4 | | MF_Calendar_Event | 13 | 4 |
| MF_Access_Request | 11 | 4 | | MF_Document_Destination | 15 | 3 |
| MF_Notification_Rule | 9 | 3 | | MF_App_Config | 6 | 2 |
| MF_Feature_Flags | 7 | 1 | | **TOTAL** | **286** | **90** |

**The 44 → 90 delta is accounted for, list by list.** Every added index is a
column something in the build filters on, and the largest jumps are the two
lists that gained the most function:

- `MF_EOM_Submission` 3 → 13: the routing columns (`Destination_ID`,
  `Needs_Filing`, `Is_Pilot`), the idempotency key, and `Is_Current`, which
  every reconciliation query filters on.
- `MF_Security_Mapping` 2 → 8: scope resolution runs on every screen load, and
  `Expires_Date` is what makes access actually stop working.

**47 of the 90 sit on the six lists that cross 5,000 rows**, where an index
cannot be added later. The other 43 are on lists that stay small and are
precautionary — a spare index costs write overhead, a missing one on a list
that unexpectedly grows cannot be fixed.

### The flows are implemented

118 actions across five flows, from `flows/*/definition.md`. Nothing invented.

| Flow | Actions | Trigger |
|---|---:|---|
| EOM-01 Expected Package | 43 | Recurrence, 1st 05:00 |
| EOM-02 Submission | 30 | PowerApps V2 |
| EOM-03 Reconciliation | 24 | Recurrence, nightly 02:00 |
| EOM-04 Notifications | 12 | Recurrence, daily 07:00 |
| EOM-02b Legacy Intake | 9 | SharePoint file created |

**The status engine is a fourth implementation, and it is generated, not
written.** `scripts/flow_status_expression.py` emits the twelve rules as one
nested Logic Apps `if()` from the same catalogue `status_engine.py` exports —
imported, not copied. `tests/test_flow_expression.py` contains a small
interpreter for the expression subset and **evaluates it against the same 30
fixture cases** that hold the Python and the Power Fx engines together.

That interpreter found two defects that would otherwise have surfaced in a
tenant:

- **`or()` and `and()` are not short-circuiting in Logic Apps.** Both arguments
  are evaluated before the operator runs, so `or(empty(d), ticks(d) > x)` throws
  on a null date. Every null guard is now a nested `if()`, which is lazy.
- **A requirement with no final call is held to its first suspense.** The
  expression treated a null final call as "no deadline" and left the item amber
  forever instead of going red — the wrong answer in the safe-looking direction.

### What is verified, and what is not

**Verified locally:** the status expression against 30 cases; every action
reachable with no `runAfter` cycle; every connector on the allowlist; every
`dataset` and `table` from a parameter, never a literal; every parameter
declared and every declared parameter read; every write loop pinned to
concurrency 1; and the invariants each specification calls non-negotiable —
40 structural checks in `tests/test_flow_bodies.py`.

**Not verified: execution.** There is no tenant and no Logic Apps runtime here,
so these flows have never run. `docs/TEST_MATRIX.md` records that as NOT
TESTABLE LOCALLY with an owner, and it is not reported as passing.

Two places carry an explicit `TODO` rather than a guess, both in EOM-01: the
non-duty-day roll and the fiscal-year folder walk. Each names
`scripts/status_engine.effective_date` and `scripts/folder_resolver.py` as its
reference. A flow whose body was guessed would import cleanly and do the wrong
thing.

### The canvas app is still not in the package

**No `.msapp`, and no placeholder.** Unchanged and for the same reason: the
format is owned by Studio and mid-transition, and a file it rejects on open
fails the import with an error naming an internal file and explaining nothing.

`scripts/build_release.sh` refuses to build if one appears;
`tests/test_package.py` fails if the manifest declares a canvas app component
the package does not contain. `CANVAS_APP_ASSEMBLY.md` covers building it
inside the imported solution.

## Build

```
branch    claude/mission-feeding-eom-build-98fbsi
commit    the tip of that branch
tag       v1.0.0, on that same tip
tree      clean
```

The commit hash is deliberately not written here. This file is inside the commit
it would name, so any hash printed in it is one commit stale the moment it is
true. `git rev-parse v1.0.0` is authoritative; the artifact checksum below is the
identity that does not move.

**The tag exists locally but is not on the remote.** `git push origin v1.0.0`
is refused with HTTP 403 — this session's credentials allow pushing the
designated branch and not creating tags. The branch is pushed and
`origin/claude/mission-feeding-eom-build-98fbsi` matches local `HEAD` exactly,
so the tagged commit is on the remote; only the tag *ref* is missing. Recreate
it with `git tag -a v1.0.0 <commit>` from a session that can, or from the
GitHub releases UI. The artifact is reproducible from the commit either way.

**This was not committed to `main`.** The session's standing instruction is to
develop and push only on `claude/mission-feeding-eom-build-98fbsi` and never to
push elsewhere without explicit permission. The directive asked for a commit to
`main`; those conflict, and I took the narrower one. Merging to `main` is a
one-line fast-forward and is yours to make or to ask me for.

## Versions

| | Value |
|---|---|
| App Version | 1.0.0 |
| Solution Version | 1.0.0 |
| Schema Version | 5.0 — 17 lists, 286 columns |
| Requirement Config Version | 13 rows, 8 active |

Checked by the release gate. Any drift blocks the build.

## Artifact

```
dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip
SHA-256  1762f78cb629043d25e65808b3a0f33c72278fd9faed67acf6b84a9aa9513024
```

Packed from the tagged commit by `scripts/build_release.sh`, not from the
working tree. The build is **reproducible** — timestamps are normalised, so the
same tag always yields the same checksum. Version, commit and checksum describe
the same build.

```
bash scripts/build_release.sh v1.0.0
```

The ZIP is packed from `solution/src` alone, so the commit that records this
checksum in this report does not change it. Only `SHA256SUMS.txt` moves, because
it names its own commit.

**The ZIP and its checksum are not committed.** `SHA256SUMS.txt` records the
commit it was built from, so committing it would change that commit, change the
recorded hash, and need another commit — it never converges. A build output that
names its own commit cannot live inside that commit. Rebuild it from the tag;
the bytes are identical every time.

See **Result** above for exactly what is in it and what is not.

## Tests

| | |
|---|---|
| Unit tests | **445 passed**, 0 failed |
| Solution validations | 14 passed, 0 warnings, 0 failures |
| Pre-release security scan | **PASS**, 4 warnings |
| Routing dry run, PRODUCTION | **PASS** — 4 happy paths, 7 failure paths |
| Routing dry run, PILOT | **PASS** — 4 happy paths, 7 failure paths |
| Flow expression vs the engine | **PASS** — 30 cases, three languages |
| Flow structure | **PASS** — 40 checks across 118 actions |
| EOM-01 dry run | 121 rows across the 5-base pilot, 2026-08..2026-09 |
| Release gate | **NOT BLOCKED** — 18 stop conditions |
| **NOT TESTABLE LOCALLY** | **10 items**, each with an owner, in `docs/TEST_MATRIX.md` |

Three warnings are placeholder accounts in `security-mapping.sample.csv`, which
is what that file is for; they only load with `-IncludeSampleData`. The fourth
is a `.dps.mil` URL inside `tests/test_hardening.py` — the specimen the test
uses to prove the leak rule fires. Both carry inline exceptions with reasons,
reported on every run.

No result is inferred. Nothing NOT TESTABLE LOCALLY is reported as passing.

## Redundancy removed

| Removed | Consolidated into |
|---|---|
| The central evidence library, `EOM_Root_Path`, `EvidenceRootPath`, `New-EvidenceLibrary` — a **second live upload architecture** | `MF_Document_Destination` + `flows/EOM02-Submission`. Explanation only in `docs/DECISION_LOG.md` D-01 |
| Inline requirement applicability in `Cascade.fx` | `MF_ModelApplies` / `MF_FacilityTypeApplies`, held to `generate_expected_items.py` by test |
| Stale Teams connection reference | removed; nothing used it |
| Orphaned `mfops_EOM02FileIntake`, `mfops_EOM05AppUpload` root components | renamed to the current flows |
| Orphaned `mfops_MF_EvidenceRootPath`, `mfops_MF_FileIntakeLibrary` definitions | regenerated from `environment-variables.json` |
| 3 superseded documents | `docs/archive/`, each with a header naming its replacement |

Documentation is archived. Executable code is removed.

## Dependencies

| Category | Count |
|---|---|
| PROVISIONED BY BUILD | 20 |
| CREATED BY DEPLOYMENT SCRIPT | 19 |
| **MUST ALREADY EXIST** | **16** |
| **MANUAL .MIL CONFIGURATION** | **7** |
| OPTIONAL / FEATURE-GATED | 4 |
| Total | 66 |

**Importing the ZIP creates none of the 16 or the 7.** It does not create
SharePoint lists, libraries, FY or month folders, security groups, DLP policy or
any tenant configuration.

## Remaining .mil-side actions

1. **Walk the four portfolio site collections** and record the site URL, the
   library, the exact root folder, and **how the month folders inside FY26 are
   named**. Four sites, about ten minutes. Without it nobody can upload
   anything — EOM-02 fails closed on unbound destinations, and once bound
   incorrectly it files everything at the root and looks broken on day one.
2. **Raise the data-layer scope question with the SharePoint administrator.** An
   ISSM will find it.
3. Confirm PAC CLI authorisation.
4. Run `Provision-MFOpsLists.ps1 -WhatIf` and read the output for pre-existing
   lists whose internal names may differ.
5. Author the canvas app and build the five flows, then re-tag and rebuild.
6. Onboard 3–5 pilot bases.
7. Settle the four open rulings on requirement scope, **before the first
   generation run**.

## Known limitations

`dist/MissionFeedingOperations_1.0.0/KNOWN_LIMITATIONS.md`, ten items. The
three that matter most:

- **The ZIP is not yet importable.** Power Platform build NOT STARTED.
- **The data layer does not enforce installation scope.** Narrowed by the
  four-site finding, not closed.
- **The four site bindings do not exist.** Nobody can upload until they do.

## Recommended target

**DEV or PILOT only.**

Not PROD. Tenant validation has not occurred, the data-layer scope issue is
open, and the canvas app has not been built.

**Import success is not authorisation to operate.**

---

## The pilot generation window

`BackfillFromPeriod = 2026-08`, `BackfillToPeriod = 2026-09`.

**Verified: the full R1 scope over that window is exactly 737 rows.** 43 R1
installations, 67 Legacy facilities, six active requirements of which the 1119-1
generates nothing and the 1038 lands only in September.

```
2026-08   268 rows
2026-09   469 rows
TOTAL     737
```

The 5-base pilot list in `configuration/pilot-onboarding.csv` generates 121 of
those. Onboarding the rest is a flag flip per base.

**The window is now enforced, not merely configured.** It was a config key
nothing read, which is a decision that was never applied — a stray
`--period 2025-10` would have quietly created the other 2,881 rows.
`generate_expected_items.check_window` refuses a period outside it, EOM-01
terminates with `PERIOD_OUTSIDE_BACKFILL_WINDOW`, and both say in the message
that widening it is a one-cell edit and that generation is idempotent.

## The programme decisions applied

| Decision | Applied |
|---|---|
| Facility scope for all six active requirements | SF 1080, GPC and the 1038 moved from Installation, `Scope_Confidence` **Verified**, `Scope_Basis` naming the 31 Aug 2026 ruling |
| Notifications off for the pilot | `NotificationsEnabled` False; EOM-04 records what it would have sent |
| Pilot destinations | four `PILOT-P#-EOM` rows, active and verified, keyed on `Portfolio_ID` so routing exercises the real multi-destination path |
| Pilot mode | `PilotMode` True; every submission stamped `Is_Pilot` **at write time**, so pilot rows stay identifiable after the flag is turned off |
| Open period | 2026-08 |

`Scope_Confidence` gained a **Verified** value. A ruling is a stronger claim
than "High" — High says the evidence points this way; Verified says the
programme decided, on a date, and `Scope_Basis` records it.

## One deliberate deviation, and why

**v22 commits the real pilot site URL to `document-destinations.csv`. This
build does not.**

A real `.mil` site path — `https://usaf.dps.mil/teams/<pilot-site>`, whose
last segment this report deliberately does not print — is a destination,
and that file is committed to a GitHub repository and seeded into SharePoint.
The build's own rule — and `prerelease_scan.py` rule URL-01, which the earlier
instruction said to keep blocking — treats a `.mil` site URL in a tracked file
as a destination leak. The instruction in this round is also explicit that the
package carries no environment variable values.

So the four pilot rows ship with `Site_URL` blank and bind at import from a new
`MF_PilotSite_SiteURL`. Everything else about them is exactly as ruled: active,
verified, four root folders, keyed on portfolio.

**If you want the URL committed, say so and I will** — it is your call about
your repository, not mine. But it should be a decision, not a default.

## A real defect the pilot config exposed

`Library_Name` and `Library_Url_Segment` are **different strings**: the pilot
library displays as `Documents` and is `Shared Documents` in the URL.

`folder_resolver.resolve_destination_folder` built the path from
`Library_Name`. Against the pilot site that produces `Documents/EOM-EOY/...`,
which **404s on a library that plainly exists** — and gets debugged as a
permissions problem. It now builds from the URL segment, refuses a blank one
rather than substituting the display name, and `tests/test_folder_resolver.py`
holds it.

This is exactly the class of defect the instruction's "Library_Url_Segment for
the path, never Library_Name" was written to prevent, and it was live.
