# Canvas app — standalone paste runbook (Path C, manual edition)

This app is built OUTSIDE any solution: **Apps → New app → Canvas →
Tablet**, name it `Mission Feeding Operations`. That is deliberate for the
manual pilot -- no solution import and no Dataverse are involved. **State
plainly and up front:** if a solution deployment happens later, the app is
recreated INSIDE the solution at that point (the same content re-paste,
about an hour). Nothing you build now is wasted learning; every formula,
screen and habit transfers verbatim.

## 1. Add the data sources — 18 now, the 19th later

The full app binds 19 sources. Here that is **17 SharePoint lists + the
Office 365 Users connector = 18**, added now; the 19th is the **EOM-02
flow, which does not exist yet** -- you build it in `FLOW-BUILD/
EOM-02-manual.md` AFTER the screens, then return to Studio and attach it
from the **Power Automate pane** (left rail) to the app. The Submit
button's formula errors until then; that is the expected order, not a
mistake.

Data pane → Add data → SharePoint → your site → add each list by its
exact name:

- [ ] `MF Installation`
- [ ] `MF Facility`
- [ ] `MF EOM Requirement`
- [ ] `MF EOM Item`
- [ ] `MF EOM Submission`
- [ ] `MF Unmatched File`
- [ ] `MF Security Mapping`
- [ ] `MF EOM Audit`
- [ ] `MF App Config`
- [ ] `MF Feature Flags`
- [ ] `MF App Event Log`
- [ ] `MF EOM Status`
- [ ] `MF Non Duty Day`
- [ ] `MF Calendar Event`
- [ ] `MF Access Request`
- [ ] `MF Notification Rule`
- [ ] `MF Document Destination`
- [ ] Connector: **Office 365 Users**

**Check:** the Data pane lists 18 entries and none is suffixed `_1`
(a `_1` means a name was mistyped at list creation -- fix the LIST, not
the app).

## 2. Paste the formulas, in this order

**App → Formulas.** Paste the four files end to end, in this order --
later files reference earlier ones, so any other order produces errors
that are real but misleading:

```
  1. formulas/App.Formulas.fx
  2. formulas/StatusEngine.fx
  3. formulas/Cascade.fx
  4. formulas/Delegation.fx
```

**Check:** the formula bar reports no errors, and `gblSchemaVersion`
resolves to `5.0` once `MF App Config` is seeded. One reference will
stay red until section 5: `EOM02_Submission` -- expected.

## 3. Create the 6 components (Insert → Components), before any screen

Paste each from `src/Components/`, in this order:
`cmpStatusBadge`, `cmpEmptyState`, `cmpMetricCard`, `cmpMetricStrip`,
`cmpFilterToolbar`, `cmpEOMItem`.

**Check:** `cmpStatusBadge` renders text, an icon and a colour together --
never colour alone.

## 4. Create the 16 screens, in this order, one visible check each

| # | Screen | Paste from | The one visible check |
|---:|---|---|---|
| 1 | `scrMaintenance` | `src/Screens/scrMaintenance.pa.yaml` | the support message from MF App Config renders |
| 2 | `scrNoAccess` | `src/Screens/scrNoAccess.pa.yaml` | the request-access button renders |
| 3 | `scrHome` | `src/Screens/scrHome.pa.yaml` | the navigation list on the left renders and the period selector shows the open period |
| 4 | `scrMyPackage` | `src/Screens/scrMyPackage.pa.yaml` | the six column headings appear: Requirement, Frequency, Suspense, Submitted, AFSVC status, Action |
| 5 | `scrOverview` | `src/Screens/scrOverview.pa.yaml` | four metric cards appear with the scope qualifier beneath them |
| 6 | `scrInstallations` | `src/Screens/scrInstallations.pa.yaml` | a row shows 'N of M accepted' -- a fraction, never a bare count |
| 7 | `scrExceptions` | `src/Screens/scrExceptions.pa.yaml` | three tabs appear, each with its own count in brackets |
| 8 | `scrUpload` | `src/Screens/scrUpload.pa.yaml` | the file picker is an Add picture / attachment control, NOT the Attachments control (the Submit button errors until section 5's flow is attached -- expected) |
| 9 | `scrReview` | `src/Screens/scrReview.pa.yaml` | the four decision buttons appear: Accept, Return, Wrong document, N/A |
| 10 | `scrInstallation` | `src/Screens/scrInstallation.pa.yaml` | the facility list for one installation renders |
| 11 | `scrCalendar` | `src/Screens/scrCalendar.pa.yaml` | the month grid renders and shows non-duty days |
| 12 | `scrActivity` | `src/Screens/scrActivity.pa.yaml` | the audit gallery renders |
| 13 | `scrAdminRequirements` | `src/Screens/scrAdminRequirements.pa.yaml` | the requirement table renders with Authority_Status shown |
| 14 | `scrUnmatched` | `src/Screens/scrUnmatched.pa.yaml` | the classification form renders with no free-text requirement field |
| 15 | `scrAccessRequest` | `src/Screens/scrAccessRequest.pa.yaml` | the scope cascade renders and is empty until an installation is chosen |
| 16 | `scrDiagnostics` | `src/Screens/scrDiagnostics.pa.yaml` | the schema version comparison renders |

## 5. Build the flow, then come back

Build EOM-02 per `FLOW-BUILD/EOM-02-manual.md`. Then in Studio:
**Power Automate pane → Add flow → EOM-02 Submission.** The red
`EOM02_Submission` references resolve; the Submit path is live.

## 6. Start screen, save, publish

- **App → StartScreen** is `=MF_StartScreen` from section 2 -- confirm it.
- Set the app **icon and description**, run the **Accessibility
  checker** and clear what it raises, then **Save** and **Publish**.
- Share per the guide: app to the pilot **security group** as User; the
  EOM-02 flow **Run-only** to the same group with connections set to
  "Use this connection"; SharePoint list permissions granted separately
  -- sharing the app grants nothing in SharePoint.
