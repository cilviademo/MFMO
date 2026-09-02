# VERIFY flow — read-only audit, click by click

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
json(concat('{"list":"', items('For_each_list')?['listTitle'],
 '","columnsFound":', length(body('Columns_present')),
 ',"columnsExpected":', items('For_each_list')?['fieldsExpected'],
 ',"indexesFound":', length(body('Indexes_present')),
 ',"indexesExpected":', items('For_each_list')?['indexesExpected'], '}'))
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
'  MF EOM Item 13/13
  MF EOM Submission 13/13
  MF EOM Status 8/8
  MF Security Mapping 8/8
  MF App Event Log 6/6
  MF EOM Audit 4/4',
 decodeUriComponent('%0A'), 'TOTAL expected: 17 lists / 286 columns / 90 indexes',
 decodeUriComponent('%0A'), 'SAFE TO LOAD CONFIGURATION: ',
 if(equals(length(body('Mismatches')), 0), 'YES', 'NO — fix and re-verify'))
```

The per-list lines print as JSON objects — found next to expected, list
by list. The critical six must read, in the audit's own numbers:

```
  MF EOM Item 13/13
  MF EOM Submission 13/13
  MF EOM Status 8/8
  MF Security Mapping 8/8
  MF App Event Log 6/6
  MF EOM Audit 4/4
```

`YES` appears only when EVERY list's found equals expected — the
`Mismatches` filter is the arbiter, not the operator's eye. Anything
else: back to the BUILD runbook's delete-fix-rerun loop.
