# Screens

Seven screens. Components are reused so FMAT, Training and Equipment modules
drop into the same shell in later releases without new UX.

| Screen | Purpose | Visible to |
|---|---|---|
| `scrHome` | Period snapshot, my work queue, installation list | All |
| `scrUpload` | The front door. Select and drop. | All |
| `scrInstallation` | Requirement grid for one installation/facility/period | All in scope |
| `scrReview` | QC one submission with version history | `varCanQC` |
| `scrUnmatched` | Needs Classification queue | `varCanQC` |
| `scrHistory` | Prior periods, read-only | All in scope |
| `scrAdminRequirements` | Edit the requirement list | `varCanEditReqs` |

## scrHome

```
MISSION FEEDING OPERATIONS                    August 2026
──────────────────────────────────────────────────────────
   82 / 89 Packages Complete
   ● 82 Accepted    ● 4 Pending Review    ● 3 Missing / Overdue
──────────────────────────────────────────────────────────
MY WORK
   Malmstrom · Bldg 1120 DFAC · 1119-1 · Pending Review   [ REVIEW ]
   Minot     · Installation   · SIK    · Correction Req   [ REVIEW ]
   Creech    · Bldg 200 DFAC  · 1119   · Overdue          [ VIEW ]
──────────────────────────────────────────────────────────
INSTALLATIONS                              [ search... ]
   Minot        ●     Malmstrom   ●     Whiteman    ●
──────────────────────────────────────────────────────────
[ UPLOAD A DOCUMENT ]              [ OPEN COP IN POWER BI ]
```

`galMyWork.Items` filters `MF EOM Item` to the user's scope where
`Status_Code in [1,2]`, sorted by Due_Date. For a DFAC manager this is usually
empty or one row — which is the point.

The COP button navigates to `varPowerBIURL`, never a hard-coded link.

## scrUpload

For a DFAC manager with one facility, `varShowDropdowns` is false and the screen
is a title, a period label and a drop target. Everything else is the exception
path.

```
UPLOAD                                    Reporting period: 2026-08 ▼
   Installation [ Lackland      ▼ ]      (hidden when only one)
   Facility     [ Bldg 1234 DFAC ▼ ]      (hidden when only one)
   Document     [ 1119           ▼ ]
   [ ] Submitting on behalf of another location   (varCanOnBehalf only)

   ┌──────────────────────────────────────┐
   │   Drop file here or browse           │
   └──────────────────────────────────────┘
   [ SUBMIT ]
```

Filenames are never validated. `Accepted_File_Types` is advisory.

## scrInstallation

```
LACKLAND AFB · Bldg 1234 DFAC · Food 2.0        AUGUST 2026
─────────────────────────────────────────────────────────────
Requirement          Scope         Due      Status
1119                 Facility      10 Sep   ● Accepted
1119-1               Facility      10 Sep   ● Accepted
SAIIT                Facility      15 Sep   ● Pending Review
SIK                  Installation  10 Sep   ● Correction Req
SF 1080              Installation  10 Sep   ○ Not Due (unverified)
CONTRACTOR INVOICE   Contract      15 Sep   ● Accepted
─────────────────────────────────────────────────────────────
PACKAGE                                     ● In review
[ Open EOM folder ]
```

Installation- and Contract-scope rows appear here with their scope labelled, so
nobody wonders why the SIK bill isn't on every DFAC. Unverified requirements
render dimmed with the reason on hover.

## scrReview

Left: the document. Right: QC.

```
SIK BILL · Minot AFB · Installation · 2026-08
Required: Yes    Due: 10 Sep 2026    Received: 7 Sep 2026
Submitted by: <uploader>   ( on behalf of: — )
File: SIK Bills August 2026.pdf                  [ OPEN DOCUMENT ]
VERSION HISTORY
   v2  12 Sep 09:17  <uploader>  Pending Review   ← current
   v1  07 Sep 14:32  <uploader>  Correction Required
QC
   ( ) Accept   ( ) Correction Required   ( ) Wrong Document   ( ) N/A
   Comment  [_______________________]   (required for the middle two)
   Correction suspense [ __________ ]   (required for Correction Required)
   [ SAVE REVIEW ]
```

Version history is always visible. Nothing is ever overwritten.

## scrUnmatched

```
NEEDS CLASSIFICATION                                       3 files
Monthly Food Report Final.xlsx
   Portfolio 3 · FY2027 · uploaded by <uploader> · 12 Sep
   Installation [ ▼ ]  Facility [ ▼ ]  Document [ ▼ ]  Period [ 2026-08 ▼ ]
   [ CLASSIFY ]   [ NOT AN EOM DOCUMENT ]
```

Suggestions pre-select the dropdowns but are never applied without a click.
