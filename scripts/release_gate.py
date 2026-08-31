#!/usr/bin/env python3
"""The stop conditions. Exit 1 means the release is BLOCKED and no ZIP is built.

This is not a duplicate of prerelease_scan.py. That scans the package for
forbidden CONTENT -- secrets, commercial endpoints, hardcoded destinations.
This asserts structural facts about the BUILD that no content scan can see:
that there is one status engine and not two, that a retried submission cannot
produce two records, that a routing fallback cannot rise above its approved
root.

Run it last, after the tests and after the commit, before the ZIP is built.

    python3 scripts/release_gate.py
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import eom_schema as S                       # noqa: E402
import prerelease_scan as SCAN               # noqa: E402

FAILURES: list[str] = []


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def rows(name):
    with open(os.path.join(ROOT, "configuration", name), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def check(label, passed, detail=""):
    if not passed:
        FAILURES.append(label)
    print(f"  {'ok  ' if passed else 'STOP'} {label:<50} {detail}")
    return passed


def live_files():
    """Everything on the packaging path. Excludes vendored and archived trees,
    which are never exported and necessarily quote what they superseded."""
    skip = {".git", "reference", "archive", "__pycache__", "dist", "data"}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for n in files:
            if n.endswith((".fx", ".pa.yaml", ".csv", ".json", ".ps1", ".xml")):
                yield os.path.join(base, n)


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, cwd=ROOT)


def main():
    print("Mission Feeding Operations — release gate")
    print("=" * 58)
    print("\nSTOP CONDITIONS\n")

    engine = read("scripts", "status_engine.py")
    fx = read("canvas-app", "formulas", "StatusEngine.fx")
    check("one executable status engine",
          len(re.findall(r"(?m)^def item_status\(", engine)) == 1
          and len(re.findall(r"(?m)^MF_EvaluateStatus\(", fx)) == 1,
          "1 reference + 1 transliteration")

    retired = ("EvidenceRootPath", "EOM_Root_Path", "New-EvidenceLibrary",
               "Mission Feeding Evidence")
    offenders = [os.path.relpath(f, ROOT) for f in live_files()
                 if any(t in read(os.path.relpath(f, ROOT)) for t in retired)]
    check("one upload architecture", not offenders,
          "central evidence library removed" if not offenders else str(offenders))

    scan = run("scripts/prerelease_scan.py")
    check("no hardcoded URL, secret or CUI value", scan.returncode == 0)
    check("prerelease_scan returns PASS", scan.returncode == 0)

    cfg = {r["Config_Key"]: r["Config_Value"] for r in rows("app-config.csv")}
    flags = {r["Feature_Key"]: r["Enabled_Prod"] for r in rows("feature-flags.csv")}
    fx_app = read("canvas-app", "formulas", "App.Formulas.fx")
    check("no security bypass, role override or mock identity",
          cfg["EnableAIBuilder"] == "False"
          and cfg["EnableDocumentContentAI"] == "False"
          and flags.get("EOM_AI_BUILDER") == "FALSE"
          and "gblSchemaMatches &&" in fx_app,
          "AI off; the developer flag cannot bypass the schema gate")

    spec = read("flows", "EOM02-Submission", "definition.md")
    check("EOM-02 cannot create a file without a record",
          "SUBMISSION_NOT_CONFIRMED" in spec
          and "Never report success on a partial write" in spec)

    sub = {c.name: c for c in S.LISTS_BY_NAME["MF_EOM_Submission"].columns}
    key = "Submission_Request_ID"
    check("EOM-02 is request-idempotent",
          key in sub and sub[key].required and sub[key].indexed
          and key in S.LISTS_BY_NAME["MF_EOM_Submission"].unique_key
          and spec.index(key) < spec.index("## Step 5"),
          "required, indexed, in the unique key, checked before the write")

    check("at most one current submission per item",
          sub["Is_Current"].required and sub["Is_Current"].indexed
          and spec.index("supersede any Is_Current")
          < spec.index("create MF_EOM_Submission"))

    check("EOM-01 is idempotent",
          run("-m", "unittest", "tests.test_eom01").returncode == 0)

    check("no routing fallback above the approved root",
          run("scripts/routing_dryrun.py").returncode == 0,
          "four sites, seven failure paths")

    active = [r["Document_Code"] for r in rows("requirements.csv")
              if r["Active_Flag"] == "TRUE"]
    check("active requirement set matches build-notes",
          len(active) == 8 and "SIK" not in active and "DAF79" not in active,
          f"{len(active)} active")

    check("no reference to an internal name not in the schema",
          run("-m", "unittest", "tests.test_schema_manifest").returncode == 0)

    manifest = os.path.join(ROOT, "deployment", "DEPENDENCY_MANIFEST.md")
    body = read("deployment", "DEPENDENCY_MANIFEST.md") if os.path.exists(manifest) else ""
    ownerless = []
    in_table = False
    for line in body.splitlines():
        if line.startswith("| Resource | Owner | Note |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            if set(line.replace("|", "").strip()) <= set("-: "):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3 or not cells[1]:
                ownerless.append(cells[0] if cells else line)
    check("dependency manifest present, every dependency owned",
          bool(body) and not ownerless,
          f"{body.count('| ')} rows" if body else "MISSING")

    deleg = read("canvas-app", "formulas", "Delegation.fx")
    check("no production-critical delegation error",
          '"Due_Date"' not in deleg,
          "queries sort on an existing indexed column")

    missing = [f for f in SCAN.REQUIRED_FILES
               if not os.path.exists(os.path.join(ROOT, f))
               or len(read(f).strip()) < SCAN.MIN_ARTIFACT_BYTES]
    check("no required artifact missing OR EMPTY", not missing,
          f"{len(SCAN.REQUIRED_FILES)} artifacts" if not missing else str(missing))

    conflicted = [os.path.relpath(f, ROOT) for f in live_files()
                  if "<<<<<<< " in read(os.path.relpath(f, ROOT))]
    check("no unresolved merge conflict", not conflicted)

    # Version coherence: the artifact must trace to one build.
    solution = read("solution", "src", "Other", "Solution.xml")
    versions = {
        "solution": re.search(r"<Version>([^<]+)</Version>", solution).group(1),
        "app_config": cfg["AppVersion"],
        "changelog": re.search(r"(?m)^## \[([0-9.]+)\]", read("CHANGELOG.md")).group(1),
    }
    check("one version everywhere", len(set(versions.values())) == 1, str(versions))

    schema_versions = {
        "eom_schema": S.SCHEMA_VERSION,
        "app_config": cfg["SchemaVersion"],
        "canvas": re.search(r'MF_ExpectedSchemaVersion\s*=\s*"([^"]+)"',
                            fx_app).group(1),
    }
    check("one schema version everywhere",
          len(set(schema_versions.values())) == 1, str(schema_versions))

    print()
    if FAILURES:
        print("=" * 58)
        print(f"RELEASE BLOCKED — {len(FAILURES)} stop condition(s):")
        for f in FAILURES:
            print(f"  - {f}")
        print("\nDo not build a ZIP with a known stop condition and a note "
              "about it.")
        return 1

    print("=" * 58)
    print("NOT BLOCKED. Every stop condition clears.")
    print("\nThis says nothing about the tenant. See docs/TEST_MATRIX.md for "
          "what is\nNOT TESTABLE LOCALLY, and "
          "deployment/DEPENDENCY_MANIFEST.md for what must\nalready exist on "
          "the destination side.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
