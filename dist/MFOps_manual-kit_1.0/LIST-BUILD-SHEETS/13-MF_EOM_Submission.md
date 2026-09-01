# 13 — create list `MF EOM Submission`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF EOM Submission`

> Versioned evidence. v1 Correction Required and v2 Accepted both persist; nothing is overwritten or deleted. QC applies to the Is_Current version.

Grain: One row per uploaded file version · expected volume ~400,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Submission_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Submission_Request_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 3 | `EOM_Item_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 4 | `Version_No` | Number | Decimal places: Automatic | Yes |  | N | N |
| 5 | `File_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 6 | `File_URL` | Hyperlink or Picture | Format: Hyperlink | Yes |  | N | N |
| 7 | `File_Size_KB` | Number | Decimal places: Automatic | No |  | N | N |
| 8 | `Uploaded_By` | User |  | Yes |  | N | N |
| 9 | `Uploaded_DateTime` | Date and Time | Include Time: Yes | Yes |  | **Y** | N |
| 10 | `Submitted_On_Behalf_Of` | Single line of text | 255 characters | No |  | N | N |
| 11 | `Intake_Method` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | App upload<br>Folder drop<br>Manual classification | N | N |
| 12 | `Classification_Method` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | Declared at upload<br>Folder context<br>Document content<br>AI Builder<br>Manual | N | N |
| 13 | `Classification_Status` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | Pending<br>Classified<br>Needs Review<br>Failed | **Y** | N |
| 14 | `Portfolio_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 15 | `Classification_Confidence` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | No | Declared<br>High<br>Low<br>Unresolved | N | N |
| 16 | `Last_Error_Code` | Single line of text | 255 characters | No |  | N | N |
| 17 | `Last_Error_Message` | Multiple lines of text | Plain text | No |  | N | N |
| 18 | `Last_Processing_DateTime` | Date and Time | Include Time: Yes | No |  | N | N |
| 19 | `Retry_Count` | Number | Decimal places: Automatic | No |  | N | N |
| 20 | `Destination_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 21 | `Source_Library` | Single line of text | 255 characters | No |  | N | N |
| 22 | `Source_Path` | Single line of text | 255 characters | No |  | N | N |
| 23 | `Is_Pilot` | Yes/No | Default: No | No |  | **Y** | N |
| 24 | `Needs_Filing` | Yes/No | Default: No | No |  | **Y** | N |
| 25 | `Filing_Note` | Single line of text | 255 characters | No |  | N | N |
| 26 | `SharePoint_Unique_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 27 | `SharePoint_File_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 28 | `Is_Current` | Yes/No | Default: No | Yes |  | **Y** | N |
| 29 | `Superseded_By` | Single line of text | 255 characters | No |  | N | N |
| 30 | `QC_Status` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Pending Review<br>Accepted<br>Correction Required<br>Incomplete<br>Wrong Document<br>Wrong Reporting Period<br>Wrong Facility<br>Recalled<br>Not Applicable | **Y** | N |
| 31 | `QC_By` | User |  | No |  | N | N |
| 32 | `QC_DateTime` | Date and Time | Include Time: Yes | No |  | N | N |
| 33 | `QC_Comment` | Multiple lines of text | Plain text | No |  | N | N |

## Indexes — 13 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Submission_ID`
- [ ] `Submission_Request_ID`
- [ ] `EOM_Item_ID`
- [ ] `Uploaded_DateTime`
- [ ] `Classification_Status`
- [ ] `Portfolio_ID`
- [ ] `Destination_ID`
- [ ] `Is_Pilot`
- [ ] `Needs_Filing`
- [ ] `SharePoint_Unique_ID`
- [ ] `SharePoint_File_ID`
- [ ] `Is_Current`
- [ ] `QC_Status`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **33 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 13**.
- [ ] Spot check: `Intake_Method` offers exactly these choices, spelled exactly: `App upload`, `Folder drop`, `Manual classification`.
- [ ] Spot check: the unique-key column(s) `Submission_ID`, `Submission_Request_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Submission_ID` is marked required.
