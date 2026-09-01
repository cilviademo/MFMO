# 05 — create list `MF EOM Requirement`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF EOM Requirement`

> THE requirement engine. The app queries this; it contains no 'if Legacy then require 1119' logic. Changing a requirement next year is a list edit, not an app rebuild.

Grain: One row per document requirement per operating model · expected volume ~200 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Requirement_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Document_Code` | Single line of text | 255 characters | Yes |  | N | N |
| 3 | `Document_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 4 | `Applicable_Model` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Legacy/APF<br>Food 2.0<br>MAFFO/MAF<br>AOR/CDS<br>All | N | N |
| 5 | `Requirement_Scope` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Facility<br>Installation<br>Contract | N | N |
| 6 | `Scope_Confidence` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Verified<br>High<br>Medium<br>Low<br>Proposed | N | N |
| 7 | `Scope_Basis` | Multiple lines of text | Plain text | No |  | N | N |
| 8 | `Applicable_Facility_Types` | Single line of text | 255 characters | No |  | N | N |
| 9 | `Applicable_Period_Month` | Number | Decimal places: Automatic | No |  | N | N |
| 10 | `Routing_Org` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | AFSVC/VMF<br>NGB/A1X<br>AFRC/A1S<br>Installation | N | N |
| 11 | `Frequency` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Monthly<br>Quarterly<br>Semiannual<br>Annual<br>Conditional | **Y** | N |
| 12 | `Required_Flag` | Yes/No | Default: No | Yes |  | N | N |
| 13 | `Due_Day` | Number | Decimal places: Automatic | Yes |  | N | N |
| 14 | `Due_Basis` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | CALENDAR<br>DUTY_DAY | N | N |
| 15 | `Final_Due_Day` | Number | Decimal places: Automatic | No |  | N | N |
| 16 | `Final_Due_Basis` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | CALENDAR<br>DUTY_DAY | N | N |
| 17 | `NonDutyDay_Policy` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | NEXT_DUTY_DAY<br>PREVIOUS_DUTY_DAY<br>NO_ADJUSTMENT | N | N |
| 18 | `QC_Required` | Yes/No | Default: No | Yes |  | N | N |
| 19 | `Accepted_File_Types` | Single line of text | 255 characters | No |  | N | N |
| 20 | `Authority_Reference` | Single line of text | 255 characters | No |  | N | N |
| 21 | `Authority_Status` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | VERIFIED<br>MANAGEMENT_RULE<br>PROPOSED<br>UNVERIFIED<br>RETIRED_OR_NOT_APPLICABLE | **Y** | N |
| 22 | `Sort_Order` | Number | Decimal places: Automatic | No |  | N | N |
| 23 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Requirement_ID`
- [ ] `Frequency`
- [ ] `Authority_Status`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **23 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Applicable_Model` offers exactly these choices, spelled exactly: `Legacy/APF`, `Food 2.0`, `MAFFO/MAF`, `AOR/CDS`, `All`.
- [ ] Spot check: the unique-key column(s) `Requirement_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Requirement_ID` is marked required.
