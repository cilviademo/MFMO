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
 accepted 152 · awaiting 14 · corrections 8 · overdue 6
```

One horizontal container, `LayoutMode = Horizontal`, four rectangles. Each
rectangle's `FillPortions` is its count. Height 8px, radius 2px, 1px gaps,
colours from `StatusFill()`.

```
rectAccepted.FillPortions   = [EOM Accepted]
rectAwaiting.FillPortions   = [EOM Awaiting]
rectCorrection.FillPortions = [EOM Corrections]
rectOverdue.FillPortions    = [EOM Overdue]
```

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
