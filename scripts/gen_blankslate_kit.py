#!/usr/bin/env python3
"""Generate dist/MFOps_blankslate-provisioning_1.0/ — revision 3 of the
manual provisioning approach: the operator DELETES every MF list first and
provisions onto a blank site with two hand-built Power Automate flows.

Nothing here is hand-typed from the schema: SCHEMA-PAYLOADS.json is a
projection of scripts/gen_rest_payloads.build() (which reads eom_schema.py,
the single authority), and every number in the two flow runbooks — totals,
list titles, the delete list, the per-list expected table — is written by
this script from that same projection. tests/test_blankslate_kit.py replays
every payload against a mock SharePoint that enforces SharePoint's own
rules and re-derives the audit.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from gen_rest_payloads import build  # noqa: E402

KIT = os.path.join(ROOT, "dist", "MFOps_blankslate-provisioning_1.0")

CRITICAL = [("MF_EOM_Item", 13), ("MF_EOM_Submission", 13),
            ("MF_EOM_Status", 8), ("MF_Security_Mapping", 8),
            ("MF_App_Event_Log", 6), ("MF_EOM_Audit", 4)]


def project(schema):
    """The kit's JSON shape, per the directive: listTitle ·
    createListPayload · fields[] (createPayload each) · indexOps[]."""
    out = []
    for l in schema:
        out.append({
            "listTitle": l["listTitle"],
            "createListPayload": l["createPayload"],
            "fieldsExpected": len(l["fields"]),
            "indexesExpected": len(l["indexOperations"]),
            "fields": [{
                "internalName": f["name"],
                "indexed": f["indexed"],
                "createPayload": f["payload"],
            } for f in l["fields"]],
            "indexOps": [{
                "field": op["field"],
                "path": op["path"],
                "method": "MERGE",
                "payload": op["payload"],
            } for op in l["indexOperations"]],
        })
    return out


def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def flow_build_md(kit):
    titles = [l["listTitle"] for l in kit]
    n_fields = sum(l["fieldsExpected"] for l in kit)
    n_idx = sum(l["indexesExpected"] for l in kit)
    n_calls = len(kit) + n_fields + n_idx
    return f"""# BUILD flow — blank-slate provisioning, click by click

**Read first: this flow assumes a BLANK site.** If any MF list already
exists, delete it before running (the delete list is at the bottom).
There is no ENSURE logic and no skip-if-exists: a create against an
existing list fails, the run stops, and that is the design.

**The design, stated plainly:** four action shapes, no conditions, no
variables, no Failed branches. Every run-after stays at its DEFAULT
(run after: Succeeded). A single failure stops the whole run, visibly,
at the exact action that failed — and the recovery is always the same:
**delete the MF lists, fix, rerun.** Simple enough to click together in
one sitting, simple enough to trust.

## Create the flow

Power Automate → Create → **Instant cloud flow** → trigger **Manually
trigger a flow** (no inputs) → name it `MF Blank-Slate BUILD`.

## Action 1 — Compose, rename it exactly: `Schema`

**Data Operation → Compose.** Into *Inputs*, paste the ENTIRE contents
of `SCHEMA-PAYLOADS.json` from this kit. (Open the file in a text
editor, Select All, copy, paste. The designer accepts large JSON in a
Compose input.)

## Action 2 — Apply to each, rename it exactly: `For each list`

*Select an output from previous steps* (paste as an expression):

```
outputs('Schema')
```

Inside `For each list`, add three actions in this order:

### 2a — SharePoint → **Send an HTTP request to SharePoint**, rename: `Create list`

| Parameter | Value |
|---|---|
| Site Address | **OPERATOR VALUE — your links sheet** |
| Method | `POST` |
| Uri | `_api/web/lists` |
| Headers | `Accept` = `application/json;odata=verbose` · `Content-Type` = `application/json;odata=verbose` |
| Body | expression: `string(items('For_each_list')?['createListPayload'])` |

**Settings → Retry Policy → Exponential, Count 4** (open the action's
`…` menu → *Settings* → *Retry Policy* → Type: Exponential, Count: 4,
Interval: PT20S). This retries ONLY 429/5xx responses — throttling and
transient server errors, the sole resilience feature of this flow. A
4xx (duplicate list, bad payload) fails immediately, correctly.

### 2b — **Apply to each**, rename: `For each field`

*Select an output*: expression `items('For_each_list')?['fields']`

**Settings → Concurrency Control → On → Degree of Parallelism = 1**
(the loop's `…` menu → *Settings* → toggle *Concurrency Control* on and
drag to 1). This makes field creation match the build-sheet order and
keeps throttling tame. Do the same on `For each index` below.

Inside it, one action — SharePoint → **Send an HTTP request to
SharePoint**, rename: `Create field`:

| Parameter | Value |
|---|---|
| Site Address | **OPERATOR VALUE — same site** |
| Method | `POST` |
| Uri | expression: `concat('_api/web/lists/getbytitle(''', items('For_each_list')?['listTitle'], ''')/fields')` |
| Headers | `Accept` = `application/json;odata=verbose` · `Content-Type` = `application/json;odata=verbose` |
| Body | expression: `string(items('For_each_field')?['createPayload'])` |

Retry Policy: Exponential, Count 4, as above.

> Every field payload passes the INTERNAL name as `Title` at creation,
> which is exactly how the internal name is frozen correctly — no
> `_x0020_` can appear because no payload contains a space.

### 2c — **Apply to each**, rename: `For each index`

*Select an output*: expression `items('For_each_list')?['indexOps']`
Concurrency Control → On → 1, as above.

Inside it, one action — SharePoint → **Send an HTTP request to
SharePoint**, rename: `Set index`:

| Parameter | Value |
|---|---|
| Site Address | **OPERATOR VALUE — same site** |
| Method | `POST` |
| Uri | expression: `items('For_each_index')?['path']` |
| Headers | `Accept` = `application/json;odata=verbose` · `Content-Type` = `application/json;odata=verbose` · `X-HTTP-Method` = `MERGE` · `IF-MATCH` = `*` |
| Body | expression: `string(items('For_each_index')?['payload'])` |

Retry Policy: Exponential, Count 4, as above.

That is the whole flow: `Schema` → `For each list` → (`Create list` →
`For each field` → `For each index`). Nothing else.

## What a clean run looks like

- Run history shows **Succeeded**, one green row.
- Opening it: `For each list` shows **{len(kit)} iterations**, every
  `Create list` returned 201; `For each field` totals **{n_fields}**
  creates; `For each index` totals **{n_idx}** merges (200/204).
- **{n_calls} REST calls in total.** At concurrency 1, expect roughly
  **10–25 minutes** — an estimate; the real duration is NOT TESTABLE
  LOCALLY and depends on tenant throttling.

## When a run fails — delete, fix, rerun

The run stops at the failing action with SharePoint's error in the
output — read it there. Then **Site contents → delete every MF list
that exists** (the flow has no resume; a partial site plus a rerun
means duplicate-create failures). Delete EXACTLY these {len(kit)} and
**nothing else on the site**:

""" + "".join(f"- `{t}`\n" for t in titles) + f"""
Fix the cause (usually a paste error in an action), then rerun. The
schema JSON itself is machine-generated and replay-proven offline; if
the same action fails twice with the same 4xx, suspect the pasted
expression, not the payload.

Then run the VERIFY flow (`FLOW-VERIFY.md`). No CSV touches any list
before its audit prints the YES line.
"""


def flow_verify_md(kit):
    n_fields = sum(l["fieldsExpected"] for l in kit)
    n_idx = sum(l["indexesExpected"] for l in kit)
    crit = {l["listTitle"]: l for l in kit}
    by_key = {l["listTitle"].replace(" ", "_"): l for l in kit}
    crit_lines = "\n".join(
        f"  {name.replace('MF_', 'MF ').replace('_', ' ')} "
        f"{exp}/{exp}" for name, exp in CRITICAL)
    return f"""# VERIFY flow — read-only audit, click by click

Run this AFTER the BUILD flow, before any CSV. It writes nothing: every
call is a GET. Its final Compose is the audit — **screenshot it or copy
it into the deployment record**, and do not load configuration until its
last line reads `SAFE TO LOAD CONFIGURATION: YES`. **Delete both flows
after the signed audit** — they are provisioning tools, not residents.

## Create the flow

Instant cloud flow → **Manually trigger a flow** → name it
`MF Blank-Slate VERIFY`.

## Action 1 — Compose, rename: `Schema`

Paste the ENTIRE contents of `SCHEMA-PAYLOADS.json` (same paste as the
BUILD flow).

## Action 2 — Initialize variable, rename: `Results`

Name `Results` · Type `Array` · Value: leave empty.

## Action 3 — Apply to each, rename: `For each list`

*Select an output*: expression `outputs('Schema')`
**Settings → Concurrency Control → On → 1** (results stay in list
order).

Inside it, four actions in order:

### 3a — SharePoint → **Send an HTTP request to SharePoint**, rename: `Get fields`

| Parameter | Value |
|---|---|
| Site Address | **OPERATOR VALUE — your links sheet** |
| Method | `GET` |
| Uri | expression: `concat('_api/web/lists/getbytitle(''', items('For_each_list')?['listTitle'], ''')/fields?$select=InternalName,FieldTypeKind,Indexed&$top=500')` |
| Headers | `Accept` = `application/json;odata=nometadata` |

### 3b — **Filter array**, rename: `Columns present`

| Setting | Value |
|---|---|
| From | expression: `items('For_each_list')?['fields']` |
| Condition (advanced mode) | `@contains(string(body('Get_fields')), concat('"InternalName":"', item()?['internalName'], '"'))` |

Counts how many of THIS list's schema fields exist on the site, by
internal name — the only name that matters.

### 3c — **Filter array**, rename: `Indexes present`

| Setting | Value |
|---|---|
| From | expression: `items('For_each_list')?['indexOps']` |
| Condition (advanced mode) | `@contains(string(body('Get_fields_indexed')), concat('"InternalName":"', item()?['field'], '"'))` |

…which needs its own read first: add **Send an HTTP request to
SharePoint**, rename `Get fields indexed`, between 3a and 3c —
identical to 3a except the Uri ends
`/fields?$select=InternalName&$filter=Indexed eq true&$top=500`.

### 3d — **Append to array variable**, rename: `Record result`

Name `Results` · Value (expression):

```
json(concat('{{"list":"', items('For_each_list')?['listTitle'],
 '","columnsFound":', length(body('Columns_present')),
 ',"columnsExpected":', items('For_each_list')?['fieldsExpected'],
 ',"indexesFound":', length(body('Indexes_present')),
 ',"indexesExpected":', items('For_each_list')?['indexesExpected'], '}}'))
```

## Action 4 — Filter array, rename: `Mismatches`

| Setting | Value |
|---|---|
| From | expression: `variables('Results')` |
| Condition (advanced mode) | `@or(not(equals(item()?['columnsFound'], item()?['columnsExpected'])), not(equals(item()?['indexesFound'], item()?['indexesExpected'])))` |

## Action 5 — Compose, rename: `Audit`

Inputs (expression):

```
concat('MF BLANK-SLATE PROVISIONING AUDIT', decodeUriComponent('%0A'),
 join(variables('Results'), decodeUriComponent('%0A')),
 decodeUriComponent('%0A'), 'CRITICAL LISTS (found must equal expected):',
 decodeUriComponent('%0A'),
'{crit_lines}',
 decodeUriComponent('%0A'), 'TOTAL expected: 17 lists / {n_fields} columns / {n_idx} indexes',
 decodeUriComponent('%0A'), 'SAFE TO LOAD CONFIGURATION: ',
 if(equals(length(body('Mismatches')), 0), 'YES', 'NO — fix and re-verify'))
```

The per-list lines print as JSON objects — found next to expected, list
by list. The critical six must read, in the audit's own numbers:

```
{crit_lines}
```

`YES` appears only when EVERY list's found equals expected — the
`Mismatches` filter is the arbiter, not the operator's eye. Anything
else: back to the BUILD runbook's delete-fix-rerun loop.
"""


def readme(kit):
    n_fields = sum(l["fieldsExpected"] for l in kit)
    n_idx = sum(l["indexesExpected"] for l in kit)
    return f"""# MF Ops — blank-slate provisioning kit (revision 3)

For a pilot provisioned ENTIRELY by hand onto a BLANK site: delete any
existing MF lists, click two small flows together, run BUILD, run
VERIFY, sign the audit, then load configuration. Email-safe: no
scripts, no binaries — everything runs inside Power Automate.

| File | What it is |
|---|---|
| `SCHEMA-PAYLOADS.json` | {len(kit)} lists / {n_fields} columns / {n_idx} indexes, every REST payload, generated from the schema authority — pasted once into each flow |
| `FLOW-BUILD.md` | the BUILD flow, click by click — 4 action shapes, no branches, fail-stop by design |
| `FLOW-VERIFY.md` | the read-only audit flow — no CSV loads before its YES line |
| `SHA256SUMS.txt` | integrity manifest |

Order: verify this kit's hashes → delete existing MF lists (BUILD
runbook lists the 17 names) → build both flows → run BUILD → run
VERIFY → record the audit → **delete both flows** → continue with the
manual kit's CSV import.

Offline proof: every payload in this kit was replayed against a mock
SharePoint that enforces create-order, rejects duplicate internal
names, and derives internal names the way SharePoint does — final
state {len(kit)}/{n_fields}/{n_idx}, zero `_x0020_` names, and the
VERIFY audit renders YES against that state
(`tests/test_blankslate_kit.py`). The live run in your tenant is
**NOT TESTABLE LOCALLY**; these flows have NOT been executed in Power
Automate, and this kit does not claim otherwise.
"""


def main():
    if os.path.isdir(KIT):
        shutil.rmtree(KIT)
    schema = build()
    kit = project(schema)

    n_lists = len(kit)
    n_fields = sum(l["fieldsExpected"] for l in kit)
    n_idx = sum(l["indexesExpected"] for l in kit)
    assert (n_lists, n_fields, n_idx) == (17, 286, 90), \
        (n_lists, n_fields, n_idx)
    for name, exp in CRITICAL:
        title = name.replace("_", " ").replace("MF ", "MF ", 1)
    _w(os.path.join(KIT, "SCHEMA-PAYLOADS.json"),
       json.dumps(kit, indent=1) + "\n")
    _w(os.path.join(KIT, "FLOW-BUILD.md"), flow_build_md(kit))
    _w(os.path.join(KIT, "FLOW-VERIFY.md"), flow_verify_md(kit))
    _w(os.path.join(KIT, "README.md"), readme(kit))
    print(f"kit: {KIT}\n  {n_lists} lists / {n_fields} columns / "
          f"{n_idx} indexes; {n_lists + n_fields + n_idx} REST calls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
