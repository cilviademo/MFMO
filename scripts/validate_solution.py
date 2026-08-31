#!/usr/bin/env python3
"""
Pre-release validation. Run before every export, tag and commit.

    python3 scripts/validate_solution.py
    python3 scripts/validate_solution.py --reconcile-fact \
        --items items_export.json --fact fact_export.json

Checks, in order:

  1. The schema validates and matches its declared size.
  2. docs/data-model.md is not stale.
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

HIGH_VOLUME = ("MF_EOM_Item", "MF_EOM_Submission", "MF_EOM_Status", "MF_App_Event_Log")

# The interactive control types. A control of one of these types needs an
# accessible name and must not carry a positive TabIndex.
INTERACTIVE = ("Button", "ComboBox", "TextInput", "DatePicker", "Toggle",
               "Checkbox", "Radio", "Slider", "Dropdown", "AddMedia")

# Anti-patterns from canvas-app/formulas/Delegation.fx. Each one returns the
# first 500 rows and reports success.
ANTI_PATTERNS = [
    (re.compile(r"IsBlank\(\s*(Facility_ID|Installation_ID|EOM_Item_ID)\s*\)"),
     "IsBlank() on a list column does not delegate, and does not distinguish "
     "null from empty string. Filter on Requirement_Scope or Classification_Status instead."),
    (re.compile(r"ClearCollect\(\s*\w+\s*,\s*(%s)\b" % "|".join(HIGH_VOLUME)),
     "collecting a high-volume list pulls the first 500 rows and calls it the table"),
    (re.compile(r"\bSearch\(\s*(%s)\b[^)]*,[^)]*,[^)]*," % "|".join(HIGH_VOLUME)),
     "multi-column Search() does not delegate"),
    (re.compile(r"\bSort\(\s*(%s)\b" % "|".join(HIGH_VOLUME)),
     "Sort() does not delegate; use SortByColumns() on an indexed column"),
    (re.compile(r"(Sum|Average|Max|Min|StdevP|VarP)\(\s*(%s)\b" % "|".join(HIGH_VOLUME)),
     "aggregates do not delegate to SharePoint; read MF_EOM_Status instead"),
    (re.compile(r"\bGroupBy\(\s*(%s)\b" % "|".join(HIGH_VOLUME)),
     "GroupBy() is client-side and operates on a truncated set"),
    (re.compile(r"ForAll\(\s*(%s)\b" % "|".join(HIGH_VOLUME)),
     "ForAll over a data source; that work belongs in EOM-01"),
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
    path = os.path.join(ROOT, "docs", "data-model.md")
    if not os.path.exists(path):
        fail("docs/data-model.md is missing; generate it from the schema")
        return
    if read(path).strip() != S.to_markdown().strip():
        fail("docs/data-model.md is stale: "
             "python3 scripts/eom_schema.py --markdown > docs/data-model.md")
    else:
        ok("docs/data-model.md matches the schema")


def check_no_hard_coded_environment():
    """No hard-coded URLs, site GUIDs or list names anywhere.

    A data-source SYMBOL (MF_EOM_Item, unquoted) is unavoidable: a canvas app
    addresses a SharePoint list by its identifier, bound at author time. A list
    name as a STRING LITERAL is not, and is what this catches.
    """
    url = re.compile(r"https://[\w.-]*sharepoint\.(com|us|mil)/", re.I)
    guid = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
    literal_list = re.compile(r'"(MF_[A-Za-z_]+)"')

    searched = ("canvas-app", "flows", "solution")
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
                if guid.search(line) and "00000000-0000" not in line:
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
    """Every query on MF_EOM_Item filters on Reporting_Period_ID."""
    text = read(os.path.join(ROOT, "canvas-app", "formulas", "Delegation.fx"))
    approved = re.findall(r"^(MF_\w+)\((.*?)\).*?:\s*Table\s*=\s*(.*?)(?=^\w|\Z)",
                          text, re.S | re.M)
    missing = []
    for name, _args, body in approved:
        if "MF_EOM_Item" in body and "Reporting_Period_ID" not in body:
            missing.append(name)
    if missing:
        fail("queries on MF_EOM_Item without a period filter: " + ", ".join(missing))
    else:
        ok("every approved MF_EOM_Item query filters on Reporting_Period_ID")

    # And nothing outside Delegation.fx queries the high-volume lists directly.
    stray = []
    for path in app_files():
        rel = os.path.relpath(path, ROOT)
        if rel.endswith("Delegation.fx"):
            continue
        for i, line in enumerate(read(path).splitlines(), 1):
            if re.search(r"(Filter|LookUp|SortByColumns)\(\s*(MF_EOM_Item|MF_EOM_Status)\b", line):
                stray.append(f"{rel}:{i}")
    if stray:
        for s in stray:
            fail(f"direct query on a high-volume list outside Delegation.fx at {s}")
    else:
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
        fail("cmpStatusBadge does not render Status_Semantic: status would be colour-only (gate A4)")
    else:
        ok("cmpStatusBadge renders text, icon and colour together")

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
    path = os.path.join(ROOT, "configuration", "feature_flags.csv")
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    # Gates 1-5 are HARD: if one is red the build stops, so a flag defaulting
    # True behind one can never be honoured against a missing dependency. The
    # rule bites on the SOFT gates, where the capability may simply be absent
    # and the app has to carry on without it.
    hard = ("Capability.1.", "Capability.2.", "Capability.3.",
            "Capability.4.", "Capability.5.")
    bad = [r["Title"] for r in rows
           if r["Requires_Capability"].strip()
           and not r["Requires_Capability"].startswith(hard)
           and r["Default_Value"] != "FALSE"]
    if bad:
        fail("flags with a soft-gated dependency defaulting True: " + ", ".join(bad))
    else:
        ok("no soft-gated dependency defaults True")

    for r in rows:
        if r["Title"] in ("EnableAIBuilder", "EnableDocumentContentAI") and r["Flag_Value"] != "FALSE":
            fail(f"{r['Title']} must ship FALSE")


def check_flows():
    paths = glob.glob(os.path.join(ROOT, "flows", "**", "*.json"), recursive=True)
    if not paths:
        fail("no flow definitions found")
        return
    for path in paths:
        rel = os.path.relpath(path, ROOT)
        try:
            json.loads(read(path))
        except json.JSONDecodeError as e:
            fail(f"{rel} does not parse: {e}")
            continue
        text = read(path)
        if "parameters('siteUrl')" not in text:
            fail(f"{rel} does not read the site from a parameter")
    ok(f"{len(paths)} flow definitions parse and parameterise the site")


def reconcile_fact(items_path, fact_path):
    """Step 8: the app and MF_EOM_Status must agree on every row, not a sample."""
    items = {r["EOM_Item_ID"]: r for r in json.loads(read(items_path))}
    fact_rows = json.loads(read(fact_path))
    latest = {}
    for row in fact_rows:
        key = row["EOM_Item_ID"]
        if key not in latest or row["Snapshot_Date"] > latest[key]["Snapshot_Date"]:
            latest[key] = row

    compared = ("Status_Code", "Final_Status", "Status_Semantic", "Action_Owner_Role")
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
        code = item.get("Status_Code")
        if isinstance(code, dict):
            code = code.get("Value")
        want_complete = code == "ACCEPTED"
        want_denominator = code not in ("NOT_DUE", "WAIVED", "NOT_APPLICABLE", "SUPERSEDED")
        if bool(f.get("Is_Complete")) != want_complete:
            fail(f"{item_id}.Is_Complete disagrees with Status_Code {code}")
            mismatches += 1
        if bool(f.get("Is_In_Denominator")) != want_denominator:
            fail(f"{item_id}.Is_In_Denominator disagrees with Status_Code {code}")
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
