# BUILD flow — blank-slate provisioning, click by click

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
- Opening it: `For each list` shows **17 iterations**, every
  `Create list` returned 201; `For each field` totals **286**
  creates; `For each index` totals **90** merges (200/204).
- **393 REST calls in total.** At concurrency 1, expect roughly
  **10–25 minutes** — an estimate; the real duration is NOT TESTABLE
  LOCALLY and depends on tenant throttling.

## When a run fails — delete, fix, rerun

The run stops at the failing action with SharePoint's error in the
output — read it there. Then **Site contents → delete every MF list
that exists** (the flow has no resume; a partial site plus a rerun
means duplicate-create failures). Delete EXACTLY these 17 and
**nothing else on the site**:

- `MF Installation`
- `MF Facility`
- `MF EOM Requirement`
- `MF EOM Item`
- `MF EOM Submission`
- `MF Unmatched File`
- `MF Security Mapping`
- `MF EOM Audit`
- `MF App Config`
- `MF Feature Flags`
- `MF App Event Log`
- `MF EOM Status`
- `MF Non Duty Day`
- `MF Calendar Event`
- `MF Access Request`
- `MF Notification Rule`
- `MF Document Destination`

Fix the cause (usually a paste error in an action), then rerun. The
schema JSON itself is machine-generated and replay-proven offline; if
the same action fails twice with the same 4xx, suspect the pasted
expression, not the payload.

Then run the VERIFY flow (`FLOW-VERIFY.md`). No CSV touches any list
before its audit prints the YES line.
