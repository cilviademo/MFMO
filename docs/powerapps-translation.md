# Power Apps translation contract

The Figma build is a React/Vite prototype. **It is a design reference, not an
import artifact.** Nothing in `src/` is uploaded to Power Platform. The
importable artifact is the solution package produced by `pac`, built against
`docs/DEPLOYMENT.md`.

This file is the bridge: every pattern in the prototype, and its Canvas
equivalent. Where there is no equivalent, that is stated rather than worked
around.

---

## The blocker to fix first

`src/` contains **250 inline `style={{ ... }}` blocks** across seven screens and
the component library. That is the single biggest obstacle to translation,
because inline styling encodes layout as properties on individual elements —
which is exactly the absolute-positioning pattern that produces brittle canvas
apps.

Before anything is ported, the prototype's layout needs to be legible as a
container hierarchy. Not refactored for its own sake — read and recorded, so the
canvas build starts from structure instead of from pixel values.

Every screen resolves to the same shape:

```
scrX
└── conRoot            vertical, fill parent
    ├── conTopBar      horizontal, fixed 48px
    ├── conNav         horizontal, fixed 40px
    ├── conBody        vertical, flexible, scrollable
    │   ├── conHeader
    │   ├── conStrip
    │   └── conTable
    └── conFooter      optional
```

---

## Pattern mapping

| Prototype | Canvas equivalent | Note |
|---|---|---|
| Inline `style={{}}` | Container properties + named formulas for tokens | The work |
| CSS custom properties (`--accent`) | Named formulas in `App.Formulas` | `gblAccent = ColorValue("#0F548C")` |
| `.dark` class swap | Modern theme + `gblTheme` named formula | Do not build a second set of screens |
| Inline SVG `Icons` object | Power Apps built-in icons | Custom SVG needs an Image control with a data URI — avoid |
| `StatusChip` component | Canvas component `cmpStatusBadge` | Label, icon, fill from one status code |
| `PrimaryButton` / `Secondary` / `Subtle` | Modern Button, `Appearance` property | Do not build three components |
| Data table | Modern Table, or Gallery when a row needs mixed controls | Table first |
| Filter toolbar | Horizontal container of ComboBoxes | Keep controls 32px |
| Drop target | Attachment via flow, **not** the Attachments control | See below |
| Version history list | Gallery bound to `MF EOM Submission` | Filter on indexed `EOM_Item_ID` |
| Progressive disclosure in Review | `Visible` bound to `rdoDecision.Selected.Value` | Native |
| Calendar month grid | PnP canvas calendar component | Not PCF — governance |
| Right rail on Review | Horizontal container, 65/35 fill ratio | Not sticky, see below |

---

## No Canvas equivalent — change the design

**Sticky positioning.** The Review decision panel is described as sticky. Canvas
has no sticky. Make the right container independently scrollable, or keep the
decision panel short enough that it does not need to scroll. The second is
better.

**CSS transitions.** `transition: opacity 0.1s` on the buttons. No equivalent,
and no loss. Remove them from the spec so nobody tries.

**Custom scrollbars.** `index.css` hides the scrollbar thumb until hover
(`background: transparent` until `*:hover`). That is not available in Canvas and
it is an accessibility defect regardless — a low-vision or keyboard user gets no
scroll affordance. Drop it.

**Arbitrary hover states.** Canvas gives `HoverFill` and `HoverColor` on
controls, not arbitrary CSS hover. The rule that matters:

> Hover may refine. Hover must never reveal.

Any action reachable only by hovering is unreachable in the built app, on touch,
and by keyboard.

**The Attachments control.** Do not use it for upload. It binds to a Form,
targets lists rather than libraries, and behaves badly in Teams and on mobile.
Upload goes: app collects file plus declared metadata → Power Automate → writes
to the document library and the lists. Already the design in
`canvas-app/formulas/Upload.fx`.

---

## Tokens as named formulas

CSS variables become named formulas in `App.Formulas` — not `App.OnStart`, which
delays app start and cannot be lazily evaluated.

```
gblBg        = If( gblDark, ColorValue("#1F1F1F"), ColorValue("#FAF9F8") );
gblSurface   = If( gblDark, ColorValue("#292929"), ColorValue("#FFFFFF") );
gblBorder    = If( gblDark, ColorValue("#3D3D3D"), ColorValue("#D1D1D1") );
gblText      = If( gblDark, ColorValue("#FFFFFF"), ColorValue("#242424") );
gblSecondary = If( gblDark, ColorValue("#ADADAD"), ColorValue("#616161") );
gblAccent    = If( gblDark, ColorValue("#4EA0D4"), ColorValue("#0F548C") );

// Six states. Fill, text and border from one code — never three lookups.
StatusFill( code: Number ): Color =
    Switch( code, 3, clrStatusGreenBg, 2, clrStatusYellowBg,
                  1, clrStatusRedBg,   5, clrStatusAmberBg,
                  4, clrStatusBlueBg,  clrStatusGrayBg );

StatusText( code: Number ): Color =
    Switch( code, 3, clrStatusGreen, 2, clrStatusYellow,
                  1, clrStatusRed,   5, clrStatusAmber,
                  4, clrStatusBlue,  clrStatusGray );

StatusLabel( code: Number ): Text =
    Switch( code, 3, "Accepted", 2, "Awaiting review", 1, "Overdue",
                  5, "Late", 4, "Not due", "Not required" );
```

**The tokens, never literals.** `App.Formulas.fx` declares them once and
`scripts/validate_solution.py` fails the build on a colour literal in a screen.
A `Switch` full of hex is how two screens drift apart.

**Amber (5) and yellow (2) are the pair to watch.** Both the prototype and the
Figma build mapped them to near-identical browns — 1.16:1 and 1.25:1 apart —
which collapses the one distinction the six states exist to make. They are now
`#944800` on `#FFF3E6` and `#5A5800` on `#FDFAE0`, 48° apart in hue and ΔE2000
30 apart, and `docs/accessibility.md` explains why hue rather than luminance is
the right measure here.

---

## What the prototype gets right and should be preserved

The design language is sound and should not be restarted. Specifically:

- 2px panel radius, 4px on controls
- 1px hairline borders, no elevation anywhere
- Focus ring: `2px solid var(--accent)`, 2px offset — present and correct
- Status chips carry icon plus text plus colour, three redundant channels
- Dark theme is a token swap, not a second design
- Restrained accent use

Those constraints are the expensive part of a design system and they are already
right. The improvement pass is about content authenticity, the status model and
information hierarchy — not aesthetics.

---

## Order of work

1. Record the container hierarchy for each screen from the prototype.
2. Replace placeholder content with the real requirement set.
3. Split amber from yellow and add the LATE state.
4. Rebuild the Admin screen against observable configuration health.
5. Map icons to the Power Apps built-in set.
6. Build `cmpStatusBadge`, `cmpRequirementRow`, `cmpMetricStrip`,
   `cmpFilterToolbar` as canvas components before any screen.
7. Then screens, in the order in `CODEX_BUILD_HANDOFF.md`.

Steps 2 and 3 can happen in the Figma file. Steps 1 and 5 onward are canvas
work and do not need Figma to finish first.


---

## Five values the design build hardcoded

Every one of these is a number or list somebody will want to change after the
pilot. **An admin edits a list row; a developer does not edit Power Fx.** The
defaults below are fine — what matters is where they live.

| Value in the Figma build | Reads from |
|---|---|
| `Max 50 MB` | `MF_App_Config.MaxUploadSizeMB` |
| `PDF, XLSX, DOCX` | `MF_EOM_Requirement.Accepted_File_Types` — per requirement, because a 1119 and a bank statement are not the same kind of file |
| `aged 4 days or more` | `MF_App_Config.ReviewAgeHighlightDays` |
| `initialDay = 5, finalDay = 10` | `MF_EOM_Requirement.Due_Day` / `Final_Due_Day`, on the requirement row — **never a default in the date code** |
| Age bands `0-1 / 2-3 / 4-5 / 6+` | derived from `ReviewAgeHighlightDays` by `MF_ReviewAgeBands` |

The last two are the ones that matter.

**The suspense days belong to the requirement, not to the engine.** The 5th and
the 10th do not have the same standing — the 5 calendar days is VERIFIED from
procedure language, the 10th is a MANAGEMENT_RULE from the programme — and a
default buried in a date function makes both unchallengeable and identical. A
requirement whose suspense differs is then a data change, not a code change.

**The age bands are derived rather than listed.** Four hardcoded buckets beside
a separately hardcoded threshold is two facts that must agree and nothing making
them. Change the threshold to 3 and the bands still say `4-5`, and the queue
quietly contradicts its own legend. `MF_ReviewAgeBands` computes them from the
one number.

Ageing never recolours a chip. An item awaiting review is yellow because AFSVC
owns it — that comes from the status engine — and the ageing is drawn as
emphasis on the row. A screen that recoloured the chip would be a second status
engine.
