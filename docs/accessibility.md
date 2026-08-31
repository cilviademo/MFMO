# Accessibility

**Settled. Do not re-derive.** Section 508 conformance is an acceptance
gate, not a review comment. A release that fails any gate below does not
ship.

The legal floor is Section 508, which incorporates WCAG 2.1 Level AA. That
is the standard applied here.

---

## Acceptance gates

Every one of these is verified before a release is tagged, and the result is
recorded in the CHANGELOG.

| # | Gate | How it is verified |
|---|---|---|
| A1 | Power Apps **Accessibility checker** reports zero issues | Maker portal, screenshot attached to the release |
| A2 | Every interactive control is reachable and operable by keyboard alone | Manual pass, whole task flow, no mouse |
| A3 | Tab order follows visual order on every screen | Manual pass with `TabIndex` audit |
| A4 | No information is conveyed by colour alone | Status chip review — see below |
| A5 | Text contrast >= 4.5:1, large text and UI components >= 3:1 | Contrast table below, checked per token |
| A6 | Every image, icon and chart has a text alternative, or is marked decorative | `AccessibleLabel` audit |
| A7 | Every input has a programmatically associated label | `AccessibleLabel` audit |
| A8 | Errors are announced, identified in text, and suggest a correction | `scrUpload` and `scrReview` error paths |
| A9 | Focus is visible at all times and never trapped | Keyboard pass, dialogs specifically |
| A10 | Screen reader announces status changes without a focus move | `Live` region on the status chip and toast |
| A11 | The app is usable at 200% zoom and at 320 CSS px width | Responsive pass |
| A12 | No time limit expires without warning and extension | Session and flow timeouts |
| A13 | Motion is minimal and respects reduced-motion preference | No autoplay, no essential animation |

Gates A1, A2, A4 and A10 are the ones this application is most likely to
fail, because they are the ones the status model touches.

---

## Status is never colour-only (A4)

`cmpStatusBadge` renders **text and colour together, always**. There is no
mode, no compact variant and no gallery density in which the label is
dropped.

| Visual | Label text | Icon | Contrast on surface |
|---|---|---|---|
| Blue | `Not due yet` | clock | 4.6:1 |
| Amber | `Due soon` / `Submitted - awaiting review` / `In review` / `Returned for correction` | alert / upload / eye / undo | 4.8:1 |
| Red | `Overdue` | warning triangle | 5.9:1 |
| Green | `Accepted` | check | 4.7:1 |
| Gray | `Past suspense - requirement unverified` / `Waived` / `Not applicable` / `Superseded` | info | 7.1:1 |

Three redundant channels: **text, icon shape, colour**. Amber and Gray are
distinguishable in greyscale by icon and by label; Red and Amber differ in
luminance by more than the icon alone would need.

The badge's `AccessibleLabel` is the full sentence, not the chip text:

```
"Status: Past suspense, requirement unverified.
 Action owner: Program. Suspense date 5 November 2026."
```

A screen reader user gets the same information the sighted user gets from
the chip's position in the row, not less.

### The colour tokens

Defined once in `App.Formulas.fx` as named formulas. No screen may declare a
colour literal.

| Token | Hex | Use | On |
|---|---|---|---|
| `clrStatusBlue` | `#0F548C` | Blue chip text/border | `#EFF6FC` |
| `clrStatusAmber` | `#8A5300` | Amber chip text/border | `#FFF9F0` |
| `clrStatusRed` | `#A4262C` | Red chip text/border | `#FDF3F4` |
| `clrStatusGreen` | `#0E700E` | Green chip text/border | `#F1FAF1` |
| `clrStatusGray` | `#424242` | Gray chip text/border | `#F5F5F5` |
| `clrText` | `#242424` | Body | `#FFFFFF` — 15.3:1 |
| `clrTextSecondary` | `#616161` | Secondary | `#FFFFFF` — 6.3:1 |
| `clrFocus` | `#0F6CBD` | Focus ring, 2px, 2px offset | any |

Chip colours are the dark *foreground* on a pale tint, not white text on a
saturated fill — that is what gets the ratios above 4.5:1 while keeping the
five hues distinguishable.

---

## Keyboard (A2, A3, A9)

* No sign-in. CAC resolves identity before the app loads, so there is no
  credential control to tab through and no screen that traps a user who
  cannot complete it.
* Auto-layout containers set the tab order implicitly. `TabIndex` is `0` on
  everything interactive and `-1` on everything decorative. **A positive
  `TabIndex` is forbidden** — it detaches tab order from visual order and
  breaks A3 the moment a container reflows.
* Galleries: arrow keys move within, `Tab` moves out. The first focusable
  control in a gallery row is the item's primary action, not the chip.
* Dialogs (`locDialogOpen`): focus moves to the dialog's first control on
  open, is confined while open, and returns to the invoking control on
  close. `Escape` always closes.
* The focus ring is `clrFocus`, 2px, with 2px offset, and is never removed
  or suppressed by a hover style.
* Skip link: the first tab stop on every screen is **Skip to main content**,
  which moves focus to `conContent`.

Keyboard-only pass is a full task: open the app, pick a facility, upload a
document, return it in QC, resubmit, accept. Mouse untouched. Any step that
cannot be completed is a release blocker, not a bug to log.

---

## Announcements and errors (A8, A10)

* Status changes announce through a live region on the item row rather than
  by moving focus. Moving focus to announce a background change is worse
  than not announcing it.
* Upload progress announces at start and at completion, once each, not per
  percent.
* Errors are: announced, identified in text next to the field, and paired
  with a correction. `"Upload failed"` is not an error message.
  `"Upload failed: this reporting period closed on 5 November. Ask your
  installation manager to reopen it, or pick a different period."` is.
* Required fields are marked in text, not by colour or an asterisk alone.
* Nothing important is communicated by a toast that disappears. Toasts
  duplicate a state that remains visible on the screen.

---

## Naming (A6, A7)

Every control's `AccessibleLabel` is set explicitly. The naming convention
carries the meaning:

* `cmbFacility` — `"Facility"`, with the selected value announced by the
  combo box itself.
* `btnReview` — `"Review submission for <requirement>, <facility>,
  <period>"`. Not `"Review"` — a screen reader user tabbing a gallery hears
  the same word twelve times otherwise.
* `lblFacilityName` — a label, `TabIndex` `-1`, not focusable.
* Decorative icons: `AccessibleLabel` empty **and** `TabIndex` `-1`.
* Charts on the COP carry a text summary and a data table alternative.

Component-level: `cmpStatusBadge`, `cmpEOMItem`, `cmpMetricCard` and
`cmpEmptyState` each expose an `AccessibleLabel` input property and set it
on their root container. A component that hard-codes its own label cannot be
made accessible by its caller.

`cmpEmptyState` is an accessibility feature, not decoration: an empty
gallery with no explanation is indistinguishable from a failed load. It
states what is empty, why, and what to do.

---

## Testing procedure

Run before every release, in this order:

1. **Automated** — Power Apps Accessibility checker on every screen,
   including `scrMaintenance`, `scrNoAccess` and `scrDiagnostics`. Zero
   issues.
2. **Contrast** — verify each token pair in the table above. Tokens change
   rarely; verify anyway.
3. **Keyboard-only** — the full task above, plus: reach `scrDiagnostics`
   as a normal user (must fail), open and escape every dialog, and tab
   through a gallery with 200+ rows.
4. **Screen reader** — NVDA or JAWS on Edge, one facility user task and one
   reviewer task end to end. Confirm the status chip announces its full
   sentence and that QC return errors are announced.
5. **Zoom** — 200% browser zoom and a 320px viewport. No horizontal
   scrolling of the page, no clipped controls, no lost content.
6. **Record** — results and any variance in the CHANGELOG entry for the
   release. A variance needs a named owner and a target release; an
   undocumented variance is a failure.

---

## Known constraints

* Power Apps galleries virtualise rows. A screen reader announces the loaded
  set, not the total. Mitigate by stating the count in text above the
  gallery (`"12 items, showing 12"`), which also helps the delegation
  question — if the app says 500 and the count says 500, suspect truncation.
* The Fluent 2 modern controls carry better ARIA semantics than the classic
  set. If capability gate 8 is not green, the classic fallback needs
  `AccessibleLabel` set on more controls, and the variance is recorded.
* PDF evidence is user-supplied and its accessibility is not controllable by
  this app. The app never depends on reading it.
