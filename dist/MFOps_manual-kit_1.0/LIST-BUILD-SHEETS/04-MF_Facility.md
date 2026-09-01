# 04 — create list `MF Facility`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Facility`

> Operating_Model is HERE, not on the installation. One base can run a legacy DFAC and a Food 2.0 cafe simultaneously, and the requirement set follows the facility. Multi-facility installations are normal: the SAIIT guidance describes transfers between a second DFAC and a flight kitchen at the same base, and the 1119 initialises ONE facility and one month.

Grain: One row per feeding facility · expected volume ~154 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Facility_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Installation_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 3 | `Facility_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 4 | `Designation` | Single line of text | 255 characters | No |  | N | N |
| 5 | `Unit` | Single line of text | 255 characters | No |  | N | N |
| 6 | `Facility_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | Main DFAC<br>Flight Kitchen<br>Kiosk<br>Satellite<br>MAF<br>Contract Cafe | N | N |
| 7 | `Operating_Model` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | Legacy/APF<br>Food 2.0<br>MAFFO/MAF<br>AOR/CDS | **Y** | N |
| 8 | `Source_Operating_Model` | Single line of text | 255 characters | No |  | N | N |
| 9 | `Program_Type` | Single line of text | 255 characters | No |  | N | N |
| 10 | `Contract_Type` | Single line of text | 255 characters | No |  | N | N |
| 11 | `Primary_PV` | Single line of text | 255 characters | No |  | N | N |
| 12 | `POS_Terminals_Raw` | Single line of text | 255 characters | No |  | N | N |
| 13 | `POC_Display_Name` | Single line of text | 255 characters | No |  | N | N |
| 14 | `In_R1_Scope` | Yes/No | Default: No | No |  | **Y** | N |
| 15 | `Source_Row` | Number | Decimal places: Automatic | No |  | N | N |
| 16 | `Source_System` | Single line of text | 255 characters | No |  | N | N |
| 17 | `Facility_DODAAC` | Single line of text | 255 characters | No |  | N | N |
| 18 | `Contract_ID` | Single line of text | 255 characters | No |  | N | N |
| 19 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 5 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Facility_ID`
- [ ] `Installation_ID`
- [ ] `Operating_Model`
- [ ] `In_R1_Scope`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **19 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 5**.
- [ ] Spot check: `Facility_Type` offers exactly these choices, spelled exactly: `Main DFAC`, `Flight Kitchen`, `Kiosk`, `Satellite`, `MAF`, `Contract Cafe`.
- [ ] Spot check: the unique-key column(s) `Facility_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Facility_ID` is marked required.
