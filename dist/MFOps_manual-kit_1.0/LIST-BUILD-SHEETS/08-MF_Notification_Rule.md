# 08 — create list `MF Notification Rule`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF Notification Rule`

> Notifications are a LIST, not code. Every rule has an Enabled toggle and a Digest flag, and the toggles are on an admin screen rather than inside a flow. Two rules ship enabled; everything else is tuned once the queue behaves.

Grain: One row per notification trigger · expected volume ~100 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Rule_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Trigger_Event` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | SubmissionCreated<br>StatusChanged<br>DueSoon<br>FirstSuspensePassed<br>FinalSuspensePassed<br>CorrectionSuspensePassed<br>PendingReviewAging<br>AccessRequested | **Y** | N |
| 3 | `Recipient_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Submitter<br>Portfolio org box<br>Installation POC<br>Reviewer<br>Portfolio Manager<br>AFSVC | N | N |
| 4 | `Recipient_Address` | Single line of text | 255 characters | No |  | N | N |
| 5 | `Enabled` | Yes/No | Default: No | Yes |  | **Y** | N |
| 6 | `Digest` | Yes/No | Default: No | Yes |  | N | N |
| 7 | `Cadence_Days` | Number | Decimal places: Automatic | No |  | N | N |
| 8 | `Subject_Template` | Single line of text | 255 characters | No |  | N | N |
| 9 | `Notes` | Multiple lines of text | Plain text | No |  | N | N |

## Indexes — 3 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Rule_ID`
- [ ] `Trigger_Event`
- [ ] `Enabled`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **9 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 3**.
- [ ] Spot check: `Trigger_Event` offers exactly these choices, spelled exactly: `SubmissionCreated`, `StatusChanged`, `DueSoon`, `FirstSuspensePassed`, `FinalSuspensePassed`, `CorrectionSuspensePassed`, `PendingReviewAging`, `AccessRequested`.
- [ ] Spot check: the unique-key column(s) `Rule_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Rule_ID` is marked required.
