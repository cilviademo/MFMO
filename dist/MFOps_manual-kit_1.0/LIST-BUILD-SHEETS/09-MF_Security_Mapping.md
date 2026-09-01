# 09 — create list `MF Security Mapping`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Security Mapping`

> ONE mapping for both Power Apps filtering and Power BI RLS. Nobody is provisioned for their own base: CAC identifies the user, the GAL gives their installation, and anyone at that installation may view and edit its EOM submissions regardless of unit. Installation is the unit of access.

WARNING: this list drives APP filtering. Power Apps Visible and Filter() are NOT an access-control boundary — see docs/security-open-issue.md. The data layer must enforce the same scope independently.

Grain: One row per user per granted scope · expected volume ~5,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Security_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `UPN` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 3 | `Scope_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Enterprise<br>Portfolio<br>Installation<br>Facility | **Y** | N |
| 4 | `Portfolio_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 5 | `Installation_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 6 | `Facility_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 7 | `Role` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | BASE_USER<br>PORTFOLIO_MANAGER | N | N |
| 8 | `Job_Title` | Single line of text | 255 characters | No |  | N | N |
| 9 | `Can_QC` | Yes/No | Default: No | Yes |  | N | N |
| 10 | `Can_Submit_On_Behalf` | Yes/No | Default: No | Yes |  | N | N |
| 11 | `Can_Edit_Requirements` | Yes/No | Default: No | Yes |  | N | N |
| 12 | `Can_Grant_Access` | Yes/No | Default: No | Yes |  | N | N |
| 13 | `Grant_Scope` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | None<br>Portfolio<br>Enterprise | N | N |
| 14 | `Grant_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | GAL derived<br>Requested<br>Manual | N | N |
| 15 | `Granted_By` | Single line of text | 255 characters | No |  | N | N |
| 16 | `Granted_Date` | Date and Time | Include Time: Yes | No |  | N | N |
| 17 | `Expires_Date` | Date and Time | Include Time: Yes | No |  | **Y** | N |
| 18 | `Developer_Flag` | Yes/No | Default: No | Yes |  | N | N |
| 19 | `Tester_Flag` | Yes/No | Default: No | Yes |  | N | N |
| 20 | `Active_Flag` | Yes/No | Default: No | Yes |  | **Y** | N |

## Indexes — 8 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Security_ID`
- [ ] `UPN`
- [ ] `Scope_Type`
- [ ] `Portfolio_ID`
- [ ] `Installation_ID`
- [ ] `Facility_ID`
- [ ] `Expires_Date`
- [ ] `Active_Flag`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **20 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 8**.
- [ ] Spot check: `Scope_Type` offers exactly these choices, spelled exactly: `Enterprise`, `Portfolio`, `Installation`, `Facility`.
- [ ] Spot check: the unique-key column(s) `Security_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Security_ID` is marked required.
