# Final release report — Mission Feeding Operations R1

## Result

**PARTIAL** — a real solution ZIP with **five implemented flows**, three
connection references and twenty-four environment variables. The canvas app is
assembled in Studio.

**READY WITH DEPLOYMENT-SIDE REQUIREMENTS**, for **DEV or PILOT only.**

## Per-list index counts

Generated from `scripts/eom_schema.py`, not typed. `tests/test_schema_manifest.py`
fails if this table and the schema disagree, and fails if any list exceeds 20.

| List | Columns | Indexes | Over 20? |
|---|---:|---:|---|
| `MF_EOM_Item` | 32 | 13 | no |
| `MF_EOM_Submission` | 33 | 13 | no |
| `MF_EOM_Status` | 39 | 8 | no |
| `MF_Security_Mapping` | 20 | 8 | no |
| `MF_App_Event_Log` | 13 | 6 | no |
| `MF_Facility` | 19 | 5 | no |
| `MF_Access_Request` | 11 | 4 | no |
| `MF_Calendar_Event` | 13 | 4 | no |
| `MF_EOM_Audit` | 9 | 4 | no |
| `MF_EOM_Requirement` | 23 | 4 | no |
| `MF_Installation` | 18 | 4 | no |
| `MF_Non_Duty_Day` | 6 | 4 | no |
| `MF_Unmatched_File` | 13 | 4 | no |
| `MF_Document_Destination` | 15 | 3 | no |
| `MF_Notification_Rule` | 9 | 3 | no |
| `MF_App_Config` | 6 | 2 | no |
| `MF_Feature_Flags` | 7 | 1 | no |
| **TOTAL** | **286** | **90** | — |

**Maximum 13, against a SharePoint cap of 20. No list is over.**

The v21 baseline was 44 indexes. <!-- historical --> The 46 added are columns something in this
build filters on. The two largest jumps carry the two lists that gained the most
function: `MF_EOM_Submission` 3 → 13, taking the routing columns
(`Destination_ID`, `Needs_Filing`, `Is_Pilot`), the idempotency key
`Submission_Request_ID`, and `Is_Current`, which every reconciliation query
filters on; and `MF_Security_Mapping` 2 → 8, because scope resolution runs on
every screen load and `Expires_Date` is what makes access actually stop working.

**47 of the 90 sit on the six lists that cross 5,000 rows**, where SharePoint
refuses to add an index afterwards. The remaining 43 are on lists that stay
small, and are precautionary: a spare index costs a little write overhead, a
missing one on a list that unexpectedly grows cannot be fixed at all.

## The four pre-release warnings, verbatim

```
  [IDN-01] configuration/security-mapping.sample.csv:5
        Placeholder account. Must not reach production.
        > SEC-004,pm.portfolio2@example.mil,Portfolio,PORTFOLIO 2,,,PORTFOLIO_MANAGER,Portfolio Mana
  [IDN-01] configuration/security-mapping.sample.csv:6
        Placeholder account. Must not reach production.
        > SEC-005,enterprise.admin@example.mil,Enterprise,,,,PORTFOLIO_MANAGER,AFSVC/VMF,TRUE,TRUE,T
  [IDN-01] configuration/security-mapping.sample.csv:8
        Placeholder account. Must not reach production.
        > SEC-007,build.developer@example.mil,Enterprise,,,,PORTFOLIO_MANAGER,Developer,TRUE,TRUE,TR
  [CON-02] scripts/gen_rest_payloads.py:16
        HTTP connector usage. Prohibited in R1 unless separately approved.
        > provisioning. The SharePoint connector includes an action called **Send an HTTP
```

**The scan itself reports six, and the extra two are this report quoting the
four above.** A file that names a prohibited string in order to prohibit it
still trips the rule, which is correct behaviour — the alternative is a scanner
that can be silenced by writing about it. `tests/test_hardening.py` asserts that
the count *outside this report* is exactly four, so the number cannot drift
without a test failing.

None blocks, and here is why each does not.

The three `IDN-01` hits are placeholder accounts in a `.sample.csv`. That file
loads only under `-IncludeSampleData`, and step 3 of the import checklist has a
box confirming it was not loaded. They sit in the `example.mil` namespace, which
exists for exactly this. **They are warnings rather than nothing because a
placeholder reaching production is a real failure** — it grants access to an
account nobody owns — and import is the right moment to catch it.

The `CON-02` hit is a false positive on prose. `scripts/gen_rest_payloads.py`
line 16 is a comment explaining that provisioning uses the SharePoint
connector's own *Send an HTTP request to SharePoint* action. That is the
SharePoint connector, not the prohibited HTTP connector. It stays a warning
rather than being suppressed: the rule is watching the right words, and a
suppression here would also silence a real HTTP connector added to that file
later.

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

## Test coverage — what the 450 actually prove

**450 tests written against the same generator that produced the artifact can
all pass while the tests and the generator share one wrong assumption.** So the
groups are split by what would have to be wrong for the test to still pass.

*Logic* means the test computes an answer from data or a standard that does not
come from the code under test. *Self-agreement* means it checks that two things
this repository generates say the same thing — real value, but it cannot tell
you the shared premise is right.

| Group | Tests | Kind | What a passing run means |
|---|---:|---|---|
| `test_status_engine.py` | 46 | **Logic** | The twelve rules produce the expected state for hand-written fixture cases covering every rule and both suspense dates. |
| `test_folder_resolver.py` | 66 | **Logic** | Destination resolution against constructed folder listings, including seven failure paths: no fallback rises above its approved root, no folder is ever created. |
| `test_eom01.py` | 44 | **Logic** | The generator run against the real 103-installation / 154-facility registry. Idempotence, the null-vs-empty-string distinction, the frequency filter, the backfill window. |
| `test_hardening.py` | 36 | **Logic** | Each scanner rule fired against a planted specimen and held off a lookalike that is not a leak. Adversarial, not descriptive. |
| `test_design_tokens.py` | 34 | **Logic** | Contrast ratios and ΔE2000 separations computed against the WCAG formula — an external standard, not a value this repo chose. |
| `test_flow_expression.py` | 13 | **Logic, with a caveat** | A Logic Apps interpreter evaluates the emitted expression against the same 30 fixtures the Python engine passes. Two implementations, one fixture set — but **the interpreter is also mine**, so a wrong belief about Logic Apps semantics would be shared. It found two real defects, which is evidence it is not vacuous; it is not evidence that it models the runtime correctly. |
| `test_schema.py` | 61 | Mixed | Schema invariants (nullability, index declarations, the 20-index cap) are logic; the list-and-column inventory is self-agreement. |
| `test_package.py` | 52 | **Self-agreement** | The solution XML and ZIP have the structure this build believes Power Platform wants. Nothing here has been near an import. |
| `test_flow_bodies.py` | 40 | **Self-agreement** | Structural assertions on generated JSON — that each body contains the actions its spec describes. It found four genuine gaps, but it cannot tell you an action works. |
| `test_schema_manifest.py` | 42 | **Self-agreement** | Documentation totals and the manifest match `eom_schema.py`. This is the group that caught eleven documents stating a stale column count. |
| `test_duplication.py` | 16 | **Self-agreement** | One implementation per concept; no second status engine, no second upload path. |

Roughly **239 logic, 150 self-agreement, 61 mixed.**

**The single largest untested assumption is that the solution ZIP imports.** No
test in this repository has opened Power Platform. `test_package.py` asserts the
package matches a structure taken from documentation, and if that reading is
wrong then 52 tests pass and the import still fails. The same holds for the flow
bodies: they are structurally complete and have never executed against
SharePoint.

That is the whole reason this release is PARTIAL rather than FULL, and the
reason `docs/TEST_MATRIX.md` keeps a NOT TESTABLE LOCALLY column rather than
quietly omitting it.

## EOM-02b packaging — one template, duplicated three times

**The ZIP contains ONE EOM-02b workflow, and it ships with no site and no
library bound.** It covers nothing on import.

A SharePoint trigger watches one site and one library. The four portfolios are
four separate site collections. No single instance can cover them, and the
connector offers no option that would.

Earlier in this round the trigger was bound to `MF_Portfolio1_SiteURL`. That
version would have imported, activated, run correctly and discovered nothing in
Portfolios 2, 3 and 4 — partial coverage that reads as full coverage from every
angle except an inspection. The flow no longer declares a portfolio parameter at
all, so the designer shows an unset field instead.

After import: duplicate three times for four copies, bind each to a different
site collection, confirm the four point at four distinct sites, and leave all
four disabled until each site is verified. `IMPORT_CHECKLIST.md` step 7 states
this as four imperative boxes, and `tests/test_package.py` fails if any of them
is dropped.

All five flows import as **Draft** (`StateCode 0`). Nothing runs until someone
turns it on.

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
| Unit tests | **450 passed**, 0 failed |
| Solution validations | 14 passed, 0 warnings, 0 failures |
| Pre-release security scan | **PASS**, 6 warnings — 4 findings, 2 of them this report quoting those 4 |
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

## No site URLs in source — ruled, not deferred

**Every `Site_URL` in `configuration/document-destinations.csv` is blank,
including the four pilot rows.** The six `MF_Portfolio{n}_SiteURL` and
`MF_PilotSite_SiteURL` environment variables carry them, bound at import.

This was an open question in the previous round and it is now closed. **The
repository is public** (`cilviademo/MFMO`, `"private": false`), which settles
it: a `.mil` site path in a tracked file is published to the open internet, and
private-channel URLs name internal site collections and channel names to anyone
who looks.

The rejected alternative bound eight real URLs into that CSV and exempted the
file from `URL-01` so the scan would still pass. Those two moves only work
together, and together they disable the control rather than narrow it — that
file is the one place those values would ever land, so a rule exempting it is a
rule that cannot fire.

Two controls now hold this, and both were verified by planting a leak and
watching them fail:

| Control | Verified by |
|---|---|
| `URL-01`, no file exempt | A `Site_URL` planted in `configuration/document-destinations.csv` returns `RELEASE BLOCKED` naming `document-destinations.csv:2`. |
| `tests/test_hardening.py` | The same plant fails the suite. A separate test asserts `URL-01` has no destination-file carve-out. |

### The sweep, and what it found

`URL-01` was widened this round to watch `/teams/` as well as `/sites/` —
every private channel is a Teams-backed site, so the rule had been watching the
one path shape the production portfolios do not use. Widening it immediately
found a leak in this report, which printed the full pilot site path inside the
paragraph arguing such paths must not be committed. Redacted.

A second sweep across all 700-odd tracked files, the 182 vendored files in
`reference/`, `docs/archive/` and `docs/handoffs/` included, found one more —
a different class, the same shape:

**Five demo personas in `docs/mf-operations-prototype.html` carried UPNs in the
real `us.af.mil` namespace**, one per role. Fabricated
fixtures, but a reader of a public repository cannot tell a fixture from a real
person's address, and a made-up surname can collide with a real one. `IDN-01`
missed them because it watched four prefixes (`admin`, `test`, `demo`, `mock`)
and these had none.

All five moved to `example.mil`, in the live copy and in all three vendored
copies. A new **`IDN-02` (FAIL)** now blocks any address in `us.af.mil`,
`mail.mil`, `us.army.mil` or `navy.mil`, verified against a planted specimen.
The test specimens in `test_hardening.py` were also changed from a real host
plus a real site slug to synthetic ones — a specimen proving the rule fires does
not need to be a working destination.

Nothing else in the tree carries a site path, a real address, a secret, or a
populated DoDAAC.

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
