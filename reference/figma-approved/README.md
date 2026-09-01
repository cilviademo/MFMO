# Approved design reference captures

Rendered captures of the approved interactive prototype
(`docs/mf-operations-prototype.html` — self-contained, zero network
fetches), taken headlessly with Chromium at the time of the Figma → Canvas
parity pass. They exist so the Studio-open visual validation gate in
`CANVAS_APP_ASSEMBLY.md` has a fixed image to compare against, even when the
prototype cannot be opened next to Studio.

| File | What it shows |
|---|---|
| `prototype-default-1440.png` | Base (DFAC manager) landing view, 1440px |
| `prototype-my-package-1440.png` | My package, 1440px |
| `prototype-activity-1440.png` | Activity, 1440px |
| `prototype-default-768.png` | Base landing at tablet width, 768px |

Everything visible is the prototype's own **synthetic fixture data** —
fictional people, example buildings, in-repo seed requirements. No secrets,
no identities, no site URLs, no CUI. Do not add captures containing real
data.

Two things to know when comparing:

- **`reference/figma-build/` outranks these captures** as the visual source
  of truth. The prototype is the older teaching artifact and shows a base
  tab set of Home / My package / Activity; the approved Figma `BASE_TABS`
  (and the shipped `colNavigation`) is Home / My Package / Calendar. The
  parity record is `configuration/figma-canvas-map.json` +
  `docs/FIGMA_CANVAS_PARITY.md`.
- The prototype's status chip inks predate the amber/yellow accessibility
  re-tint in some views; `docs/accessibility.md` holds the shipped values.

Post-assembly Studio captures (if taken for the record) belong under
`artifacts/canvas-render/`, never here — this directory is the *approved
design*, frozen; that one is *what the platform rendered*.
