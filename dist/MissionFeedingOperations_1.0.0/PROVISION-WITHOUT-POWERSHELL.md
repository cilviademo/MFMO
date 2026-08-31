# Provisioning without PowerShell

No module install rights is a normal .mil constraint and it does not block you.
Three routes, best first.

`scripts/gen_rest_payloads.py` has produced:

```
provisioning/sharepoint-schema.json     17 lists, 284 columns, 89 indexes
provisioning/manual-column-sheet.csv    the same thing as a flat checklist
```

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

Viable but slow: 284 columns. Use `manual-column-sheet.csv` as the checklist.

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
89 indexes via List settings → Indexed columns.

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
