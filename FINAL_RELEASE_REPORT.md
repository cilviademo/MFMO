# Final release report — Mission Feeding Operations R1

## Result

**PARTIAL** — a real solution ZIP with **five implemented flows**, three
connection references and twenty-four environment variables. The canvas app is
assembled in Studio.

**READY WITH DEPLOYMENT-SIDE REQUIREMENTS**, for **DEV or PILOT only.**

**This culmination is RELEASE V1** — the programme label wrapping Artifact 1
(1.0.0), the canvas source and parity contract, the REFERENCE msapp, and the
Path A assembly pipeline (which mints the 1.1.0 candidate tenant-side). The
internal version numbers are load-bearing and are not renumbered by the V1
label; `RELEASE_NOTES.md` carries the mapping.

## Per-list index counts

Generated from `scripts/eom_schema.py` by the same code that emits the
provisioning payloads. `tests/test_schema_manifest.ReportIndexTableMatchesTheSchema`
fails if this table and the schema disagree, and fails if any list exceeds 20.

| List | Columns | Indexes | Over the cap of 20? |
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

**Maximum 13 on one list, against a SharePoint cap of 20. None is over.**

The v21 baseline was 44 indexes. <!-- historical --> The 46 added are columns
something in this build filters on. The two largest jumps carry the two lists
that gained the most function: `MF_EOM_Submission` 3 → 13, taking the routing
columns (`Destination_ID`, `Needs_Filing`, `Is_Pilot`), the idempotency key
`Submission_Request_ID`, and `Is_Current`, which every reconciliation query
filters on; and `MF_Security_Mapping` 2 → 8, because scope resolution runs on
every screen load and `Expires_Date` is what makes access actually stop working.

**47 of the 90 sit on the six lists that cross 5,000 rows**, where SharePoint
refuses to add an index afterwards. The other 43 are on lists that stay small
and are precautionary: a spare index costs a little write overhead, a missing
one on a list that unexpectedly grows cannot be fixed at all.

## The four pre-release warnings

Captured from `python3 scripts/prerelease_scan.py` stdout, not transcribed.

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

The scan itself prints **6**; the extra two are this report
quoting the four above, and a file that names a prohibited string still trips
the rule. That is correct — the alternative is a scanner you can silence by
writing about it. `tests/test_hardening` pins the count *outside this report* at
four, so the number cannot drift unnoticed.

**Why none blocks.**

The three `IDN-01` hits are placeholder accounts in a `.sample.csv`, which loads
only under `-IncludeSampleData`; step 3 of the import checklist has a box
confirming it was not loaded. They sit in the `example.mil` namespace, which
exists for this. They are warnings rather than nothing because a placeholder
reaching production is a real failure — it grants access to an account nobody
owns — and import is the right moment to catch it.

The `CON-02` hit is a false positive on prose. `scripts/gen_rest_payloads.py`
line 16 is a comment explaining that provisioning uses the SharePoint
connector's own *Send an HTTP request to SharePoint* action — the SharePoint
connector, not the prohibited HTTP connector. It stays a warning rather than
being suppressed: the rule is watching the right words, and suppressing it here
would also silence a real HTTP connector added to that file later.

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

## STATUS: READY FOR PATH A ASSEMBLY

Not FULLY VALIDATED FINAL RELEASE. That status is only reachable after the
platform cycle on the .mil side, and this report does not round up.

### The four artifacts, kept distinct

| Artifact | What it is | Version | SHA-256 | Studio-validated | Tenant-executed |
|---|---|---|---|---|---|
| **Artifact 1** — `MissionFeedingOperations_1.0.0.zip` | backend bootstrap solution: 5 flows (disabled), 24 blank env vars, 3 connection refs. **Canvas app: NO, by design.** | 1.0.0 | recorded below, reproducible from the build commit | n/a | no |
| **Reference `.msapp`** — `MissionFeedingOperations_REFERENCE_ONLY.msapp` | build validation only. Packed by pac 2.11.2 from schema-validated source over the neutralised scaffolding; round-trips byte-identically; residue-swept. **No platform identity; never a deployment artifact.** | n/a | printed by `build_msapp.py` on every build | **no** | no |
| **Locally assembled candidate** — `MissionFeedingOperations_1.1.0.zip` | produced by `assemble_full_solution.sh` from the operator's wrapper export, through nine fail-closed gates. A candidate, not the release. | 1.1.0 (enforced against `Solution.xml`) | printed at assembly | not yet | no |
| **Studio-validated final export** | the platform's own re-export after import → open → zero errors → Accessibility Checker → publish. **The canonical Canvas-inclusive artifact**, promoted by `validate_final_export.sh`. | 1.1.0 | recorded at promotion | **yes** | still NO until the pilot runs |

### The residue finding, owned

The previous round claimed the built `.msapp`'s "leak sweep: clean". **That
claim was false.** User inspection found, inside the shipped archive: signed
Azure Blob URLs (`blob.core.windows.net/…sig=…`), a donor tenant identifier
(`sktid=`), three donor images and their `Resources.json` entries, the donor's
AppName in `PublishInfo.json`, and donor feature flags enabled (runtime
copilot, experimental CDS/SQL connectors). The sweep missed them because its
blocklist had five entries and none of these classes.

Closed structurally, not just with a longer list:

- **The raw donor left the tree.** The tracked artifact is now the
  pre-neutralised `scaffolding.msapr` (hash-pinned), produced by
  `neutralise_donor.py`, which documents the disposition of every donor entry
  and refuses to write output containing any blocked string. Donor images:
  stripped, after *proving* the source references no image resource. Donor
  flags: forced `False`. Donor name: gone. (The raw bytes remain in git
  history at the earlier commit; the current tree is what ships and what the
  scanner guards.)
- **The scanner now inspects archives.** Every tracked or built `.msapp`,
  `.msapr` and `.zip` — dist included, since that is exactly where the residue
  lived — has every entry swept by every content rule plus four archive rules
  (`ARC-01..04`: blob storage, SAS `sig=`, `sktid=`, `windows.net`). An
  archive that cannot be opened is itself a FAIL. Only `tests/fixtures/` is
  exempt, for the same reason the scanner's own rule file is: specimens must
  contain what the rules forbid.
- **Regression tests plant each residue class in a real archive** and require
  the block; the shipped reference `.msapp` is re-probed by test against the
  original finding list, not against the build script's word.

### The assembler, made fail-closed

The previous version piped pac through `grep … || true` — a failed pack could
be masked and the blank wrapper re-shipped as the candidate. Rewritten with
nine gates, each proven by a failure simulation:

| Gate | Proven by |
|---|---|
| pinned PAC CLI 2.11.2 (drift refuses; override only after the round-trip suite passes on the new version) | wrong-version simulation |
| exactly one canvas app, or `MF_EXPECTED_APP` selects — never first-alphabetically | zero-app, two-app, and selector simulations |
| all **19 data sources present in the wrapper, by name** — a missing one stops and names itself | missing-source simulation |
| environment-minted flow name matches `EOM02_Submission` — a mismatch stops with instructions to fix the *repository* source, never the built app | mismatch simulation |
| unpack verified; pack verified **and the `.msapp` bytes must change** | pack-failure and no-op-pack simulations |
| internal `Solution.xml` version = release version (bump in Power Apps before export; identity metadata is never rewritten here) | version-mismatch simulation |
| structural validation + full archive leak sweep on the output | dry run |

The full happy path was dry-run end to end with the real packer: a simulated
wrapper export went through all nine gates to a validated candidate.

### Also closed this round

- `requirements-dev.txt` + a dependency preflight in `tests/run_tests.sh`: a
  missing `yaml` module now says "environment problem, install this" instead
  of surfacing mid-validator looking like a schema failure. Proven by
  shadowing the module.
- `validate_final_export.sh`: 18 structural PASS/FAIL rows plus three
  NOT TESTABLE LOCALLY rows that are never converted to PASS. Proven against
  a good synthetic post-Studio export and three broken ones (planted SAS
  residue, version mismatch, missing type-300 RootComponent).
- "The export wins" policy revised: normalisation-only differences reconcile
  automatically; **semantic** differences require explicit review before the
  repository changes.
- Path A contamination guard: static tests prove the assembler deletes and
  copies only `Src/` and never references the donor.

## The canvas app is now BUILT, not pasted

The user asked for the full import ZIP to be producible without a human
rebuild. That is now true to within one ten-minute platform step, and the
line that remains is drawn exactly where fabrication would begin.

### What was established, by experiment, with Microsoft's own tools

- `pac canvas pack --layout SourceCode` **validates nothing**: fed a
  structurally broken YAML file and a nonexistent control type, it reported
  "Packing succeeded" both times. Every pack success below is therefore
  backed by independent validation, never by the packer's word.
- The modern msapp format (MSAppStructureVersion 2.4.0) carries the app's
  YAML source INSIDE it, marked `LoadFromYaml: true`. The `.msapr` reference
  archive the packer requires was reverse-engineered to its exact contract
  (`MsaprHeaderJson` via reflection over Microsoft's own Persistence library,
  run under the .NET runtime assembled from NuGet) and then bypassed entirely
  in favour of a genuine one.
- A genuine Studio-built 2.4.0 app (Microsoft's ALM test asset, MIT, vendored
  with its hash pinned) **round-trips byte-perfectly** through unpack + pack:
  22 of 22 entries identical.

### The built artifact

`dist/canvas/MissionFeedingOperations.msapp` — 38 entries, 24 of them this
repository's screens/components/App yaml, packed by `pac canvas pack` against
the donor's scaffolding, **neutralised entry by entry** (the donor's
Properties.json named a commercial Dataverse dev instance; its data-source
metadata, control trees and analysis results are stripped; identity is fresh
and deterministic). The build FAILS on donor-hash drift, on round-trip
divergence, and on any commercial-cloud string in the output.

**It has never been opened by Studio**, and Microsoft's packer prints on
every run that a source-packed app is validated by that open. That sentence
ships with the artifact.

### The full ZIP: `scripts/assemble_full_solution.sh`

A CanvasApp solution component needs metadata only the platform mints at
export. So the wrapper is the operator's: import Artifact 1, create ONE blank
canvas app in the solution (adding the 19 data sources while there), export —
ten minutes — then one command swaps the blank app's content for this
repository's, keeping THEIR identity and THEIR environment's data-source
metadata, and validates the result. **Dry-run here end to end** against a
simulated export: unpack, swap, pack, re-zip, `validate_solution.py --export`
green — 16 screens, 5 workflows, no literal URLs.

What is deliberately NOT done: authoring the CanvasApp component metadata
myself. R2 of the build directive names that fabrication and says refuse; it
is the difference between an artifact whose every byte has a provenance and
one that merely looks like it does.

### Source truth got harder on the way

Getting the source through a real YAML parser and Microsoft's published
pa.yaml v3 schema — neither had ever run against it — found:

| Defect | Where | Why nothing caught it |
|---|---|---|
| **Ten of twenty-two files were not valid YAML** — inline formulas carrying record literals (`=[{{ Period: gblOpenPeriod }}]`) | 8 screens, 2 components | every prior check was regex-based; none parsed YAML. Studio would have rejected the paste an hour into the operator's session |
| `Children:` nested inside `Properties:` | scrMaintenance | same |
| `DataType: Date` (schema: `DateAndTime`) | cmpStatusBadge ×2 | schema never enforced |
| `Default:` on Output properties (schema forbids; the formula belongs in Properties) | cmpStatusBadge, cmpMetricCard | schema never enforced |

All fixed in the source of truth; a YAML-parse test and the schema validation
now run in the suite, and the validator was calibrated against Studio's own
output (the published control ENUM lags Studio — the genuine app fails it 20
times — so the enum check is relaxed to the schema's own pattern and
everything else stays strict).

## The approved screen set is complete

Four screens were absent against the approved UX. They are present, wired to
real lists and flows rather than decorated:

| Screen | What it answers | Query |
|---|---|---|
| `scrMyPackage` | the state of everything this period | `MF_PackageForPeriod` — delegates on `Reporting_Period` + scope |
| `scrOverview` | AFSVC landing: shape, then what needs me | `MF_VisibleItems` narrowed on `Final_Status`, `Requirement_ID`, `Portfolio_ID`, all indexed |
| `scrInstallations` | the list; `scrInstallation` stays the detail | `MF_InstallationsInScope`, rollup over the already-scoped registry |
| `scrExceptions` | three problems, three owners, never one number | `MF_UnmatchedQueue`, `MF_NeedsFilingQueue`, `MF_CorrectionsPastDue` |

Two components, added only where they remove duplication across two or more
screens: `cmpMetricStrip` and `cmpFilterToolbar`. The toolbar emits **values**
and touches no data source — a component that ran the query would decide
delegation for screens it cannot see. Four other candidates would have been
used once and were skipped.

**The metrics are semantic, never colour.** Amber covers both "the base owes a
correction" and "AFSVC owes a review", so counting by colour would put two
different people's work in one number.

### Two audits, both proven against a planted violation

| | Catches | Why it has to exist |
|---|---|---|
| `canvas_reference_check.py` | a data source, screen, component, flow or formula that does not exist | A wrong list name does **not** error in a canvas app. It renders an empty gallery, which reads as "nothing due". |
| `canvas_delegation_check.py` | a predicate on a non-indexed column of a high-volume list | A non-delegable `Filter` returns the **first 500 rows and reports success**. |

Both are wired into the suite, and both were verified by planting a violation
and watching them fail rather than by reading their output once.

### Two predicates reported, not rounded up

`MF EOM Item.Requirement_Scope` and `MF Calendar Event.Scope_Type` are
unindexed columns inside an `OR`, behind indexed leading predicates. SharePoint
can *usually* resolve those through the leading index, and usually is not a
word this build accepts — whether the optimiser uses the index across an OR
spanning an unindexed column cannot be established without a list of over 5,000
items on the real tenant.

**No index was added.** That is a schema change and the schema is a settled
authority; `MF_EOM_Item` has 13 of 20 if the owner decides otherwise.

### A defect in the previous round's work

The formula extractor never saw `Delegation.fx` — its regex did not handle
`Name(a: Text): Table =`, so **the file that decides whether every query
delegates contributed zero formulas and was never parsed**, while the total
looked healthy because the other twenty files made it up. The test asserted a
file *count*, which cannot catch that. It asserts a **named list** now.

With it fixed: **1,829 formulas across 27 files, no syntax errors** under
Microsoft.PowerFx.

## Design fidelity — Figma → Canvas

The vendored Figma package (`reference/figma-build/`) is the **visual**
source of truth, the canvas source the **functional** one, and Studio the
platform authority. The contract between them is now machine-checked:
`configuration/figma-canvas-map.json` maps every Figma screen file and
component to its real canvas counterpart with a parity verdict (PASS /
MINOR DRIFT / PLATFORM SUBSTITUTION / FAIL — FAIL blocks release, and there
are none), `scripts/check_design_parity.py` enforces it in the suite, and
`docs/FIGMA_CANVAS_PARITY.md` narrates every deviation with its rationale.

What the gate proves mechanically: all 19 colour tokens match the approved
values byte-for-byte and are defined exactly once in `App.Formulas.fx`; no
screen or component contains a colour literal; every screen paints the token
ground (default Power Apps styling is treated as functional design drift);
base navigation is exactly Home / My Package / Calendar with **Submit as a
primary action, not a tab**; the status chip carries label + icon + 1px
status border + radius 2; amber and yellow can never be merged; no runtime
fetch exists anywhere in the app source; and the map covers every screen and
component with real identifiers only. The gate is proven fallible in the
suite — it caught an unmapped screen on its first run.

Fixes this pass made to the source, found by holding it against the Figma
package: `clrAccent` was referenced but defined nowhere (Studio would have
shown the error at open); three navigation entries encoded tabs the approved
design never had (Submit, Request access, Unmatched — all reached by
action or row, never navigation); the chip radius was 4 against the spec's
2; two labels drifted in casing.

Approved deviations, recorded rather than silently resolved: the
amber/yellow inks deviate from the Figma CSS **because the Figma CSS
predates the accessibility fix** — the shipped pair is 41° apart in hue and
ΔE2000 25.1 where the prototype's pair measured 1.16:1 (`docs/accessibility.md`
is the arbiter); nav badge-count chips are omitted (a count query per tab
per paint against >2,000-row lists); AccessManagement has no canvas screen
because grant administration belongs in the SharePoint list — Power Apps
`Visible` is not a security boundary and the open issue stays open.

**No claim of pixel-perfection is made.** How Studio renders is NOT TESTABLE
LOCALLY; the Studio-open visual validation gate in `CANVAS_APP_ASSEMBLY.md`
(structure, no default styling, six distinct chips, navigation shape,
density at 1024/768, zero external fetches) is where a human confirms the
render before publish, and substantial divergence there blocks the release
exactly as a failing test would. `validate_final_export.sh` additionally
fails any assembled ZIP in which a default `Screen1` survived Src/
replacement.

## Provisioning, and the threshold that was conflated

`gen_rest_payloads.py` now emits an explicit index **operation** per indexed
column rather than a flag for the operator to translate, plus what uniqueness
SharePoint actually enforces — a composite key is a flow-side check, and saying
so stops an operator assuming the list protects something it does not.

`provisioning/whatif-report.md` lists every call before any of them run, with
the irreversible ones marked.

**A defect found while writing it.** The report's "irreversible after 5,000
rows" column was driven by a flag called `crossesDelegationCeiling` that tested
`> 5000`. Two different limits had been conflated:

| | Rows | Cost of crossing it |
|---|---:|---|
| Delegation ceiling | 2,000 | a query returns the first page and reports success |
| List view threshold | 5,000 | an index can **never** be added |

They are separate flags now, and the irreversible one is **inclusive**: a list
projected at exactly 5,000 crosses it on its next row. Three lists were marked
"no" that should have read "YES".

`scripts/verify_provisioning.py` compares a tenant export against the schema
and fails on a missing list, a missing column, or an index missing from a
high-volume list. **"The provisioning run said OK" is not evidence** — a run can
create a list, most of its columns and none of its indexes and report success
throughout.

## CON-02 tightened, not exempted

"Send an HTTP request to SharePoint" is an action of the **SharePoint**
connector and is the provisioning route this deployment depends on. A negative
lookahead teaches the rule the difference. A file-level exemption would also
have silenced a real HTTP connector added to that file later, which is the
finding the rule exists for. Warnings: **4**, down from 6.

## The canvas app — what changed this round

**The `.msapp` question is settled, and not by judgement.** I obtained
Microsoft's own Power Platform CLI 2.11.2 and ran it against this source tree.
(NuGet is reachable from here; the .NET 10 runtime was assembled from
`microsoft.netcore.app.runtime.linux-x64` and `microsoft.aspnetcore.app.runtime.linux-x64`
because the dotnet CDN is blocked by policy.)

**`pac canvas pack` cannot originate an app from YAML.**

| Layout | Requires | Evidence |
|---|---|---|
| `SourceCode` | Exactly one `.msapr` archive in the sources directory; the `.pa.yaml` files are an **edit layer** over it | The packer's own assertion string: *"Call to ValidateSources should've ensured the sources directory contains exactly one .msapr file."* Supplying a `.msapr` moves it past validation into packing. |
| `Experimental` | The full PAModel tree — `CanvasManifest.json`, `Controls/*.json`, `Entropy/`, `Checksum.json` — where the control tree lives in **JSON, not YAML** | `pac canvas pack --layout Experimental` on a YAML-only tree: *"The sources directory is invalid."* |

A canvas app's control identities live in a binary archive; the YAML edits
them. There is no supported path from YAML alone to a new app. So the gap was
never effort — it is an artifact only Studio or an authenticated environment
can mint, and no amount of building here produces one.

### What that gap actually costs, and the bridge

It costs **one blank app**. `scripts/build_canvas.sh` does the rest:

```
pac auth create --environment <url> --cloud UsGovDod
pac canvas list                                    # the seed app's id
scripts/build_canvas.sh <app-id> MissionFeedingOperations.msapp
```

It downloads the seed, unpacks it, overlays every screen and component from
this repository, and packs a real `.msapp` with Microsoft's packer. Then add
the `.msapp` to the solution and re-export — and the ZIP carries the app, the
five flows, the connection references and the environment variables together,
which is the deliverable that was being asked for.

Nobody rebuilds a screen, a formula, a gallery or a status badge by hand.

### The canvas source is now verified as Power Fx

Nothing here had ever parsed the `.pa.yaml` as Power Fx — the tests read it as
text. It has now been run through **Microsoft.PowerFx**, the same engine Studio
uses:

```
Power Fx syntax check — 1300 formulas from 20 files
  binding diagnostics ignored: 2000
No syntax errors. Every formula parses under Microsoft.PowerFx.
```

Reproduce with `PAC=<path to pac> python3 scripts/check_powerfx.py`. Without
the CLI it prints SKIPPED and exits 0 — an unavailable checker must not read as
a passing one, and a test asserts that behaviour.

The 2,000 ignored diagnostics are one thing: nothing is connected here, so
every SharePoint source, every named formula from the `.fx` files and every
canvas-host function (`Navigate`, `Back`, `User`, `Defaults`) is out of scope.
Nine "deprecated use of `.`" advisories are the same cascade — the engine
cannot tell record-field access from table-column shorthand on an unbound
identifier, and the ones I spot-checked are correct record access.

**This is a parse result, not a runtime one.** It does not say a formula
returns the right answer against real data. But it moves 3,652 lines of canvas
source from *entirely unverified* to *parses under the real engine*, which is
the largest single reduction in this release's unknowns.

## Test classification — what 530 passing tests actually prove

**A suite written against the generator that produced the artifact can pass in
full while the tests and the generator share one wrong premise.** Counting tests
cannot distinguish that from real coverage, so every test class is classified by
what would have to be wrong for it to still pass. The classification is
*declared* in `scripts/classify_tests.py`, per class, and an unclassified class
fails the release gate — a new test cannot join the total unlabelled.

| Kind | Tests | Share | What a pass means |
|---|---:|---:|---|
| **BEHAVIOURAL** | 239 | 45% | Logic exercised against data, or against an external standard. Something is computed and compared to an answer that did not come out of the code under test. |
| **STRUCTURAL** | 157 | 29% | Two things this repository generates agree. Catches drift; cannot tell you the shared premise is right. |
| **POLICY** | 134 | 25% | A settled decision stays applied. These outlive the decisions they encode. |
| **TOTAL** | **530** | | |

### Three POLICY tests encoded the decision this round reversed

This is not hypothetical. `tests/test_folder_resolver.SeededDestinations` held
three assertions that the four pilot rows must be **ACTIVE** and **VERIFIED**,
and that Portfolio 2's site slug must appear in a note. Every one of those would
have **failed the correct configuration and argued for the rejected one** — the
exact hazard of a policy test outliving its decision.

They are rewritten to the current ruling, with the reversal recorded in the
docstring so the next reader sees that the assertion flipped and why:

| Was | Is now |
|---|---|
| `test_every_portfolio_has_exactly_one_active_destination` — four rows ACTIVE | `test_no_row_ships_active_or_verified` — every row FALSE, `Verified_By` and `Verified_Date` blank |
| `test_the_pilot_rows_are_the_active_ones` | `test_no_row_carries_a_site_url` — `Site_URL` blank on all eight |
| `test_portfolio_two_keeps_its_odd_slug_on_the_record` — asserts the slug | `test_portfolio_two_keeps_its_irregularity_on_the_record` — asserts the warning, and asserts the slug is **absent** |

### Where STRUCTURAL is the only coverage

Three places, and they are the honest limits of this release.

**1. The five flow bodies — 118 actions, 0 BEHAVIOURAL tests.**
`test_flow_bodies` is 40 tests and every one is STRUCTURAL: each body contains
the actions its spec describes, the `runAfter` graph has no cycle, every
`foreach` pins concurrency. **Nothing executes them.** The one exception is the
status expression, which `test_flow_expression` evaluates against the engine's
fixture set — and that found two defects that would otherwise have reached the
tenant, which is a fair measure of what the other 116 actions are not getting.
The right test is a run against a real SharePoint site, and it is not available
here.

**2. Whether the ZIP imports — `test_package`, 52 tests, 0 BEHAVIOURAL.**
They assert the package matches a structure taken from documentation. If that
reading is wrong, all 52 pass and the import still fails naming an internal file.
This is the single largest untested assumption in the release.

**3. Accessibility labels — `EveryInteractiveControlHasAName`, 2 STRUCTURAL.**
Every control declares a label in source. Whether a screen reader announces it
usefully needs Studio's Accessibility Checker and a person.

`docs/TEST_MATRIX.md` keeps a NOT TESTABLE LOCALLY column rather than quietly
omitting these.

### Per class

| Module | Class | Kind | Tests | What a pass means |
|---|---|---|---:|---|
| `test_design_tokens` | `SixStatesExist` | **P** | 1 | the six-state palette is the settled model |
| `test_design_tokens` | `EveryChipIsReadable` | **B** | 2 | WCAG contrast ratios computed from the token values |
| `test_design_tokens` | `AmberIsNotYellow` | **B** | 6 | ΔE2000 and hue separation computed between the two tokens |
| `test_design_tokens` | `TheDocumentedRatiosAreTrue` | **B** | 1 | documented ratios recomputed from the tokens |
| `test_design_tokens` | `ThePrototypeTeachesSixStates` | **S** | 4 | the prototype and the token file agree |
| `test_design_tokens` | `ThePeriodSelectorIsGenerated` | **S** | 3 | the selector reads the generator, not a literal list |
| `test_design_tokens` | `EveryInteractiveControlHasAName` | **S** | 2 | every control in the source declares a label |
| `test_design_tokens` | `NothingTheAdminOwnsIsHardcoded` | **P** | 6 | the five admin-owned values stay in configuration |
| `test_design_tokens` | `ColourIsNeverTheOnlyChannel` | **P** | 3 | accessibility ruling: text and icon accompany colour |
| `test_design_tokens` | `NoCountIsReportedWithoutItsDenominator` | **P** | 6 | the reporting ruling stays applied |
| `test_duplication` | `ApplicabilityAgrees` | **B** | 5 | the Power Fx and Python predicates evaluated on the same cases |
| `test_duplication` | `TheFxStillHasTheShapeTheModelAssumes` | **S** | 4 | the Fx source matches what the comparison assumes |
| `test_duplication` | `OneImplementationPerConcept` | **P** | 4 | one reference implementation per concept |
| `test_duplication` | `TheSecondUploadArchitectureIsGone` | **P** | 3 | the central evidence library stays removed |
| `test_eom01` | `TestIdempotency` | **B** | 3 | the generator run twice against the real registry |
| `test_eom01` | `TestFacilityIdIsNullNotEmptyString` | **B** | 6 | payload inspection across all three scopes |
| `test_eom01` | `TestOnboardingGate` | **B** | 3 | generation gated on the flag, run and counted |
| `test_eom01` | `TestOperatingModelFollowsTheFacility` | **B** | 7 | model filter applied at facility scope only, verified by run |
| `test_eom01` | `TestCatalogueRespected` | **B** | 8 | frequency and scope filters exercised per period |
| `test_eom01` | `TestGeneratedStatus` | **B** | 5 | the status engine run on generated rows |
| `test_eom01` | `TheBackfillWindowIsEnforced` | **B** | 8 | periods inside and outside the window generated and counted |
| `test_eom01` | `EverySixActiveRequirementIsFacilityScope` | **P** | 4 | the programme's scope ruling stays applied |
| `test_flow_bodies` | `TheGraphIsSound` | **B** | 4 | runAfter graph walked for cycles and unreachable actions |
| `test_flow_bodies` | `NothingEnvironmentSpecificIsHardCoded` | **S** | 4 | generated JSON checked for literals |
| `test_flow_bodies` | `ConnectorsAreOnTheAllowlist` | **P** | 2 | the connector allowlist is the settled policy |
| `test_flow_bodies` | `EveryWriteLoopIsSerial` | **S** | 1 | every foreach in the generated JSON pins concurrency |
| `test_flow_bodies` | `TheSpecificationInvariantsHold` | **S** | 28 | each body contains the actions its spec describes |
| `test_flow_bodies` | `EveryFlowImportsDisabled` | **P** | 1 | flows ship Draft by decision |
| `test_flow_expression` | `TheInterpreterIsStrict` | **B** | 5 | the interpreter itself tested on cases with known answers |
| `test_flow_expression` | `TheExpressionIsWellFormed` | **S** | 5 | the emitted expression parses and is shaped as expected |
| `test_flow_expression` | `TheExpressionAgreesWithTheEngine` | **B** | 3 | the expression evaluated against the engine's fixture set |
| `test_folder_resolver` | `FiscalYear` | **B** | 3 | date arithmetic against known DAF fiscal-year boundaries |
| `test_folder_resolver` | `FiscalYearFolder` | **B** | 4 | folder matching against constructed listings |
| `test_folder_resolver` | `MonthFolder` | **B** | 8 | month-folder matching across the naming variants seen on the sites |
| `test_folder_resolver` | `Resolve` | **B** | 6 | end-to-end resolution against constructed listings |
| `test_folder_resolver` | `FailClosed` | **B** | 5 | each failure path exercised and its code checked |
| `test_folder_resolver` | `SeededDestinations` | **P** | 12 | the shape the destination seed ships in |
| `test_folder_resolver` | `Sanitising` | **B** | 4 | path sanitising against adversarial inputs |
| `test_folder_resolver` | `Versioning` | **B** | 3 | version suffixing against existing-file listings |
| `test_folder_resolver` | `SpecAgreesWithTheCode` | **S** | 8 | the definition.md and the resolver say the same thing |
| `test_folder_resolver` | `BindingsAreDocumented` | **S** | 5 | site-bindings.md covers what the schema declares |
| `test_folder_resolver` | `ThePathUsesTheUrlSegment` | **B** | 3 | the built path is checked against the segment, not the display name |
| `test_folder_resolver` | `TheFallbackCeiling` | **B** | 6 | fallback refused at and above the library root, computed per row |
| `test_hardening` | `SplittingFilters` | **B** | 3 | delegable filter splitting exercised on queries |
| `test_hardening` | `TheGuard` | **B** | 5 | the schema guard run against matching and mismatched versions |
| `test_hardening` | `TheGuardCatchesTheDefectThatCostAMonth` | **B** | 3 | the historical defect reproduced and caught |
| `test_hardening` | `EmptyFilterMeansNoConstraint` | **B** | 4 | empty-filter semantics exercised |
| `test_hardening` | `RequiredArtifactsMustSaySomething` | **B** | 4 | the emptiness check run against planted stubs |
| `test_hardening` | `InlineExceptionsMustBeExplained` | **B** | 5 | marker parsing run against good and bad markers |
| `test_hardening` | `TheScanStillPasses` | **B** | 7 | each rule fired on a planted specimen and held off a lookalike |
| `test_hardening` | `ConnectorsMatchTheAllowlist` | **P** | 5 | the connector allowlist is the settled policy |
| `test_package` | `TheFilesAreWellFormed` | **S** | 3 | the emitted XML and JSON parse |
| `test_package` | `TheManifestIsComplete` | **S** | 4 | solution components and configuration agree |
| `test_package` | `NoOrphanedReference` | **S** | 9 | every reference resolves within the package |
| `test_package` | `ThePackageHasNoCanvasApp` | **P** | 4 | no .msapp and no fabricated Canvas component |
| `test_package` | `TheFlowsAreWiredEvenWhereTheyAreUnfinished` | **S** | 10 | each workflow is registered and parameterised |
| `test_package` | `NothingEnvironmentSpecificIsBaked` | **P** | 2 | no connection or environment variable values in the package |
| `test_package` | `VersionsAgree` | **S** | 1 | one version across solution, config and changelog |
| `test_package` | `CustomizationsMatchesTheConfiguration` | **S** | 4 | Customizations.xml and the config files agree |
| `test_package` | `TheDependencyManifestIsUsable` | **S** | 8 | the manifest covers what the package needs |
| `test_package` | `LegacyIntakeShipsUnbound` | **P** | 3 | EOM-02b ships as an unbound template |
| `test_package` | `ImportChecklistIsSequenced` | **P** | 4 | the import order and its gates are settled |
| `test_schema` | `TestSchemaItself` | **B** | 10 | schema invariants computed: nullability, index cap, key shape |
| `test_schema` | `TestRequirementSeed` | **P** | 11 | the requirement catalogue is the settled configuration |
| `test_schema` | `TestConfigurationSeeds` | **P** | 21 | the seeded configuration is the settled configuration |
| `test_schema` | `TestNoHardCodedEnvironment` | **P** | 4 | no environment literal in source |
| `test_schema` | `TestFlowSpecs` | **S** | 8 | flow specs and schema agree |
| `test_schema` | `TestAppSource` | **S** | 7 | app source and schema agree |
| `test_schema_manifest` | `ListsReferencedExist` | **S** | 2 | every list named anywhere exists in the schema |
| `test_schema_manifest` | `ColumnsReferencedExist` | **S** | 5 | every column named anywhere exists in the schema |
| `test_schema_manifest` | `InternalNamesAreSafe` | **B** | 4 | internal-name encoding computed from display names |
| `test_schema_manifest` | `TheManifestIsCurrent` | **S** | 5 | the manifest and the schema agree |
| `test_schema_manifest` | `SchemaVersionIsGated` | **S** | 9 | every flow and the app compare the same version |
| `test_schema_manifest` | `SubmissionIsRequestIdempotent` | **P** | 11 | request idempotency is the settled design |
| `test_schema_manifest` | `OneCurrentSubmissionPerItem` | **P** | 2 | one current submission per item is the settled design |
| `test_schema_manifest` | `ReportIndexTableMatchesTheSchema` | **S** | 3 | the report's table and the schema agree |
| `test_schema_manifest` | `NoDocumentStatesAStaleTotal` | **S** | 1 | every stated total and the schema agree |
| `test_schema_manifest` | `EveryTestIsClassified` | **S** | 2 | every test class carries a declared kind |
| `test_status_engine` | `TestFixtureCases` | **B** | 2 | the engine run against fixture cases with hand-written expected states |
| `test_status_engine` | `TestNonNegotiables` | **B** | 26 | each of the twelve rules exercised on constructed inputs |
| `test_status_engine` | `TestTransliterationsAgree` | **B** | 10 | Python, Power Fx and Logic Apps evaluated against one fixture set |
| `test_status_engine` | `TestReconciliationHeld` | **P** | 8 | the ten reconciliation rulings stay applied |

## The URL sweep — every hit, explained

Swept **all 318 tracked files** with no directory skips, no file skips and no
inline allow markers — a wider net than the scanner itself, which exempts the
four documents that define it and three vendored trees. Patterns: a site path on
`.dps.mil` or `.sharepoint.<tld>` under `/sites/` or `/teams/`; a bare government
host; an address in a real `.mil` namespace.

**29 hits. None is a destination.**

| Class | Hits | Where | Why each is not a leak |
|---|---:|---|---|
| Bare tenant host `usaf.dps.mil` | 15 | `README.md:15`, `configuration/app-config.csv:12`, `deployment/site-bindings.md:101`, `docs/DECISION_LOG.md:44`, `docs/DEPLOYMENT.md:5`, `docs/government-environment-mode.md:15`, `docs/handoffs/README.md:24`, `docs/handoffs/RECONCILIATION.md:341`, `docs/archive/CLAUDE_CODE_HANDOFF_v2.md:7`, `reference/v14/ACTION_DOCUMENT.md:25`, `reference/v14/CLAUDE_CODE_HANDOFF.md:23`, `reference/v14/deployment/site-bindings.md:39`, `security/security-manifest.yaml:16`, `tests/test_hardening.py:301`, `tests/test_schema.py:227` | A host with **no site path**. It names which cloud this is — the correction from GCC High to DoD that invalidated every earlier endpoint — and it identifies no destination. `URL-01` deliberately does not fire on it, and `test_naming_the_tenant_in_prose_is_not_a_leak` pins that. |
| Admin endpoint table | 3 | `docs/government-environment-mode.md:55` | The commercial/GCC High/DoD comparison row. The table **is** the policy; naming the wrong endpoint is the point of the row. Carries an inline `CLD-03` marker with a reason, and the scanner prints it in its ALLOWED section every run. |
| Cloud endpoint table | 2 | `deployment/site-bindings.md:40-41` | Same shape, added this round: the "Not" column names the two commercial Power Platform endpoints in order to forbid them. Inline `CLD-01` markers with reasons. |
| Test specimens | 9 | `tests/test_hardening.py:257,259,269,271,296` | Synthetic `tenant.dps.mil` / `tenant.sharepoint.us` hosts with `ExampleSiteCollection` / `ExampleTeamSite` slugs, each carrying an inline `URL-01` marker. Changed this round from a real host plus a real site slug — a specimen proving a rule fires does not need to be a working destination. |

**Nothing in `configuration/` matched anything.** Every `Site_URL` is blank on
all eight rows, and the site slugs that were in the `Site_Note` column were
removed: the notes now record *that* Portfolio 2's slug is irregular without
reproducing it, and the slug itself lives only in the operator's worksheet.

One hit was fixed rather than explained: `scripts/prerelease_scan.py:139`
quoted a `us.af.mil` address inside the comment introducing the rule that
forbids them. The scanner skips itself, so it could not catch it — the third
time this round a document leaked the thing it was arguing against.

## EOM-02b — verified unbound, from the packaged artifact

Codex reports the trigger still references `MF_Portfolio1_SiteURL` with only the
library blank. **That is not true of this artifact.** Read straight out of the
workflow JSON in the ZIP:

```json
{
  "host": {
    "connectionName": "shared_sharepointonline",
    "operationId": "OnNewFileV2",
    "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
  },
  "parameters": {
    "dataset": "",
    "table": ""
  },
  "authentication": "@parameters('$authentication')"
}
```

Declared parameters, complete:

```
  $connections
  $authentication
  MF_SharePointSiteURL (mfops_MF_SharePointSiteURL)
  MF_ConfigList (mfops_MF_ConfigList)
  MF_UnmatchedList (mfops_MF_UnmatchedList)
  MF_SubmissionList (mfops_MF_SubmissionList)
  MF_SecurityList (mfops_MF_SecurityList)
```

**No `MF_Portfolio*` parameter appears anywhere in the file.** The site is
blank, the library is blank, and there is no portfolio parameter to bind. Codex
was reading an earlier state — the binding it describes did exist and was
removed, along with the parameter declaration, before the previous build.

Its reasoning is right regardless, and it is why the parameter went too: blank
library plus bound site is not unbound. It imports, activates, runs correctly,
and discovers nothing in three portfolios — coverage indistinguishable from full
coverage until someone asks why Portfolio 3 has never had an unmatched file.

One template, duplicated three times after import, each copy bound to a
different site collection. `IMPORT_CHECKLIST.md` step 7 states it as four
imperative boxes; `deployment/site-bindings.md` section 2 is the worksheet;
`tests/test_package.LegacyIntakeShipsUnbound` fails if the trigger regains a
site, a library, or a portfolio parameter.

All five flows import as **Draft** (`StateCode 0`).

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
branch    main
commit    23114e1563776dfd6ac1e920b6e3fd76d99c835f
tag       v1.0.0, local only
tree      clean
history   fast-forward from claude/mission-feeding-eom-build-98fbsi
          no force, no rebase, no history rewritten
```

`main` held one commit — an empty `.gitkeep` — so the merge was a
fast-forward and every commit on it is the branch's, unaltered. The full suite
was re-run **after** the merge, on `main`, and the artifact was rebuilt from
that commit, so the ZIP, the commit and the checksum describe one build.

**The commit hash above is the anchor. The tag is convenience.** `git push
origin v1.0.0` is refused with HTTP 403 — this session's credentials permit
pushing a branch and not creating a tag ref. The commit is on the remote;
only the ref is missing. Recreate it with `git tag -a v1.0.0
23114e1563776dfd6ac1e920b6e3fd76d99c835f` from a session that can, or from the
GitHub releases UI. Nothing depends on it: the build takes any commit-ish.

One caveat on the hash, stated rather than hidden: this file is inside the
commit that follows the one it names, because a file cannot contain its own
commit's hash. `23114e1` is the commit the artifact was **built from** and is
the one to check the checksum against. The commit that records it is its child,
and changes no file the ZIP is packed from — verified by rebuilding after this
was written and confirming the checksum is byte-identical.

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
commit   23114e1563776dfd6ac1e920b6e3fd76d99c835f
branch   main
tag      v1.0.0 (local only — see below)
```

Rebuild it with:

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
| Unit tests | **530 passed**, 0 failed — 239 behavioural, 157 structural, 134 policy |
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
