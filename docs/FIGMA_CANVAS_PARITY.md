# Figma → Canvas visual parity

Three sources of truth, in tension by design:

| Truth | Where | Governs |
|---|---|---|
| **Visual** | `reference/figma-build/` (vendored, read-only) | What the screens should look like |
| **Functional** | `canvas-app/src/` + `canvas-app/formulas/` | What the screens do |
| **Platform** | Power Apps Studio | What can actually render |

The machine-readable contract between them is
`configuration/figma-canvas-map.json`, enforced by
`scripts/check_design_parity.py` (runs in the suite; a `FAIL` row or a token
drift blocks release). This document is the narrative: what matches, what
deviates, and **why every deviation exists**.

Parity vocabulary, per the fidelity directive:

- **PASS** — visually faithful within platform rendering differences.
- **MINOR DRIFT** — visible difference that does not change meaning; rationale
  recorded.
- **PLATFORM SUBSTITUTION** — Power Apps cannot express the Figma construct;
  the nearest native equivalent is used and named.
- **FAIL** — meaningful visual/functional divergence. Blocks release. There
  are none.

Nothing in this repo claims pixel-perfection. What the gate proves is
narrower and honest: the canvas source *cannot draw from anything but the
approved token set*, its navigation is exactly the approved navigation, and
every screen and component is accounted for in the map. How Studio actually
paints it is **NOT TESTABLE LOCALLY** — the Studio-open visual gate in
`CANVAS_APP_ASSEMBLY.md` is where a human confirms the render, before
Save → Publish → Re-export.

---

## 1. Tokens

Declared exactly once, in `canvas-app/formulas/App.Formulas.fx`. The parity
gate fails if any screen or component contains a `ColorValue()`/`RGBA()`
literal, if any token drifts from the approved value, or if any screen skips
its token `Fill` (default Power Apps styling is treated as FUNCTIONAL DESIGN
DRIFT).

Identical to the Figma package (`src/index.css` `:root`): background
`#FAF9F8`, surface `#FFFFFF`, border `#D1D1D1`, text `#242424`, secondary
`#616161`, accent `#0F548C`, and the blue/red/green/gray-bg status values.

**Approved deviations** (the arbiter is `docs/accessibility.md`):

| Token | Canvas | Figma | Why |
|---|---|---|---|
| `clrStatusAmber` | `#944800` | `#8A5300` | The Figma CSS predates the amber/yellow separation fix. The shipped pair `#944800`/`#5A5800` is 41° apart in hue, ΔE2000 25.1, and holds under all three CVD simulations; the pre-fix pair was 1.16:1 — two near-identical browns telling a DFAC manager that "you still owe this" and "AFSVC has it" are the same problem. |
| `clrStatusYellow` | `#5A5800` | `#6B4C00` | Same fix, the other half of the pair. |
| `clrStatusAmberBg` | `#FFF3E6` | `#FFF4E5` | Fill side of the same re-tint. |
| `clrStatusYellowBg` | `#FDFAE0` | `#FEFCE8` | Fill side of the same re-tint. |
| `clrStatusGray` | `#424242` | `#484848` | Minor darkening for contrast on the gray chip. |
| `clrFocus` | `#0F6CBD` | — | Fluent focus ring; Figma has no counterpart. |

The design language survives intact: low radius (2px chips, 4px cards),
hairline 1px borders, no shadows, the muted Cognos-adjacent palette on an
off-white ground. Dark theme is not implemented in the canvas app
(**PLATFORM SUBSTITUTION** — canvas apps have no `prefers-color-scheme`; a
manual theme toggle was judged not worth doubling the token surface for
pilot. The Figma dark palette remains in the vendored CSS if that changes).

## 2. Typography

**PASS, with no substitution needed.** The Figma package itself says it:
Inter is the *design-time* substitute, and the production font is Segoe UI
Variable / Segoe UI — which is exactly what Power Apps renders natively. The
Google Fonts `@import` was already removed from the vendored CSS. The text
ramp maps `Body→Body1`, `Caption→Caption1`, `Subtitle→Subtitle1` during
msapp-source generation (`scripts/gen_msapp_source.py`) — a **PLATFORM
SUBSTITUTION** in name only, since the Fluent ramp is what the Figma sizes
were sampled from.

## 3. Navigation

The approved experience, and what `colNavigation` now encodes verbatim:

- **Base user** sees exactly `Home / My Package / Calendar` — the Figma
  `BASE_TABS`. **Submit is a primary action on those screens, not a tab**;
  an earlier `upload` nav entry was removed in this pass.
- **Request access** is a button on `scrNoAccess`, never a tab (its nav
  entry was removed).
- **Unmatched classification** is reached from `scrExceptions` rows, never a
  tab (removed).
- **AFSVC** sees Overview / Installations / Exceptions / Review / Calendar /
  Activity / Admin — the directive's approved AFSVC experience.
  `reference/figma-build`'s `PM_TABS` lacks Exceptions and Activity; the
  directive supersedes the prototype there, and that is recorded in the map
  rather than silently resolved.
- **Nav badge-count chips** (the `badge: 2` / `badge: 14` red chips in
  `ui.tsx`) are omitted — **MINOR DRIFT**: a live count on every tab means a
  count query per tab on every screen paint against >2,000-row lists; the
  queue screens themselves lead with the counts. The visual affordance lost
  is a number the user reaches one tap later.

Labels match the Figma casing (`My Package`, `Admin`) — both corrected in
this pass.

## 4. Screens

16 canvas screens ↔ 16 Figma screen files. Full row-by-row detail lives in
the map; the deviations worth reading:

- **`Launch.tsx` → `App.StartScreen`** (PLATFORM SUBSTITUTION). Power Apps
  runs `MF_StartScreen` before painting anything; the platform's own loading
  state replaces a hand-built splash.
- **`ConfigRequired.tsx` → `scrMaintenance`** (MINOR DRIFT). The kill switch
  blocks exactly as designed. A *schema-version mismatch* deliberately does
  not: users keep read access to their own status (the thing they came for,
  which is still true) and the full `CONFIGURATION_REQUIRED` detail renders
  on `scrDiagnostics`. Function over visual fidelity, documented rather than
  hidden.
- **`ScopeUnresolved.tsx` + `NoAccess.tsx` → `scrNoAccess`** (MINOR DRIFT).
  Both states resolve to the same operator action — fix the
  `MF Security Mapping` row — and both offer the request-access route.
- **`ReviewQueue.tsx` + `Review.tsx` → `scrReview`** (MINOR DRIFT). Queue
  and detail are one screen with a gallery and a detail pane: same
  information, one fewer hop.
- **`AccessManagement.tsx` → nothing** (PLATFORM SUBSTITUTION). Grant
  administration happens in the SharePoint list UI. Power Apps
  `Visible`/`Filter` is **not** a security boundary
  (`docs/security-open-issue.md`, still OPEN); an in-app grants editor would
  dress that boundary up as one.
- **Canvas-only screens** (`scrExceptions`, `scrActivity`, `scrUnmatched`,
  `scrInstallations`, `scrAdminRequirements`, `scrMaintenance`) each carry a
  recorded origin in the map — none is an invented requirement.

Information density is preserved: the AFSVC tables are galleries with the
Figma column sets, not simplified cards.

## 5. Components

6 canvas components ↔ the Figma component inventory. The one with real
drift is the one that matters most:

**`cmpStatusBadge` ↔ `StatusChip`** — label + icon + 1px status border +
radius 2 + tinted fill, per spec, and never colour alone. Two recorded
deviations: the chip is 32px tall against Figma's ~20px (minimum touch
target beats visual scale — accessibility outranks visual in the directive's
priority order), and the border colour follows the status *text* token
rather than Figma's separate border tokens, which were designed against the
pre-fix amber/yellow inks. **Amber and yellow are never merged** — the gate
asserts the inks and the fills differ, mechanically, forever.

## 6. Assets and icons

**No runtime fetches, anywhere.** The gate greps every screen, component and
formula file for CDN, Google Fonts, Figma CDN and Blob references — the app
renders entirely from tokens and native controls, with no image assets
embedded (`AFSVC-Shield.png` in the Figma package is unused by the approved
screens). Icons are native Power Apps icons mapped from the Figma icon
intent (warning, clock, check, minus, circle); no emoji stand-ins.

## 7. Responsive behaviour

The Figma package targets 1440 / 1024 / 768. The canvas app is built on
AutoLayout containers (`verticalAutoLayoutContainer` /
`horizontalAutoLayoutContainer`) which reflow rather than scale, matching
the prototype's flexbox behaviour. True breakpoint checks are **NOT
TESTABLE LOCALLY**; the Studio-open gate includes resizing the preview to
tablet width.

## 8. What would block release

- Any `FAIL` parity row in the map.
- Token drift, a colour literal outside the token layer, a screen without
  its token `Fill` (anti-default-styling check), a nav shape change, a chip
  spec break, an unmapped screen or component, or a runtime fetch —
  all machine-checked by `scripts/check_design_parity.py`.
- At assembly time: a default `Screen1` surviving in the packed app
  (`scripts/validate_final_export.sh`), or a human judging the Studio render
  substantially divergent from the Figma reference at the §25 gate in
  `CANVAS_APP_ASSEMBLY.md`.
