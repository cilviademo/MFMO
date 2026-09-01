# 01 — create list `MF App Config`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF App Config`

> Admin-managed, read-only to everyone else. This is the kill switch: when something breaks after a publish you flip MaintenanceMode rather than racing to unpublish. Every environment-variable value has a matching row here, so neither path is load-bearing alone.

Grain: One row per configuration key · expected volume ~100 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Config_Key` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Config_Value` | Single line of text | 255 characters | Yes |  | N | N |
| 3 | `Config_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | String<br>Boolean<br>Number<br>Date | N | N |
| 4 | `Description` | Multiple lines of text | Plain text | No |  | N | N |
| 5 | `Admin_Only` | Yes/No | Default: No | Yes |  | N | N |
| 6 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 2 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Config_Key`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **6 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 2**.
- [ ] Spot check: `Config_Type` offers exactly these choices, spelled exactly: `String`, `Boolean`, `Number`, `Date`.
- [ ] Spot check: the unique-key column(s) `Config_Key` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Config_Key` is marked required.
