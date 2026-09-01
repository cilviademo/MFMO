# Pre-flight — what I need from you for steps 1 to 3

Three groups: **decisions only you can make**, **things to run**, and **things
to send back**. Nothing here needs the solution ZIP.

---

## A. Decisions — four of them

### A1. Which site hosts the 17 SharePoint lists?

This is not obvious and it is not answered anywhere yet.

The lists are the application's database. They are **not** the document
libraries. Options:

| Option | For | Against |
|---|---|---|
| **A dedicated site** — a new one, e.g. `DAFMissionFeeding-Ops` | Clean separation, one permission story, does not clutter a portfolio site | You have to get a site created |
| The main DAF Mission Feeding team site | Exists already, everyone knows it | Mixes app data with conversation and general files |
| One of the four portfolio sites | Exists already | Arbitrary — why Portfolio 2? — and confusing forever after |

**Recommendation: a dedicated site.** The lists carry every submission record,
every access grant and the audit log. They deserve their own permission boundary
and their own backup story, and putting them on a portfolio site means one
portfolio's admins own everyone's data.

**One site, not four.** The documents live on four sites; the lists live on one.

### A2. Open reporting period at go-live

Which month does the pilot start with? If you onboard in September, the open
period is probably `2026-08` — the month that just closed. Confirm, because
EOM-01 generates against it.

### A3. Notification org boxes

Two rules ship enabled: submission-created notifies the portfolio org box, and
status-changed notifies the submitter. I need the four org box addresses, or a
decision to ship with notifications off and add them later.

Shipping with them off is a legitimate choice and arguably the safer one.

### A4. The three open scope rulings

Still unanswered and they change what EOM-01 generates:

- **SF 1080** — installation or facility scope?
- **GPC Bank Statement** — installation or facility?
- **1038** — installation or facility?

Facility scope on a six-DFAC base like Lackland means six uploads. Installation
means one. Changing this after items exist means regenerating a period, so it is
cheaper to decide now than to discover later.

If you cannot get a ruling, say so and we ship them as currently seeded —
installation scope, marked PROPOSED — and correct forward.

---

## B. Things to check before running anything

- [ ] **PnP.PowerShell installed?** If module installation is blocked — which
      is normal on .mil — you do not need it. See
      `provisioning/PROVISION-WITHOUT-POWERSHELL.md`. The Power Automate route
      uses the standard SharePoint connector and needs no admin rights.

- [ ] **Site Owner on the target list site?** Provisioning needs it. Read is not
      enough.

- [ ] **At least Read on all four portfolio sites?** Discovery needs it.

- [ ] **Can you create a SharePoint site**, or does that go through a request?
      Depends on A1.

---

## C. Run this and send it back

`provisioning/Discover-MFDestinations.ps1` is read-only. It creates nothing,
changes nothing, uploads nothing. It reads the four portfolio sites and reports
what is actually there.

```powershell
.\Discover-MFDestinations.ps1 -SiteUrls @(
    "https://<tenant>/sites/DAFMissionFeeding-Portfolio1",
    "https://<tenant>/sites/DAFMissionFeeding-Legacy_Portfolio2",
    "https://<tenant>/sites/DAFMissionFeeding-Portfolio3",
    "https://<tenant>/sites/DAFMissionFeeding-Portfolio4"
)
```

Substitute your real tenant host. Note that **Portfolio 2's slug contains
`Legacy_` and the others do not** — do not build these by pattern.

It writes `discovery-output.csv` with:

```
Portfolio · SiteUrl · Library · RootFolder · FYFolders · MonthFolderSample
```

**Send that file back.** From it I can fill
`configuration/document-destinations.csv` completely, and write the month-folder
matching rule against the real naming rather than a guess.

`MonthFolderSample` is the one that matters. `Aug 26`, `August 2026`,
`08. August`, `AUG` — all plausible, and the four sites already prove they name
things differently. This is the field that decides whether uploads land in the
right folder or at the root.

---

## D. What I do with your answers

| You send | I produce |
|---|---|
| `discovery-output.csv` | Completed `document-destinations.csv` and the month-matching rule |
| A1 — list site | The exact `Provision-MFOpsLists.ps1` command line |
| A2 — open period | `app-config.csv` with the right period |
| A3 — org boxes, or "off" | `notification-rules.csv` set accordingly |
| A4 — scope rulings | Updated `requirements.csv`, or a note that they stay PROPOSED |

Then steps 1 to 3 are: run one script, import six CSVs, paste four rows.

---

## Two things already fixed

**The provisioning script had the wrong cloud.** It said
`USGovernmentHigh`; this tenant is DoD. Wrong endpoint fails at Connect with an
authentication error that reads like a permissions problem, which is a bad
afternoon. It is now a `-Cloud` parameter defaulting to `USGovernmentDoD`.

**Indexes are set by the script**, on `Reporting_Period`, `Installation_ID`,
`Facility_ID`, `Requirement_ID` and `Status_Code`. Verify they exist after the
run. Past the 5,000-item List View Threshold, adding an index to a large list
is restricted and painful, and `MF EOM Item` crosses that inside the first
year. Treat index creation as before-data-only: plan on it not being fixable
later rather than betting the pilot on an exception.
