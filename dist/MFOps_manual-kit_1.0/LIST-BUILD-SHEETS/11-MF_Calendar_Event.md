# 11 — create list `MF Calendar Event`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Calendar Event`

> Authored events only. Every expected item is ALREADY a dated event and is projected onto the calendar from MF_EOM_Item — duplicating them here would create two sources of truth for the same suspense. This list carries what the checklist cannot: assessments, data calls, reminders.

Grain: One row per authored calendar entry · expected volume ~20,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Event_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Event_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Suspense<br>Correction due<br>Assessment<br>Data call<br>Reminder | N | N |
| 3 | `Title` | Single line of text | 255 characters | Yes |  | N | N |
| 4 | `Event_Date` | Date and Time | Include Time: Yes | Yes |  | **Y** | N |
| 5 | `End_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 6 | `All_Day` | Yes/No | Default: No | Yes |  | N | N |
| 7 | `Scope_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Enterprise<br>Portfolio<br>Installation<br>Facility | N | N |
| 8 | `Scope_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 9 | `Linked_Item_ID` | Single line of text | 255 characters | No |  | N | N |
| 10 | `Status_Code` | Number | Decimal places: Automatic | Yes |  | N | N |
| 11 | `Created_By` | User |  | Yes |  | N | N |
| 12 | `Created_DateTime` | Date and Time | Include Time: Yes | Yes |  | N | N |
| 13 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Event_ID`
- [ ] `Event_Date`
- [ ] `Scope_ID`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **13 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Event_Type` offers exactly these choices, spelled exactly: `Suspense`, `Correction due`, `Assessment`, `Data call`, `Reminder`.
- [ ] Spot check: the unique-key column(s) `Event_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Event_ID` is marked required.
