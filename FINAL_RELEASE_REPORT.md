# Final release report — Mission Feeding Operations R1

## Result

**PARTIAL** — a real solution ZIP containing the flows, environment variables
and connection references, with the canvas app assembled in Studio.

**READY WITH DEPLOYMENT-SIDE REQUIREMENTS**, for **DEV or PILOT only.**

### What the ZIP contains

Hand-authored against the documented schemas:

| | |
|---|---|
| `[Content_Types].xml` | at the archive root, where import expects it |
| `Other/Solution.xml` | manifest, 26 root components |
| `Other/Customizations.xml` | 5 workflows, 3 connection references, 18 environment variable definitions |
| `Workflows/*.json` | five cloud flows, each with its real trigger |

Every flow carries its **real trigger**, its **real connection reference
bindings**, its **environment-variable parameters** and the
schema-compatibility guard that terminates on `CONFIGURATION_REQUIRED` before
any write. All five import **disabled**, which is what the deployment procedure
requires anyway.

**The body of each flow is not implemented.** The logic is specified in
`flows/*/definition.md` and was not invented to fill a JSON file — a flow whose
body was guessed would import cleanly and do the wrong thing, which is worse
than one that is obviously unfinished. Each flow's first action is a Compose
naming its specification and saying so.

### What the ZIP deliberately does not contain

**No `.msapp`, and no placeholder for one.**

The canvas app's internal format is owned by Studio, `pac canvas pack` is being
deprecated, and the source format is mid-transition. A hand-authored file with
the right extension that Studio rejects on open would fail the import with an
error naming an internal file and explaining nothing — and whoever is holding it
would spend an afternoon assuming the tenant was at fault.

`scripts/build_release.sh` **refuses to build** if a `.msapp` appears in the
solution tree, and `tests/test_package.py` fails if the manifest declares a
canvas app component the package does not contain.

`CANVAS_APP_ASSEMBLY.md` covers creating the app **inside the imported
solution**, where it inherits these connection references and environment
variables the moment it exists: data sources, formula paste order, the four
components before the twelve screens, the container hierarchy, and a
twelve-item smoke test.

### Confidence, stated plainly

The XML and flow-definition schemas are documented and stable, and every file
is well-formed, cross-referenced and free of any baked destination. **It has not
been import-tested against a tenant** — PAC CLI cannot authenticate here. That
is item N1 in `docs/TEST_MATRIX.md` and it is not reported as passing.

If the import does reject something, it will be a manifest detail in
`Customizations.xml`, not a corrupt binary, and the error will name the element.

### The one thing this does not become

Not BLOCKED: all 18 stop conditions clear. Not FULL: the canvas app is not in
the package and will not be until it is built in Studio. Not SOURCE: the flows,
connection references and environment variables are real and importable.

## Build

```
branch    claude/mission-feeding-eom-build-98fbsi
commit    d0833bbaf2bd2557a4e676c05d1f42f0464cc67a
tag       v1.0.0
tree      clean
```

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
| Schema Version | 5.0 — 17 lists, 284 columns |
| Requirement Config Version | 13 rows, 8 active |

Checked by the release gate. Any drift blocks the build.

## Artifact

```
dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip
SHA-256  a646731f2b2cc72879f39bc83c6e4110b5f7ed1adbb369482d1eaf78ba9aa497
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

See **Result** above for exactly what is in it and what is not.

## Tests

| | |
|---|---|
| Unit tests | **361 passed**, 0 failed |
| Solution validations | 14 passed, 0 warnings, 0 failures |
| Pre-release security scan | **PASS**, 4 warnings |
| Routing dry run, four sites | **PASS** — 4 happy paths, 7 failure paths |
| EOM-01 dry run | 32 rows across the 5-base pilot |
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
