# 02 — create list `MF Feature Flags`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Feature Flags`

> Ship a new screen inside the published app while normal users still see the old one. Beats the manual old-screen/new-screen rename: no rebuild, and the rollback is a checkbox.

Grain: One row per feature · expected volume ~100 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Feature_Key` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Feature_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 3 | `Enabled_Prod` | Yes/No | Default: No | Yes |  | N | N |
| 4 | `Enabled_Testers` | Yes/No | Default: No | Yes |  | N | N |
| 5 | `Minimum_Role` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | BASE_USER<br>PORTFOLIO_MANAGER<br>DEVELOPER | N | N |
| 6 | `Effective_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 7 | `Notes` | Multiple lines of text | Plain text | No |  | N | N |

## Indexes — 1 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Feature_Key`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **7 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 1**.
- [ ] Spot check: `Minimum_Role` offers exactly these choices, spelled exactly: `BASE_USER`, `PORTFOLIO_MANAGER`, `DEVELOPER`.
- [ ] Spot check: the unique-key column(s) `Feature_Key` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Feature_Key` is marked required.
