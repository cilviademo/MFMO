Screens look good. Six defects first — two are real bugs, not cosmetics.

## Bugs

**SF 1080 shows Overdue and should show Late.** The landing screen says three days until the 10 Sep final call, so today is ~7 Sep — past the initial suspense, before the final call. That's **amber / Late**, not red / Overdue. The six-state model isn't wired into the package table.

**"Weekend — no action" is on Monday 7 September.** Sep 7 2026 is a Monday, and Labor Day. Which surfaces the bigger miss: **5 Sep 2026 is a Saturday.** With `NEXT_DUTY_DAY`, the effective initial suspense is Tuesday 8 Sep, and nothing on any screen says so.

**The role pill overlaps the identity block** on every screen, hiding "Base Accountant, JBSA Lackland" and "CAC authenticated". It also collides with the help button bottom-right.

**"Correction req."** is truncated. Say "Correction needed".

**The Submitted column shows "2 Sep — returned"** for SAIIT, mixing a submission date with a QC event in one column.

---

```
CALENDAR ON BASE HOME, AND A CALENDAR THAT GENERATES ITSELF

==================================================
1. FIX FIRST
==================================================

a. The role pill overlaps the identity block. Move it into the dark harness
   layer with the Frames pill, or shift the whole harness to a thin strip that
   does not overlay application chrome. It must never cover a real control.

b. SF 1080 renders Overdue. Today is before the 10 Sep final call, so it is
   LATE (amber). Wire the six states into the package table:
     Blue not due · Amber late · Red overdue or returned ·
     Yellow awaiting review · Green accepted · Gray not required

c. "Correction req." -> "Correction needed". No truncated labels.

d. Split the Submitted column. Submitted holds a submission date. A QC event
   goes in Status: "Correction needed · returned 2 Sep".

e. Sep 7 2026 is a Monday, and a federal holiday. Remove "Weekend — no action".

==================================================
2. NOMINAL vs EFFECTIVE DATES
==================================================

5 Sep 2026 is a Saturday. Mon 7 Sep is Labor Day. So the effective initial
suspense is Tuesday 8 Sep, and every screen currently shows only the nominal
date.

Show both wherever a suspense appears:

  Due 5 Sep (Tue 8 Sep)
  Final call 10 Sep

Nominal stays visible — policy says the 5th and leadership reads the 5th. The
parenthetical is what the user is actually held to. When the two match, show one
date and no parenthetical.

On the calendar, mark the nominal date and the effective date differently:

  Sat 5 Sep    Initial suspense (nominal)     muted, dashed left edge
  Tue 8 Sep    Initial suspense — effective   solid, amber

==================================================
3. CALENDAR CARD ON BASE HOME
==================================================

Add below the package strip, above WAITING ON AFSVC. Full width, one row,
1px border, 2px radius, no shadow.

Left 40%: a compact month grid. 28px cells, day numbers only, no event text.
Marked days carry a 3px bottom bar in the status colour. Current day gets a
2px accent top border. Header row is single letters: S M T W T F S.

Right 60%: the three dates as an agenda, each one line.

  AUGUST 2026 EOM

  31 Aug   Reporting period closed              ✓
  5 Sep    Initial suspense · effective Tue 8 Sep    passed
  10 Sep   Final call                           3 days

  [ Open calendar → ]

The next actionable date is emphasised; past dates are muted; future dates are
normal weight. A countdown appears only on the next date, never on all three.

This is a reference card, not a mini application. No navigation arrows, no view
toggle, no event creation, nothing clickable except the link.

==================================================
4. THE CALENDAR MUST GENERATE, NOT BE AUTHORED
==================================================

The period selector currently offers four hardcoded months. Replace it with a
generated range so nobody builds a month by hand ever again.

RANGE
  From FY2026 through FY2126. Selector shows a rolling window — 13 months back,
  3 months forward — with a year jump for anything further. Do not render 1,200
  options in a dropdown.

EVERY DATE IS COMPUTED FROM THE PERIOD

  Reporting period          the month itself, YYYY-MM
  Period closes             last calendar day of that month
  Nominal initial suspense  day 5 of the following month
  Nominal final call        day 10 of the following month
  Effective dates           each nominal date rolled forward to the next duty
                            day when it lands on a weekend or a federal holiday
  Fiscal year               Oct-Sep, so 2026-08 is FY26

Day 5 and day 10 are configuration values, not constants. Read them from the
requirement, do not inline them.

FEDERAL HOLIDAYS ARE COMPUTED, NOT LISTED

A hardcoded holiday table is wrong the moment it runs past its last year. All
eleven are rules:

  New Year's Day        1 Jan
  MLK Jr Day            third Monday in January
  Washington's Birthday third Monday in February
  Memorial Day          last Monday in May
  Juneteenth            19 Jun
  Independence Day      4 Jul
  Labor Day             first Monday in September
  Columbus Day          second Monday in October
  Veterans Day          11 Nov
  Thanksgiving          fourth Thursday in November
  Christmas             25 Dec

Observation: a fixed-date holiday falling on Saturday is observed the preceding
Friday; on Sunday, the following Monday.

Local non-duty days — wing down days, family days — come from a configuration
list, not from code, and are scoped enterprise, portfolio or installation.

WHAT ELSE APPEARS, BY RULE

  Quarterly       1038 in periods ending Dec, Mar, Jun, Sep
  Annual          EOY MFR and inventory in the September period
  Conditional     1119-1 only when an item exists for that period
  Submissions     from the data, dated when they happened
  Corrections     correction suspense dates from returned items

Nothing on the calendar is typed by a person except a locally authored event.

TEST IT WITH THESE

  2026-08   suspense Sat 5 Sep -> effective Tue 8 Sep (Mon 7 is Labor Day)
  2026-12   suspense Sat 5 Jan? -> verify; 1038 quarterly also lands
  2027-09   EOY requirements appear
  2030-05   suspense 5 Jun 2030 is a Wednesday, no roll
  2100-02   the algorithm still works, no table lookup

If the last one fails, the holidays were listed rather than computed.

==================================================
5. CALENDAR SCREEN — TWO CHANGES ONLY
==================================================

a. Period selector uses the generated range described above.
b. Distinguish nominal from effective suspense as in section 2.

Everything else on that screen is fine. The right detail rail, the thin event
bars and the Month/Agenda toggle all work.

==================================================
6. FRAMES
==================================================

Update: Base Home (with the calendar card) · My Package (six states, split
column) · Calendar (generated period, nominal vs effective).

Add: Base Home at 768px showing the calendar card stacked below the package
strip.

Four frames.
```

**One thing worth deciding:** `NEXT_DUTY_DAY` currently pushes a Saturday suspense to Tuesday when Monday is a holiday — a three-day slip. If the intent is that people should file by Friday instead, the policy is `PREVIOUS_DUTY_DAY` and it's a one-cell change in `MF_EOM_Requirement`. The schema supports both; the seed assumes forward.