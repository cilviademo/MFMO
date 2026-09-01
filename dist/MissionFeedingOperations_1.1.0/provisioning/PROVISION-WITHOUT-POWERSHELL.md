# Provisioning without PowerShell

**PowerShell is unavailable on the target network.** This is the route.

Everything here is generated from `scripts/eom_schema.py` by
`scripts/gen_rest_payloads.py`. Regenerate rather than hand-edit:

```
python3 scripts/gen_rest_payloads.py
```

| File | What it is |
|---|---|
| `provisioning/sharepoint-schema.json` | 17 lists, 286 columns, 90 indexes. Per list: the create payload, one payload per field with the internal name passed as `Title`, an explicit index operation per indexed column, and what uniqueness SharePoint actually enforces. |
| `provisioning/whatif-report.md` | What every call would do, in order, before any of them run. The irreversible ones are marked. |
| `provisioning/manual-column-sheet.csv` | The same thing as a checklist, for creating columns by hand. |

## Read the WhatIf report first

Provisioning is the one step in this deployment with an unrepairable failure in
it. SharePoint refuses to add an index once a list passes **5,000 items**, and
`MF EOM Item` passes that in the first quarter. The WhatIf report marks every
list that will cross it.

Two thresholds are involved and conflating them is how an index gets skipped:

| | Rows | What happens past it |
|---|---:|---|
| Delegation ceiling | 2,000 | A non-delegable query returns the first page **and reports success**. A client limit. |
| List view threshold | 5,000 | An index can never be added. A server limit, and permanent. |

## The route: Send an HTTP request to SharePoint

Provisioning runs from a Power Automate flow using the **SharePoint
connector's** own *Send an HTTP request to SharePoint* action. That is the
SharePoint connector, not the prohibited HTTP connector — a different connector
entirely. `prerelease_scan.py` rule `CON-02` was tightened to know the
difference rather than being told to skip this file, because a file-level
exemption would also have silenced a real HTTP connector added here later.

For each list, in the order the JSON gives them:

1. `POST _api/web/lists` with `createPayload`
2. `POST .../fields` once per entry in `fields`, with that entry's `payload`
3. `MERGE` once per entry in `indexOperations` — **do not skip these and do not
   defer them**

## Then verify, because "the run said OK" is not evidence

A run can create a list, most of its columns and none of its indexes, and
report success throughout. Export the tenant's real list schemas to JSON and
compare:

```
python3 scripts/verify_provisioning.py <tenant-export.json>
```

It fails on a missing list, a missing column, and — hardest — an index missing
from a list projected past 5,000 rows. It is **NOT TESTABLE LOCALLY** against a
real tenant; `tests/fixtures/tenant-schema-*.json` prove the comparison, not
the tenant.

---


## Route 1 — Power Automate (recommended)

The SharePoint connector includes an action called **Send an HTTP request to  <!-- prerelease: allow CON-02 SharePoint connector action, not the HTTP connector; no custom connector and no admin rights -->
SharePoint**. It is not the HTTP connector, it is not a custom connector, and it
does not need admin rights. It runs under your own credentials against a site
you own, and it can do everything the PowerShell script does.

You already have Power Automate. This is the route.

### Build one flow, run it once

**Trigger:** Manually trigger a flow

**Step 1 — Compose: `Schema`**
Paste the entire contents of `sharepoint-schema.json`.

**Step 2 — Apply to each: `outputs('Schema')`**

Inside the loop:

**2a. Create the list**

```
Send an HTTP request to SharePoint  <!-- prerelease: allow CON-02 SharePoint connector action, not the HTTP connector; no custom connector and no admin rights -->
  Site Address: <your site URL — see deployment/site-bindings.md>
  Method:       POST
  Uri:          _api/web/lists
  Headers:      Accept:        application/json;odata=verbose
                Content-Type:  application/json;odata=verbose
  Body:         @{items('Apply_to_each')?['createPayload']}
```

Set **Configure run after** to continue on failure. A list that already exists
returns an error and the run should carry on to the columns.

**2b. Apply to each field: `items('Apply_to_each')?['fields']`**

```
Send an HTTP request to SharePoint  <!-- prerelease: allow CON-02 SharePoint connector action, not the HTTP connector; no custom connector and no admin rights -->
  Method: POST
  Uri:    _api/web/lists/getbytitle('@{items('Apply_to_each')?['listTitle']}')/fields
  Headers: as above
  Body:   @{items('Apply_to_each_2')?['payload']}
```

**2c. Add each field to the default view**

Newly created fields do not appear in the default view. Immediately after 2b:

```
  Method: POST
  Uri:    _api/web/lists/getbytitle('<list>')/defaultView/viewfields/addviewfield('<field>')
```

Optional but you will want it when checking your work.

**2d. Set the indexes**

Separate loop over `indexedFields`:

```
  Method: POST
  Uri:    _api/web/lists/getbytitle('<list>')/fields/getbyinternalnameortitle('<field>')
  Headers: add  X-HTTP-Method: MERGE
                IF-MATCH: *
  Body:   {"__metadata":{"type":"SP.Field"},"Indexed":true}
```

**Indexes are the one thing you cannot add later.** SharePoint refuses on a list
past 5,000 items, and `MF EOM Item` reaches roughly 3,600 rows on the first
FY26 backfill. If the index calls fail, stop and fix them before importing any
data.

### Why the internal names come out right

The payload sends `Installation_ID` as the `Title` at creation, so SharePoint
derives the internal name from that — `Installation_ID`, no escaping. Had you
typed "Installation ID" in the UI, the internal name would be
`Installation_x0020_ID` permanently, and every formula referencing
`Installation_ID` would fail with no error.

That single detail is why this route is worth the setup over hand-building.

### Verify

```
_api/web/lists/getbytitle('MF EOM Item')/fields?$select=Title,InternalName,TypeAsString&$top=100
```

Every `InternalName` should match `Title`. If any shows `_x0020_`, that column
was created by hand and needs deleting and recreating.

---

## Route 2 — Hand-build in the UI

Viable but slow: 286 columns. Use `manual-column-sheet.csv` as the checklist.

**The one technique that matters.** SharePoint sets the internal name from
whatever you type when the column is created, and it never changes afterwards.
So:

1. Create the column named exactly `Installation_ID` — underscores, no spaces
2. Save
3. Reopen it and change the *display* name to `Installation ID` if you want

Internal name stays `Installation_ID`. Skip step 1 and you are stuck with
`Installation_x0020_ID` forever.

**Do not** create a column by typing a friendly name first.

Order: create all 17 lists, then work list by list down the sheet, then set the
90 indexes via List settings → Indexed columns.

If you take this route, do `MF EOM Item`, `MF EOM Submission`,
`MF EOM Requirement`, `MF Installation` and `MF Facility` first. Those five run
the core loop and let you test while you finish the rest.

---

## Route 3 — Import from Excel

**Do not use this.** SharePoint's "New list → From Excel" infers column types
from the data and mangles names with spaces. You get a list that looks right and
has wrong internal names, which is the worst outcome — it fails later, silently,
somewhere else.

---

## What this does not change

Everything downstream is identical. Same lists, same internal names, same
indexes. The CSV imports, the solution import and the smoke test are unaffected.

The only loss is `Provision-MFOpsLists.ps1` as a one-command rerun. Keep it in
the repo — someone with rights may run it in a later environment, and it stays
the readable definition of what the flow builds.
