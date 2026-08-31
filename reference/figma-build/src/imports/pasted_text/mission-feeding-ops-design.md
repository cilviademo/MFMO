Design a desktop enterprise application UI called "Mission Feeding Operations".
It is a U.S. Air Force document-tracking system that runs embedded inside
Microsoft Teams. Design at 1440x1024. Build a light theme and a dark theme.

AUDIENCE AND TONE
Government operations staff using this forty times a month. Serious,
information-dense, unglamorous. It should read as infrastructure, not as a
product launch. Reference point: IBM Cognos Analytics — sharp rectangles,
hairline rules, large light-weight headings, generous whitespace, restrained
colour. Combine that density with Microsoft Fluent 2 controls so it sits
naturally inside Teams.

TYPE
Segoe UI Variable, or Inter as a substitute.
Display 48/1.1 weight 300. Page title 32/1.2 weight 300.
Section 20/1.3 weight 600. Body 14/1.5 weight 400.
Label 12/1.4 weight 600 uppercase, letterspacing 0.04em.
Meta 12/1.4 weight 400.
Headings get their authority from size and space, never from bold weight.

GEOMETRY
Corner radius 2px on panels, tables and cards. 4px on buttons and inputs.
Nothing is a pill. Nothing is a circle except avatars.
Borders are 1px hairlines. Use rules, not shadows. No elevation anywhere.
Spacing scale 4 8 12 16 24 40. Table rows 36px. Section gaps 40px.
Card padding 20px.

COLOUR — LIGHT THEME
Background #FAF9F8. Surface #FFFFFF. Border #D1D1D1.
Text #242424. Secondary text #616161.
Accent #0F548C used sparingly — links, focus rings, one primary button.
Status, five states, each with its own text label always visible:
  Green  #0E700E on #F1FAF1  accepted
  Amber  #8A5300 on #FFF9F0  awaiting review or correction needed
  Red    #A4262C on #FDF3F4  overdue
  Blue   #0F548C on #EFF6FC  not due yet
  Gray   #424242 on #F5F5F5  not applicable
Status is never conveyed by colour alone. Every status chip carries a text
label and a small outline glyph. The design must survive being viewed in
greyscale.

COLOUR — DARK THEME
Background #1F1F1F. Surface #292929. Border #3D3D3D. Text #FFFFFF.
Same five status hues, lightened for contrast on dark.

SCREENS TO PRODUCE

1. LAUNCH SCREEN
Full-bleed deep navy background, a flat linear gradient from #001141 to
#0043CE, left to right. Left half: the product name at 48px weight 300 in
white, with one line in italic. Below it two lines of plain description.
Beneath that, two boxy entry cards side by side, each 280x180, light surface,
2px radius, 1px border, containing a 32px outline icon, a 16px bold title, two
lines of description, and a text link reading "Start" with a right arrow.
Right half: four small screenshot thumbnails of the application stacked
vertically with generous gaps, slightly cropped at the right edge.
No photography. No illustration. No glow.

2. HOME — PORTFOLIO MANAGER
Teams-style top bar: 30px square app mark, product name, a reporting-period
dropdown reading "August 2026", and on the right the signed-in user's name,
role and a 30px circular initials avatar. Directly under the avatar, 11px grey
text reading "Identified by CAC". There is no sign-in button anywhere.
Below: a horizontal tab strip, six tabs, active tab marked by a 2px underline
in the accent colour and a weight change. One tab carries a small red count
badge.
Then a row of four metric tiles, edge to edge, separated by 1px rules rather
than gaps, no card shadows. Each tile: 12px uppercase label, 28px weight 300
number, 12px grey detail line.
Then a panel titled "Needs your attention" containing a data table with columns
Location, Requirement, Due, Status, Action owner, and a right-aligned button.
The status column holds the chips. The action-owner column holds a small
outlined tag reading either "Your action" or "With the facility".
Then a second panel titled "Installations" with a similar table.

3. HOME — FACILITY MANAGER
The same chrome but only three tabs. No portfolio metrics at all. A single
panel headed with the facility name, its operating model, and one status chip.
Two buttons: "Open my package" and "Open EOM folder in Teams". Below it, one
panel "Needs your attention" and one panel "Waiting on AFSVC". Show that this
role sees dramatically less.

4. FACILITY PACKAGE
Panel header with facility name, installation, operating model, period, and a
package-level status chip on the right. A table of requirements: Requirement,
Scope, Suspense, Status, Action owner, Action. Rows show a bold document code
with a grey full name beneath it.
Below, a second panel "Installation and contract items" with the same table.
Below that, a collapsed section "Add a submission" containing a dashed-border
drop target, a requirement dropdown, and a primary button.

5. REVIEW
Two columns. Left: a bordered document panel with the filename at 15px bold,
submitted-by metadata, and an "Open document" button; beneath it a version
history list where the current version is highlighted with a tinted background
and each row shows v1/v2, filename, date, submitter and QC state; beneath that
an amber-left-bordered note quoting the previous reviewer comment.
Right: a decision panel with four radio options in bordered rows, the selected
row outlined in the accent colour; a comment textarea; a date input; and a
primary button reading "Save decision". Show the comment and date fields
present only because a returning option is selected.

6. CALENDAR
Month grid, seven columns, 1px rules, no rounded cells. Day number top-left of
each cell in 12px. Up to three events per cell rendered as small left-accented
bars carrying an 11px label and a status colour, plus a "+2 more" link when
there are more. Today's cell has a 2px accent top border, not a filled circle.
Above the grid: month navigation arrows, a "Today" button, and a segmented
control for Month / Agenda. On the right, a 280px side panel listing the
selected day's events grouped by scope, and a secondary button reading
"Add a date".

7. ADMIN — SYSTEM HEALTH
A vertical list of check rows, each with a small status chip and a sentence.
One row is amber and expands into a bordered warning panel explaining a
configuration problem in plain language.

COMPONENTS TO PUBLISH AS A LIBRARY
Status chip in all five states, both themes. Metric tile. Data table row.
Panel with header and optional right slot. Tab strip. Period selector.
Identity block. Drop target. Version history row. Radio decision row.
Calendar day cell. Calendar event bar. Empty state. Warning panel.
Primary, secondary and subtle buttons in rest, hover, pressed, focused and
disabled states.

RULES
Every interactive element has a visible focus ring: 2px, accent colour, 2px
offset.
Text contrast at least 4.5:1 in both themes.
No purple. No glassmorphism, frosted glass or blur. No drop shadows. No pill
buttons. No emoji. No gradient text. No 3D or donut charts. No hero
illustration. No stock photography. No animated numbers.
Icons are Fluent outline style at 16px or 20px, and every icon that carries
meaning has a text label beside it.
Tables never scroll horizontally; below 800px they become stacked cards.