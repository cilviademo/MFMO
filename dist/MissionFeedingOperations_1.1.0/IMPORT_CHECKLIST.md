# Import checklist — 1.0.0

**Do these in order and stop at the first unchecked box.** The order is not a
preference. Indexes cannot be added after a list passes 5,000 items, and every
step below that one assumes the lists exist and are shaped correctly.

Every box is something the import cannot do for you.

---

## 0. Before anything

- [ ] Read `KNOWN_LIMITATIONS.md`.
- [ ] Read `DEPENDENCY_MANIFEST.md`. **16 resources MUST ALREADY EXIST** and
      7 require manual `.mil` configuration. None is created by importing.
- [ ] Confirm the checksum in `SHA256SUMS.txt` matches the ZIP you hold.
- [ ] The Power Platform environment is in the **DoD** cloud
      (`make.apps.appsplatform.us`), not GCC High.
- [ ] The environment is in the **same tenant** as the four SharePoint sites.
      Same cloud does not guarantee same tenant, and a cross-tenant connection
      fails in a way that reads like a permissions problem for a week.
- [ ] Confirm the DLP policy permits SharePoint. New connectors are disabled by
      default in DoD.

---

## 1. Provision the 17 lists — through Power Automate

**PowerShell is unavailable on this network.** `Provision-MFOpsLists.ps1` is
kept for environments that have it; it is not the route here.

- [ ] Follow `PROVISION-WITHOUT-POWERSHELL.md`. It drives the SharePoint REST
      API from a Power Automate flow using generated payloads.
- [ ] Before creating anything, check whether any of the 17 lists already
      exists. A fresh site has none. **Even one pre-existing list means every
      column on it must be checked against `SHAREPOINT_SCHEMA_MANIFEST.md`** —
      an internal name is fixed at creation and can never be changed, so a list
      someone made earlier by hand will have `Installation ID` where the
      formulas expect `Installation_x0020_ID`, and every read returns blank
      rather than erroring.

**Verify:** 17 lists exist. 286 columns across them. Compare against
`SHAREPOINT_SCHEMA_MANIFEST.md` list by list, not by eye.

---

## 2. Verify the indexes — before any data is loaded

**This is the one step that cannot be repaired later.** SharePoint refuses to
add an index once a list passes 5,000 items, and `MF_EOM_Item` passes 5,000 in
the first quarter of use.

- [ ] Open **List settings → Indexed columns** on each of the 17 lists and
      count them against the per-list table in `FINAL_RELEASE_REPORT.md`.
- [ ] Confirm the six high-volume lists in particular: `MF_EOM_Item` (13),
      `MF_EOM_Submission` (13), `MF_EOM_Status` (8), `MF_Security_Mapping` (8),
      `MF_App_Event_Log` (6), `MF_EOM_Audit` (4).

**Verify:** 90 indexes total, no list over 20. If any list is short, fix it
now. After step 9 it is permanent.

---

## 3. Import the six configuration CSVs

- [ ] `app-config.csv`, `requirements.csv`, `installations.csv`,
      `facilities.csv`, `document-destinations.csv`, `feature-flags.csv`.
- [ ] Do **not** load any `.sample.csv`. Those hold placeholder accounts.

**Verify:**
- `MF_App_Config.SchemaVersion` reads `5.0`. Every flow compares against this
  and terminates on a mismatch, so a wrong value here stops everything.
- All 103 installations have `Generation_Enabled = FALSE`.
- `MF_Document_Destination` holds **8 rows** — four `PILOT-P#-EOM` and four
  `PORT#-EOM` — and **every one is `Active_Flag FALSE`, `Verified_By` blank,
  `Verified_Date` blank**. Nothing ships pre-verified: `Verified_By` is a claim
  that a person walked that site, and no one has. Activation happens in step 6.
- **Every row's `Site_URL` is blank.** It is blank in source deliberately and
  is bound in step 6. A destination with a blank `Site_URL` fails closed.

---

## 4. Add the first user to MF Security Mapping

Authorisation is deny-by-default. Until a row exists, nobody — including you —
can see anything.

- [ ] Create one row: your UPN, `Scope_Type = Enterprise`,
      `Role = PORTFOLIO_MANAGER`, `Active_Flag TRUE`, `Expires_Date` set.

**Verify:** exactly one row. Not the sample file.

---

## 5. Import the solution ZIP

- [ ] Import **unmanaged**. This is a DEV or PILOT environment.

**Verify:** the import succeeds and **all five flows arrive disabled**
(`StateCode 0`). Leave them that way. EOM-01 writes 737 rows the moment it is
turned on.

---

## 6. Bind the connection reference and all 24 environment variables

The package carries **no connection values and no environment variable
values**. Both are supplied here, from a deployment settings file kept **out of
source control**.

- [ ] Bind the **SharePoint** connection reference (`mfops_sharepointonline`).
      Every flow needs it.
- [ ] Bind `mfops_office365users` and `mfops_office365`. Only the disabled
      EOM-04 uses them, but an unbound reference blocks the import.
- [ ] Set all 24 environment variables. The six that carry site URLs are
      `MF_SharePointSiteURL`, `MF_Portfolio1..4_SiteURL` and
      `MF_PilotSite_SiteURL`.
- [ ] Walk **each of the four portfolio site collections** and read the site
      URL, library name and exact root folder including its sort prefix off the
      site. **Never build one by pattern:** Portfolio 2's slug carries a
      `Legacy_` prefix the other three do not, so a pattern-built URL 404s on
      exactly one portfolio — three work and one is a mystery.
- [ ] Record **how the month folders inside FY26 are actually named**. EOM-02
      matches existing folders and never creates one.
- [ ] Work `deployment/site-bindings.md` section 4 per row, then set
      `Site_URL`, `Month_Folder_Pattern_Note`, `Verified_By`, `Verified_Date`
      and `Active_Flag = TRUE` — **only** for rows you actually walked.

**Verify:** no environment variable is left blank. A blank one does not error;
it reads as empty and the flow writes nothing.

---

## 7. Duplicate EOM-02b three times and bind each

**The package contains ONE EOM-02b, and it ships unbound. It covers nothing
until you duplicate it.**

A SharePoint trigger watches one site and one library. The four portfolios are
four separate site collections, so one instance cannot cover them. A template
nobody duplicates means three portfolios go unmonitored and look exactly like
three portfolios with nothing to report.

- [ ] **Duplicate it three times** (Save As), for four copies total.
- [ ] **Bind each copy to a different site collection** — set the trigger's
      site and library from `MF_Portfolio1_SiteURL` … `MF_Portfolio4_SiteURL`,
      one per copy.
- [ ] **Verify the four copies point at four distinct sites.** Open all four
      triggers and read the site off each. Four copies aimed at the same site
      is the original gap with more moving parts.
- [ ] **Leave all four disabled** until that copy's site has been verified in
      step 6 and its destination row is active.

---

## 8. Build the canvas app — no pasting

The app is **built from source by Microsoft's own toolchain**; what remains
for a person is platform-minted identity and one validation open.

- [ ] In the imported solution: **New → App → Canvas (tablet)**, name it
      **Mission Feeding Operations**, add the 19 data sources listed in
      `CANVAS_APP_ASSEMBLY.md`, save. Build nothing.
- [ ] **Bump the solution version to 1.1.0** (solution → settings). The
      assembler reads it from Solution.xml and refuses a mismatch.
- [ ] **Export the solution**, then on a machine with the Power Platform CLI
      (**2.11.2** — the pinned, proven version):

      scripts/assemble_full_solution.sh <your-export>.zip

      This swaps the blank app's content for the repository's 16 screens,
      6 components and 1,800+ formulas — keeping YOUR app identity and YOUR
      environment's data-source metadata — and validates the result. The whole
      pipeline was dry-run here end to end.
- [ ] Import the assembled `MissionFeedingOperations_1.1.0.zip`.
- [ ] **Open the app for edit once** — Microsoft's packer states this open IS
      the validation for a source-packed app — then save, publish, and
      **re-export**. The re-export is the permanent artifact; no Studio work
      ever again.

Fallback with no CLI anywhere: `CANVAS_APP_ASSEMBLY.md` Path C, the paste
runbook.

## 9. Enable EOM-01 only, and run it twice

- [ ] Turn on **EOM-01 alone**. Leave the other four off.
- [ ] Run it once.

**Verify:** **737 `MF_EOM_Item` rows** for `2026-08` and `2026-09` — 268 in
August, 469 in September.

- [ ] Run it **again** without changing anything.

**Verify:** **still 737.** The generator is idempotent on a deterministic
`EOM_Item_ID`; a second run that adds rows means the key check is not working
and every count downstream is wrong.

- [ ] Confirm with two views — one filtered `Facility_ID is empty`, one
      filtered `Requirement_Scope is Installation or Contract` — that the
      counts agree exactly. A mismatch means empty strings were written where
      nulls belong, and every `Filter()` in the app is wrong.

---

## Then, before anyone else uses it

- [ ] Raise the data-layer scope question with the SharePoint administrator.
      `SECURITY_README.md`. **This is open.** Power Apps `Visible`/`Filter` is
      not a security boundary; the data layer does not yet enforce installation
      scope independently. It is a deployment dependency, not a build blocker,
      and an ISSM will find it.
- [ ] Activate EOM-03, then EOM-02, in that order.
- [ ] **Leave EOM-04 disabled.** `NotificationsEnabled` is FALSE by programme
      decision.

**Import success is not authorisation to operate.**
