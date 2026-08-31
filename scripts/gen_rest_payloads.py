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
request to SharePoint** — not the HTTP connector, not a custom connector, no
admin rights. It runs under your own credentials against a site you own and it
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
            "crossesDelegationCeiling": l.volume_estimate > 5000,
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
        })
    return schema


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

    cols = sum(len(l["fields"]) for l in schema)
    idx = sum(len(l["indexedFields"]) for l in schema)
    assert cols == total_columns(), (cols, total_columns())
    print(f"schema v{SCHEMA_VERSION}: {len(schema)} lists, {cols} columns, "
          f"{idx} indexes")
    print("  provisioning/sharepoint-schema.json")
    print("  provisioning/manual-column-sheet.csv")


if __name__ == "__main__":
    main()
