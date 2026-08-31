# Accessibility — a build gate, not a review step

Section 508 applies to software developed, maintained, procured or used by
federal agencies. Web software maps to WCAG 2.x A and AA plus the software
criteria. Accessibility is built into the lifecycle, not added at the end, so
**these are acceptance tests that block release.**

---

## Rules for this app

### Status is never communicated by colour alone

Every status carries a text label. **A green square on its own is a defect.**

This is why `Final_Status` — the semantic string — is stored alongside
`Status_Code` on both `MF_EOM_Item` and `MF_EOM_Status`, and why
`cmpStatusBadge` takes a status rather than a colour. There is no compact chip
variant that drops the label, at any gallery density.

> V3 named this column `Status_Semantic` on the fact and `Final_Status` on the
> item, and carried both on the fact. There is now one semantic column,
> `Final_Status`, on both — two columns that must always agree are a defect
> waiting to happen. See `handoffs/RECONCILIATION.md` C8.

Three redundant channels: **text, icon shape, colour.**

| Code | Colour | Label examples | Icon |
|---|---|---|---|
| 0 | Gray | Not applicable | blocked |
| 1 | Red | Overdue | warning |
| 2 | Amber | Correction needed · Awaiting review · Not satisfied | undo · view · error |
| 3 | Green | Accepted | check |
| 4 | Blue | Not due · Informational | clock · info |

Amber and Blue are distinguishable in greyscale by icon and by label. The badge
announces the whole sentence, not the chip text:

```
"Status: Correction needed. Action owner: Facility. Due 10 September 2026."
```

A screen reader user gets what a sighted user reads from the row's position,
not less.

### Use native modern controls

Do not build a fake combo box out of a gallery and a button, a custom table
from labels, or a tab strip from rectangles. Microsoft warns specifically about
composite controls assembled where a native one exists, and they are the most
common cause of a screen reader announcing nothing useful.

| Need | Use | Never |
|---|---|---|
| Selection | native Combobox / Dropdown | gallery + button |
| Tabular data | modern Table | gallery of labels |
| Status | modern Badge with text | coloured rectangle |
| Confirmation | modern Dialog | overlaid rectangle group |
| Action | native Button | clickable icon with no label |

### Responsive layout via containers

Auto-layout horizontal and vertical containers, never absolute X/Y positioning.

```
scrHome
└── conRoot            (vertical, fill parent)
    ├── conHeader      (horizontal, fixed height)
    ├── conBody        (horizontal, flexible)
    │   ├── conNav     (fixed width, collapses under 700px)
    │   └── conContent (flexible)
    └── conFooter
```

`Button.X = 475` and `Gallery.Width = App.Width - 423` are the signature of a
brittle app and they break at 200% zoom.

On narrow Teams and mobile widths, **wrap into record cards rather than hiding
table columns.** A truncated table on a phone loses the status column, which is
the one thing the row exists to show.

### Keyboard

* **No sign-in.** CAC resolves identity before the app loads, so there is no
  credential control to tab through and no screen that traps a user who cannot
  complete it.
* `TabIndex` is `0` on everything interactive and `-1` on everything
  decorative. **A positive `TabIndex` is forbidden** — it detaches tab order
  from visual order the moment a container reflows.
* The first tab stop on every screen is **Skip to main content**.
* Galleries: arrow keys move within, `Tab` moves out. The first focusable
  control in a row is its primary action, not the chip.
* Focus moves into a dialog on open, is confined while open, and returns to the
  invoking control on close. `Escape` always closes.
* The focus ring is never removed or suppressed by a hover style.

---

## Acceptance tests

- [ ] Every interactive control reachable by keyboard alone, in logical order
- [ ] Visible focus indicator on every control
- [ ] `AccessibleLabel` set on every control conveying meaning
- [ ] Text contrast at least 4.5:1; UI components and large text at least 3:1
- [ ] No status conveyed by colour alone anywhere, in the app **or the COP**
- [ ] Screen reader announces status chips as text
- [ ] Status changes announce without moving focus
- [ ] Usable at 200% zoom and 320px width with no horizontal scrolling
- [ ] Errors announced, tied to the field, and written in plain language
- [ ] Form fields have programmatic labels, not adjacent text only
- [ ] Document links describe the document, not "click here"
- [ ] Empty galleries explain what is empty and why
- [ ] Power Apps Accessibility Checker returns zero errors before each release

The gates this app is most likely to fail are the status-colour rule, the
keyboard-only pass, and announcing state changes — all three are things the
status model touches.

## Colour tokens

Declared once in `App.Formulas.fx`. **No screen may use a colour literal**, and
`scripts/validate_solution.py` fails the build on one.

| Token | Hex | On | Ratio | Means |
|---|---|---|---|---|
| `clrStatusBlue` | `#0F548C` | `#EFF6FC` | 7.2:1 | Not due — nobody acts |
| `clrStatusAmber` | `#944800` | `#FFF3E6` | 6.0:1 | Late — BASE owes it, has runway |
| `clrStatusYellow` | `#5A5800` | `#FDFAE0` | 7.0:1 | Awaiting review — AFSVC owes it |
| `clrStatusRed` | `#A4262C` | `#FDF3F4` | 6.7:1 | Overdue or returned — BASE, no runway |
| `clrStatusGreen` | `#0E700E` | `#F1FAF1` | 5.9:1 | Accepted |
| `clrStatusGray` | `#424242` | `#F5F5F5` | 9.2:1 | Not required this period |
| `clrText` | `#242424` | `#FFFFFF` | 15.5:1 |  |
| `clrTextSecondary` | `#616161` | `#FFFFFF` | 6.2:1 |  |

Chip colours are a dark foreground on a pale tint, not white on a saturated
fill — that is what keeps six hues distinguishable while staying above 4.5:1.

### Amber and yellow, and why "3:1 between them" is the wrong test

The six states exist so that **colour carries ownership**. Amber says the base
still owes the document and still has runway; yellow says AFSVC has it and the
base owes nothing. Collapsing them tells a DFAC manager that a document they
filed on time and one they never sent are the same kind of problem.

They were `#8A5300` and `#6B5300` — **1.16:1 apart**, two near-identical
browns. The Figma build had the same pair at 1.25:1. Labels and icons differed,
so it was never a 508 failure, but at that distance nobody can tell them apart
at a glance, which was the entire purpose.

The build note asked for **at least 3:1 between the two text colours**. That
test cannot be passed and should not be attempted. WCAG contrast is a ratio of
*relative luminance*; two colours can differ only in hue and sit at 1.0:1. To
put 3:1 between two chip texts, one of them has to become roughly three times
lighter — at which point it fails 4.5:1 against its own pale background. The
requirement is self-defeating: it trades a real accessibility guarantee for a
proxy measure of a different property.

3:1 is also not a text-contrast threshold in WCAG. It is 1.4.11 Non-text
Contrast, which governs a UI component against **adjacent** colour — not two
foregrounds that never touch.

What actually matters is whether the two are *perceptually distinct*, which is
measured in a perceptually uniform space:

| Pair | Luminance ratio | ΔE2000 | Hue separation |
|---|---|---|---|
| Old amber vs old yellow | 1.16:1 | 10.5 | 17° |
| **New amber vs new yellow** | **1.13:1** | **25.1** | **41°** |

ΔE2000 above about 5 is unambiguous to a casual observer. 25 is not a
borderline call.

**Amber must not arrive at red on its way to orange.** Red means the base has
no runway left and amber means it still has some — a distinction as load-bearing
as the one against yellow, and one that a naive "make amber more orange" fix
walks straight into. The first candidate pair scored ΔE 30 against yellow and
only 14.5 against red, which traded one collision for another. The shipped
amber is **ΔE 19.5 from red**, and `tests/test_design_tokens.py` holds both
distances at once.

And it survives colour-vision deficiency, simulated at the token level:

| Simulation | ΔE2000 | Luminance ratio |
|---|---|---|
| Deuteranopia | 17.6 | 1.78:1 |
| Protanopia | 13.9 | 1.61:1 |
| Tritanopia | 14.8 | 1.26:1 |

The luminance ratio *improves* under deutan and protan, because the two hues
collapse onto different points of the remaining axis rather than the same one.

None of this is the guarantee. **The guarantee is that colour is never the only
channel**: every chip carries its label in text and a distinct icon, and the
app is usable in greyscale and by a screen reader with the colours switched
off entirely. Hue is what makes the six scannable; text is what makes them
readable. `tests/test_design_tokens.py` holds all of it.

---

## Error copy

Never expose a status code. Say what happened and what to do.

| Situation | Message |
|---|---|
| No matching requirement | We found the file but there's no expected requirement matching that facility, document and period. Send it to Needs Classification and someone will confirm whether the requirement should exist. |
| Comment missing on return | Add a comment explaining what needs correcting. |
| Suspense missing | Set a date for the corrected document. |
| Read-only mode | The app is read-only while we finish maintenance. You can view status but not submit. |
| No scope mapping | You're signed in as *name*. Your account isn't mapped to a facility yet. This isn't a sign-in problem, and signing in again won't change it. |
| Nothing in the queue | Every current submission has been accepted or returned. New submissions appear here as they arrive. |

**An empty gallery with no explanation is indistinguishable from a failed
load.** `cmpEmptyState` is an accessibility feature, not decoration: it states
what is empty, why, and what to do. Every gallery has one.

---

## Known constraints

* Power Apps galleries virtualise rows, so a screen reader announces the loaded
  set rather than the total. Every gallery states its count in text above it,
  which also makes a delegation truncation visible instead of silent.
* If the modern-controls capability gate is not available, the classic fallback
  needs `AccessibleLabel` set on more controls, and the variance is recorded in
  the CHANGELOG for that release.
* PDF evidence is user-supplied and its accessibility is not controllable by
  this app. The app never depends on reading it.
