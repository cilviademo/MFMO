<!-- Regenerate the file list with `git ls-files`; the classifications are
     deliberate and are maintained by hand. -->

# Repository inventory

Every tracked file, classified. Produced for the R1 release consolidation.

| Class | Meaning |
|---|---|
| **KEEP** | Live source, live documentation, or vendored prior art kept for traceability |
| **MERGE** | Content that belongs in another file (none outstanding — see below) |
| **ARCHIVE** | Superseded documentation, moved to `docs/archive/` with a header naming what replaced it |
| **GENERATED** | Produced by a script. Never edited by hand; regenerate instead |
| **RELEASE-ONLY** | Exists to describe or hold release artifacts, not part of the application |

**Documentation is archived, never deleted.** History is cheap; a decision
rediscovered from scratch is not. Executable code is different — a superseded
implementation is removed from the source and packaging path in the same commit
that replaces it, and only its *explanation* is archived. See Phase 3 in
`docs/DECISION_LOG.md`.

**MERGE is empty.** Nothing in the tree is content awaiting a home in another
file. Three documents were superseded outright and were archived rather than
merged, because each is a complete document whose value is the reasoning it
records, not fragments to be folded into something else.


## `(root)`

Release-level documents.

| File | Class | Note |
|---|---|---|
| `.gitignore` | KEEP |  |
| `CHANGELOG.md` | KEEP |  |
| `README.md` | KEEP |  |
| `ROLLBACK.md` | KEEP |  |

## `scripts`

The reference implementations and the gates. Python, no dependencies beyond the standard library.

| File | Class | Note |
|---|---|---|
| `scripts/eom_schema.py` | KEEP | SINGLE SOURCE OF TRUTH for lists, columns and SharePoint INTERNAL names. Edit here only. |
| `scripts/folder_resolver.py` | KEEP | THE destination resolver. Find, never create. |
| `scripts/gen_registry.py` | KEEP | QRG -> registry. Its outputs are GENERATED; it is not. |
| `scripts/generate_expected_items.py` | KEEP | EOM-01 reference implementation. |
| `scripts/prerelease_scan.py` | KEEP | The release gate. FAIL means do not export. |
| `scripts/status_engine.py` | KEEP | THE status engine. One evaluation, twelve rules, six states. |
| `scripts/validate_solution.py` | KEEP | Delegation, accessibility and staleness gate. |
| `scripts/vocabulary_guard.py` | KEEP | The zero-match assertion every generator runs before generating. |

## `tests`

The suite that holds every transliteration to its reference implementation.

| File | Class | Note |
|---|---|---|
| `tests/fixtures/status_cases.json` | KEEP |  |
| `tests/run_tests.sh` | KEEP |  |
| `tests/test_design_tokens.py` | KEEP |  |
| `tests/test_eom01.py` | KEEP |  |
| `tests/test_folder_resolver.py` | KEEP |  |
| `tests/test_hardening.py` | KEEP |  |
| `tests/test_schema.py` | KEEP |  |
| `tests/test_status_engine.py` | KEEP |  |

## `configuration`

Seed data imported into SharePoint lists. The registry is real; two files are marked `.sample`.

| File | Class | Note |
|---|---|---|
| `configuration/app-config.csv` | KEEP |  |
| `configuration/connection-references.json` | KEEP |  |
| `configuration/document-destinations.csv` | KEEP | Four rows, all unbound, unverified and inactive. EOM-02 fails closed on all three. |
| `configuration/environment-variables.json` | KEEP |  |
| `configuration/facilities.csv` | GENERATED | Regenerate: `python3 scripts/gen_registry.py` |
| `configuration/feature-flags.csv` | KEEP |  |
| `configuration/installations.csv` | GENERATED | Regenerate: `python3 scripts/gen_registry.py` |
| `configuration/non-duty-days.sample.csv` | KEEP | SAMPLE. Real non-duty days are tenant data. |
| `configuration/notification-rules.csv` | KEEP |  |
| `configuration/qrg-data-quality.csv` | GENERATED | Regenerate: `python3 scripts/gen_registry.py` |
| `configuration/requirements.csv` | KEEP |  |
| `configuration/security-mapping.sample.csv` | KEEP | SAMPLE. Contains placeholder accounts the scanner warns about by design. |

## `data`

The scrubbed QRG the registry was generated from.

| File | Class | Note |
|---|---|---|
| `data/QRG__Scrubbed_.csv` | KEEP | Source of record for the registry. Never edited by hand. |

## `canvas-app`

`.pa.yaml` and `.fx` — **this is the app**. The `.msapp` is a build output.

| File | Class | Note |
|---|---|---|
| `canvas-app/formulas/App.Formulas.fx` | KEEP | Colour tokens, config readers, scope. No screen may declare a colour or a scope rule. |
| `canvas-app/formulas/Cascade.fx` | KEEP |  |
| `canvas-app/formulas/Delegation.fx` | KEEP |  |
| `canvas-app/formulas/StatusEngine.fx` | KEEP | Transliteration of status_engine.py. Held equal by tests, never edited independently. |
| `canvas-app/src/App.pa.yaml` | KEEP |  |
| `canvas-app/src/Components/cmpEOMItem.pa.yaml` | KEEP |  |
| `canvas-app/src/Components/cmpEmptyState.pa.yaml` | KEEP |  |
| `canvas-app/src/Components/cmpMetricCard.pa.yaml` | KEEP |  |
| `canvas-app/src/Components/cmpStatusBadge.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrAccessRequest.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrActivity.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrAdminRequirements.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrCalendar.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrDiagnostics.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrHome.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrInstallation.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrMaintenance.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrNoAccess.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrReview.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrUnmatched.pa.yaml` | KEEP |  |
| `canvas-app/src/Screens/scrUpload.pa.yaml` | KEEP |  |

## `flows`

Power Automate specs in Markdown, deliberately not fabricated JSON.

| File | Class | Note |
|---|---|---|
| `flows/EOM01-ExpectedPackage/definition.md` | KEEP |  |
| `flows/EOM02-Submission/definition.md` | KEEP |  |
| `flows/EOM02b-LegacyIntake/definition.md` | KEEP |  |
| `flows/EOM03-Reconciliation/definition.md` | KEEP |  |
| `flows/EOM04-Notifications/definition.md` | KEEP |  |
| `flows/README.md` | KEEP |  |

## `provisioning`

PowerShell: capability gates, list and index creation, configuration seeding.

| File | Class | Note |
|---|---|---|
| `provisioning/Provision-MFOpsLists.ps1` | KEEP |  |
| `provisioning/Seed-MFOpsConfiguration.ps1` | KEEP |  |
| `provisioning/Verify-MFOpsCapabilities.ps1` | KEEP |  |

## `solution`

Solution packaging envelope. Version and connection references only; no behaviour.

| File | Class | Note |
|---|---|---|
| `solution/README.md` | KEEP |  |
| `solution/src/Other/Customizations.xml` | KEEP |  |
| `solution/src/Other/Solution.xml` | KEEP |  |

## `powerbi`

Semantic model, measures and RLS for the COP.

| File | Class | Note |
|---|---|---|
| `powerbi/MF_EOM_Status.md` | KEEP |  |

## `security`

The directive, the machine-verified manifest, the connector allowlist, the role matrix.

| File | Class | Note |
|---|---|---|
| `security/SECURITY_PROMPTS.md` | KEEP |  |
| `security/connector-allowlist.yaml` | KEEP |  |
| `security/role-matrix.csv` | KEEP |  |
| `security/security-manifest.yaml` | KEEP |  |

## `deployment`

What has to be true on the destination side, and who does it.

| File | Class | Note |
|---|---|---|
| `deployment/site-bindings.md` | KEEP | The four site collections. Required release artifact; the scan fails without it. |

## `docs`

Settled decisions, the runbook, the prototype, the decision record.

| File | Class | Note |
|---|---|---|
| `docs/DEPLOYMENT.md` | KEEP |  |
| `docs/MF_EOM_Data_Dictionary.csv` | GENERATED | Regenerate: `python3 scripts/eom_schema.py --dictionary` |
| `docs/REPOSITORY_INVENTORY.md` | KEEP |  |
| `docs/access-management.md` | KEEP |  |
| `docs/accessibility.md` | KEEP |  |
| `docs/archive/CLAUDE_CODE_HANDOFF_v2.md` | ARCHIVE |  |
| `docs/archive/MASTER_HANDOFF-consolidated.md` | ARCHIVE |  |
| `docs/archive/figma-prompt-v1.md` | ARCHIVE |  |
| `docs/build-notes.md` | KEEP | The programme's own answers. Its folder-structure section is marked superseded in place. |
| `docs/data-model.md` | GENERATED | Regenerate: `python3 scripts/eom_schema.py --markdown` |
| `docs/design-system.md` | KEEP |  |
| `docs/figma-prompt-registry.md` | KEEP |  |
| `docs/figma-prompt-v2.md` | KEEP |  |
| `docs/government-environment-mode.md` | KEEP |  |
| `docs/handoffs/CODEX_BUILD_HANDOFF.md` | KEEP |  |
| `docs/handoffs/MASTER_HANDOFF_2026-08-31.md` | KEEP |  |
| `docs/handoffs/RECONCILIATION.md` | KEEP | The decision record. C1-C35. |
| `docs/mf-operations-prototype.html` | KEEP | Working prototype. Carries a staleness banner; predates parts of the current model. |
| `docs/native-visuals.md` | KEEP |  |
| `docs/powerapps-translation.md` | KEEP |  |
| `docs/prototype-notes.md` | KEEP |  |
| `docs/security-open-issue.md` | KEEP |  |
| `docs/status-calculation.md` | KEEP | THE status definition. Arbitrates disputes. Carries no Power Fx by design. |

## `dist`

Release ZIPs and their documentation.

| File | Class | Note |
|---|---|---|
| `dist/README.md` | RELEASE-ONLY |  |

## `reference`

Prior snapshots and the Figma design build, **as delivered and unmodified**. Not live source, never built, never packaged. `reference/README.md` lists what is known stale in each.

**175 files, all KEEP.** Listing them individually would bury the
classifications that carry information. The rule for the whole tree is
the same: vendored unmodified, never edited to "fix" it, never on the
packaging path.

* `reference/AFSVC-Shield.png` — 1 file(s)
* `reference/README.md` — 1 file(s)
* `reference/figma-build` — 32 file(s)
* `reference/v11` — 54 file(s)
* `reference/v14` — 57 file(s)
* `reference/v3` — 30 file(s)
