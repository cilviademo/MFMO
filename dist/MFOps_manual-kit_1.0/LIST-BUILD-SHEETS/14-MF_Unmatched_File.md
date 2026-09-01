# 14 — create list `MF Unmatched File`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Unmatched File`

> The safety net for folder drops. Should trend toward empty once people use the app. No content parsing and no AI Builder in MVP — a human picks from dropdowns. NEVER INVENT A REQUIREMENT: resolving a row here attaches the file to an existing expected item and never creates one.

Grain: One row per file found in the FY folder that could not be resolved · expected volume ~5,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Unmatched_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `File_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 3 | `File_URL` | Hyperlink or Picture | Format: Hyperlink | Yes |  | N | N |
| 4 | `Portfolio_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 5 | `Fiscal_Year` | Single line of text | 255 characters | No |  | N | N |
| 6 | `Discovered_DateTime` | Date and Time | Include Time: Yes | Yes |  | **Y** | N |
| 7 | `Uploaded_By` | User |  | No |  | N | N |
| 8 | `Suggested_Installation_ID` | Single line of text | 255 characters | No |  | N | N |
| 9 | `Suggested_Document_Code` | Single line of text | 255 characters | No |  | N | N |
| 10 | `Resolution_Status` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Needs Classification<br>Classified<br>Not an EOM document<br>Duplicate | **Y** | N |
| 11 | `Resolved_Submission_ID` | Single line of text | 255 characters | No |  | N | N |
| 12 | `Resolved_By` | User |  | No |  | N | N |
| 13 | `Resolved_DateTime` | Date and Time | Include Time: Yes | No |  | N | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Unmatched_ID`
- [ ] `Portfolio_ID`
- [ ] `Discovered_DateTime`
- [ ] `Resolution_Status`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **13 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Resolution_Status` offers exactly these choices, spelled exactly: `Needs Classification`, `Classified`, `Not an EOM document`, `Duplicate`.
- [ ] Spot check: the unique-key column(s) `Unmatched_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Unmatched_ID` is marked required.
