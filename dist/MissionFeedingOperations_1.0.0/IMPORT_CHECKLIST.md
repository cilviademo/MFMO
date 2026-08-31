# Import checklist — 1.0.0

**Stop at the first unchecked box.** Every one of these is something an import
cannot do for you, and every one has cost somebody a day somewhere.

## Before anything

- [ ] Read `KNOWN_LIMITATIONS.md`. **The ZIP in this folder is the solution
      envelope and will not import until the canvas app and flows are built.**
- [ ] Read `DEPENDENCY_MANIFEST.md`. **16 resources MUST ALREADY EXIST.**
- [ ] Confirm the checksum in `SHA256SUMS.txt` matches the ZIP you hold.

## Capability

- [ ] The Power Platform environment is in the **DoD** cloud
      (`make.apps.appsplatform.us`), not GCC High.
- [ ] The environment is in the **same tenant** as the four SharePoint sites.
      Same cloud does not guarantee same tenant, and a cross-tenant connection
      fails in a way that reads like a permissions problem for a week.
- [ ] You are permitted to import a solution into it.
- [ ] PAC CLI authorisation is confirmed one way or the other. Nothing in the
      design depends on it; the deployment scripts differ.
- [ ] SharePoint, Power Apps, Power Automate and government Power BI are all
      available. There is no fallback for the first three.

## Lists — before the import, not after

- [ ] Run `Provision-MFOpsLists.ps1 -WhatIf` first. **Always.**
- [ ] Read the output for any list reported as "list exists". A fresh site
      reports none. Even one means every column on it needs checking against
      `docs/SHAREPOINT_SCHEMA_MANIFEST.md` — see the pre-existing list hazard in
      `DEPENDENCY_MANIFEST.md`.
- [ ] Run it for real. Expect **17 lists, 286 columns**.
- [ ] **Confirm every declared index was created.** SharePoint will not add an
      index once a list passes 5,000 items, and `MF_EOM_Item` passes that in the
      first quarter. This is the one failure that cannot be repaired later.
- [ ] Seed the configuration. Confirm all four destinations are inactive and all
      103 installations are `Generation_Enabled = FALSE`.

## The four sites

- [ ] Open **each of the four portfolio site collections** and record the site
      URL, the library name, the exact root folder including its sort prefix,
      and **how the month folders inside FY26 are actually named**.
- [ ] Note that Portfolio 2's slug carries `Legacy_` and the other three do
      not. A URL built by pattern 404s on exactly one portfolio.
- [ ] Bind `MF_Portfolio1..4_SiteURL` at import.
- [ ] Set `Verified_By`, `Verified_Date` and `Active_Flag = TRUE` only for rows
      you actually walked.

## Flows

All five import as **Draft** (`StateCode 0`). Nothing runs until you turn it on,
which is deliberate: EOM-01 writes 737 rows the moment it is activated.

- [ ] Activate in this order: **EOM-01**, then **EOM-03**, then **EOM-02**.
      Nothing downstream has anything to act on until expected items exist.
- [ ] **Leave EOM-04 disabled.** `NotificationsEnabled` is FALSE by programme
      decision and the flow ships off.
- [ ] **EOM-02b ships unbound, and must be duplicated four times — once per
      portfolio site collection.** A SharePoint trigger watches one site and
      one library; the four portfolios are four separate site collections, so
      no single instance can cover them. Save As, then set the site and library
      on each copy from `MF_Portfolio{n}_SiteURL`. One instance bound to one
      portfolio runs perfectly and discovers nothing in the other three, which
      looks identical to working.
- [ ] Confirm the trigger site on each copy is a **different** site collection.
      Four copies pointed at the same site is the same gap with more moving
      parts.

## Security, before anyone uses it

- [ ] Raise the data-layer scope question with the SharePoint administrator.
      `SECURITY_README.md`. It is a deployment dependency, not a build blocker,
      and an ISSM will find it.
- [ ] Confirm the DLP policy permits SharePoint, and decide about Office 365
      Users and Outlook. New connectors are disabled by default in DoD.
- [ ] Confirm no sample security mapping was loaded. The `.sample.csv` files
      hold placeholder accounts and only load with `-IncludeSampleData`.

## Import

- [ ] Import **unmanaged** for a DEV or PILOT environment.
- [ ] Supply connection ids and environment variable values from a deployment
      settings file kept **out of source control**.
- [ ] Expect every flow to arrive **off**. Leave them off.

**Import success is not authorisation to operate.**
