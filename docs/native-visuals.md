# Status visuals in Power Apps — do not use the chart controls

The app shows the current period. Power BI shows the arc across periods. Both
are needed and they are not substitutes.

## Why not the built-in charts

The classic Column, Line and Pie controls have four problems that matter here:

- **They read roughly the first 50 rows.** Not delegable, not configurable. At
  103 installations a portfolio comparison silently shows part of the data and
  reports success — the same failure mode as a non-delegable `Filter()`.
- **They ignore modern theming.** They will not follow the six status colours,
  so a chart drifts from the chips beside it.
- **Screen-reader support is poor.** That collides directly with the Section 508
  gate in `docs/accessibility.md`, and colour-only encoding is already
  prohibited.
- **They cannot render a stacked proportion** the way the completion bar needs.

## Build them from containers instead

Every visual is a horizontal container holding sized rectangles, or a gallery of
rows. Full theme control, no row cap, keyboard reachable, and they degrade to
text when someone zooms to 200%.

**The numbers appear as text beside every visual. The graphic is the second
channel, never the only one.**

### Completion bar

```
AUGUST 2026        152 of 180 items accepted        84%
[████████████████████████░░░░░░░░]
 accepted 152 · awaiting AFSVC 14 · base owes 12 · overdue 2
```

**The denominator is written out.** `84%` alone invites the reader to supply
their own 180. Worse, a percentage over an unstated denominator is how a base
that was never onboarded gets counted as clean — see the note at the end of
this file, and `powerbi/MF_EOM_Status.md`.

One horizontal container, `LayoutMode = Horizontal`, four rectangles. Each
rectangle's `FillPortions` is its count. Height 8px, radius 2px, 1px gaps,
colours from `StatusFill()`.

```
rectAccepted.FillPortions   = CountRows(Filter(scope, Status_Code = 3))
rectAwaiting.FillPortions   = CountRows(Filter(scope, Status_Code = 2))
rectWithRunway.FillPortions = CountRows(Filter(scope, Status_Code = 5))
rectOverdue.FillPortions    = CountRows(Filter(scope, Status_Code = 1))
```

Five segments, not four: **amber (5) and yellow (2) are separate bars**, because
they are separate claims about who owes the work. A bar that merges "the base
still owes this and has time" with "AFSVC is holding it" tells a DFAC manager
nothing they can act on. `docs/accessibility.md` carries the colours.

Colours come from `StatusFill()`, which reads the tokens in `App.Formulas.fx`.
No screen uses a colour literal, and `scripts/validate_solution.py` fails the
build on one.

`FillPortions` handles the proportional maths, so nothing computes a pixel
width. A zero-count segment collapses on its own.

Selecting a segment sets a filter variable and the table below narrows. That is
a `Select` on a rectangle, which is keyboard reachable — a hover tooltip is not.

### Portfolio comparison

A gallery over a small aggregate collection, sorted worst first. The portfolio
needing attention should not be at the bottom of the list.

Each row: label, track rectangle at fixed width, fill rectangle whose `Width`
is `trackWidth * ThisItem.Pct`, then the percentage and the count as text.

Aggregate server-side. Never `ClearCollect` the item list to compute this —
build the counts with `CountRows(Filter(...))` per portfolio, four queries, all
delegable.

### Review age distribution

Four gallery rows: 0-1 day, 2-3, 4-5, 6+. The last band turns amber past the
review target. Answers "am I keeping up" without a chart.

## What not to build

No pie or donut. No sparklines. No gauge. No animated counters. No trend line —
the app holds one period, and a trend across periods is Power BI's job.

## Where Power BI still earns its place

Trend across reporting periods · cross-portfolio history · on-time rate over
time · anything leadership briefs from · anything needing RLS at a different
grain than the app's.

`MF_EOM_Status` is the fact table for all of it, and the COP reconstructs no
workflow logic — it reads `Status_Code` and formats.


## Every count states what it counted

A completion figure with an unstated denominator is not a summary, it is a
claim the reader has to take on trust — and the trust is usually misplaced.

**A not-onboarded installation is not compliant. It has not been asked.** All
103 installations ship `Generation_Enabled = FALSE`, which means EOM-01
generates nothing for them. A percentage computed over "installations with
items" therefore reports 100% while most of the enterprise has never been
brought into the system.

So the app writes both numbers, always:

```
43 of 43 onboarded installations complete
60 installations not yet onboarded
```

Never one number that silently treats the un-asked as clean. The same rule
governs the Power BI measures, where the temptation is stronger because a card
visual has room for exactly one figure.

`MF_Installation.Generation_Enabled` is the denominator. It is not a
convenience flag — it is the difference between "we are done" and "we have not
started asking".
