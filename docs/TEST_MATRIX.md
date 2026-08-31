# Test matrix — Phase 6

Every row carries exactly one of **PASS**, **PASS WITH WARNING**, **FAIL**,
**NOT TESTABLE LOCALLY**.

**NOT TESTABLE LOCALLY is an honest outcome and is never reported as PASS.** A
tenant result is never inferred. Each one names what is needed and who does it.

Run everything: `bash tests/run_tests.sh`

```
317 unit tests                      OK
 14 solution validations            0 warnings, 0 failures
    pre-release security scan       PASS, 3 warnings
    routing dry run, four sites     PASS
    EOM-01 dry run                  32 rows, 5 of 103 onboarded
```

---

## Routing — four site collections

Representative bindings; no real site URL is used. The month folder naming
differs per portfolio **on purpose**: four sites name their root folders four
different ways, so assuming they agree about months is the assumption
`deployment/site-bindings.md` exists to prevent.

| # | Test | Result | Detail |
|---|---|---|---|
| R1 | Portfolio 1 resolves | PASS | `…/H. Monthly Data Call/FY26/Aug 26` |
| R2 | Portfolio 2 resolves — the `Legacy_` slug | PASS | `…/5. Monthly Data Call/FY 26/August 2026` |
| R3 | Portfolio 3 resolves | PASS | `…/Monthly Data Call/FY2026/08. August` |
| R4 | Portfolio 4 resolves | PASS | `…/Monthly Data Call/FY26/08` |
| R5 | FY folder missing | PASS | root, `Needs_Filing`, note names FY26 |
| R6 | Month folder missing | PASS | root, `Needs_Filing`, note names August 2026 |
| R7 | Site binding missing | PASS | `CONFIGURATION_REQUIRED` |
| R8 | Ambiguous month — `08` and `August 2026` both present | PASS | resolves to the **named** folder |
| R9 | Installation not mapped to a portfolio | PASS | `DESTINATION_NOT_CONFIGURED` |
| R10 | Destination inaccessible / unverified | PASS | `DESTINATION_NOT_VERIFIED` |
| R11 | **No folder is created, in any case** | PASS | reads only; the resolver is handed a read-only view with no create to call |
| R12 | **Fallback never rises above the Monthly Data Call root** | PASS | a blank `Root_Folder` is refused rather than falling back to the library |
| R13 | Fallback never reaches another portfolio | PASS | each fallback stays inside its own root, checked across all four |
| R14 | Seeded rows fail closed | PASS | `Site_URL` blank, `Verified_By` blank, `Active_Flag` FALSE |

`scripts/routing_dryrun.py` · `tests/test_folder_resolver.py` (57 tests)

## Registry and generation

| # | Test | Result | Detail |
|---|---|---|---|
| G1 | Registry loads | PASS | 103 installations, 154 facilities |
| G2 | Regeneration is byte-identical | PASS | the generator and its output cannot drift |
| G3 | IDs deterministic, 1:N preserved | PASS | 0 orphans, all IDs unique |
| G4 | Blank portfolio not auto-assigned | PASS | 20 blank, recorded as issues |
| G5 | Duplicates recorded not dropped | PASS | 151 issues, 107 exact duplicates |
| G6 | Expected package generation | PASS | 32 rows for the 5-base pilot |
| G7 | Idempotency — a second run creates nothing | PASS | |
| G8 | Only onboarded installations generate | PASS | 5 of 103; 98 reported as awaiting onboarding |
| G9 | Food 2.0 and MAFFO excluded from Legacy requirements | PASS | `model_applies` |
| G10 | 1119-1 generates nothing | PASS | Conditional, all 12 months |
| G11 | 1038 only Dec/Mar/Jun/Sep | PASS | |
| G12 | Weekend suspense rolls | PASS | Sat 5 Sep → Tue 8 Sep past Labor Day |
| G13 | A vocabulary filter matching nothing raises | PASS | reproduced with a de-normalised registry |
| G14 | Installation- and Contract-scope rows carry null `Facility_ID` | PASS | not empty string |

`tests/test_eom01.py` (32) · `tests/test_hardening.py` (33)

## Submission, QC, versioning, status

| # | Test | Result | Detail |
|---|---|---|---|
| S1 | Duplicate-request retry produces one submission | PASS | `Submission_Request_ID` required, indexed, in the unique key, checked before the file write |
| S2 | The app mints the key when the file is chosen, not at Submit | PASS | a second press reuses it |
| S3 | The app does not name its own user | PASS | `uploadedBy` is not in the payload |
| S4 | Supersede runs before create | PASS | exactly one current per item |
| S5 | No screen supersedes a submission | PASS | zero patch sites |
| S6 | QC verdicts and required fields | PASS | comment required on return; suspense required on correction |
| S7 | All six status transitions | PASS | 30 fixture cases + 10 package cases |
| S8 | Rollups over semantic statuses | PASS | `[ACCEPTED, NOT_DUE, NOT_DUE]` is IN_PROGRESS |
| S9 | Wrong document is not permanently red | PASS | NOT_SATISFIED before the final call, OVERDUE after |
| S10 | Both on-time facts recorded independently | PASS | |

`tests/test_status_engine.py` (46) · `tests/test_schema_manifest.py` (38)

## Configuration, security, accessibility

| # | Test | Result | Detail |
|---|---|---|---|
| C1 | Security scope and deep-link block | PASS | `MF_LiveScope`; expired access stops working |
| C2 | Missing environment variable | PASS | fails closed to `CONFIGURATION_REQUIRED` |
| C3 | Schema version mismatch disables writes | PASS | for developers too |
| C4 | Notification enable and disable | PASS | two rules ship enabled by design, six disabled |
| C5 | Every declared connector is on the allowlist | PASS | the stale Teams reference was removed |
| C6 | Every chip clears 4.5:1 on its own background | PASS | measured, not asserted |
| C7 | Amber and yellow are perceptually distinct | PASS | ΔE2000 25, 41° hue, ≥13.9 under three CVD simulations |
| C8 | Every interactive control has an accessible name | PASS | 0 offenders |
| C9 | No screen hardcodes a month in a picker | PASS | |
| C10 | Documented contrast ratios match the tokens | PASS | recomputed from source |

`tests/test_design_tokens.py` (34) · `tests/test_duplication.py` (16) · `tests/test_schema.py` (61)

## SharePoint failure

| # | Test | Result | Detail |
|---|---|---|---|
| X1 | Partial write returns `SUBMISSION_NOT_CONFIRMED` | PASS | specified and asserted in the flow spec; **not exercised against a tenant** |
| X2 | A real SharePoint outage mid-write | NOT TESTABLE LOCALLY | needs a tenant and a way to interrupt the connector. Owner: the build team, during pilot |

---

## NOT TESTABLE LOCALLY

Each of these is real, none is a defect, and none may be reported as passing.

| # | What | What is needed | Who |
|---|---|---|---|
| N1 | PAC CLI solution validation | An authenticated PAC CLI session against the tenant. `MF_App_Config.PacCliAuthorized` is still `UNKNOWN`. | Build team, after Gate 1 |
| N2 | Solution import | A Power Platform environment in the DoD cloud, and permission to import | Build team |
| N3 | Power Apps Accessibility Checker | The maker portal with the app open. The static checks here cover contrast and accessible names; the Checker covers tab order, screen reader order and control roles | Build team, before UAT |
| N4 | Real SharePoint writes | The four site collections, bound and verified | Build team, at Gate 3b |
| N5 | Actual connector behaviour in DoD | The tenant. New connectors are disabled by default in DoD until an administrator reviews them | Tenant administrator |
| N6 | Tenant DLP policy | The Power Platform admin centre | Tenant administrator |
| N7 | The real month folder naming on each of the four sites | Somebody opening each site and reading it. **This is the single most likely cause of a broken first day** | Whoever administers each portfolio site |
| N8 | Data-layer permission enforcement | A SharePoint-side change; see `docs/security-open-issue.md` | SharePoint administrator + ISSM |
| N9 | Whether a list already exists on the destination side with different internal names | Reading the four sites' existing lists | Build team, at Gate 2 |
| N10 | Delegation behaviour at real volume | 5,000+ rows in `MF_EOM_Item` on a real list | Build team, after the first two periods |

## No FAIL outstanding

Every row above is PASS or NOT TESTABLE LOCALLY. The three scan warnings are
placeholder accounts in a file named `.sample`, which is what that file is for.
