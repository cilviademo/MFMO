# Figma prompt v2 — improvement pass

The previous draft ran to 27 sections. Generation tools average long prompts
toward the middle; a 27-section brief produces a compromise of everything in it.
This is the same instruction set at roughly half the length, with the
non-negotiables front-loaded and the repetition removed.

Paste the block. Notes for you follow it.

---

```
IMPROVE the existing "Mission Feeding Operations" build. Do not redesign it.

The visual foundation is right and stays: sharp rectangles, 2px panel radius,
1px hairline borders, no shadows, no floating cards, restrained palette,
light-weight large headings, compact tables, status labels with text and icon.

Three things are wrong and must change: the content is placeholder, the status
model has a colour collision, and the Admin screen invents infrastructure the
system cannot know about.

Reference: IBM Cognos Analytics for workspace density and table quality.
Microsoft Fluent 2 for controls, states and Teams compatibility.
It must not look like a SaaS dashboard, a SharePoint app, or a Power BI report.

==================================================
1. REPLACE ALL PLACEHOLDER CONTENT
==================================================

Delete every instance of: EOM-MRR, Monthly Review Report, NUT-Q3, Nutritional
Analysis, EQUIP-INV, Equipment Inventory Log, FSIP, Sanitation Inspection,
Contractor Invoice.

Delete: Ramstein AB, Aviano AB, Spangdahlem, 86th Airlift Wing, 31st FW,
"AAFES Contractor-Operated".

The real Legacy/APF monthly package is exactly these:

  1119     AF Form 1119 Feeding Summary          facility    monthly
  SF 1080  Voucher for Transfers                 installation monthly
  SAIIT    Sales, Adjustments, Invoices,
           Inventory, Transfers review           facility    monthly
  GPC      Bank Statement (GPC purchases)        installation monthly
  1119-1   AF Form 1119-1 (Field feeding)        facility    conditional
  1038     AF Form 1038                          installation quarterly

The 1119-1 is FIELD FEEDING. It is not a continuation of the 1119 and it is not
required every month. Show it as "Not required this period" in most states.

Do not show SIK or DAF Form 79 anywhere.

Use these installations: Lackland, Minot, Malmstrom, Creech. Operating model is
"Legacy / APF". Portfolios are numbered 1 to 4.

Facility names look like "Bldg 1234 DFAC" and "Flightline Kitchen".

==================================================
2. FIX THE STATUS MODEL — SIX STATES
==================================================

The current build maps "awaiting review" and "correction needed" to the same
amber. Those are opposite situations: one is waiting on AFSVC, the other is
waiting on the base. Separate them.

  Blue    Submission window open      nobody acts yet
  Amber   Late — initial suspense passed, final call not reached   BASE acts
  Red     Overdue, or correction required                          BASE acts
  Yellow  Awaiting AFSVC review                                    AFSVC acts
  Green   Accepted                                                 done
  Gray    Not required this period                                 nothing

Colour resolves ownership at a glance. Amber means time risk. Yellow means
somebody else has it. Never the same hue.

Status labels are compact rectangles, 2px radius maximum, pale background,
strong text, thin border, a small Fluent outline icon, and always a text label.
Never a pill. Never colour alone. The design must survive greyscale.

==================================================
3. TWO SUSPENSE DATES
==================================================

Every requirement has two:

  Initial suspense   5 calendar days after the reporting month closes
  Final call         the 10th

Show both in plain language, never as raw fields:

  Due 5 Sep · Final call 10 Sep
  Initial suspense passed · 3 days until final call

When a suspense falls on a weekend or holiday, show both dates:

  Due 5 Sep (Mon 8 Sep)

==================================================
4. TWO ROLES, TWO INFORMATION HIERARCHIES
==================================================

Do not build one dashboard with hidden controls.

BASE USER — DFAC manager, accountant, GM. Opens this once a month under time
pressure. Navigation: Home · My Package · Calendar. Three items, no more.
They need: what is due, upload, did AFSVC get it, what came back, resubmit.
They see no portfolio arithmetic, no enterprise tables, no other installations.

AFSVC USER — portfolio and operations managers. Navigation: Overview · Review ·
Installations · Exceptions · Activity. Admin appears only for administrators.
They need: what needs review, who is late, what corrections are outstanding,
and one click to the evidence.

==================================================
5. APPLICATION SHELL
==================================================

Top bar 48px. Left: small app mark, "Mission Feeding Operations". Centre: the
reporting period selector, "August 2026" with a chevron — this is a global
control and changing it updates everything. Right: help, user name, role,
initials avatar, and beneath it "CAC authenticated" at 11px.

No sign-in button anywhere. Identity is resolved before the app loads.

Navigation is a low-weight horizontal task strip. Active state is a 2px accent
underline and a weight change. No filled tab buttons. Badge counts only when
actionable, as a small square, never a pill: "Review 14".

==================================================
6. BASE HOME — THE MOST IMPORTANT SCREEN
==================================================

It answers one question: what do I need to do this month?

Header, plain text, not a card:

  Lackland AFB
  August 2026 EOM
  Legacy / APF · Portfolio 2 · Due 5 Sep · Final call 10 Sep

One full-width package strip:

  AUGUST EOM PACKAGE
  4 of 5 requirements submitted · 3 accepted · 1 awaiting AFSVC · 1 missing
  [thin progress bar, not a donut]
  Right side: [ Submit document ]  [ Open package ]

Then three sections, in this order, each a compact list not a table:

  ACTION REQUIRED — only items the base owns
      SF 1080   Overdue — final call passed 10 Sep        [ Submit ]
      SAIIT     Returned · Wrong reporting period          [ Submit correction ]

  WAITING ON AFSVC
      1119      Submitted 4 Sep 09:14 · awaiting review

  ACCEPTED
      GPC Bank Statement   Accepted 3 Sep

If a section is empty, omit it. Do not render an empty "Action required"
heading.

==================================================
7. MY PACKAGE
==================================================

One dense table. Columns: Requirement · Frequency · Suspense · Submitted ·
Status · Action.

Requirement cell: document code in stronger text, full name beneath at 12px
secondary. Row height 44-52px.

Filter above the table as an understated text or segmented control, not pills:
All · Action required · Under review · Complete.

Row action is a text link with a chevron — "Submit →", "Open →" — not a button
in every row. Filled buttons are reserved for page-level actions.

==================================================
8. SUBMIT
==================================================

Four fields. A base user finishes in under thirty seconds.

  Installation      Lackland AFB      (pre-filled from access)
  Reporting period  August 2026       (pre-filled)
  Requirement       [ select ]        (only what applies here, this period)
  File              drop target
  Notes             optional

Never expose Requirement ID, Portfolio ID, Facility ID, source path, intake
metadata, classification confidence, or SharePoint IDs. Those are system fields.

Confirmation is compact:

  Submitted · 1119 · 4 Sep 2026 09:14
  Awaiting AFSVC review          [ View package ]

==================================================
9. AFSVC OVERVIEW
==================================================

No detached metric cards. One full-width strip divided by 1px vertical rules:

  ACCEPTED 152 · AWAITING REVIEW 14 · CORRECTIONS 8 · OVERDUE 6
  small context line: of 180 expected items · August 2026

Below it a functional filter toolbar, controls 32px high:
search installations · Portfolio [All] · Status [Action required] ·
Requirement [All] · Reset

Then one dense table: Installation · Requirement · Submitted · Status ·
Action owner · Age · Action.

Action owner reads "AFSVC" or "Installation", not "Your action".

==================================================
10. REVIEW
==================================================

Left 65 percent: document workspace. Utility row with the requirement,
installation, period, version and submitted date, plus [Open in Teams] and
[Download]. Then a restrained file placeholder — icon, filename, type, "Open
document to review". Then version history as a compact list: version, submitted,
by, QC result, which is current. Then previous reviewer comments.

Right 35 percent: decision panel.

  Accept · Return for correction · Wrong document · Not applicable

Progressive disclosure. Reason dropdown, comment and correction-due date appear
only when a returning option is selected. Nothing extra shows for Accept.

==================================================
11. CORRECTIONS ARE TICKETS
==================================================

The base sees a reason, not a colour change:

  ACTION REQUIRED
  SAIIT · Correction required
  Wrong reporting period

  AFSVC comment
  "The uploaded SAIIT reflects July. Submit the August review."

  Returned 9 Sep 2026
  [ Submit correction ]  [ Open previous submission ]

==================================================
12. CALENDAR
==================================================

Deadline awareness, not event management.

  August 2026    [ ‹ ] [ Today ] [ › ]    Month | Agenda

Thin event bars. Mark: 31 Aug reporting period closes · 5 Sep initial suspense ·
10 Sep final call · quarterly 1038 periods when they apply.

Right rail shows the selected date: what is due, how many remain,
[ View package ].

"Add a date" is an admin action, not a base user action. Remove it from the
base view.

==================================================
13. ADMIN — DELETE THE FABRICATED INFRASTRUCTURE
==================================================

Remove every one of these: database heartbeat, Entra authentication service
reachability, Teams bot webhook registration, file storage quota.

A Canvas Power App over SharePoint cannot know any of that, and showing it
implies monitoring that does not exist.

Replace with configuration and data health the solution can actually observe:

  Healthy    All active Legacy requirements have scope and frequency set
  Attention  3 installations missing facility mapping
  Healthy    August generation completed for 87 of 89 installations
  Healthy    0 duplicate expected items
  Attention  2 submissions need classification
  Healthy    Reconciliation last completed 18 minutes ago
  Attention  Reminder notifications disabled
  Healthy    September 2026 configured as the open reporting period

Three levels: Healthy · Attention · Error. Expandable plain-language detail.

==================================================
14. TABLES
==================================================

Tables are the strongest element on the page, not decoration.

Header 36px, 12px, weight 600, neutral gray, minimal uppercase. Body 13-14px,
rows 40-48px, subtle bottom rules, no zebra striping. Hover is a very slight
neutral change. Selection is a thin accent line or very pale blue. Sort icon
small, beside the header text. Actions right-aligned as text links.

==================================================
15. EMPTY STATES
==================================================

  No documents awaiting your review.
  All submissions in this view have been processed.

Small Fluent icon at most. No illustrations, no celebratory graphics.

==================================================
16. TYPE, COLOUR, GEOMETRY
==================================================

Production font is Segoe UI Variable. Use Inter only as a Figma substitute and
note it — the metrics differ and the layout must survive the swap.

  Light   bg #FAF9F8 · surface #FFF · border #D1D1D1
          text #242424 · secondary #616161 · accent #0F548C
  Dark    bg #1F1F1F · surface #292929 · border #3D3D3D
          text #FFF · secondary #ADADAD · accent #4EA0D4

Accent blue only for: primary action, active navigation, selection, links, focus
rings. No large blue areas except the launch screen.

Panel radius 2px. Input and button radius 4px maximum. No shadows. No pills. No
gradient text. No illustrations.

==================================================
17. BUILDABLE IN CANVAS POWER APPS
==================================================

Every pattern must have a Canvas equivalent. Design with auto-layout containers
throughout — no absolute positioning, no fixed X/Y.

Do not rely on: sticky positioning, CSS transitions, hover as the only way to
reach an action, custom scrollbars, arbitrary overlays, custom React components.

Hover may refine but never reveal. Any action reachable only by hovering is
unreachable in the built app and by keyboard.

==================================================
18. RESPONSIVE AND ACCESSIBLE
==================================================

Primary 1440x1024 embedded in Teams. Also 1024 and 768.

Below 800px: metric strip becomes two columns, tables become record cards,
review becomes one column, filter toolbar wraps. No horizontal scrolling on
business tables, ever.

Text contrast 4.5:1 in both themes. Visible keyboard focus on everything. No
meaning carried by colour alone. Labels always visible — never placeholder-only.
Icons that carry meaning have a text label.

==================================================
19. FRAMES TO PRODUCE
==================================================

Base Home · Base Home with a correction outstanding · Submit · My Package ·
AFSVC Overview · Review queue · Review returning for correction · Installation
workspace · Calendar · Admin health · Empty state · Base Home at 768 · Review at
768 · Dark AFSVC Overview.

Fourteen frames. Do not produce more.

==================================================
20. THE BAR
==================================================

A base DFAC manager understands in five seconds: which month, what is required,
what is missing, what was accepted, what came back, what to do next.

An AFSVC manager understands in five seconds: how many need review, who is late,
what corrections are outstanding, and how to open the evidence.

Do not make it prettier by adding anything. Make it clearer by removing.
```

---

## What I changed from the previous draft, and why

**Cut roughly in half.** Twenty sections instead of twenty-seven, and the
surviving ones are shorter. Sections 1, 2 and 13 of the original said the same
thing about visual discipline three times; generation tools respond to that by
splitting the difference rather than by trying harder.

**Fixed a document error.** The previous draft listed "1119 — Field Feeding /
Daily Feeding Summary" *and* "1119-1 — Field Feeding". The 1119-1 is the field
feeding form; the 1119 is the feeding summary. Conflating them would have
produced a prototype that mislabels the most important document in the package.

**Made the amber/yellow rule crisp.** The previous draft said awaiting review
should be "yellow / amber family, visually distinguishable from late through
text and icon". That is the collision, restated as a solution. They are
different hues or the rule does not hold.

**Named the placeholder content to delete explicitly.** "Replace generic
placeholder requirements" leaves the tool to decide what counts as generic. The
current build contains nine specific fictional requirements and four USAFE
installations; listing them by name is the difference between a rewrite and a
partial one.

**Added the font warning.** The build loads Inter from Google Fonts. On a .mil
network that CDN may be blocked, and Power Apps gives you Segoe UI Variable
natively. Their metrics differ enough that a layout tuned to Inter reflows on
the swap. Better to know now.

**Added the hover rule.** "Hover may refine but never reveal." The original said
to avoid hover-dependent patterns; this states the testable version.

**Capped the frame count.** Fifteen became fourteen with "do not produce more".
Without a cap these tools generate variants nobody asked for and the component
library drifts.
