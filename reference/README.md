# Reference — prior art, not live source

`v3/` is the Mission Feeding Operations V3 build exactly as it was handed over,
unmodified. **Nothing here is built, tested or deployed.** It is kept so that
every decision in the live tree can be traced back to what it came from, and so
that a reviewer can see what changed and why.

The live source is the repository root. If `reference/v3` and the root disagree,
the root is current and `docs/handoffs/RECONCILIATION.md` says why.

Two things in `v3/` are known to be stale, and the live tree fixes both — see
the reconciliation record for the detail:

* `v3/canvas-app/formulas/App.Formulas.fx` derives the label, the colour and the
  semantic string in three separate `Switch` statements over the numeric code.
  That is the divergence the one-engine rule exists to prevent, and the three
  disagree with `v3/docs/status-calculation.md` already.
* `v3/docs/status-calculation.md` carries a Power Fx block that returns `0` for
  a not-due item and has no Blue branch at all, contradicting the decision table
  four sections above it in the same file.

`v3/docs/mf-operations-prototype.html` is the opposite: it is the most current
and most correct artifact in the V3 set, and the live prototype is derived from
it rather than replacing it.
