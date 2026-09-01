# 15 — create list `MF EOM Status`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF EOM Status`

> Materialized by EOM-03. Power BI NEVER reconstructs workflow logic; it colours on Status_Code and labels with Final_Status. Every workflow decision is resolved before the report sees the row.

Grain: One flat row per EOM item — the canonical Power BI fact · expected volume ~250,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Status_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `EOM_Item_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 3 | `Reporting_Period` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 4 | `Fiscal_Year` | Single line of text | 255 characters | Yes |  | N | N |
| 5 | `Portfolio_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 6 | `Installation_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 7 | `Installation_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 8 | `Facility_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 9 | `Facility_Name` | Single line of text | 255 characters | No |  | N | N |
| 10 | `Operating_Model` | Single line of text | 255 characters | No |  | N | N |
| 11 | `Contract_ID` | Single line of text | 255 characters | No |  | N | N |
| 12 | `Requirement_ID` | Single line of text | 255 characters | Yes |  | N | N |
| 13 | `Requirement_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 14 | `Document_Code` | Single line of text | 255 characters | Yes |  | N | N |
| 15 | `Requirement_Scope` | Single line of text | 255 characters | Yes |  | N | N |
| 16 | `Authority_Status` | Single line of text | 255 characters | Yes |  | N | N |
| 17 | `Scope_Confidence` | Single line of text | 255 characters | No |  | N | N |
| 18 | `Routing_Org` | Single line of text | 255 characters | No |  | N | N |
| 19 | `Component` | Single line of text | 255 characters | No |  | N | N |
| 20 | `Required_Flag` | Yes/No | Default: No | Yes |  | N | N |
| 21 | `Nominal_Due_Date` | Date and Time | Include Time: Yes | Yes |  | N | N |
| 22 | `Effective_Due_Date` | Date and Time | Include Time: Yes | Yes |  | N | N |
| 23 | `Nominal_Final_Call_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 24 | `Effective_Final_Call_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 25 | `Due_Date_Adjusted` | Yes/No | Default: No | No |  | N | N |
| 26 | `Received_Flag` | Yes/No | Default: No | Yes |  | N | N |
| 27 | `Initial_Submitted_DateTime` | Date and Time | Include Time: Yes | No |  | N | N |
| 28 | `Initial_Submission_On_Time` | Yes/No | Default: No | No |  | N | N |
| 29 | `Final_Evidence_On_Time` | Yes/No | Default: No | No |  | N | N |
| 30 | `Version_No` | Number | Decimal places: Automatic | No |  | N | N |
| 31 | `QC_Status` | Single line of text | 255 characters | No |  | N | N |
| 32 | `Final_Status` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 33 | `Status_Code` | Number | Decimal places: Automatic | Yes |  | **Y** | N |
| 34 | `Action_Owner` | Single line of text | 255 characters | Yes |  | N | N |
| 35 | `Action_Required` | Yes/No | Default: No | Yes |  | N | N |
| 36 | `Package_State` | Single line of text | 255 characters | Yes |  | N | N |
| 37 | `Days_Late` | Number | Decimal places: Automatic | No |  | N | N |
| 38 | `Current_File_URL` | Hyperlink or Picture | Format: Hyperlink | No |  | N | N |
| 39 | `Generated_DateTime` | Date and Time | Include Time: Yes | Yes |  | N | N |

## Indexes — 8 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Status_ID`
- [ ] `EOM_Item_ID`
- [ ] `Reporting_Period`
- [ ] `Portfolio_ID`
- [ ] `Installation_ID`
- [ ] `Facility_ID`
- [ ] `Final_Status`
- [ ] `Status_Code`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **39 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 8**.
- [ ] Spot check: the unique-key column(s) `Status_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Status_ID` is marked required.
