# 17 — create list `MF App Event Log`

> **THE INTERNAL-NAME TRAP, RESTATED.** Type every list name and every column
> name EXACTLY as printed, at creation time, and never rename to fix a typo.
> SharePoint freezes a column's INTERNAL name from the name it is created
> with: create `Installation ID` (with a space) and the internal name is
> `Installation_x0020_ID` forever -- renaming the display name afterwards
> changes nothing underneath, and every formula and flow in this kit
> addresses the internal name. Create it wrong, DELETE it and create it
> again; never rename.

**Site Contents → New → List → Blank list.** Name it exactly: `MF App Event Log`

> Business telemetry, NOT click tracking. Answers 'why didn't Minot's 1119 show up' operationally, and 'how many manual interventions did we avoid' strategically. Append-only; never bind a gallery directly to it.

Grain: One row per meaningful business event · expected volume ~2,000,000 rows

## Columns, in creation order

| # | Internal name (type EXACTLY) | Create as | Settings | Required | Choices (verbatim) | Indexed | Unique-key part |
|---|---|---|---|---|---|---|---|
| 1 | `Event_ID` | Single line of text | 255 characters | Yes |  | **Y** | **Y** |
| 2 | `Event_DateTime` | Date and Time | Include Time: Yes | Yes |  | **Y** | N |
| 3 | `User_UPN` | Single line of text | 255 characters | Yes |  | **Y** | N |
| 4 | `Role` | Single line of text | 255 characters | No |  | N | N |
| 5 | `Portfolio_ID` | Single line of text | 255 characters | No |  | N | N |
| 6 | `Installation_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 7 | `Facility_ID` | Single line of text | 255 characters | No |  | N | N |
| 8 | `Event_Type` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | AppOpened<br>DocumentDiscovered<br>SubmissionCreated<br>VersionSuperseded<br>ClassificationSucceeded<br>ClassificationUncertain<br>ManualClassification<br>ExpectedItemMatched<br>QCAccepted<br>QCCorrectionRequired<br>QCWrongDocument<br>ExpectedGenerationFailed<br>ReconciliationMismatch<br>FlowFailure<br>PermissionDenied<br>MaintenanceModeBlocked | **Y** | N |
| 9 | `Record_ID` | Single line of text | 255 characters | No |  | **Y** | N |
| 10 | `Result` | Choice | Display choices in: Drop-Down Menu; Allow 'Fill-in' choices: No | Yes | Success<br>Warning<br>Failure | N | N |
| 11 | `Error_Code` | Single line of text | 255 characters | No |  | N | N |
| 12 | `Error_Message` | Multiple lines of text | Plain text | No |  | N | N |
| 13 | `App_Version` | Single line of text | 255 characters | Yes |  | N | N |

## Indexes — 6 for this list

List settings → **Indexed columns** → Create a new index, once per column below. Simple indexes only; no compound indexes in this schema.

- [ ] `Event_ID`
- [ ] `Event_DateTime`
- [ ] `User_UPN`
- [ ] `Installation_ID`
- [ ] `Event_Type`
- [ ] `Record_ID`

**Create every index NOW, while the list is empty.** Past the 5,000-item List View Threshold, adding an index to a large list is restricted and not to be counted on.

## VERIFY before moving on

- [ ] List settings shows **13 columns you created** (SharePoint's own Title/ID/Modified rows are extra and do not count).
- [ ] Indexed columns shows **exactly 6**.
- [ ] Spot check: `Event_Type` offers exactly these choices, spelled exactly: `AppOpened`, `DocumentDiscovered`, `SubmissionCreated`, `VersionSuperseded`, `ClassificationSucceeded`, `ClassificationUncertain`, `ManualClassification`, `ExpectedItemMatched`, `QCAccepted`, `QCCorrectionRequired`, `QCWrongDocument`, `ExpectedGenerationFailed`, `ReconciliationMismatch`, `FlowFailure`, `PermissionDenied`, `MaintenanceModeBlocked`.
- [ ] Spot check: the unique-key column(s) `Event_ID` exist with the exact internal names above. (Row uniqueness itself is enforced by the flows' idempotency logic, not by a SharePoint unique constraint — do NOT switch 'Enforce unique values' on unless the sheet's settings column says so.)
- [ ] Spot check: `Event_ID` is marked required.
