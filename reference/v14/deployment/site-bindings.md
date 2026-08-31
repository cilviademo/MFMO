# Site bindings — fill in at import, do not commit real URLs

The four portfolios are **four separate SharePoint site collections**. Bind each
at solution import as an environment variable. A real .mil site URL committed to
source is a destination leak and `prerelease_scan.py` rule URL-01 blocks it.

## What to record

| Portfolio | Env variable | Site slug | Library | Root folder |
|---|---|---|---|---|
| 1 | `MF_Portfolio1_SiteURL` | `DAFMissionFeeding-Portfolio1` | Shared Documents | `Legacy_Portfolio 1/H. Monthly Data Call` |
| 2 | `MF_Portfolio2_SiteURL` | `DAFMissionFeeding-Legacy_Portfolio2` | Shared Documents | `Legacy_Portfolio 2/5. Monthly Data Call` |
| 3 | `MF_Portfolio3_SiteURL` | `DAFMissionFeeding-Portfolio3` | Shared Documents | `Legacy_Portfolio 3/Monthly Data Call` |
| 4 | `MF_Portfolio4_SiteURL` | `DAFMissionFeeding-Portfolio4` | Shared Documents | `Legacy_Portfolio 4/Monthly Data Call` |

Portfolio 2's slug contains `Legacy_` and the others do not. Do not build these
by pattern.

## Before the first upload — walk each site

For each of the four, record:

- [ ] Exact site URL
- [ ] Exact library name (assumed `Shared Documents`, verify)
- [ ] Exact root folder name, including the sort prefix where present
- [ ] **The month folder naming inside FY26** — `Aug 26`? `August 2026`?
      `08. August`? This is the one nobody will guess right.
- [ ] Whether FY25, FY26 and FY27 all exist
- [ ] Who administers permissions on that site

Then set `Site_URL`, `Verified_By`, `Verified_Date` and `Active_Flag = TRUE` in
`configuration/document-destinations.csv`.

EOM-02 fails closed on an inactive or unbound destination, so an unverified
site cannot silently receive files.

## Cloud

The SharePoint tenant is `usaf.dps.mil`; Teams resolves to
`dod.teams.microsoft.us`. This is the **DoD** cloud, not GCC High.

```
Maker  https://make.apps.appsplatform.us
Flow   https://flow.appsplatform.us
Admin  https://admin.appsplatform.us
```

Confirm the Power Platform environment is in the same tenant as the SharePoint
sites. Same cloud does not guarantee same tenant.
