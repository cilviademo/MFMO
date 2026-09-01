# 03 — create list `MF Installation`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Installation`

> With MF_Facility this is the authoritative EOM operational registry until an enterprise source supersedes it. CrunchTime, Aloha Enterprise and Teams all differ and none tracks what EOM needs, so it is built here by hand and signed off per base.

Grain: One row per installation · expected volume ~103 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Installation_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Installation_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 3 | `Source_Installation_String` | Single line of text | 255 characters | No |  | N | N |
| 4 | `Location` | Single line of text | 255 characters | No |  | N | N |
| 5 | `Portfolio_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 6 | `MAJCOM` | Single line of text | 255 characters | No |  | N | N |
| 7 | `Component` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Active<br>ANG<br>AFRC | N | N |
| 8 | `EOM_Folder_URL` | Hyperlink or Picture | Format: Hyperlink | No |  | N | N |
| 9 | `Generation_Enabled` | Yes/No | Default: No | Yes |  | **Y** | N |
| 10 | `Registry_Validated_By` | Single line of text | 255 characters | No |  | N | N |
| 11 | `Registry_Validated_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 12 | `Source_System` | Single line of text | 255 characters | No |  | N | N |
| 13 | `Needs_Review_Flag` | Yes/No | Default: No | No |  | N | N |
| 14 | `DODAAC` | Single line of text | 255 characters | No |  | N | N |
| 15 | `DODAAD` | Single line of text | 255 characters | No |  | N | N |
| 16 | `Org_Box_Email` | Single line of text | 255 characters | No |  | N | N |
| 17 | `Official_POC_UPN` | Single line of text | 255 characters | No |  | N | N |
| 18 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Installation_ID`
- [ ] `Portfolio_ID`
- [ ] `Generation_Enabled`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **18 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Component` offers exactly these choices, spelled exactly: `Active`, `ANG`, `AFRC`.
- [ ] Spot check: the unique-key column(s) `Installation_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Installation_ID` is marked required.
