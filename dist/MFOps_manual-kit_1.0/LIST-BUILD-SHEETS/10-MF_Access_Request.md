# 10 — create list `MF Access Request`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Access Request`

> Modelled on how Teams handles a request to join. Someone who PCS'd but still owes their losing base a package requests that installation, with a justification and an expiry. The exception path to the GAL-derived model, not a parallel provisioning system.

Grain: One row per request for access to an installation the requester is not posted to · expected volume ~5,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Request_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Requester_UPN` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 3 | `Requester_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 4 | `Home_Installation` | Single line of text | 255 characters | No |  | N | N |
| 5 | `Requested_Installation_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 6 | `Justification` | Multiple lines of text | Plain text | Yes |  | N | N |
| 7 | `Requested_Until` | Date and Time | Include Time: Yes | No |  | N | N |
| 8 | `Status` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Pending<br>Approved<br>Denied<br>Expired | **Y** | N |
| 9 | `Decided_By` | Single line of text | 255 characters | No |  | N | N |
| 10 | `Decided_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 11 | `Decision_Comment` | Multiple lines of text | Plain text | No |  | N | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Request_ID`
- [ ] `Requester_UPN`
- [ ] `Requested_Installation_ID`
- [ ] `Status`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **11 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Status` offers exactly these choices, spelled exactly: `Pending`, `Approved`, `Denied`, `Expired`.
- [ ] Spot check: the unique-key column(s) `Request_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Request_ID` is marked required.
