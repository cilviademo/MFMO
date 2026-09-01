# 16 — create list `MF EOM Audit`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF EOM Audit`

> Cheap now, invaluable during an IG. Every QC decision, every generated item, and every notification the system decided not to send.

Grain: One row per state change · expected volume ~1,000,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Audit_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Entity_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | EOM_Item<br>EOM_Submission<br>Requirement | N | N |
| 3 | `Entity_ID` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 4 | `Action` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Generated<br>Uploaded<br>QC Accepted<br>QC Correction Required<br>QC Wrong Document<br>QC Not Applicable<br>Waived<br>Reclassified<br>Status Recalculated<br>Notification Suppressed<br>Notification Sent | **Y** | N |
| 5 | `Actor_UPN` | Single line of text | 255 characters | Yes |  | N | N |
| 6 | `Action_DateTime` | Date and Time | Include Time: Yes | Yes |  | **Y** | N |
| 7 | `Old_Value` | Single line of text | 255 characters | No |  | N | N |
| 8 | `New_Value` | Single line of text | 255 characters | No |  | N | N |
| 9 | `Detail` | Multiple lines of text | Plain text | No |  | N | N |

## Indexes — 4 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Audit_ID`
- [ ] `Entity_ID`
- [ ] `Action`
- [ ] `Action_DateTime`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **9 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 4**.
- [ ] Spot check: `Entity_Type` offers exactly these choices, spelled exactly: `EOM_Item`, `EOM_Submission`, `Requirement`.
- [ ] Spot check: the unique-key column(s) `Audit_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Audit_ID` is marked required.
