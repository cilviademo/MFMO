# Final release report — Mission Feeding Operations R1

## Result

**READY WITH DEPLOYMENT-SIDE REQUIREMENTS** — for **DEV or PILOT only.**

Not BLOCKED: all 18 stop conditions clear. Not READY without qualification: the
Power Platform build has not started, so the artifact in `dist/` is the
solution **envelope** and is not yet importable, and 16 destination-side
resources must already exist before any of this runs.

## Build

```
branch    claude/mission-feeding-eom-build-98fbsi
commit    a200a3dc9f6ebdd107530b979dfdf9c7fa51e36e
tag       v1.0.0
tree      clean
```

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
| Schema Version | 5.0 — 17 lists, 284 columns |
| Requirement Config Version | 13 rows, 8 active |

Checked by the release gate. Any drift blocks the build.

## Artifact

```
dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip
SHA-256  a79d208c4100d3c9c7644688d048912c115db628541e6171d9b3a473c6c6078e
```

Packed from the tagged commit by `scripts/build_release.sh`, not from the
working tree. The build is **reproducible** — timestamps are normalised, so the
same tag always yields the same checksum. Version, commit and checksum describe
the same build.

```
bash scripts/build_release.sh v1.0.0
```

**The ZIP and its checksum are not committed.** `SHA256SUMS.txt` records the
commit it was built from, so committing it would change that commit, change the
recorded hash, and need another commit — it never converges. A build output that
names its own commit cannot live inside that commit. Rebuild it from the tag;
the bytes are identical every time.

**It contains the solution envelope only** — `Solution.xml` and
`Customizations.xml`. There is no `.msapp` and no flow `definition.json`,
because the canvas app has not been authored in Power Apps and the flows have
not been built. The envelope declares components it does not contain, so
importing it will fail on the missing components.

That is the state of the programme, not a defect in the package. Calling it an
importable solution would be the exact failure this consolidation was run to
prevent. `dist/MissionFeedingOperations_1.0.0/README.md` says so on its first
line.

## Tests

| | |
|---|---|
| Unit tests | **346 passed**, 0 failed |
| Solution validations | 14 passed, 0 warnings, 0 failures |
| Pre-release security scan | **PASS**, 3 warnings |
| Routing dry run, four sites | **PASS** — 4 happy paths, 7 failure paths |
| EOM-01 dry run | 32 rows across the 5-base pilot |
| Release gate | **NOT BLOCKED** — 18 stop conditions |
| **NOT TESTABLE LOCALLY** | **10 items**, each with an owner, in `docs/TEST_MATRIX.md` |

The three warnings are placeholder accounts in `security-mapping.sample.csv`,
which is what that file is for. They only load with `-IncludeSampleData`.

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
