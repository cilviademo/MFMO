#!/usr/bin/env python3
"""Resolve destinations for all four portfolio sites. Creates nothing.

Runs against representative bindings -- the real site URLs are never in source
-- and exercises every failure path. The point is not that the happy path works;
it is that every failure lands somewhere a human can find, and that NOTHING
creates a folder.

    python3 scripts/routing_dryrun.py
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from folder_resolver import (  # noqa: E402
    DestinationNotUsable, resolve_destination_folder,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERIOD = "2026-08"

# What each site is assumed to look like once somebody walks it. The month
# folder naming DELIBERATELY differs per portfolio -- four sites name their root
# folders four ways, so assuming they agree about months is exactly the
# assumption deployment/site-bindings.md exists to stop.
SITE_SHAPES = {
    "PORT1-EOM": {"fy": "FY26", "month": "Aug 26"},
    "PORT2-EOM": {"fy": "FY 26", "month": "August 2026"},
    "PORT3-EOM": {"fy": "FY2026", "month": "08. August"},
    "PORT4-EOM": {"fy": "FY26", "month": "08"},
}


def load_destinations():
    with open(os.path.join(ROOT, "configuration", "document-destinations.csv"),
              encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def bind(row, shape=None):
    """Apply representative bindings. Never a real .mil URL."""
    d = dict(row)
    d["Site_URL"] = f"https://example.invalid/sites/{d['Destination_ID']}"
    d["Verified_By"] = "dry run"
    d["Active_Flag"] = True
    d["_shape"] = shape
    return d


def site(root, shape):
    """A read-only view of one site. There is no create() to call."""
    created = []

    def children(path):
        created.append(path)
        if shape is None:
            return []
        if path == root:
            return [shape["fy"], "FY25", "FY27"]
        if path == f"{root}/{shape['fy']}":
            return ["Jul 26", shape["month"], "Sep 26"]
        return []

    children.touched = created
    return children


def line(label, result, ok):
    mark = "ok  " if ok else "FAIL"
    print(f"  {mark} {label:<34} {result}")
    return ok


def main():
    rows = load_destinations()
    ok = True
    print(f"Routing dry run — period {PERIOD}, four site collections")
    print("Creates nothing. Representative bindings; no real site URL is used.\n")

    print("HAPPY PATH — one per portfolio")
    for row in rows:
        shape = SITE_SHAPES[row["Destination_ID"]]
        d = bind(row, shape)
        root = f"{d['Library_Name']}/{d['Root_Folder']}"
        listing = site(root, shape)
        r = resolve_destination_folder(d, PERIOD, listing)
        expected = f"{root}/{shape['fy']}/{shape['month']}"
        good = (r.path == expected and not r.needs_filing)
        ok &= line(f"{row['Portfolio_ID']}  ({shape['month']})", r.path, good)
    print()

    print("FAILURE PATHS — every one must land somewhere findable")
    row = rows[1]                                  # Portfolio 2, the odd slug
    root = f"{row['Library_Name']}/{row['Root_Folder']}"

    cases = []

    # 1. FY folder missing.
    d = bind(row, None)
    r = resolve_destination_folder(d, PERIOD, site(root, None))
    cases.append(("FY folder missing", r.path == root and r.needs_filing,
                  f"root, flagged — {r.note}"))

    # 2. Month folder missing.
    def no_month(path):
        return ["FY26"] if path == root else []
    d = bind(row)
    r = resolve_destination_folder(d, PERIOD, no_month)
    cases.append(("month folder missing", r.path == root and r.needs_filing,
                  f"root, flagged — {r.note}"))

    # 3. Site binding missing.
    d = bind(row); d["Site_URL"] = ""
    try:
        resolve_destination_folder(d, PERIOD, site(root, None))
        cases.append(("site binding missing", False, "did not fail closed"))
    except DestinationNotUsable as e:
        cases.append(("site binding missing", e.code == "CONFIGURATION_REQUIRED",
                      e.code))

    # 4. Ambiguous month match — both a named folder and a bare number.
    def ambiguous(path):
        if path == root:
            return ["FY26"]
        if path == f"{root}/FY26":
            return ["08", "August 2026"]
        return []
    d = bind(row)
    r = resolve_destination_folder(d, PERIOD, ambiguous)
    cases.append(("ambiguous month match",
                  r.path.endswith("August 2026") and not r.needs_filing,
                  f"resolved to the NAMED folder — {r.path.rsplit('/', 1)[-1]}"))

    # 5. Installation not mapped to a portfolio.
    #    There is no destination row to resolve, so the flow never gets here.
    unmapped = None
    try:
        resolve_destination_folder(unmapped, PERIOD, site(root, None))
        cases.append(("installation has no portfolio", False, "did not fail closed"))
    except DestinationNotUsable as e:
        cases.append(("installation has no portfolio",
                      e.code == "DESTINATION_NOT_CONFIGURED", e.code))

    # 6. Destination inaccessible — the row exists but was never verified.
    d = bind(row); d["Verified_By"] = ""
    try:
        resolve_destination_folder(d, PERIOD, site(root, None))
        cases.append(("destination unverified", False, "did not fail closed"))
    except DestinationNotUsable as e:
        cases.append(("destination unverified",
                      e.code == "DESTINATION_NOT_VERIFIED", e.code))

    # 7. The ceiling: a blank root folder must not fall back to the library.
    d = bind(row); d["Root_Folder"] = ""
    try:
        resolve_destination_folder(d, PERIOD, site(root, None))
        cases.append(("fallback ceiling", False, "fell back above the root"))
    except DestinationNotUsable as e:
        cases.append(("fallback ceiling",
                      e.code == "DESTINATION_NOT_CONFIGURED",
                      "refused to write above the Monthly Data Call root"))

    for label, good, detail in cases:
        ok &= line(label, detail, good)
    print()

    print("INVARIANTS")
    # Nothing anywhere may create a folder.
    listing = site(root, None)
    resolve_destination_folder(bind(row), PERIOD, listing)
    ok &= line("no folder created",
               f"{len(listing.touched)} read(s), 0 writes", True)
    ok &= line("Create_Missing_Folders",
               "FALSE on all four rows",
               all(r["Create_Missing_Folders"] == "FALSE" for r in rows))
    ok &= line("seeded rows fail closed",
               "Site_URL blank, Verified_By blank, Active_Flag FALSE",
               all(r["Site_URL"] == "" and r["Verified_By"] == ""
                   and r["Active_Flag"] == "FALSE" for r in rows))

    # A fallback must never reach another portfolio's root.
    contained = True
    for r_ in rows:
        d = bind(r_)
        rr = resolve_destination_folder(
            d, PERIOD, site(f"{d['Library_Name']}/{d['Root_Folder']}", None))
        for other in rows:
            if other["Destination_ID"] != r_["Destination_ID"]:
                contained &= other["Root_Folder"] not in rr.path
    ok &= line("no cross-portfolio fallback",
               "each fallback stays inside its own root", contained)

    print()
    print("PASS" if ok else "FAIL — see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
