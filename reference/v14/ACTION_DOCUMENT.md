# ACTION DOCUMENT — Figma build handoff to Claude Code

Read with `CLAUDE_CODE_HANDOFF.md`. This is the delta since the last integration.

Three parts: what the Figma build needs, answers to the findings from the last
build run, and the SharePoint routing, which changes an assumption everything
downstream was built on.

---

# PART 1 — THE ROUTING FINDING

**The four portfolios are four separate SharePoint site collections, not four
channels in one team.** Every earlier document assumed one site with four
portfolio channels. That is wrong, and it invalidates any single-site
provisioning plan.

| Portfolio | Site | Library | Root folder |
|---|---|---|---|
| 1 | `DAFMissionFeeding-Portfolio1` | Shared Documents | `Legacy_Portfolio 1/H. Monthly Data Call` |
| 2 | `DAFMissionFeeding-Legacy_Portfolio2` | Shared Documents | `Legacy_Portfolio 2/5. Monthly Data Call` |
| 3 | `DAFMissionFeeding-Portfolio3` | Shared Documents | `Legacy_Portfolio 3/Monthly Data Call` |
| 4 | `DAFMissionFeeding-Portfolio4` | Shared Documents | `Legacy_Portfolio 4/Monthly Data Call` |

All four hosted on the `usaf.dps.mil` SharePoint tenant. The Teams link resolves
to `dod.teams.microsoft.us`.

**Four things to notice, because each one breaks a naive implementation:**

1. **Four site URLs, not one.** Four connection targets, four sets of
   permissions, four things to bind at import.
2. **The site slugs are inconsistent.** Portfolio 2 is
   `DAFMissionFeeding-Legacy_Portfolio2`; the others omit `Legacy_`. A URL built
   by pattern will 404 on exactly one portfolio, which is the worst failure
   shape — three work and one is a mystery.
3. **The root folder names are all different.** `H. Monthly Data Call`,
   `5. Monthly Data Call`, `Monthly Data Call`, `Monthly Data Call`. The `H.`
   and `5.` are sort-order prefixes. There is no rule that derives these; they
   are configuration.
4. **This is the DoD cloud, not GCC High.** Maker is
   `make.apps.appsplatform.us`, flow is `flow.appsplatform.us`, admin is
   `admin.appsplatform.us`. Every GCC High endpoint in earlier drafts is wrong
   for this deployment. Confirm the Power Platform environment sits in the same
   tenant as the SharePoint sites — same cloud does not guarantee same tenant.

`configuration/document-destinations.csv` now carries this structure with
`Site_URL` blank. **The real URLs are environment variables bound at import.**
A .mil site URL committed to source is a destination leak, and
`prerelease_scan.py` rule URL-01 blocks it — correctly. Keep it blocking.

## Folder resolution — find, never create

Each Monthly Data Call folder already contains FY25, FY26 and FY27 with month
folders inside. Those are curated by hand and the flow must not add to them.

```
resolve(Installation_ID, Reporting_Period):
    portfolio    = MF_Installation[Installation_ID].Portfolio_ID
    destination  = MF_Document_Destination[portfolio, 'EOM']
    base         = Site_URL + Library_Name + Root_Folder

    fyFolder     = find a child of base matching the fiscal year
                   (FY26 for the 2026-08 period — Oct-Sep)
    monthFolder  = find a child of fyFolder matching the reporting month

    if both found  -> write there
    else           -> write to base, set Needs_Filing = TRUE, log
                      SUBMISSION_FILED_AT_ROOT
```

**Match, do not construct.** The root folders already prove these four sites
name things differently. Assume the month folders do too — `Aug 26`, `08 Aug`,
`August 2026`, `08. August` are all plausible and you will not know until you
look. Match case-insensitively on: the month name, its three-letter
abbreviation, and the two-digit month number, in that order, anywhere in the
folder name. Same for the FY folder: `FY26`, `FY 26`, `FY2026`.

**`Create_Missing_Folders = FALSE`, permanently.** A flow that creates folders
will eventually produce `Aug 26` beside someone's `August 2026`, and nobody
notices for a month.

When the folder cannot be matched, the file goes to the Monthly Data Call root
with `Needs_Filing = TRUE`. A submission that lands somewhere findable beats one
that fails — the user did their part. Surface the count in Admin: *"3
submissions filed at root — folder not matched"*, with the installation, period
and expected folder name so someone can either move the file or fix the
configuration.

## What has to happen before the first upload

Someone opens each of the four sites and records: the exact site URL, the
library name, the exact root folder name, and **the actual naming pattern of the
month folders inside FY26**. Four sites, ten minutes. Without it, EOM-02 files
everything at root and looks broken on day one.

---

# PART 2 — ANSWERS TO THE BUILD FINDINGS

The last integration run raised several things. These are the rulings.

**Operating-model vocabulary mismatch — correct fix, keep it.** The QRG says
`Legacy`, `Food 2.0`, `MAFFO`, `Deployed / Field Feeding`; the requirements
filter on `Legacy/APF`. Normalising at import with the raw value preserved is
right. This is the second time a filter has silently matched nothing, so make it
a standing check: **any generator that filters on a vocabulary must assert that
the filter matched something, and fail loudly at zero.** Silent zero is the
failure mode that costs a month.

**`Facility_Type` empty in the QRG — same class, different column.** The QRG has
no facility type, so `Applicable_Facility_Types` excluded every facility. The
rule: **an empty filter column means "no constraint", never "no match".** A
requirement with `Applicable_Facility_Types` populated must not exclude a
facility whose type is unknown — it should generate and flag the facility as
needing a type. Under-generating is worse than over-generating: an extra row is
visible and gets fixed; a missing row is invisible and reads as compliant.

**Inline scanner exceptions over file skipping — better than what I did.** I
excluded whole files, which means a real secret added to `SECURITY_PROMPTS.md`
later would pass. An auditable inline exception is the correct call. Keep it,
and require a reason string on every one.

**Empty `ROLLBACK.md` — the scanner was right.** It checked existence, not
content. Add a non-empty check for the required release artifacts.

**Three inactive requirement rows asserting a grain with no basis — good
catch.** That is exactly the conflation of authority with scope the build notes
warn about, and it applies to inactive rows too.

**"A not-onboarded installation is not compliant."** This is the single most
important line to come out of that run and it belongs in the Power BI measures,
not just the tests. Any completion percentage must state its denominator:

```
43 of 43 onboarded installations complete
60 installations not yet onboarded
```

Never one number that silently treats the un-asked as clean.

**On-time is two rates, not one.** `Submission on-time rate` uses the effective
date and is what the base was held to. `Evidence on-time rate` uses the final
call and is what leadership is told. Do not merge them, and do not show one
labelled ambiguously.

**Leadership reads nominal dates.** A slipped suspense is an operational
adjustment, not a changed policy date. The 5th stays the 5th in a brief.

---

# PART 3 — FIGMA BUILD, ACTION ITEMS

The build is in good shape. The date engine is correct — I compiled and ran it,
and every case passes including the 2028 New Year observed on 31 Dec 2027 and
the year 2100. Rules, not tables.

## Three defects to fix

**1. Amber and yellow are visually identical.** The six states exist in the type
union, but:

```
late    #8a5300 on #fff4e5
review  #6b4c00 on #fefce8
text-to-text contrast: 1.25:1
```

Two nearly identical browns. Labels and icons differ so it is not a 508 failure,
but the entire purpose of the split was distinguishing *base owes* from *AFSVC
owes* at a glance, and at 1.25:1 nobody can. Move review toward a true yellow
(`#7a6200`) or amber toward orange (`#9a4a00` on `#fff1e0`). **Verify at least
3:1 between the two text colours** before calling it done.

**2. The shared period selector is still four hardcoded options.**
`ui.tsx:647` has `<option>August 2026</option>` through September.
`Calendar.tsx:314` correctly calls `generatePeriodOptions()`. So the generator
exists and the shared TopBar does not use it — every screen except Calendar has
a dead four-month dropdown.

**3. Zero `aria-label` across 31 buttons.** The help button and the calendar
navigation arrows are icon-only and announce nothing. Straight 508 gate failure.

## Five hardcoded values that must become configuration

| Value | Location | Reads from |
|---|---|---|
| `Max 50 MB` | `Submit.tsx:223` | `MF_App_Config.MaxUploadSizeMB` |
| `PDF, XLSX, DOCX` | `Submit.tsx:223` | `MF_EOM_Requirement.Accepted_File_Types` |
| `aged 4 days or more` | `ReviewQueue.tsx:139,189` | `MF_App_Config.ReviewAgeHighlightDays` |
| `initialDay = 5, finalDay = 10` | `dates.ts:105` | the requirement row, not a default |
| Age bands `0-1 / 2-3 / 4-5 / 6+` | `ReviewQueue.tsx:39` | derived from the highlight threshold |

The defaults are fine. What matters is that an admin edits a list row rather
than a developer editing Power Fx.

## Confirmed working — do not change

Date engine, six states in the type union, all twelve chip contrast ratios above
4.5:1 in both themes, Google Fonts import removed with the reasoning in a
comment, self-revoke guarded by `CURRENT_USER_ID`, Dismiss replaced with *Go to
Facility Registry*, MAFFO and Food 2.0 no longer generating Legacy
requirements, no CDN dependencies, no fictional installations, no `onClick` on a
`div`.

## One to confirm rather than fix

`correction` maps to the `overdue` colour key, so *Correction needed* renders
red like *Overdue*. Consistent with the ownership model — both are the base's
action. Worth a conscious yes rather than an accident.

## Porting to Power Apps

`docs/powerapps-translation.md` has the pattern map. Two reminders:

The Figma build is a **design reference**. Nothing in `src/` imports into Power
Platform. The importable artifact is the solution package from `pac`.

`docs/native-visuals.md` covers the in-app status visuals. Do not use the
built-in chart controls — roughly 50-row cap, no modern theming, poor
screen-reader support. Build from containers and `FillPortions`.

---

# ORDER OF WORK

1. Bind the four site URLs and confirm the month folder naming. Ten minutes,
   and everything downstream depends on it.
2. Fix the three Figma defects. Amber/yellow first — it is the one that changes
   whether the app is readable at a glance.
3. Move the five hardcoded values to configuration.
4. Add the zero-match assertion to every generator that filters on a vocabulary.
5. Add the non-empty check for required release artifacts.
6. Then port the screens.

## Still open, unchanged

The data layer does not enforce installation scope independently of the app.
`docs/security-open-issue.md`. **Four separate sites makes this easier, not
harder** — a portfolio boundary is now a site boundary, which SharePoint
enforces natively. The remaining question is installation scope within a
portfolio site, which is a smaller problem than it was this morning.
