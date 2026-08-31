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
    Switch( code, 3, ColorValue("#F1FAF1"), 2, ColorValue("#FFFBEB"),
                  1, ColorValue("#FDF3F4"), 5, ColorValue("#FFF9F0"),
                  4, ColorValue("#EFF6FC"), ColorValue("#F5F5F5") );

StatusText( code: Number ): Color =
    Switch( code, 3, ColorValue("#0E700E"), 2, ColorValue("#7A5C00"),
                  1, ColorValue("#A4262C"), 5, ColorValue("#8A5300"),
                  4, ColorValue("#0F548C"), ColorValue("#424242") );

StatusLabel( code: Number ): Text =
    Switch( code, 3, "Accepted", 2, "Awaiting review", 1, "Overdue",
                  5, "Late", 4, "Not due", "Not required" );
```

**Amber (5) and yellow (2) need distinct hex values.** The current prototype
maps both to `#8A5300` / `#FFF9F0`, which is the collision. Yellow moves toward
`#7A5C00` on `#FFFBEB`; verify 4.5:1 on both themes before committing.

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
