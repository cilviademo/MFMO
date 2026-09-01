# CSV import — grid-view paste, list by list

**Never use "New list → From Excel"** — it creates its own columns with its own internal names and silently orphans every formula in this kit. The lists already exist (the build sheets made them); these CSVs fill them.

Per CSV: open the target list → **Edit in grid view** → in a spreadsheet, arrange the CSV's columns into the SAME order as the grid → copy the data rows → click the first empty cell → paste → wait for every cell to commit → count.

| CSV | Target list | Rows to paste | After paste, list shows |
|---|---|---:|---|
| `app-config.csv` | MF App Config | 28 | 28 items |
| `document-destinations.csv` | MF Document Destination | 8 | 8 items |
| `expected-items-2026-08-09.csv` | MF EOM Item | 737 | 737 items |
| `facilities.csv` | MF Facility | 154 | 154 items |
| `feature-flags.csv` | MF Feature Flags | 16 | 16 items |
| `installations.csv` | MF Installation | 103 | 103 items |
| `notification-rules.csv` | MF Notification Rule | 8 | 8 items |
| `pilot-onboarding.csv` | (worksheet — read, do not paste) | 5 | 5 items |
| `qrg-data-quality.csv` | (worksheet — read, do not paste) | 151 | 151 items |
| `requirements.csv` | MF EOM Requirement | 13 | 13 items |

## expected-items-2026-08-09.csv — read this before pasting

Generated OFFLINE by the same EOM-01 engine the test suite runs: full R1
scope (43 installations, 67 Legacy facilities), periods 2026-08 and
2026-09, **exactly 737 rows**. Statuses are computed by the status engine
**as of 2026-09-01** and come out:

  NOT_DUE: 737 rows

They will NOT refresh on their own during the manual pilot (EOM-03 is
deferred); EOM-02 updates a row when a submission lands, and the rest
stay as seeded until reconciliation exists. That is expected, not a
defect. Blank cells in the CSV are deliberate nulls — paste them as
empty, never as the text "null".
