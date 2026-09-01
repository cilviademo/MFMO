# 06 — create list `MF Document Destination`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Document Destination`

> THE FOUR PORTFOLIOS ARE FOUR SEPARATE SITE COLLECTIONS, not four channels in one team and not four folders in one library. Every earlier document in this programme assumed one site; that assumption was wrong and it invalidated every single-site provisioning plan. Site, library and root folder are configured per portfolio and never derived: Portfolio 2's site slug carries a 'Legacy_' prefix the other three do not, so a URL built by pattern 404s on exactly one portfolio — three work and one is a mystery, which is the worst failure shape there is. EOM-02 fails closed on an unbound, unverified or inactive row.

Grain: One row per portfolio per document domain · expected volume ~20 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Destination_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Portfolio_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 3 | `Document_Domain` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | EOM<br>EOY<br>FMAT<br>Other | **Y** | N |
| 4 | `Site_URL` | Single line of text | 255 characters | No |  | N | N |
| 5 | `Library_Name` | Single line of text | 255 characters | Yes |  | N | N |
| 6 | `Library_Url_Segment` | Single line of text | 255 characters | Yes |  | N | N |
| 7 | `Root_Folder` | Single line of text | 255 characters | Yes |  | N | N |
| 8 | `Folder_Template` | Single line of text | 255 characters | Yes |  | N | N |
| 9 | `Create_Missing_Folders` | Yes/No | Default: No | Yes |  | N | N |
| 10 | `Fallback_Policy` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | FIND_OR_ROOT<br>FIND_OR_FAIL | N | N |
| 11 | `Month_Folder_Pattern_Note` | Single line of text | 255 characters | No |  | N | N |
| 12 | `Site_Note` | Single line of text | 255 characters | No |  | N | N |
| 13 | `Verified_By` | Single line of text | 255 characters | No |  | N | N |
| 14 | `Verified_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 15 | `Active_Flag` | Yes/No | Default: No | Yes |  | N | N |

## Indexes — 3 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Destination_ID`
- [ ] `Portfolio_ID`
- [ ] `Document_Domain`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **15 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 3**.
- [ ] Spot check: `Document_Domain` offers exactly these choices, spelled exactly: `EOM`, `EOY`, `FMAT`, `Other`.
- [ ] Spot check: the unique-key column(s) `Destination_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Destination_ID` is marked required.
