#!/usr/bin/env bash
# Everything checkable without a tenant. Run before every release.
#
# COVERS: the schema and its generated artifacts, the status engine and its
# three transliterations, EOM-01's three properties, the seeds, the flow specs,
# the delegation and accessibility static checks, and that the ten
# reconciliation corrections stayed applied.
#
# DOES NOT COVER: anything needing SharePoint. Delegation at 5,000+ rows, index
# verification, RLS with two scopes, the keyboard and screen-reader passes and
# the maintenance/read-only tests are in docs/DEPLOYMENT.md and run in the
# tenant. Passing this is necessary, not sufficient.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== schema =="
# Dependency preflight FIRST. A missing yaml module surfacing mid-validator
# reads like a schema failure, which is the wrong way to find out. Say what is
# missing and how to fix it, then stop.
python3 - <<'DEPS'
import sys
missing = []
for mod, pkg in (("yaml", "pyyaml"), ("jsonschema", "jsonschema"),
                 ("referencing", "referencing")):
    try:
        __import__(mod)
    except ImportError:
        missing.append(pkg)
if missing:
    print("MISSING DEV DEPENDENCIES:", ", ".join(missing))
    print()
    print("This is an environment problem, not a schema problem. Fix it with:")
    print("    python3 -m venv .venv && source .venv/bin/activate")
    print("    pip install -r requirements-dev.txt")
    sys.exit(1)
DEPS

python3 scripts/eom_schema.py --validate
python3 scripts/eom_schema.py --summary

echo
echo "== unit tests =="
python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -5

echo
echo "== solution validation =="
python3 scripts/validate_solution.py

echo
echo "== pre-release security scan =="
# A gate, not a linter. A FAIL means do not export.
python3 scripts/prerelease_scan.py

echo
echo "== routing dry run: four PRODUCTION site collections =="
python3 scripts/routing_dryrun.py PORT

echo
echo "== routing dry run: four PILOT destinations =="
python3 scripts/routing_dryrun.py PILOT

echo
echo "== EOM-01 dry run across the configured backfill window =="
python3 scripts/generate_expected_items.py --backfill --today 2026-09-12

echo
echo "All local checks passed. Tenant checks remain: see docs/DEPLOYMENT.md,"
echo "and the data layer still does not enforce installation scope —"
echo "docs/security-open-issue.md."

echo
echo "== release gate: the stop conditions =="
python3 scripts/release_gate.py
