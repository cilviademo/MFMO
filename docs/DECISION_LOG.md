# Decision log — what was superseded, when, and what carries it now

One line per superseded decision. This is the shortest place to find out why the
repository says what it says; `docs/handoffs/RECONCILIATION.md` carries the
long-form reasoning as corrections C1–C35.

## Authority order

Newest wins. Where two documents disagree, the newer is followed, the older is
archived with a header naming its replacement, and the implementation follows
the newer.

| # | Source | Governs |
|---|---|---|
| 1 | `reference/v14/ACTION_DOCUMENT.md` | Anything it touches. It is explicitly a delta and it is the latest. |
| 2 | `reference/v14/CLAUDE_CODE_HANDOFF.md` | Accumulated build state |
| 3 | `docs/build-notes.md` and its addenda | The programme's own answers |
| 4 | `docs/status-calculation.md` | THE status definition. Arbitrates status disputes. |
| 5 | `security/SECURITY_PROMPTS.md` | The security directive |
| 6 | everything else | |

Two carve-outs, both narrower than they look:

**Where a snapshot's code disagrees with the same snapshot's decision table,
the table wins.** This has happened in every snapshot delivered — v3 shipped
three parallel status functions already diverged from its own table, v11 a
four-state Power Fx block under a twelve-rule decision order, v14 a
construct-and-create flow spec under a find-never-create action document.

**`CODEX_BUILD_HANDOFF.md` still governs engineering discipline** — one engine,
delegable queries, no fabricated artifacts — because nothing later revisits
those. It is not an authority on the domain.

---

## Superseded decisions

| # | What changed | When | Why | Carried now by |
|---|---|---|---|---|
| D-01 | **Central evidence library retired.** Submissions were written into one `Mission Feeding Evidence` library on the app's own site, with `EOM_Root_Path` and `EvidenceRootPath` telling the intake flow which subtree to watch and which to ignore. R1 writes directly into each portfolio's own authoritative destination. | 31 Aug 2026 | One authoritative copy. A second copy creates ambiguity about which is authoritative, a retention problem, and broken links when the two diverge. | `flows/EOM02-Submission/definition.md`, `configuration/document-destinations.csv` |
| D-02 | **Four portfolio channels in one Teams site → four separate site collections.** | 31 Aug 2026 | The routing finding. Portfolio 2's slug carries a `Legacy_` prefix the other three do not; a URL built by pattern 404s on exactly one portfolio. | `deployment/site-bindings.md`, `MF_Document_Destination` |
| D-03 | **Construct-and-create → find-never-create.** The flow rendered `{FiscalYear}/{ReportingPeriod}/{InstallationName}/{RequirementCode}` and created missing folders. It now matches `{FiscalYearShort}/{MonthFolder}` against folders that already exist. | 31 Aug 2026 | A flow that creates folders eventually produces `Aug 26` beside someone's `August 2026`, and nobody notices for a month. | `scripts/folder_resolver.py`, `flows/EOM02-Submission/definition.md` |
| D-04 | **`Channel_Type` gate → `Active_Flag` + `Verified_By` + `Site_URL`.** | 31 Aug 2026 | `Channel_Type` went away with the four-channels model. A spec that fails closed on an absent column fails open. | `scripts/folder_resolver.check_destination` |
| D-05 | **Tenant cloud GCC High / UNKNOWN → DoD.** | 31 Aug 2026 | `usaf.dps.mil` / `dod.teams.microsoft.us`. Every GCC High endpoint written before this date is wrong for this deployment. | `docs/government-environment-mode.md`, `MF_App_Config.TenantCloud` |
| D-06 | **Four status states → six.** Colour carries ownership, not severity. | earlier, ratified 31 Aug 2026 | Amber (base owes, has runway) and yellow (AFSVC owes) are opposite situations. | `docs/status-calculation.md`, `scripts/status_engine.py` |
| D-07 | **Amber and yellow given distinct hues.** They were 1.16:1 apart. | 31 Aug 2026 | The split exists to show who owes the item at a glance, and at 1.16:1 it does not. | `docs/accessibility.md`, `canvas-app/formulas/App.Formulas.fx` |
| D-08 | **"3:1 between the two text colours" → ΔE2000 ≥ 20 and ≥ 30° of hue.** | 31 Aug 2026 | The 3:1 test cannot be passed: WCAG contrast is a luminance ratio, and forcing 3:1 between two chip texts makes one fail 4.5:1 against its own tint. | `docs/accessibility.md`, `tests/test_design_tokens.py` |
| D-09 | **Six roles → two, with capability in flags.** `Can_Grant_Access` defaults FALSE even for Portfolio Managers. | earlier, ratified 31 Aug 2026 | If every PM could grant PM, the role self-propagates. | `docs/access-management.md`, `security/role-matrix.csv` |
| D-10 | **One suspense → two, and two dates → four.** Nominal for reporting, effective for evaluation. | earlier, ratified 31 Aug 2026 | Leadership sees "the 5th"; the base is held to a date they can meet. | `docs/status-calculation.md` |
| D-11 | **`EOM-05 App Upload` → `EOM-02 Submission`; `EOM-02 File Intake` → `EOM-02b Legacy Intake`.** | 31 Aug 2026 | The app is the front door; discovery is the exception route. Names now match the programme handoff. | `flows/README.md` |
| D-12 | **Path-based intake deduplication → GUID.** | 31 Aug 2026 | Under `FIND_OR_ROOT` a file is moved *by design* by the human who files it. A path check would rediscover it as a stray the day somebody tidied up. | `flows/EOM02b-LegacyIntake/definition.md` |
| D-13 | **Vocabulary filters checked by inspection → asserted before generation.** | 31 Aug 2026 | Twice a filter matched nothing and reported success. | `scripts/vocabulary_guard.py` |
| D-14 | **Required release artifacts checked for existence → checked for content.** | 31 Aug 2026 | `ROLLBACK.md` shipped as a zero-byte file and passed. | `scripts/prerelease_scan.py` REQ-02 |
| D-15 | **Attachments control → EOM-02.** | earlier | The control binds to a Form, targets lists rather than libraries, and behaves badly on Teams and mobile. That is a reason not to use the control, not a reason to stop people uploading through the app. | `flows/EOM02-Submission/definition.md` |
| D-16 | **Naive colour rollup removed.** "Any 1 then 1, any 2 then 2" marked `[ACCEPTED, NOT_DUE, NOT_DUE]` Complete. | earlier | Rollups run over semantic statuses, never colours. | `powerbi/MF_EOM_Status.md`, `scripts/status_engine.package_state` |

## Archived documents

| Document | Superseded by | Why kept |
|---|---|---|
| `docs/archive/figma-prompt-v1.md` | `docs/figma-prompt-v2.md` | v2 says so itself — 27 sections averaged toward the middle by generation tools. v1's section-by-section reasoning about what the UI must not do is more detailed and still sound. |
| `docs/archive/MASTER_HANDOFF-consolidated.md` | `docs/handoffs/MASTER_HANDOFF_2026-08-31.md` | The later document states it supersedes earlier assumptions. `RECONCILIATION.md` still cites this one by section. |
| `docs/archive/CLAUDE_CODE_HANDOFF_v2.md` | `reference/v14/CLAUDE_CODE_HANDOFF.md`, and above it `ACTION_DOCUMENT.md` | Its statement of the data-layer scope problem is the clearest written anywhere. Two of its facts are now wrong and its header says which. |

`docs/build-notes.md` is **not** archived. Its folder-structure section is
superseded and is marked so in place, because the rest of the document is the
programme's current answers and the reasoning in that section — what the path
tells you and what it does not — is unaffected by where the folders live.

`docs/archive/` is excluded from the pre-release scan by an explicit path, not
by directory name: a superseded document necessarily quotes the endpoints and
structures it was superseded *for*, and nothing there is on the packaging path.
A directory called `archive` anywhere else in the tree is still scanned.
