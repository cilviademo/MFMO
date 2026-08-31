# Site bindings — the operator's worksheet

**Nothing in this repository carries a site URL.** This file is where they are
recorded, and it ships with placeholders. Fill it in as you walk the sites, then
keep your filled-in copy **out of source control** — this repository is public.

A destination with a blank `Site_URL` makes EOM-02 **fail closed** with
`CONFIGURATION_REQUIRED`. Before binding, that is correct behaviour, not a
fault: a submission that cannot be routed must stop rather than land somewhere
plausible. `scripts/folder_resolver.check_destination` enforces it, and
`tests/test_folder_resolver.FailClosed` proves it.

---

## Why none of this can be guessed

**The four portfolios are four separate site collections** in SharePoint. Not four
channels in one team, not four folders in one library. Every plan written before
31 Aug 2026 assumed one site; that assumption was wrong and it invalidated every
single-site provisioning design.

**Portfolio 2's site slug carries a prefix the other three do not.** A URL built
by pattern works for three portfolios and 404s on one. Three work and one is a
mystery is the worst failure shape available, so **read every URL off the site**
and never derive one from another.

**Month folder naming differs per site and nobody can guess it.** EOM-02 finds
folders and never creates them, so a mismatch means every submission falls back
to the root with `Needs_Filing TRUE`. Record what is actually there.

---

## 0. The cloud

**This deployment is DoD, not GCC High.** Every GCC High endpoint written for
this programme before 31 Aug 2026 is wrong for it.

| | This deployment | Not |
|---|---|---|
| Power Apps | `make.apps.appsplatform.us` | `make.powerapps.com`, `make.gov.powerapps.us` | <!-- prerelease: allow CLD-01 the wrong-endpoint column IS the warning; naming it is the point of the row -->
| Power Automate | `flow.appsplatform.us` | `flow.microsoft.com` | <!-- prerelease: allow CLD-01 the wrong-endpoint column IS the warning; naming it is the point of the row -->
| PAC CLI cloud | `UsGovDod` | `UsGovHigh`, `Public` |

Commercial cloud is not supported. A commercial endpoint in any binding is a
pre-release stop condition, not a configuration preference.

---

## 1. Environment variables — which one takes which URL

Set these at import. All ship blank.

| # | Environment variable | Takes the URL of | Your value |
|---|---|---|---|
| 1 | `mfops_MF_SharePointSiteURL` | The site holding the 17 MF lists | `_______________________` |
| 2 | `mfops_MF_PilotSite_SiteURL` | The pilot site — all four pilot destinations share it | `_______________________` |
| 3 | `mfops_MF_Portfolio1_SiteURL` | Portfolio 1 production site collection | `_______________________` |
| 4 | `mfops_MF_Portfolio2_SiteURL` | Portfolio 2 — **the irregular slug. Read it off the site.** | `_______________________` |
| 5 | `mfops_MF_Portfolio3_SiteURL` | Portfolio 3 production site collection | `_______________________` |
| 6 | `mfops_MF_Portfolio4_SiteURL` | Portfolio 4 production site collection | `_______________________` |

The remaining 18 of the 24 environment variables are list names, feature flags
and thresholds. None is a URL.

---

## 2. EOM-02b copies — which copy watches which site

The package contains **one** EOM-02b, unbound. Duplicate it three times.

| Copy | Rename it to | Trigger site | Trigger library | Enabled? |
|---|---|---|---|---|
| 1 (the imported one) | `EOM-02b Legacy Intake — Portfolio 1` | value of `MF_Portfolio1_SiteURL` | `Shared Documents` | **No** |
| 2 | `EOM-02b Legacy Intake — Portfolio 2` | value of `MF_Portfolio2_SiteURL` | `Shared Documents` | **No** |
| 3 | `EOM-02b Legacy Intake — Portfolio 3` | value of `MF_Portfolio3_SiteURL` | `Shared Documents` | **No** |
| 4 | `EOM-02b Legacy Intake — Portfolio 4` | value of `MF_Portfolio4_SiteURL` | `Shared Documents` | **No** |

**Then open all four triggers and read the site off each.** Four copies pointed
at the same site is the original gap with more moving parts, and it looks
identical to working.

Enable a copy only once its site is verified in section 4.

---

## 3. Destination rows — which row gets which URL

Eight rows ship in `configuration/document-destinations.csv`, every one with
`Site_URL` blank, `Verified_By` blank, `Verified_Date` blank and `Active_Flag`
FALSE.

| Destination_ID | Set `Site_URL` from | `Root_Folder` (already set) | Library segment |
|---|---|---|---|
| `PILOT-P1-EOM` | `MF_PilotSite_SiteURL` | `EOM-EOY/Portfolio 1` | `Shared Documents` |
| `PILOT-P2-EOM` | `MF_PilotSite_SiteURL` | `EOM-EOY/Portfolio 2` | `Shared Documents` |
| `PILOT-P3-EOM` | `MF_PilotSite_SiteURL` | `EOM-EOY/Portfolio 3` | `Shared Documents` |
| `PILOT-P4-EOM` | `MF_PilotSite_SiteURL` | `EOM-EOY/Portfolio 4` | `Shared Documents` |
| `PORT1-EOM` | `MF_Portfolio1_SiteURL` | `Legacy_Portfolio 1/H. Monthly Data Call` | `Shared Documents` |
| `PORT2-EOM` | `MF_Portfolio2_SiteURL` | `Legacy_Portfolio 2/5. Monthly Data Call` | `Shared Documents` |
| `PORT3-EOM` | `MF_Portfolio3_SiteURL` | `Legacy_Portfolio 3/Monthly Data Call` | `Shared Documents` |
| `PORT4-EOM` | `MF_Portfolio4_SiteURL` | `Legacy_Portfolio 4/Monthly Data Call` | `Shared Documents` |

All four pilot rows share one site and differ only by root folder, so pilot
routing still exercises four destinations rather than a simplified single one.

**`Library_Name` and `Library_Url_Segment` are different strings and are not
interchangeable.** The pilot library displays as `Documents` and is
`Shared Documents` in the URL. The path is always built from the segment;
substituting the display name produces a 404 that reads like a permissions
problem.

---

## 4. Verify before setting Active_Flag TRUE

Do this per row, on the site, with the row in front of you. Do not set
`Active_Flag TRUE` on a row you have not walked.

| # | Check | Why it cannot be skipped |
|---|---|---|
| 1 | The `Site_URL` you recorded opens in a browser | A pattern-built URL 404s on exactly one portfolio |
| 2 | The library exists, and its **URL segment** matches `Library_Url_Segment` | The display name is not the URL segment |
| 3 | `Root_Folder` exists **exactly**, sort prefix and all | `H. Monthly Data Call` and `Monthly Data Call` are different folders; the prefixes are inconsistent across portfolios |
| 4 | An `FY26` folder exists under the root, and you have recorded **its exact name** | It might be `FY26`, `FY 26`, `FY2026`, or something else on this site |
| 5 | **Record the exact month folder naming inside FY26** in `Month_Folder_Pattern_Note` | This differs per site and nobody can guess it. `08 Aug`, `Aug`, `August`, `2026-08`, `08` — all are in use somewhere |
| 6 | The flow's service account can write to the root folder | A permission failure at write time strands a submission record with no file |
| 7 | Only then: set `Verified_By`, `Verified_Date`, `Active_Flag TRUE` | `Verified_By` is a claim that a person walked this site on that date |

**If step 5 is skipped, everything still "works".** EOM-02 finds no month
folder, falls back to the configured root, flags `Needs_Filing TRUE`, and the
documents pile up one level above where anyone looks for them. Nothing errors.
That is the failure this worksheet exists to prevent.

---

## 5. Discovery is still outstanding for production

The four production rows have never been walked. `PROVISION-WITHOUT-POWERSHELL.md`
covers running a discovery pass against them.

This does not block the pilot: pilot routing goes to the automations team site,
whose four rows are configured and need only their shared `Site_URL` bound and
their folders verified as above.
