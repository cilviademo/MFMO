# Design system

Three PnP samples inform this, and one of them needs a correction before you
copy anything out of it.

---

## 1. Fluent, but modern controls — not the 2021 theme hack

`pnp/powerapps-samples/samples/fluentui-for-teams-theme` (Luise Freese) is the
best reference for Teams-native look in canvas: it ships a heavily modified
`themes.json`, ten canvas components, and context-aware switching across
default, dark and high-contrast, storing colours as `gblAppColors` and styles as
`gblAppStyles`.

**But it predates modern controls, and Fluent UI v8 controls in Teams canvas
apps are now deprecated — Microsoft says upgrade to modern controls for design,
performance and accessibility.**

So:

| Take from it | Don't take from it |
|---|---|
| Token values (colour, type ramp, spacing) | The v8 control set |
| The component inventory — what needed wrapping and why | `themes.json` overrides as the theming mechanism |
| Theme-context awareness and runtime switching | `gblAppColors` in `App.OnStart` |
| Its honesty about what isn't stylable | — |

Use **modern controls plus a modern theme**. Put token values in named
formulas (`App.Formulas`), not `OnStart` — same reasoning as everywhere else in
this repo: named formulas evaluate lazily and don't delay app start.

The sample's most useful lesson is negative: some things cannot be styled even
in `themes.json` (the DatePicker's calendar background, for one), which is why
it ships canvas components instead. Expect the same and budget for wrappers.

---

## 2. Calendar — the canvas component, not the PCF control

`pnp/powerapps-samples/samples/calendar-component` (April Dunnam) is a canvas
component that takes a plain table of events:

```
Table(
  { Date: "5/3/2021", Title: "Meeting", Time: "2:30pm" },
  ...
)
```

That's the right shape and the right dependency profile. **Do not use the PCF
Calendar control** (rwilson504/PCFControls) — it needs PCF enabled for canvas
apps in the environment, which is on the "avoid initially" list in
`government-environment-mode.md`.

### What the calendar is for

Two audiences, one component:

**Bases** see when their documents are due. Nothing to configure — the calendar
is generated from `MF_EOM_Item.Due_Date` filtered to their scope. Every event
carries the requirement's status code, so a base can see at a glance that the
1119 due on the 10th is already accepted and the SAIIT due on the 15th is not.

**Portfolio managers and MFMs** author dates. Correction suspenses, FMAT visit
windows, data call cut-offs, ad-hoc taskers. These are not requirement rows and
must not become them — a correction suspense is an instruction, not an
obligation the requirement engine generated.

### Two event sources, one surface

```
MF_EOM_Item.Due_Date          generated, read-only, status-coloured
MF_Calendar_Event             authored, editable by PM/MFM/Admin
```

Do not let an authored event write back into `MF_EOM_Item`. Changing when a
1119 is due is a **requirement change** — `Due_Day` on `MF_EOM_Requirement`,
which regenerates cleanly for future periods. Editing one month's due date on a
calendar would silently desynchronise the item from the requirement that
produced it, and the next generation run would overwrite it.

The calendar therefore has one hard rule: **generated events open the item;
authored events open an editor.** They never merge.

### `MF_Calendar_Event`

| Column | Notes |
|---|---|
| `Event_ID` | PK |
| `Event_Type` | Suspense · Correction due · Assessment · Data call · Reminder |
| `Title` | One line |
| `Event_Date` | Indexed |
| `End_Date` | Nullable — visit windows span days |
| `All_Day` | |
| `Scope_Type` | Enterprise · Portfolio · Installation · Facility |
| `Scope_ID` | Who sees it. Same pattern as `MF_Security_Mapping`. |
| `Linked_Item_ID` | Nullable FK to `MF_EOM_Item` for a correction suspense |
| `Created_By` / `Created_DateTime` | |
| `Status_Code` | For authored events, set by the author; for generated, derived |
| `Active_Flag` | |

Scope means a Portfolio Manager can post one date to every base in the
portfolio, and a base sees it without anyone copying it eleven times.

### Behaviour

- Month view default; agenda list below it on narrow widths, same
  table-desktop/cards-mobile rule as the record lists.
- Day cell shows up to three events plus a count. Never a scrolling cell.
- Event colour uses the same five-state palette. Text label always present.
- Tapping a generated event opens the requirement item. Tapping an authored
  event opens the editor if the user has `Can_QC` or higher, otherwise
  read-only detail.
- Adding an event is a single dialog: type, title, date, scope. Four fields.
- Keyboard: arrow keys move between days, Enter opens, Escape closes. A
  calendar built as a gallery of buttons with no keyboard model is one of the
  accessibility traps in `accessibility.md`.

---

## 3. Routing — what the Timesheet sample actually teaches

`pnp/powerapps-samples/samples/Timesheet` is a tablet canvas app over two
SharePoint lists: `BillTo` (reference data) and `TimesheetEntries`
(transactions). The newer `pnp/powerplatform-samples/samples/weekly-timesheet-sharepoint`
is the better reference — same idea, but built with modern controls, named
formulas and containers, and it ships as a solution rather than a bare `.msapp`.

The structural parallel is exact:

| Timesheet | Mission Feeding |
|---|---|
| `BillTo` reference list | `MF_EOM_Requirement` |
| `TimeEntries` transaction list | `MF_EOM_Item` + `MF_EOM_Submission` |
| Week period navigation | Reporting-period selector |
| Submit → manager review → approve | Submit → QC → accept / return |
| Draft vs Returned indicator | `Final_Status` + `Action_Owner` |
| Submitted entries cannot be deleted | Versions are never overwritten |

**What to adopt:**

- **Period navigation as the primary axis.** The timesheet app is organised by
  week; ours is organised by reporting period. That's already in the app chrome.
- **Bulk operations.** The Dynamics time-entry variant supports acting on
  multiple days at once. A Portfolio Manager reviewing thirty 1119s should be
  able to accept a filtered set in one action, with the comment requirement
  still enforced per return. Add `Accept selected` to the review queue.
- **Recall.** The time-entry sample lets a submitter recall a submission before
  approval. Ours should too: a base that uploads the wrong month can withdraw
  it before review rather than waiting to be told. That's a new
  `QC_Status = "Recalled"` and a superseding version, not a delete.
- **Draft state.** Timesheets have a draft before submission. We deliberately
  don't — a file in the folder is submitted. Don't add one.

**What not to adopt:** the `ClearCollect` pattern that appears in most timesheet
walkthroughs. At timesheet scale it works. At 89 installations it silently
truncates. See `Delegation.fx`.

---

## 4. Two aesthetics, and how they coexist

Teams-native and Cognos-boxy pull in opposite directions. The resolution is by
surface, not by compromise:

**Chrome is Teams.** Anything that sits inside the Teams frame — navigation,
controls, dialogs, form fields — uses modern controls and modern theme tokens
and adapts to light, dark and high-contrast. A Power App that ignores the host
theme looks broken, and high-contrast is a 508 requirement, not a preference.

**Content is Cognos.** Inside the working area: sharp corners, hairline rules,
generous type scale, dense tables, restrained palette, no shadows. The IBM
Cognos reference does this well — the density comes from structure, not from
decoration.

**The launch screen can be branded.** A deep-navy entry screen with large light
type and two or three boxy entry cards is appropriate for a first-run or
launcher surface. It is not appropriate for the screen someone uses forty times
a month.

### Tokens

```
Type        Segoe UI Variable (Teams native). 12 / 13 / 14 / 16 / 20 / 32 / 48
            Headline weight 300, not 700. The Cognos reference gets its
            authority from size and space, not from bold.
Radius      2px on content surfaces. 4px on interactive controls only.
            Nothing is a pill.
Border      1px hairline. Prefer a rule to a shadow. No elevation on tables.
Spacing     4 / 8 / 12 / 16 / 24 / 40
Density     Table row 36px. Section gap 40px. Card padding 20px.
Colour      Neutral surfaces carry the layout. Colour appears only in status
            and in one accent. Five status states, always with a text label.
Accent      #0F548C on light. Navy #001141 → #0043CE gradient reserved for the
            launch surface only.
Charts      One hue per series. No gradient fills. No 3D. No donut.
```

### Explicitly not

No purple. No glassmorphism or frosted panels. No drop shadows on cards. No
pill buttons. No emoji as iconography. No gradient text. No rounded 16px
everything. No hero illustration. No animated counters. Icons are Fluent
outline, 16 or 20px, and every icon has a text label beside it.
