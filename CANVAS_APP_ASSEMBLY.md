# Canvas app assembly

**The app is not in the solution ZIP, and there is no placeholder for one.**

You build it in Power Apps Studio, **inside the already-imported solution**. It
then inherits the solution's connection references and environment variables the
moment it is created, so there is no plumbing to reconstruct — you paste
formulas into a shell that is already wired.

## Why it is not in the ZIP

The `.msapp` is a zip of internal JSON that Studio owns. `pac canvas pack` is
being deprecated and the source format is mid-transition, so a hand-authored
file with the right extension is a file Studio may reject on open.

A ZIP that fails at import is worse than one that is honestly incomplete,
because the import error names an internal file and explains nothing. You would
spend an afternoon assuming the tenant was the problem.

Everything else in the package is real: five flows with real triggers, three
connection references, eighteen environment variables. Import it first.

---

## Step 0 — Import the solution first, and confirm it landed

Do not create the app before the import. An app created outside the solution
does not inherit its connection references, and moving it in afterwards means
rebinding every data source by hand — which is the work this ordering exists to
avoid.

After importing:

- [ ] The solution appears with **five flows**, all **off**. Leave them off.
- [ ] **18 environment variables** are listed, each with the value you supplied
      at import. Any left blank will surface as `CONFIGURATION_REQUIRED`.
- [ ] **3 connection references** show a connection.
- [ ] The 17 SharePoint lists exist and are populated — see
      `deployment/DEPENDENCY_MANIFEST.md`. **The import does not create them.**

## Step 1 — Create the app inside the solution

Solutions → `MissionFeedingOperations` → **+ New** → App → **Canvas app**
(blank, **Tablet** layout).

Name it `Mission Feeding Operations`. Creating it here rather than from the
Power Apps home page is the whole point.

## Step 2 — Add the data sources

Add these **17 SharePoint lists** from the site bound to
`MF_SharePointSiteURL`. Add them in this order; the first five carry the core
loop and let you test while you finish the rest.

```
MF EOM Item · MF EOM Submission · MF EOM Requirement
MF Installation · MF Facility
MF Security Mapping · MF App Config · MF Feature Flags
MF EOM Status · MF Document Destination · MF Non Duty Day
MF EOM Audit · MF App Event Log · MF Unmatched File
MF Calendar Event · MF Access Request · MF Notification Rule
```

Add **EOM-02 Submission** as a Power Automate flow on `scrUpload`. The other
four flows are not called from the app.

> **Check the display names.** The app references lists as `'MF EOM Item'` —
> spaces, not underscores. The *columns* are underscored internal names. If a
> list was created with a different display name, the references will not
> resolve. `docs/SHAREPOINT_SCHEMA_MANIFEST.md` is the contract.

## Step 3 — Paste the formulas, in this order

Enable **Settings → Upcoming features → Named formulas** first. Everything below
depends on it.

App → **App.Formulas**, pasted in this order — later files reference earlier
ones:

| Order | File | What it defines |
|---|---|---|
| 1 | `canvas-app/formulas/App.Formulas.fx` | Config readers, colour tokens, identity and scope, write gates, telemetry |
| 2 | `canvas-app/formulas/StatusEngine.fx` | The six states, the twelve rules, package rollup, chip colour |
| 3 | `canvas-app/formulas/Delegation.fx` | Every query the app is allowed to run against a high-volume list |
| 4 | `canvas-app/formulas/Cascade.fx` | The cascading dropdowns and the applicability predicates |

**Paste them verbatim, comments included.** The comments are why the formulas
are shaped the way they are, and the next person to open this needs them more
than you do.

Three things to verify immediately after pasting:

- [ ] `MF_ExpectedSchemaVersion` reads **"5.0"**. It is a literal on purpose:
      reading it from the environment would compare a value with itself.
- [ ] `gblSchemaMatches` resolves. If it is false, `MF_App_Config.SchemaVersion`
      does not read `5.0` and **writes are disabled for everyone, developers
      included**. That is the gate working.
- [ ] No red squiggle on `MF_LiveScope`. If there is, `MF Security Mapping` is
      not added or is named differently.

There is **no `App.OnStart`**. Everything resolves through named formulas, which
is deliberate: `OnStart` runs once and goes stale, and a value that goes stale
mid-session is how a status engine starts lying.

## Step 4 — Build the four components first

Components before screens: every screen uses them, and building a screen against
a component that does not exist yet means building it twice.

| Order | Component | Source | Input properties |
|---|---|---|---|
| 1 | `cmpStatusBadge` | `canvas-app/src/Components/cmpStatusBadge.pa.yaml` | `FinalStatus` (Text), `NominalDueDate` (Date), `EffectiveDueDate` (Date) |
| 2 | `cmpEOMItem` | `cmpEOMItem.pa.yaml` | `Item` (Record), `ShowFacility` (Boolean) |
| 3 | `cmpMetricCard` | `cmpMetricCard.pa.yaml` | `Items` (Table), `Label` (Text) |
| 4 | `cmpEmptyState` | `cmpEmptyState.pa.yaml` | `Title` (Text), `Body` (Text), `ActionLabel` (Text) |

`cmpStatusBadge` is the one to get right. It carries the chip's **text, its
colour and its shape** — three redundant channels — so the six states stay
distinguishable in greyscale and to a colour-blind reader. Amber and yellow are
41° of hue apart and need all three.

## Step 5 — Build the screens, in this order

Do **not** build in alphabetical order. This order lets you test each screen
against real data as you go.

| # | Screen | Lines | Containers | Why here |
|---|---|---|---|---|
| 1 | `scrNoAccess` | 84 | `conRoot` | Smallest, and it is where an unmapped user lands. Build it first so you can test the access gate |
| 2 | `scrMaintenance` | 100 | `conRoot` | Same shape, second gate |
| 3 | `scrHome` | 316 | `conRoot` → `conHeader`, `conBody` | The landing screen. Proves the period selector, the scope resolution and the metric cards |
| 4 | `scrInstallation` | 198 | `conRoot` → `conHeader`, `conContent` | Proves the cascade and delegation at installation grain |
| 5 | `scrUpload` | 332 | `conRoot` → `conHeader`, `conContent` | The front door. Proves the flow call and idempotency |
| 6 | `scrReview` | 423 | `conRoot` → `conHeader`, `conBody` | QC. The largest screen and the one that writes status |
| 7 | `scrActivity` | 220 | `conRoot` → `conHeader`, `conContent` | Version history |
| 8 | `scrUnmatched` | 403 | `conRoot` → `conHeader`, `conBody` | The classification queue |
| 9 | `scrCalendar` | 213 | `conRoot` → `conHeader`, `conContent` | Suspense calendar |
| 10 | `scrAccessRequest` | 215 | `conRoot` → `conHeader`, `conContent` | Access requests |
| 11 | `scrAdminRequirements` | 248 | `conRoot` → `conHeader`, `conBody` | Requirement authority |
| 12 | `scrDiagnostics` | 235 | `conRoot` → `galFlags`, `galEvents` | Developer only. Last, because it reports on everything above |

### The container hierarchy, every screen

Every screen is the same shape, and it is not decoration — it is what makes the
app work at 200% zoom and on a phone.

```
Screen
└── conRoot              vertical auto-layout container, Fill = Parent
    ├── conHeader        horizontal auto-layout, fixed height
    │   ├── title, period selector, identity
    │   └── (scrHome only) the read-only / schema-mismatch banner
    └── conBody          vertical auto-layout, Fill = remaining
        └── galleries and cards
```

Rules that matter:

- **`conRoot` is a vertical auto-layout container filling the screen.** Not
  absolute positioning. A screen built with fixed X/Y breaks the moment somebody
  zooms.
- **Never set a colour literal on a control.** Every colour comes from a token
  in `App.Formulas`, and `scripts/validate_solution.py` fails the build on a
  literal in a screen.
- **Every icon-only control needs `AccessibleLabel`.** The Figma build had zero
  across 31 buttons; the canvas source has one on every interactive control and
  `tests/test_design_tokens.py` keeps it that way.
- **`TabIndex: 0` on every interactive control.** Not a positive number —
  positive tab indexes create an order nobody can maintain.

### Reading a `.pa.yaml`

The YAML is the code. Each file is the screen's control tree with its
properties, and every property value beginning `=` is a Power Fx formula you
paste into the corresponding property in Studio.

```yaml
- lblTitle:
    Control: Text
    Variant: Heading
    Properties:
      Text: ="Mission Feeding Operations"      <- paste into Text
      Color: =clrText                          <- paste into Color
      TabIndex: =0
```

Build the tree top-down and paste each property as you go. Do not retype the
formulas: an autocorrected quote or a dropped `$` in an interpolated string
fails at run time, not at edit time.

## Step 6 — Wire the navigation

`App.Formulas` defines `MF_StartScreen`, which is the gate:

```
!gblHasAccess     -> scrNoAccess
!gblCanEnterApp   -> scrMaintenance
otherwise         -> scrHome
```

Set the app's start screen to `MF_StartScreen`. **Do not** hardcode `scrHome` —
an unmapped user would then land on an empty home screen rather than a screen
telling them how to get access.

## Step 7 — Verify against the smoke test

Work `dist/MissionFeedingOperations_1.0.0/POST_IMPORT_CHECKLIST.md`. The
app-specific subset, in order:

| # | Check | Expected |
|---|---|---|
| 1 | Open as a user with no `MF Security Mapping` row | `scrNoAccess`, with a route to request access. **Not** an empty home screen |
| 2 | Open as a mapped user | `scrHome`, scoped to their installation only |
| 3 | Set `MF_App_Config.SchemaVersion` to `4.9` | Banner appears, **submit is disabled**, `scrDiagnostics` names both versions. Set it back to `5.0` |
| 4 | Set `ReadOnlyMode` to True | Banner appears, submit disabled, viewing still works |
| 5 | Upload with an arbitrary filename — `Copy of copy FINAL(2).xlsx` | Succeeds. The filename is never read for meaning |
| 6 | Press Submit twice on one file | **One file, one submission row.** The second is a replay |
| 7 | Upload against a requirement with no expected item | Refused with the Needs Classification route. **No tracker row is created** |
| 8 | View a package with `[ACCEPTED, NOT_DUE, NOT_DUE]` | `IN_PROGRESS`, not Complete |
| 9 | Compare an amber chip and a yellow chip side by side | Three people who did not build the app tell them apart at a glance |
| 10 | Zoom to 200% | Nothing overlaps, nothing is cut off |
| 11 | Tab through `scrUpload` with no mouse | Every control reachable, in a sensible order |
| 12 | Run the Power Apps **Accessibility Checker** | Zero errors. Warnings reviewed |

Item 3 is the one people skip. It is the only way to see the schema gate work,
and a gate nobody has watched fire is a gate nobody knows is wired.

## Step 8 — Export and commit back

```
Export the solution, UNMANAGED
pac canvas unpack --msapp <exported>.msapp --sources ./unpacked
```

Compare `unpacked/` against `canvas-app/src`. **If they disagree, the committed
YAML wins and the app is corrected** — not the other way round. Then commit the
exported YAML so the two stay in step.

---

## What you are not building

- **No login screen, no password field, no user picker.** Identity comes from
  CAC through Entra before the app loads. A role selector on the front door is
  an access bypass wearing a friendly face.
- **No colour picker anywhere.** Status is calculated, never chosen.
- **No chart controls.** They read roughly the first 50 rows and report success.
  Build visuals from containers and `FillPortions` — `docs/native-visuals.md`.
- **No external fonts.** Segoe UI Variable is the production font; the Google
  Fonts CDN may be blocked on `.mil` and is a supply-chain dependency either
  way.
- **No second status engine.** If you find yourself writing a `Switch` over
  `Status_Code` in a screen, stop: call `MF_EvaluateStatus`. That divergence is
  what the whole build is arranged to prevent.
