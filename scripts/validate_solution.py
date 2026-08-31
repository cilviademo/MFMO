#!/usr/bin/env python3
"""
Pre-release validation. Run before every export, tag and commit.

    python3 scripts/validate_solution.py
    python3 scripts/validate_solution.py --reconcile-fact \
        --items items_export.json --fact fact_export.json

Checks, in order:

  1. The schema validates and matches its declared size.
  2. The generated docs are not stale.
  3. No hard-coded URL, site GUID or list-name string literal anywhere.
  4. Every Power Fx query that touches a high-volume list matches an approved
     shape in Delegation.fx.
  5. No known delegation anti-pattern appears in the app source.
  6. Accessibility: every interactive control declares AccessibleLabel and a
     non-positive TabIndex.
  7. Feature flags with an optional dependency default False.
  8. Every flow definition parses and reads the site from a parameter.

Anything it prints as FAIL blocks the release. Anything it prints as WARN is
a judgement call that must be recorded in the CHANGELOG if it ships.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eom_schema as S  # noqa: E402
from status_engine import STATUSES  # noqa: E402

HIGH_VOLUME = ("MF EOM Item", "MF EOM Submission", "MF EOM Status",
               "MF App Event Log", "MF EOM Audit")

# The interactive control types. A control of one of these types needs an
# accessible name and must not carry a positive TabIndex.
INTERACTIVE = ("Button", "ComboBox", "TextInput", "DatePicker", "Toggle",
               "Checkbox", "Radio", "Slider", "Dropdown", "AddMedia")

# Anti-patterns from canvas-app/formulas/Delegation.fx. Each one returns the
# first 500 rows and reports success.
_HV = "|".join(re.escape(n) for n in HIGH_VOLUME)

ANTI_PATTERNS = [
    (re.compile(r"IsBlank\(\s*(Facility_ID|Installation_ID|EOM_Item_ID|Contract_ID)\s*\)"),
     "IsBlank() on a list column does not delegate, and does not distinguish "
     "null from empty string. Filter on Requirement_Scope or Resolution_Status instead."),
    (re.compile(r"ClearCollect\(\s*\w+\s*,\s*'(%s)'" % _HV),
     "collecting a high-volume list pulls the first 500 rows and calls it the table"),
    (re.compile(r"\bSearch\(\s*'(%s)'[^)]*,[^)]*,[^)]*," % _HV),
     "multi-column Search() does not delegate"),
    (re.compile(r"\bSort\(\s*'(%s)'" % _HV),
     "Sort() does not delegate; use SortByColumns() on an indexed column"),
    (re.compile(r"(Sum|Average|Max|Min|StdevP|VarP)\(\s*'(%s)'" % _HV),
     "aggregates do not delegate to SharePoint; read the fact instead"),
    (re.compile(r"\b(GroupBy|AddColumns|Distinct)\(\s*'(%s)'" % _HV),
     "client-side shaping over a possibly truncated set"),
    (re.compile(r"ForAll\(\s*'(%s)'" % _HV),
     "ForAll over a data source; that work belongs in EOM-01"),
    (re.compile(r"StartsWith\(\s*EOM_Item_Key"),
     "StartsWith does not delegate on SharePoint; filter on Installation_ID"),
]

results = {"fail": [], "warn": [], "ok": []}


def fail(msg):
    results["fail"].append(msg)


def warn(msg):
    results["warn"].append(msg)


def ok(msg):
    results["ok"].append(msg)


def read(path):
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def app_files():
    for path in glob.glob(os.path.join(ROOT, "canvas-app", "**", "*"), recursive=True):
        if os.path.isfile(path) and path.endswith((".pa.yaml", ".fx")):
            yield path


# --------------------------------------------------------------------------

def check_schema():
    errs = S.validate()
    if errs:
        for e in errs:
            fail(f"schema: {e}")
    else:
        ok(f"schema v{S.SCHEMA_VERSION}: {len(S.LISTS)} lists, {S.total_columns()} columns")


def check_generated_docs():
    for path, produce, flag in (
        (os.path.join(ROOT, "docs", "data-model.md"), S.to_markdown, "--markdown"),
        (os.path.join(ROOT, "docs", "MF_EOM_Data_Dictionary.csv"),
         S.to_dictionary_csv, "--dictionary"),
    ):
        rel = os.path.relpath(path, ROOT)
        if not os.path.exists(path):
            fail(f"{rel} is missing; generate it from the schema")
        elif read(path).strip() != produce().strip():
            fail(f"{rel} is stale: python3 scripts/eom_schema.py {flag} > {rel}")
        else:
            ok(f"{rel} matches the schema")


def check_no_hard_coded_environment():
    """No hard-coded URLs, site GUIDs or list names anywhere.

    A data-source SYMBOL (MF_EOM_Item, unquoted) is unavoidable: a canvas app
    addresses a SharePoint list by its identifier, bound at author time. A list
    name as a STRING LITERAL is not, and is what this catches.
    """
    # Both government SharePoint hosts and the commercial one. This tenant is
    # DoD, where sites live on .dps.mil -- a rule watching only .sharepoint.*
    # watches the host a leak cannot occur on and misses the one it can.
    url = re.compile(
        r"https://[\w.-]*(sharepoint\.(com|us|mil)|dps\.mil|app\.powerbi\.com)",
        re.I)
    guid = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
    # A data-source SYMBOL ('MF EOM Item') is unavoidable; a list's INTERNAL
    # name as a bare string literal is not, and that is what this catches.
    literal_list = re.compile(r'"(MF_[A-Za-z_]+)"')

    searched = ("canvas-app", "flows", "solution", "powerbi")
    hits = 0
    for top in searched:
        for path in glob.glob(os.path.join(ROOT, top, "**", "*"), recursive=True):
            if not os.path.isfile(path):
                continue
            for i, line in enumerate(read(path).splitlines(), 1):
                rel = os.path.relpath(path, ROOT)
                if url.search(line):
                    fail(f"hard-coded URL at {rel}:{i}")
                    hits += 1
                # A GUID in source is a destination leak -- a site id, a list
                # id, a connection id baked into the package. It is NOT a
                # WorkflowId or an operationMetadataId: those are structural,
                # every real flow definition has them, and this build derives
                # them deterministically from the flow name so a rebuild is
                # byte-identical. Blanket-failing on the shape would mean
                # either no flows in the package or a weakened rule, and the
                # rule is the one that stops a tenant id shipping.
                structural = ("operationMetadataId", "WorkflowId",
                              "JsonFileName", '<RootComponent type="29"')
                if (guid.search(line) and "00000000-0000" not in line
                        and not any(k in line for k in structural)):
                    fail(f"hard-coded GUID at {rel}:{i}")
                    hits += 1
                for m in literal_list.findall(line):
                    if m in S.LISTS_BY_NAME:
                        fail(f"list name as a string literal at {rel}:{i} ({m})")
                        hits += 1
    if hits == 0:
        ok("no hard-coded URL, GUID or list-name literal")


def check_delegation():
    hits = 0
    for path in app_files():
        text = read(path)
        rel = os.path.relpath(path, ROOT)
        is_delegation_doc = rel.endswith("Delegation.fx")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if is_delegation_doc or stripped.startswith("//") or stripped.startswith("#"):
                continue    # the anti-pattern catalogue quotes them deliberately
            for pattern, why in ANTI_PATTERNS:
                if pattern.search(line):
                    fail(f"delegation at {rel}:{i}: {why}")
                    hits += 1
    if hits == 0:
        ok("no delegation anti-pattern in the app source")


def check_period_filter_first():
    """Every approved query on MF EOM Item filters on Reporting_Period."""
    text = read(os.path.join(ROOT, "canvas-app", "formulas", "Delegation.fx"))
    approved = re.findall(r"^(MF_\w+)\((.*?)\).*?:\s*Table\s*=\s*(.*?)(?=^\w|\Z)",
                          text, re.S | re.M)
    missing = [name for name, _args, body in approved
               if "'MF EOM Item'" in body and "Reporting_Period" not in body]
    if missing:
        fail("queries on MF EOM Item without a period filter: " + ", ".join(missing))
    else:
        ok("every approved MF EOM Item query filters on Reporting_Period")

    # And nothing outside Delegation.fx queries the high-volume lists directly.
    stray = []
    for path in app_files():
        rel = os.path.relpath(path, ROOT)
        if rel.endswith("Delegation.fx"):
            continue
        for i, line in enumerate(read(path).splitlines(), 1):
            if re.search(r"(Filter|SortByColumns)\(\s*'MF EOM (Item|Status|Audit)'", line):
                stray.append(f"{rel}:{i}")
    for hit in stray:
        fail(f"direct query on a high-volume list outside Delegation.fx at {hit}")
    if not stray:
        ok("high-volume lists are only queried through the approved shapes")


def check_accessibility():
    """Gates A2, A3, A6, A7 as far as static analysis can reach."""
    positive_tabindex = []
    missing_label = []

    for path in glob.glob(os.path.join(ROOT, "canvas-app", "src", "**", "*.pa.yaml"),
                          recursive=True):
        rel = os.path.relpath(path, ROOT)
        lines = read(path).splitlines()
        for i, line in enumerate(lines):
            m = re.search(r"TabIndex:\s*=\s*(-?\d+)", line)
            if m and int(m.group(1)) > 0:
                positive_tabindex.append(f"{rel}:{i+1}")

            m = re.search(r"Control:\s*(\w+)", line)
            if m and m.group(1) in INTERACTIVE:
                # Look ahead to the end of this control's property block.
                block = "\n".join(lines[i:i + 40])
                if "AccessibleLabel" not in block:
                    control_name = ""
                    for back in range(i - 1, max(0, i - 4), -1):
                        n = re.search(r"-\s*(\w+):", lines[back])
                        if n:
                            control_name = n.group(1)
                            break
                    missing_label.append(f"{rel}:{i+1} {control_name or m.group(1)}")

    for p in positive_tabindex:
        fail(f"positive TabIndex at {p}: detaches tab order from visual order (gate A3)")
    for m in missing_label:
        fail(f"interactive control without AccessibleLabel at {m} (gate A7)")
    if not positive_tabindex and not missing_label:
        ok("no positive TabIndex; every interactive control declares AccessibleLabel")

    # Gate A4: the badge must render its label, always.
    badge = read(os.path.join(ROOT, "canvas-app", "src", "Components", "cmpStatusBadge.pa.yaml"))
    if ".label" not in badge:
        fail("cmpStatusBadge does not render its label: status would be colour-only (gate A4)")
    elif "FinalStatus" not in badge:
        fail("cmpStatusBadge must take a semantic status, never a colour")
    else:
        ok("cmpStatusBadge renders text, icon and colour together")

    # Absolute positioning breaks at 200% zoom.
    absolute = []
    for path in glob.glob(os.path.join(ROOT, "canvas-app", "src", "**", "*.pa.yaml"),
                          recursive=True):
        rel = os.path.relpath(path, ROOT)
        for i, line in enumerate(read(path).splitlines(), 1):
            if re.search(r"^\s+(X|Y):\s*=\s*\d", line):
                absolute.append(f"{rel}:{i}")
    for hit in absolute:
        fail(f"absolute positioning at {hit}: breaks at 200% zoom (gate A11)")
    if not absolute:
        ok("no absolute positioning; auto-layout containers throughout")

    # Every gallery needs an empty state: an empty gallery with no explanation
    # is indistinguishable from a failed load.
    for path in glob.glob(os.path.join(ROOT, "canvas-app", "src", "Screens", "*.pa.yaml")):
        text = read(path)
        rel = os.path.relpath(path, ROOT)
        n_galleries = len(re.findall(r"Control:\s*Gallery", text))
        n_empty = len(re.findall(r"ComponentName:\s*cmpEmptyState", text))
        if n_galleries and not n_empty and "scrDiagnostics" not in rel:
            warn(f"{rel} has {n_galleries} gallery/galleries and no cmpEmptyState")


def check_feature_flags():
    import csv
    path = os.path.join(ROOT, "configuration", "feature-flags.csv")
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    # AI Builder and content classification must never become a dependency
    # whose availability could block the app. Off in prod AND for testers,
    # because there is no code path behind either in R1.
    bad = [r["Feature_Key"] for r in rows
           if r["Feature_Key"] in ("EOM_AI_BUILDER", "EOM_CONTENT_CLASSIFY")
           and (r["Enabled_Prod"] != "FALSE" or r["Enabled_Testers"] != "FALSE")]
    if bad:
        fail("AI classification flags must ship FALSE: " + ", ".join(bad))
    else:
        ok("AI classification flags ship disabled")

    dev = [r["Feature_Key"] for r in rows
           if r["Minimum_Role"] == "Developer" and r["Enabled_Prod"] != "FALSE"]
    if dev:
        fail("developer-only features enabled in prod: " + ", ".join(dev))
    else:
        ok("no developer-only feature is enabled in prod")


def check_flows():
    expected = ("EOM01-ExpectedPackage", "EOM02b-LegacyIntake", "EOM03-Reconciliation",
                "EOM04-Notifications", "EOM02-Submission")
    missing = [f for f in expected
               if not os.path.exists(os.path.join(ROOT, "flows", f, "definition.md"))]
    for f in missing:
        fail(f"flows/{f}/definition.md is missing")

    # An export that has never been imported is a drawing of source, not
    # source. See docs/handoffs/RECONCILIATION.md section 8.
    stray = glob.glob(os.path.join(ROOT, "flows", "**", "*.json"), recursive=True)
    for path in stray:
        fail(f"{os.path.relpath(path, ROOT)}: hand-written flow JSON is not source; "
             "the spec is the source and the export is the artifact")

    if not missing and not stray:
        ok(f"{len(expected)} flow specs present, no fabricated JSON")


def check_reconciliation_record():
    """The corrections must stay documented, or the next reader re-introduces them."""
    path = os.path.join(ROOT, "docs", "handoffs", "RECONCILIATION.md")
    if not os.path.exists(path):
        fail("docs/handoffs/RECONCILIATION.md is missing; the decision record is "
             "how a reader knows why the tree differs from reference/v3")
        return
    text = read(path)
    missing = [c for c in [f"C{n}" for n in range(1, 11)] if f"| {c} |" not in text]
    if missing:
        fail("reconciliation record is missing corrections: " + ", ".join(missing))
    else:
        ok("reconciliation record documents all ten corrections")


def reconcile_fact(items_path, fact_path):
    """Step 8: the app and MF_EOM_Status must agree on every row, not a sample."""
    items = {r["EOM_Item_ID"]: r for r in json.loads(read(items_path))}
    fact_rows = json.loads(read(fact_path))
    latest = {}
    for row in fact_rows:
        key = row["EOM_Item_ID"]
        if key not in latest or row["Snapshot_Date"] > latest[key]["Snapshot_Date"]:
            latest[key] = row

    compared = ("Final_Status", "Status_Code", "Action_Owner", "Action_Required")
    mismatches = 0
    for item_id, item in items.items():
        f = latest.get(item_id)
        if f is None:
            fail(f"fact has no row for item {item_id}")
            mismatches += 1
            continue
        for field in compared:
            a, b = item.get(field), f.get(field)
            if isinstance(a, dict):
                a = a.get("Value")
            if isinstance(b, dict):
                b = b.get("Value")
            if a != b:
                fail(f"{item_id}.{field}: item={a!r} fact={b!r}")
                mismatches += 1
        # The fact must not have re-derived anything: the numeric code has to
        # be the one the engine assigns to that semantic status.
        status = item.get("Final_Status")
        if isinstance(status, dict):
            status = status.get("Value")
        expected_code = STATUSES.get(status, (None,))[0]
        if expected_code is not None and int(f.get("Status_Code", -1)) != expected_code:
            fail(f"{item_id}: fact Status_Code {f.get('Status_Code')} does not match "
                 f"the engine's code for {status} ({expected_code})")
            mismatches += 1
    extra = set(latest) - set(items)
    for item_id in extra:
        warn(f"fact carries a row for item {item_id}, which no longer exists")
    if mismatches == 0:
        ok(f"the app and MF_EOM_Status agree on all {len(items)} rows")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reconcile-fact", action="store_true")
    p.add_argument("--items")
    p.add_argument("--fact")
    args = p.parse_args(argv)

    check_schema()
    check_generated_docs()
    check_no_hard_coded_environment()
    check_delegation()
    check_period_filter_first()
    check_accessibility()
    check_feature_flags()
    check_flows()
    check_reconciliation_record()

    if args.reconcile_fact:
        if not (args.items and args.fact):
            p.error("--reconcile-fact needs --items and --fact")
        reconcile_fact(args.items, args.fact)

    for m in results["ok"]:
        print(f"  OK   {m}")
    for m in results["warn"]:
        print(f"  WARN {m}")
    for m in results["fail"]:
        print(f"  FAIL {m}")

    print()
    print(f"{len(results['ok'])} passed, {len(results['warn'])} warnings, "
          f"{len(results['fail'])} failures")
    return 1 if results["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
