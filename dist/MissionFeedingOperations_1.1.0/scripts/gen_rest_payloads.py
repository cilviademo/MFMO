#!/usr/bin/env python3
"""Emit SharePoint REST payloads for provisioning WITHOUT PowerShell.

    python3 scripts/gen_rest_payloads.py

Produces:
    provisioning/sharepoint-schema.json    one array, every list and column,
                                           ready to paste into a Power Automate
                                           Compose action
    provisioning/manual-column-sheet.csv   the same thing as a flat checklist,
                                           for the hand-build fallback

WHY THIS EXISTS
---------------
No module-install rights is a normal `.mil` constraint, and it does not block
provisioning. The SharePoint connector includes an action called **Send an HTTP
request to SharePoint** -- not the HTTP connector, not a custom connector, no
admin rights.  # prerelease: allow CON-02 names the SharePoint connector action in order to distinguish it from the prohibited HTTP connector It runs under your own credentials against a site you own and it
can do everything `Provision-MFOpsLists.ps1` does.

THE INTERNAL NAME IS SET AT CREATION AND NEVER AGAIN
----------------------------------------------------
`Title` in the field payload below is the name SharePoint derives the internal
name from. Passing `Installation_ID` gets you `Installation_ID`; passing
"Installation ID" gets you `Installation_x0020_ID`, permanently, and every Power
Fx reference and flow expression then binds to a name the app does not use — it
reads blank, without erroring.

So the payloads pass the **underscored internal name** as `Title`, and the
display title is set afterwards if anyone wants a prettier one. Renaming later
is safe; recreating is not. `docs/SHAREPOINT_SCHEMA_MANIFEST.md` is the contract.
"""

from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eom_schema import LISTS, SCHEMA_VERSION, total_columns  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "provisioning")

# SP.FieldType enumeration.
KIND = {"Text": 2, "Note": 3, "Number": 9, "Currency": 10, "DateTime": 4,
        "Boolean": 8, "Choice": 6, "URL": 11, "User": 20, "Lookup": 7,
        "Calculated": 17}


def field_payload(col):
    p = {
        "__metadata": {"type": "SP.Field"},
        # THE INTERNAL NAME. See the module docstring.
        "Title": col.name,
        "FieldTypeKind": KIND[col.type],
        "Required": bool(col.required),
        "EnforceUniqueValues": False,
    }
    if col.type == "Text":
        p["MaxLength"] = 255
    elif col.type == "Note":
        p["__metadata"]["type"] = "SP.FieldMultiLineText"
        p["NumberOfLines"] = 6
        p["RichText"] = False
        p["AppendOnly"] = False
    elif col.type == "Choice":
        p["__metadata"]["type"] = "SP.FieldChoice"
        p["Choices"] = {"__metadata": {"type": "Collection(Edm.String)"},
                        "results": list(col.choices)}
        p["EditFormat"] = 0
        # The vocabularies live in eom_schema.py. A free-text value would
        # silently break the status engine.
        p["FillInChoice"] = False
    elif col.type == "DateTime":
        p["__metadata"]["type"] = "SP.FieldDateTime"
        p["DisplayFormat"] = 0                 # date only
    elif col.type == "Number":
        p["__metadata"]["type"] = "SP.FieldNumber"
    elif col.type == "Currency":
        p["__metadata"]["type"] = "SP.FieldCurrency"
    elif col.type == "URL":
        p["__metadata"]["type"] = "SP.FieldUrl"
        p["DisplayFormat"] = 0                 # hyperlink
    elif col.type == "Boolean":
        p["__metadata"]["type"] = "SP.Field"
    elif col.type == "User":
        p["__metadata"]["type"] = "SP.FieldUser"
        p["SelectionMode"] = 0                 # people only
    return p


def build():
    schema = []
    for l in LISTS:
        schema.append({
            "listInternalKey": l.name,
            "listTitle": l.title,
            "description": l.grain[:255],
            "volumeEstimate": l.volume_estimate,
            # TWO DIFFERENT THRESHOLDS, and conflating them is how a list
            # ends up without an index nobody can add any more.
            #
            #   delegation ceiling      2,000 rows. A Power Apps client limit.
            #                           Past it a non-delegable query returns
            #                           the first page and reports success.
            #   list view threshold     5,000 items. A SharePoint server limit.
            #                           Past it an index can never be added.
            #
            # The threshold is INCLUSIVE for the irreversible one: a list
            # projected at exactly 5,000 crosses it on its next row, and there
            # is no second chance.
            "crossesDelegationCeiling": l.volume_estimate > 2000,
            "crossesListViewThreshold": l.volume_estimate >= 5000,
            "createPayload": {
                "__metadata": {"type": "SP.List"},
                "BaseTemplate": 100,           # generic list
                "Title": l.title,
                "Description": l.grain[:255],
                "ContentTypesEnabled": False,
            },
            "fields": [
                {
                    "name": c.name,
                    "type": c.type,
                    "required": bool(c.required),
                    "indexed": bool(c.indexed),
                    "choices": list(c.choices),
                    "payload": field_payload(c),
                }
                for c in l.columns
            ],
            # Indexes are created at provisioning time or never: SharePoint
            # will not add one to a list past the 5,000-item threshold, and
            # MF_EOM_Item crosses that in the first year.
            "indexedFields": list(l.indexed_columns),
            # The index calls, spelled out as operations rather than left as a
            # flag for the operator to translate. SharePoint indexes a column
            # by PATCHing Indexed=true on the field, and it refuses once the
            # list passes 5,000 items -- so these run at provisioning time or
            # never.
            "indexOperations": [
                {
                    "field": name,
                    "method": "MERGE",
                    "path": (f"_api/web/lists/getbytitle('{l.title}')"
                             f"/fields/getbyinternalnameortitle('{name}')"),
                    "payload": {"__metadata": {"type": "SP.Field"},
                                "Indexed": True},
                }
                for name in l.indexed_columns
            ],
            # The uniqueness the design DECLARES. SharePoint can enforce
            # EnforceUniqueValues only on an indexed single-value column, so a
            # composite key is a flow-side check, not a list constraint. Saying
            # which is which here stops an operator assuming the list protects
            # something it does not.
            "uniqueKey": {
                "columns": list(l.unique_key or ()),
                "enforcedBySharePoint": bool(
                    l.unique_key and len(l.unique_key) == 1
                    and l.unique_key[0] in l.indexed_columns),
                "note": (
                    "single indexed column -- EnforceUniqueValues applies"
                    if (l.unique_key and len(l.unique_key) == 1
                        and l.unique_key[0] in l.indexed_columns)
                    else "composite or unindexed -- enforced by the flow, "
                         "never by the list"),
            },
        })
    return schema


def what_if(schema):
    """What each call would do, before any of them run.

    Provisioning is the one step with an unrepairable failure in it: an index
    that was not created before a list passes 5,000 items can never be created.
    So the operator gets the plan in advance, in the order it executes, with
    the irreversible steps marked.
    """
    lines = []
    w = lines.append
    total_calls = 0
    w("# Provisioning WhatIf report")
    w("")
    w("Generated by `scripts/gen_rest_payloads.py` from `scripts/eom_schema.py`.")
    w("Nothing here has run. This is what would run, in this order.")
    w("")
    w("**Read the irreversible column first.** SharePoint will not add an index")
    w("to a list once it passes 5,000 items, and `MF_EOM_Item` passes that in")
    w("the first quarter. Everything else on this page can be repaired later.")
    w("")
    w("| # | List | Creates | Fields | Indexes | Irreversible after 5,000 rows |")
    w("|---:|---|---|---:|---:|---|")
    for i, l in enumerate(schema, 1):
        calls = 1 + len(l["fields"]) + len(l["indexOperations"])
        total_calls += calls
        w(f"| {i} | `{l['listTitle']}` | list + {len(l['fields'])} fields | "
          f"{len(l['fields'])} | {len(l['indexOperations'])} | "
          f"{'**YES** — ' + str(l['volumeEstimate']) + ' rows projected' if l['crossesListViewThreshold'] else 'no'} |")
    w("")
    w(f"**{total_calls} REST calls in total** across {len(schema)} lists.")
    w("")
    w("## Per list, what already existing would mean")
    w("")
    w("A list reported as already existing is NOT a no-op. An internal name is")
    w("fixed at creation and can never be changed, so a list somebody made by")
    w("hand will have `Installation ID` where every formula expects")
    w("`Installation_x0020_ID`, and every read returns blank rather than")
    w("erroring. Check it column by column against")
    w("`docs/SHAREPOINT_SCHEMA_MANIFEST.md` before continuing.")
    w("")
    w("## Uniqueness: what the list enforces and what it does not")
    w("")
    w("| List | Declared key | Enforced by SharePoint? |")
    w("|---|---|---|")
    for l in schema:
        u = l["uniqueKey"]
        cols = ", ".join(f"`{c}`" for c in u["columns"]) or "—"
        w(f"| `{l['listTitle']}` | {cols} | "
          f"{'yes' if u['enforcedBySharePoint'] else 'no — ' + u['note']} |")
    w("")
    with open(os.path.join(OUT, "whatif-report.md"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return total_calls


def main():
    schema = build()
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(OUT, "sharepoint-schema.json"), "w",
              encoding="utf-8") as fh:
        json.dump(schema, fh, indent=2)
        fh.write("\n")

    rows = []
    for l in schema:
        for f in l["fields"]:
            rows.append([
                l["listTitle"], f["name"], f["type"],
                "Yes" if f["required"] else "No",
                "Yes" if f["indexed"] else "No",
                "; ".join(f["choices"]),
            ])
    with open(os.path.join(OUT, "manual-column-sheet.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["List", "Column name (type this EXACTLY)", "Type",
                    "Required", "Index it", "Choices"])
        w.writerows(rows)

    what_if(schema)

    cols = sum(len(l["fields"]) for l in schema)
    idx = sum(len(l["indexedFields"]) for l in schema)
    assert cols == total_columns(), (cols, total_columns())
    print(f"schema v{SCHEMA_VERSION}: {len(schema)} lists, {cols} columns, "
          f"{idx} indexes")
    print("  provisioning/sharepoint-schema.json")
    print("  provisioning/manual-column-sheet.csv")
    print("  provisioning/whatif-report.md")


if __name__ == "__main__":
    main()
