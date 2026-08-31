# Reference — prior art, not live source

`v3/` and `v11/` are the Mission Feeding Operations builds exactly as they were
handed over, unmodified. **`v11` is the later and is the domain truth**; `v3` is
kept because several decisions in the live tree are still traceable to it. **Nothing here is built, tested or deployed.** It is kept so that
every decision in the live tree can be traced back to what it came from, and so
that a reviewer can see what changed and why.

The live source is the repository root. If `reference/v3` and the root disagree,
the root is current and `docs/handoffs/RECONCILIATION.md` says why.

### The recurring pattern

In every snapshot, the **decision table is current and the code is stale.** V3
shipped three parallel status functions that had already diverged from its own
table; v11 still carries a four-state Power Fx block underneath a twelve-rule,
six-state decision order in the same file.

That is the whole reason the live tree keeps one reference implementation and a
test suite that holds every transliteration to it. Twenty corrections are
recorded in `docs/handoffs/RECONCILIATION.md`.

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

`v3/docs/mf-operations-prototype.html` is the best artifact in either set — its
information architecture and security model are still the reference — but it
predates the six-state model and carries a staleness banner in the live tree.
