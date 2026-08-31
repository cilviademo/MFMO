# Reference — prior art, not live source

`v3/`, `v11/`, `v14/` and `figma-build/` are handed-over artifacts kept exactly
as they arrived, unmodified. **`v14` is the latest and is the domain truth.**
`v11` and `v3` are kept because decisions in the live tree are still traceable
to them. **Nothing here is built, tested or deployed.**

The live source is the repository root. Where a snapshot and the root disagree,
the root is current and `docs/handoffs/RECONCILIATION.md` says why.

`v12` and `v13` are not vendored separately: `v14` contains both in full, and
the only differences are things `v14` adds (`ACTION_DOCUMENT.md`,
`deployment/site-bindings.md`, `docs/native-visuals.md`, the routing rewrite of
`document-destinations.csv`). Keeping three near-identical trees would make the
diff that matters harder to find, not easier.

`figma-build/` is the Figma design build's `src/`, minus its lockfile and its
copies of the shield and the QRG, which already live in the tree. **It is a
design reference and never an import artifact** — nothing in it uploads to
Power Platform. The importable artifact is the solution package from `pac`.

### The recurring pattern

In every snapshot, the **decision table is current and the code is stale.** V3
shipped three parallel status functions that had already diverged from its own
table; v11 carries a four-state Power Fx block underneath a twelve-rule,
six-state decision order in the same file; v14 states "find, never create" in
`ACTION_DOCUMENT.md` and still specifies constructing the path and creating
folders in `flows/EOM02-Submission/definition.md`.

That is the whole reason the live tree keeps one reference implementation per
decision and a test suite that holds every transliteration to it. The
corrections are recorded in `docs/handoffs/RECONCILIATION.md`.

Known stale in `v3/`:

* `v3/canvas-app/formulas/App.Formulas.fx` derives the label, the colour and the
  semantic string in three separate `Switch` statements over the numeric code.
  That is the divergence the one-engine rule exists to prevent, and the three
  disagree with `v3/docs/status-calculation.md` already.
* `v3/docs/status-calculation.md` carries a Power Fx block that returns `0` for
  a not-due item and has no Blue branch at all, contradicting the decision table
  four sections above it in the same file.

Known stale in `v11/`:

* `v11/docs/status-calculation.md` opens with the correct twelve-rule, six-state
  decision order and closes with a Power Fx block implementing four states and
  no Blue branch.
* `v11/scripts/eom_schema.py` omits `LATE` and `RETURNED` from the
  `Final_Status` choices its own decision order produces, and declares a column
  name three characters over SharePoint's limit.
* `v11/configuration/facilities.csv` names operating models the requirement
  catalogue never matches, which would have generated nothing at all.
* `v11/CHANGELOG.md` and `v11/ROLLBACK.md` are empty files.

Known stale in `v14/`:

* `flows/EOM02-Submission/definition.md` builds the destination path from
  `{FiscalYear}/{ReportingPeriod}/{InstallationName}/{RequirementCode}` and
  creates missing folders. `ACTION_DOCUMENT.md` and
  `configuration/document-destinations.csv` in the same snapshot say
  `{FiscalYearShort}/{MonthFolder}`, `Create_Missing_Folders = FALSE` and
  `FIND_OR_ROOT`. The action document wins; the live spec is rewritten.
* The same spec fails closed on `Channel_Type = 'Unverified'`, a column that
  snapshot's own schema no longer defines — the four portfolios turned out to
  be site collections rather than channels, and the column went with them.
  The live schema fails closed on `Active_Flag`, `Site_URL` and `Verified_By`.
* `scripts/eom_schema.py` still describes `Folder_Template` with the
  constructed four-token path in a `note` beside a `Create_Missing_Folders`
  column whose own note says the flow must not create folders.
* `CLAUDE_CODE_HANDOFF.md` §7 describes four channels in one team; PART 1 of
  `ACTION_DOCUMENT.md` supersedes it with four separate site collections. The
  handoff's own header says the later document wins.
* `docs/MF_EOM_Data_Dictionary.csv` reports 15 lists and 212 columns against a
  schema of 17 and 249 — a generated file committed before its generator ran.

Known stale in `figma-build/`:

* `src/index.css` gives amber (`--status-late-text: #8a5300`) and yellow
  (`--status-review-text: #6b4c00`) two near-identical browns, 1.25:1 apart.
  The split exists to show *who owes the item at a glance*, and at 1.25:1 it
  does not.
* `src/components/ui.tsx` hardcodes four months in the shared period selector
  while `src/screens/Calendar.tsx` calls the generator that already exists.
* Zero `aria-label` across 31 buttons, several of them icon-only.

`v3/docs/mf-operations-prototype.html` is still the best artifact in any of the
sets — its information architecture and security model remain the reference —
but it predates the six-state model and carries a staleness banner in the live
tree.
