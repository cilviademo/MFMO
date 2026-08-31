#!/usr/bin/env bash
# Everything that can be checked without a tenant. Run before every release.
#
# What this DOES cover: the schema, the status engine, EOM-01's three
# properties, the seed files, the delegation and accessibility static checks,
# and that the Power Fx and flow transliterations still agree with the
# reference implementation.
#
# What it does NOT cover: anything that needs SharePoint. Delegation at 5,000+
# rows, the index verification, RLS, the keyboard and screen-reader passes and
# the maintenance/read-only tests are in docs/DEPLOYMENT.md and are run in the
# tenant. Passing this script is necessary, not sufficient.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== schema =="
python3 scripts/eom_schema.py --validate

echo
echo "== unit tests =="
python3 -m unittest discover -s tests -p 'test_*.py' -v 2>&1 | tail -25

echo
echo "== solution validation =="
python3 scripts/validate_solution.py

echo
echo "== EOM-01 dry run against the sample seed =="
python3 scripts/generate_expected_items.py --as-of "$(date +%Y-%m-%d)"

echo
echo "All local checks passed. Tenant checks remain: see docs/DEPLOYMENT.md."
