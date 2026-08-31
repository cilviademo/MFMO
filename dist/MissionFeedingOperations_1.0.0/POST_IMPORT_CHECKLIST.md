# Post-import checklist — 1.0.0

In order. Do not reorder, and **do not build screens before EOM-01 produces
correct rows** — every downstream decision depends on the shape of that data.

## 1. Rebind

- [ ] Re-point each canvas data source to the provisioned lists. Canvas data
      sources bind to list ids, and the lists were provisioned separately.
- [ ] Confirm `MF_App_Config.SchemaVersion` reads **5.0**. On a mismatch the app
      disables writes for everyone, developers included, and shows
      `CONFIGURATION_REQUIRED`. That is the gate working, not a fault.
- [ ] Confirm `MF_App_Config.AppVersion` reads **1.0.0** and `TenantCloud` reads
      **UsGovDod**.

## 2. Prove the data before the app

- [ ] Onboard 3–5 pilot bases: populate facilities and operating models,
      validate them, record `Registry_Validated_By` and `_Date`, then set
      `Generation_Enabled = TRUE`.
- [ ] Run EOM-01 for the open period.
- [ ] **Installation- and Contract-scope rows have `Facility_ID` null**, not
      empty string. Verify with a two-view count comparison.
- [ ] The 1119-1 generated **nothing**.
- [ ] Re-run. **Row count unchanged.**
- [ ] Nominal and effective dates are both populated, and a weekend suspense
      rolled with `Due_Date_Adjusted` set.

## 3. Prove the routing before anyone relies on it

- [ ] One upload per portfolio lands in the **matched** month folder on that
      portfolio's own site.
- [ ] Upload for a period whose month folder does not exist: the file lands at
      the Monthly Data Call root, `Needs_Filing = TRUE`, `Filing_Note` says what
      was searched for, and Admin shows the count.
- [ ] **Compare the folder listing before and after. Nothing was created.**
- [ ] An upload to a portfolio whose destination is inactive is refused, and the
      message shows no path, no site URL and no connector text.
- [ ] `SharePoint_Unique_ID` is populated on every submission row.
- [ ] Press Submit twice on one file. **One file, one submission row.**
- [ ] Move a filed document by hand and re-run EOM-02b. It is **not**
      rediscovered as a stray.

## 4. Then the app

- [ ] Upload with an arbitrary filename — `Copy of copy FINAL(2).xlsx`.
- [ ] Correction cycle end to end: submit → return with comment and suspense →
      resubmit → accept. **v1 survives with its QC comment.**
- [ ] Wrong Document before and after the due date: `NOT_SATISFIED` then
      `OVERDUE`, not permanently red.
- [ ] Three people who did not build the app tell amber and yellow apart at a
      glance, on the real screen, at the real size.

## 5. Flows, one at a time

- [ ] EOM-03 first. Reconcile **every row, not a sample**, against the app.
- [ ] Then EOM-02 and the classification queue.
- [ ] EOM-02b **four times**, once per site collection. One instance does not
      cover four sites.
- [ ] EOM-04 last, notifications **off**. Read `MF_EOM_Audit` for a full cycle —
      every intended send is recorded as `Notification Suppressed` — before
      enabling anything.

## 6. Accept

- [ ] `docs/DEPLOYMENT.md` acceptance tests, all sections.
- [ ] `docs/accessibility.md` gates, including the Power Apps Accessibility
      Checker, which cannot be run outside the maker portal.
- [ ] `security/SECURITY_PROMPTS.md` §15.

## What is still not done after all of this

- The data layer still does not enforce installation scope.
- 98 installations are still not onboarded — **not compliant, not yet asked.**
- Four rulings on requirement scope are still open, and changing scope after
  items exist means regenerating a period.

**Import success is not authorisation to operate.**
