# Known limitations — 1.0.0

Stated plainly. None of these is hidden behind a caveat elsewhere.

## 1. This is not yet an importable solution

The ZIP is the solution envelope. The canvas app has not been authored in Power
Apps and the five flows have not been built, so the package declares components
it does not contain. **Power Platform build: NOT STARTED.**

## 2. Tenant validation has not occurred

Nothing in this release has touched a Power Platform environment. PAC CLI could
not authenticate here and `MF_App_Config.PacCliAuthorized` is still `UNKNOWN`.

Ten things are **NOT TESTABLE LOCALLY** and are listed with an owner in
`docs/TEST_MATRIX.md`. None is reported as passing.

## 3. The data layer does not enforce installation scope

The open security issue. `docs/security-open-issue.md`.

Power Apps `Visible` and `Filter()` are not access control. A base user who can
reach a portfolio's library can reach every other installation's documents in
it, through any client. The app will show a Lackland manager only Lackland;
SharePoint will still serve them Creech's 1119.

**Narrowed, not closed.** The four portfolios turned out to be four separate
site collections, so a portfolio boundary is now a site boundary that SharePoint
enforces natively. What remains is installation scope *within* a portfolio site.

`security-manifest.yaml` carries `data_layer_permissions_verified: false` and it
stays false until a SharePoint-side change is made.

## 4. Audit authorship is not enforced at the data layer

`Actor_UPN` and `Uploaded_By` are written from the signed-in session and cannot
be forged from inside the app. A user with direct write access to
`MF_EOM_Audit` could set them to anything. Same gap as above, same lists, same
fix.

## 5. The four site bindings do not exist

All four document destinations ship with `Site_URL` blank, `Verified_By` blank
and `Active_Flag` FALSE. EOM-02 fails closed on all three, which means **nobody
can upload anything** until somebody opens each of the four portfolio site
collections and records what is actually there.

The item nobody will guess right is **how the month folders inside FY26 are
named**. Four sites name their root folders four different ways; there is no
reason to believe they agree about months. Without it EOM-02 files everything at
the Monthly Data Call root and looks broken on day one.

Four sites, about ten minutes. `deployment/site-bindings.md`.

## 6. No installation is onboarded

All 103 ship `Generation_Enabled = FALSE`. EOM-01 generates nothing until a
base's facilities and operating models are populated and validated.

**A base with the flag FALSE reads as *not yet onboarded*, never as compliant**,
and every completion figure states its denominator so the un-asked are never
counted clean.

## 7. Facility types are unknown

The QRG carries no facility type for any row, so every type-scoped requirement
applies to every facility until a base confirms one. That over-generates on
purpose: an extra expected row is visible and a reviewer can waive it; a missing
one is invisible until an inspection. EOM-01 reports the count.

## 8. Four rulings are still open

Getting these wrong is not cosmetic, and changing scope after items exist means
regenerating a period.

* The grain of SF 1080, GPC and 1038 — all `Proposed`. Facility scope on a
  three-DFAC base means three uploads; installation scope means one.
* Whether the 1119-1 is conditional or a monthly companion to the 1119.
* Whether the 5-day suspense is programme policy or derived from DAFMAN.
* Whether the 5th and the 10th are calendar or duty days.

`docs/handoffs/RECONCILIATION.md`.

## 9. EOY is only partially defined

The two documents and their citations are settled. The expected-row grain, the
QC checklist, whether count sheets are retained or submitted, and the closeout
rules are not. Do not implement a complete EOY workflow until they are.

## 10. Delegation is proven by construction, not at volume

Every production query filters server-side on an indexed column, and the
patterns are enforced by `scripts/validate_solution.py`. None of it has been run
against a SharePoint list holding more than 5,000 rows, because no such list
exists yet.

**Indexes are created at provisioning time or never.** Verify them before
seeding anything.
