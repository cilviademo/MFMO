# Site bindings — four sites, walked by a person, before the first upload

The four portfolios are **four separate SharePoint site collections.** Not four
channels in one team, not four folders in one library. Every document in this
programme before 31 Aug 2026 assumed one site, and that assumption invalidated
every single-site provisioning plan built on it.

Nothing here can be derived. It has to be read off the sites.

## What has to be recorded

| Portfolio | Environment variable | Site slug | Library | Root folder |
|---|---|---|---|---|
| 1 | `MF_Portfolio1_SiteURL` | `DAFMissionFeeding-Portfolio1` | Shared Documents | `Legacy_Portfolio 1/H. Monthly Data Call` |
| 2 | `MF_Portfolio2_SiteURL` | `DAFMissionFeeding-Legacy_Portfolio2` | Shared Documents | `Legacy_Portfolio 2/5. Monthly Data Call` |
| 3 | `MF_Portfolio3_SiteURL` | `DAFMissionFeeding-Portfolio3` | Shared Documents | `Legacy_Portfolio 3/Monthly Data Call` |
| 4 | `MF_Portfolio4_SiteURL` | `DAFMissionFeeding-Portfolio4` | Shared Documents | `Legacy_Portfolio 4/Monthly Data Call` |

**Portfolio 2's slug contains `Legacy_` and the other three do not.** A URL built
by pattern works on three portfolios and 404s on one. That is the worst failure
shape available: three people report it working and the fourth is told it must
be something on their end.

**All four root folder names differ.** `H. Monthly Data Call`, `5. Monthly Data
Call`, and two bare `Monthly Data Call`. The `H.` and `5.` are sort-order
prefixes somebody typed years ago. No rule derives them.

Real URLs never enter source. They are bound at import from the environment
variables above, and `scripts/prerelease_scan.py` rule URL-01 blocks a `.mil`
site URL in a tracked file — correctly, and it stays blocking.

## The walkthrough — four sites, about ten minutes

For each portfolio, open the site and record:

- [ ] Exact site collection URL
- [ ] Exact library name (assumed `Shared Documents` — verify, do not assume)
- [ ] Exact root folder name, **including the sort prefix** where there is one
- [ ] **The actual naming of the month folders inside FY26** — see below
- [ ] Whether FY25, FY26 and FY27 all exist
- [ ] Who administers permissions on that site

Then set `Site_URL`, `Month_Folder_Pattern_Note`, `Verified_By`,
`Verified_Date` and `Active_Flag = TRUE` in
`configuration/document-destinations.csv`.

## The month folder question

This is the one item nobody will guess right, and it is the reason the checklist
exists.

Four sites name their **root** folders four different ways. There is no reason
to believe they name their **month** folders the same way as each other. `Aug
26`, `August 2026`, `08 Aug`, `08. August` are all plausible and all live
somewhere in the DAF.

The matcher in `scripts/folder_resolver.py` handles the variants it can — month
name, three-letter abbreviation, and two-digit number, case-insensitively,
anywhere in the folder name, plus `FY26` / `FY 26` / `FY2026`. Record what is
actually there anyway. When a file lands at root, the first question is always
*"what was it looking for, and what is actually on the site"*, and
`Month_Folder_Pattern_Note` is the answer written down before the incident
rather than after it.

## Find, never create

`Create_Missing_Folders` is **FALSE, permanently**, on all four rows. The FY and
month folders are curated by hand and the flow's job is to find them.

A flow that creates folders will eventually produce `Aug 26` beside someone's
`August 2026`. Both look right. Half the submissions go to each, and nobody
notices for a month — at which point there is no way to tell which folder a
given base was told to use.

When the folder cannot be matched, `Fallback_Policy = FIND_OR_ROOT` puts the
file at the Monthly Data Call root with `Needs_Filing = TRUE` and a
`Filing_Note` saying what was looked for. Admin shows the count. **A submission
that lands somewhere findable beats one that fails** — the base did their part,
and the mess is ours to clean up, visibly.

`FIND_OR_FAIL` exists in the vocabulary for a destination where a stray file at
root would be worse than a failed upload. No R1 row uses it.

## Fail closed

EOM-02 refuses to write when any of these is true:

| Condition | Error |
|---|---|
| No destination row for the portfolio and domain | `DESTINATION_NOT_CONFIGURED` |
| `Active_Flag` is FALSE | `DESTINATION_NOT_CONFIGURED` |
| `Verified_By` is blank | `DESTINATION_NOT_VERIFIED` |
| `Site_URL` is blank | `CONFIGURATION_REQUIRED` |

All three gates default to "no", so a destination nobody has walked cannot
receive a file by accident. None of these errors shows the user a path, a site
URL or a connector message.

## Cloud

The SharePoint tenant is `usaf.dps.mil`; Teams resolves to
`dod.teams.microsoft.us`. This is the **DoD** cloud — **not GCC High**. Every
GCC High endpoint in a document dated before 31 Aug 2026 is wrong for this
deployment.

```
Maker   make.apps.appsplatform.us
Flow    flow.appsplatform.us
Admin   admin.appsplatform.us
```

`MF_TenantCloud` is `UsGovDod`, and the provisioning scripts take
`-TenantCloud UsGovDod`.

Confirm the Power Platform environment is in the **same tenant** as the
SharePoint sites. Same cloud does not guarantee same tenant, and a cross-tenant
connection fails in a way that reads like a permissions problem for a week.

## What this does to the security gap

`docs/security-open-issue.md` is the open finding that the data layer does not
enforce installation scope independently of the app.

Four separate site collections make it **smaller, not larger**. A portfolio
boundary is now a site boundary, and SharePoint enforces that natively without
anyone building anything. What remains is installation scope *within* a
portfolio site — a real problem, and a smaller one than it was.

It is not closed. `security/security-manifest.yaml` keeps
`data_layer_permissions_verified: false` until it is.
