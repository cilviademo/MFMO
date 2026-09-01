# Canvas app assembly

**The hour of pasting is gone.** The app is now BUILT from source by
Microsoft's own toolchain; what remains for a person is minted identity and a
validation open. Three paths, best first.

---

## Path A — assemble against your own export (~15 minutes, recommended)

1. Import `MissionFeedingOperations_1.0.0.zip` (Artifact 1).
2. In the solution: **New → App → Canvas (tablet)**, name it
   **Mission Feeding Operations**. While you are in Studio, **add the 19 data
   sources listed in step 2 of Path C below** — your environment then mints the
   real SharePoint data-source metadata and the assembled app opens with
   sources already bound. Save. Do not build anything.
3. **Export the solution** (unmanaged).
4. On a machine with the Power Platform CLI:

       scripts/assemble_full_solution.sh <your-export>.zip

   It unpacks *your* app with `pac canvas unpack`, keeps **your identity and
   your environment's scaffolding**, swaps in this repository's 16 screens,
   6 components and 1,800+ formulas, re-packs with `pac canvas pack`, puts the
   app back into *your* export, and validates the result structurally
   (`validate_solution.py --export`). Nothing in the output is fabricated:
   wrapper and identity are the platform's, scaffolding is Studio's, content
   is this repository's, assembly is Microsoft's packer.
5. Import the assembled `MissionFeedingOperations_1.1.0.zip`.
6. **Open the app for edit once.** Microsoft's packer states on every run that
   a SourceCode-packed app is validated by that open. Add any data source
   still missing, save, **publish**, and **re-export** — the re-export is the
   final, permanent artifact. No further Studio work, ever.

This path was dry-run end to end here — unpack, swap, pack, re-zip,
validate: 16 screens, 5 workflows, no literal URLs — against a simulated
export. Your export differs only in being real.

## Path B — the pre-built .msapp (already built, not Studio-validated)

`scripts/build_msapp.py` builds `dist/canvas/MissionFeedingOperations.msapp`
from the same source, using a genuine Studio-built donor app for format
scaffolding (see `canvas-app/donor/README.md`), neutralised entry by entry —
the build **fails** if a single commercial-cloud string survives. It
round-trips byte-identically through `pac canvas unpack`.

**It has never been opened by Studio, and no solution component metadata is
fabricated for it** — a CanvasApp component without platform-minted metadata
is exactly the fabrication this project refuses. Use it as reference or for a
side-by-side diff; Path A supersedes it.

## Path C — the paste runbook (fallback, no CLI anywhere)

The original one-sitting session. Everything below this line is Path C, and
its step 2 data-source list is also Path A's step 2 list.

---

## Before you start

Import the solution and confirm these exactly. If any count differs, stop:
the ZIP is not the one this runbook describes.

| | Expected | Where to look |
|---|---:|---|
| Flows | **5**, all disabled | Solution → Cloud flows |
| Environment variables | **24** | Solution → Environment variables |
| Connection references | **3** | Solution → Connection references |
| Canvas apps | **0** | Solution → Apps. You are about to make the first. |
| SharePoint lists provisioned | **17** lists, **286** columns, **90** indexes | the lists site |

The flows, in the order they appear:

```
  EOM-01 Expected Package Generator
  EOM-02 Submission
  EOM-02b Legacy Intake
  EOM-03 Reconciliation
  EOM-04 Notifications
```

---

## Step 1 — create the app INSIDE the solution

Solution → **New → App → Canvas → Tablet**. Name it **Mission Feeding Operations**.

Creating it inside the solution is the whole point. An app made outside and
added later is a different component with a different identity, and the
export will not carry your later edits back into this repository's lineage.

---

## Step 2 — add the 19 data sources, in this order

Order matters: a formula pasted before its data source exists shows an error
that clears itself later, and you cannot tell those from real ones.

```
   1. MF Installation
   2. MF Facility
   3. MF EOM Requirement
   4. MF EOM Item
   5. MF EOM Submission
   6. MF Unmatched File
   7. MF Security Mapping
   8. MF EOM Audit
   9. MF App Config
  10. MF Feature Flags
  11. MF App Event Log
  12. MF EOM Status
  13. MF Non Duty Day
  14. MF Calendar Event
  15. MF Access Request
  16. MF Notification Rule
  17. MF Document Destination
  18. EOM-02 Submission        (the Power Automate flow, via Power Automate)
  19. Office365Users           (the Office 365 Users connector)
```

The last two are not SharePoint lists: the flow is added from the Power
Automate pane, and Office 365 Users from Connectors.

**When you add the flow, note the identifier Studio generates for it.** The
source calls it `EOM02_Submission.Run(...)`. If Studio names it differently,
the formula shows an error immediately — this is one of the few failures in a
canvas app that is *visible* rather than silent. Fix it in
`canvas-app/src/Screens/scrUpload.pa.yaml` and commit, do not fix it only in
Studio.

---

## Step 3 — paste the formulas, in this order

**App → Formulas**. Paste the four files end to end, in this order. Later
files reference earlier ones, so any other order produces errors that are
real but misleading.

```
  1. canvas-app/formulas/App.Formulas.fx
  2. canvas-app/formulas/StatusEngine.fx
  3. canvas-app/formulas/Cascade.fx
  4. canvas-app/formulas/Delegation.fx
```

**Check:** the formula bar reports no errors. `gblSchemaVersion` resolves to
`5.0` once `MF App Config` is seeded.

---

## Step 4 — create the 6 components

**Components → New component**, one per file. Paste its `.pa.yaml`.

Dependency order — cmpMetricStrip contains cmpMetricCard, so the card exists
first:

```
  1. cmpStatusBadge   canvas-app/src/Components/cmpStatusBadge.pa.yaml
  2. cmpEmptyState    canvas-app/src/Components/cmpEmptyState.pa.yaml
  3. cmpMetricCard    canvas-app/src/Components/cmpMetricCard.pa.yaml
  4. cmpEOMItem       canvas-app/src/Components/cmpEOMItem.pa.yaml
  5. cmpMetricStrip   canvas-app/src/Components/cmpMetricStrip.pa.yaml
  6. cmpFilterToolbar canvas-app/src/Components/cmpFilterToolbar.pa.yaml
```

**Check:** `cmpStatusBadge` renders text, an icon and a colour together.
Colour is never the only channel, and a badge showing colour alone is the
defect this component exists to prevent.

---

## Step 5 — create the 16 screens

**New screen → Blank**, rename it to match the file, then paste.

Order is the app's screen order. The two gate screens come first so the
start-screen formula in step 6 has something to resolve to.

| # | Screen | Paste from | The one visible check |
|---:|---|---|---|
| 1 | `scrMaintenance` | `canvas-app/src/Screens/scrMaintenance.pa.yaml` | the support message from MF App Config renders |
| 2 | `scrNoAccess` | `canvas-app/src/Screens/scrNoAccess.pa.yaml` | the request-access button renders |
| 3 | `scrHome` | `canvas-app/src/Screens/scrHome.pa.yaml` | the navigation list on the left renders and the period selector shows the open period |
| 4 | `scrMyPackage` | `canvas-app/src/Screens/scrMyPackage.pa.yaml` | the six column headings appear: Requirement, Frequency, Suspense, Submitted, AFSVC status, Action |
| 5 | `scrOverview` | `canvas-app/src/Screens/scrOverview.pa.yaml` | four metric cards appear with the scope qualifier beneath them |
| 6 | `scrInstallations` | `canvas-app/src/Screens/scrInstallations.pa.yaml` | a row shows 'N of M accepted' -- a fraction, never a bare count |
| 7 | `scrExceptions` | `canvas-app/src/Screens/scrExceptions.pa.yaml` | three tabs appear, each with its own count in brackets |
| 8 | `scrUpload` | `canvas-app/src/Screens/scrUpload.pa.yaml` | the file picker is an Add picture / attachment control, NOT the Attachments control |
| 9 | `scrReview` | `canvas-app/src/Screens/scrReview.pa.yaml` | the four decision buttons appear: Accept, Return, Wrong document, N/A |
| 10 | `scrInstallation` | `canvas-app/src/Screens/scrInstallation.pa.yaml` | the facility list for one installation renders |
| 11 | `scrCalendar` | `canvas-app/src/Screens/scrCalendar.pa.yaml` | the month grid renders and shows non-duty days |
| 12 | `scrActivity` | `canvas-app/src/Screens/scrActivity.pa.yaml` | the audit gallery renders |
| 13 | `scrAdminRequirements` | `canvas-app/src/Screens/scrAdminRequirements.pa.yaml` | the requirement table renders with Authority_Status shown |
| 14 | `scrUnmatched` | `canvas-app/src/Screens/scrUnmatched.pa.yaml` | the classification form renders with no free-text requirement field |
| 15 | `scrAccessRequest` | `canvas-app/src/Screens/scrAccessRequest.pa.yaml` | the scope cascade renders and is empty until an installation is chosen |
| 16 | `scrDiagnostics` | `canvas-app/src/Screens/scrDiagnostics.pa.yaml` | the schema version comparison renders |

---

## Step 6 — start screen, save, publish

- **App → StartScreen** is already `=MF_StartScreen` from step 3. Confirm it.
  It is a formula, not a screen name, so maintenance and no-access are decided
  before anything renders rather than by a redirect the user sees through.
- **Save**, then **Publish**.
- Run the **Accessibility checker** and clear anything it raises. The source
  declares a label on every interactive control; the checker verifies Studio
  agrees.

---

## Step 7 — export the solution

Solution → **Export** → **unmanaged**, then again as **managed**.

Both ZIPs go to the release step. The unmanaged one is the DEV/PILOT artifact;
the managed one is what a later production environment would take.

**This is the moment the app stops being Studio work.** From here the ZIP
carries it.

---

## Step 8 — round-trip the export back into the repository

The exported app is now the truth about control identities; this repository is
the truth about formulas. Reconcile them once, immediately:

```
pac solution unpack --zipfile <exported>.zip --folder ./unpacked
pac canvas unpack --msapp ./unpacked/CanvasApps/*.msapp --sources ./exported-src \
      --layout SourceCode
diff -r ./exported-src/Src canvas-app/src
```

**Where they disagree, the export wins and the repository is updated in a
commit.** Studio normalises formulas, and a repository that quietly disagrees
with the shipped app is how the next round starts from a wrong premise.

From then on `scripts/build_canvas.sh` can rebuild the `.msapp` from this
repository against that app as the seed, and no further Studio session is
needed for a formula change.

---

## What this session does NOT do

- It does not bind site URLs. Those are environment variables, set at import.
  See `deployment/site-bindings.md`.
- It does not enable a flow. All five stay disabled until the import
  checklist's step 9.
- It does not make the app secure. Power Apps `Visible`/`Filter` is not a
  security boundary, and the data layer does not yet enforce installation
  scope independently — `docs/security-open-issue.md`, still OPEN.

