# 07 — create list `MF Non Duty Day`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Non Duty Day`

> Federal holidays and wing down days. Resolves Nominal to Effective dates under NonDutyDay_Policy. A nominal suspense landing on a Saturday cannot be the date someone is held to, and a weekend suspense with no rule produces a monthly argument.

Grain: One row per non-duty date · expected volume ~2,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Non_Duty_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Date` | Date and Time | Include Time: Yes | Yes |  | **Y** | N |
| 3 | `Name` | Single line of text | 255 characters | Yes |  | N | N |
| 4 | `Scope_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Enterprise<br>Portfolio<br>Installation | N | N |
| 5 | `Scope_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 6 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Non_Duty_ID`
- [ ] `Date`
- [ ] `Scope_ID`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **6 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Scope_Type` offers exactly these choices, spelled exactly: `Enterprise`, `Portfolio`, `Installation`.
- [ ] Spot check: the unique-key column(s) `Non_Duty_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Non_Duty_ID` is marked required.
