# Figma prompt — real registry, real scope, AFSVC identity

I profiled the CSV before writing this. Several assumptions in the earlier
directive do not survive contact with the file. Read "What the data actually
says" below before sending the prompt, because two of the numbers everyone has
been quoting are wrong.

Attach `QRG__Scrubbed_.csv` to Figma with this prompt.

---

## What the data actually says

**261 rows is not 261 facilities.** 107 of those rows are *exact* duplicates —
every column identical. Fairchild's Ross DFAC appears four times, Andersen's
DFAC three times. Deduplicated: **154 distinct rows, 153 distinct
installation-facility pairs.**

**R1 scope is 43 installations and 67 facilities, not 89 and not 107.** Only 43
installations have any Legacy row. Everything else is Food 2.0, MAFFO, Deployed
/ Field Feeding, or unassigned, and none of those generate an EOM package in R1.

**Four bases are split into two installation rows each** by program:
`EGLIN AFB` / `EGLIN AFB (2.0)`, and `(2.0)` / `(MAF)` pairs at FE Warren,
Malmstrom and Minot. So 107 installation strings resolve to **103 physical
installations**. This is the enterprise modelling a mixed base as two
installations rather than one base with facilities of different operating
models — which is the opposite of how the schema handles it.

**Six joint bases use surname-first naming:** `CHARLESTON, JB`,
`ELMENDORF, JB`, `HICKAM, JBP`, `LANGLEY, JB`, `MCCHORD, JBL`, `MCGUIRE, JB`.
JBSA Lackland does not — it is `JBSA LACKLAND`.

**JB Lindsey Graham is Food 2.0.** The Charleston row is `CHARLESTON, JB |
Gaylor DFAC | PORTFOLIO 4 | Food 2.0`. It is out of R1 scope and appears only in
enterprise views, so the rename matters for the directory and search, not for
any base-user screen.

**Legacy facility counts per installation:** 28 bases have one, 10 have two,
three have three, one has four, and JBSA Lackland has six. Multi-facility is
common enough that the design must handle it, and single-facility is the
majority case that must stay simple.

**Portfolio 4 carries 104 of 261 rows.** Twenty rows have no portfolio at all.

**POS TERMINALS is free text**, as expected: `Six Hats – 3 (1 inop)`,
`Reef – 2 Riptide – 2`, `Offline (2)`, `Joshua Tree – N/A`.

---

## The prompt

```
MISSION FEEDING OPERATIONS — REAL REGISTRY AND AFSVC IDENTITY

This supersedes all fictional data in the current build. Delete Ramstein's demo
rows, Spangdahlem, 86th Airlift Wing, 31st FW and "AAFES Contractor-Operated"
wherever they appear as invented examples.

Every installation, facility, portfolio, MAJCOM, feeding type, program type,
contract type and prime vendor comes from the attached QRG CSV. Invent nothing.
If a name is not in the file, it does not appear in the design.

==================================================
1. AFSVC IDENTITY
==================================================

The Air Force Services Center emblem appears on the landing screen and as the
application mark throughout. Source it from
https://www.afimsc.af.mil/Units/Air-Force-Services-Center/

Rules, because this is an official DoD organizational emblem:

- Reproduce it unaltered. Do not recolour, restyle, flatten to a single colour,
  crop, rotate, add effects, or place it inside another shape.
- Place it on a plain white or plain neutral field. Never on a gradient, never
  on a photograph, never as a translucent background watermark.
- Clear space on all sides equal to at least a quarter of its height.
- Landing screen: 96-120px tall, above the product name.
- Application top bar: 28-32px tall, left of the wordmark.
- Never scale it below 24px — the detail becomes illegible and it reads as a
  smudge.
- It is the organization's mark, not the product's. Do not treat it as an app
  icon, do not animate it, do not use it as a loading indicator.

The product wordmark sits beside or beneath it as ordinary type:

  Mission Feeding Operations
  Air Force Services Center

Set in the interface typeface at normal weight. No custom lettering, no logo
lockup, no tagline.

==================================================
2. THE DATA, ACCURATELY
==================================================

261 rows, of which 107 are exact duplicates. 154 distinct rows. 153 distinct
installation-facility pairs. 107 installation strings resolving to 103 physical
installations. 4 portfolios. 14 MAJCOMs.

Feeding type: 144 Legacy, 69 Food 2.0, 22 Deployed / Field Feeding, 6 MAFFO,
20 unassigned.

R1 EOM scope is Legacy only: 43 installations, 67 facilities.

Do not show 261 anywhere as a facility count. Show 153, or show the
deduplicated count the file yields, and surface the duplicates in admin.

==================================================
3. NAMING — MATCH THE SOURCE, NORMALIZE THE KEY
==================================================

Display exactly what the CSV says. The key is derived and never shown.

  Display                    Key
  JBSA LACKLAND              JBSA_LACKLAND
  ALTUS AFB                  ALTUS_AFB
  AL UDEID AB (AUAB)         AL_UDEID_AB
  RAMSTEIN AB                RAMSTEIN_AB

Six joint bases are stored surname-first and must display in natural order while
remaining findable either way:

  CHARLESTON, JB   ->  JB Charleston      key JB_CHARLESTON
  ELMENDORF, JB    ->  JB Elmendorf
  HICKAM, JBP      ->  JBP Hickam
  LANGLEY, JB      ->  JB Langley
  MCCHORD, JBL     ->  JBL McChord
  MCGUIRE, JB      ->  JB McGuire

Search must match both forms. A portfolio manager typing "Langley" and one
typing "JB" both find it.

**JB Charleston is now JB Lindsey Graham.** Display the new name; keep the old
one as a searchable alias and show it once as small secondary text in the
installation workspace header and in search results:

  JB Lindsey Graham
  formerly JB Charleston

It is a Food 2.0 location, so this appears only in enterprise views. No base
screen shows it.

Facility key is installation key, pipe, facility slug:

  JBSA_LACKLAND|GATEWAY_DFAC
  ANDERSEN_AB|DFAC

==================================================
4. FOUR BASES ARE SPLIT — SHOW BOTH TRUTHS
==================================================

The source models mixed bases as separate installations:

  EGLIN AFB and EGLIN AFB (2.0)
  FE WARREN AFB (2.0) and FE WARREN AFB (MAF)
  MALMSTROM AFB (2.0) and MALMSTROM AFB (MAF)
  MINOT AFB (2.0) and MINOT AFB (MAF)

In the installation directory, show them as the source has them — do not
silently merge, and do not present a base twice with no explanation. Group the
pair under the physical base with a small note:

  MINOT AFB
  2 program records · Food 2.0, MAFFO

Design one frame showing an expanded pair, so it is clear the interface handles
this rather than hiding it.

==================================================
5. WHAT DRIVES BEHAVIOUR
==================================================

  Legacy                    generates the R1 EOM package
  Food 2.0                  enterprise and admin views only
  MAFFO                     visible, no package
  Deployed / Field Feeding  visible, no package
  unassigned                visible, flagged in admin, no package

A Food 2.0 installation with no EOM package is correct. Its EOM Status column
reads "Not in R1 scope" in neutral gray — never "Missing", never red. Sixty-nine
rows must not look like a failure.

Program type is preserved verbatim: Legacy - SB, Legacy - LN, Legacy - RSA,
Legacy - BOS, Legacy - LN - No ESM - No Dorms, Legacy - AB1 (No NAFs),
Food 2.0 - AB1, Food 2.0 - In Development. Never simplify these. They appear in
installation workspace, facility detail, AFSVC filters and admin only.

==================================================
6. WHAT EACH ROLE SEES
==================================================

BASE USER sees their installation and nothing about the enterprise. No
portfolio, no MAJCOM, no program type, no contract type, no prime vendor, no POS
terminals, no POC. Installation is pre-filled. The submission screen asks for
installation, period, requirement, file, optional note — the system knows the
rest.

Twenty-eight of the 43 Legacy bases have exactly one facility. For those users
the facility selector should not appear at all.

AFSVC USER sees the enterprise: portfolio, MAJCOM, feeding type, program type,
contract, prime vendor as filters and columns.

==================================================
7. INSTALLATION DIRECTORY
==================================================

A working directory, not a dashboard. One dense table:

  Installation · Portfolio · MAJCOM · Location · Feeding Type · Facilities ·
  Contract · Prime Vendor · EOM Status

Filter toolbar above it, controls 32px:
search · Portfolio · MAJCOM · Feeding Type · Program Type · Contract Type ·
Status · Reset

103 rows needs sortable headers, pagination or virtual scroll, and a result
count: "103 installations · 24 shown".

==================================================
8. INSTALLATION WORKSPACE
==================================================

  JBSA LACKLAND
  Texas (TX) · AETC · Portfolio 2

  Legacy · Legacy - RSA · 502 FSS · Full Food Service · [prime vendor]

Sections: EOM Package · Facilities · Activity · Access.

Facilities is a table, not cards. Lackland has six Legacy facilities; cards
would push the EOM package off the screen. Columns: Facility · Designation ·
Unit · Feeding Type · Program · POS Terminals · EOM Status.

==================================================
9. FIELDS THAT NEED CARE
==================================================

POS TERMINALS is free text: "Six Hats – 3 (1 inop)", "Reef – 2 Riptide – 2",
"Offline (2)", "Joshua Tree – N/A". Render as text, left-aligned. Never sum it,
never right-align it, never make it a metric.

DESIGNATION is "N/A" in 223 of 261 rows. When it is populated it says COCOM HQ,
SILVER FLAG, MAFFO or AFSOUTH. Show it only when present. Do not render a row
reading "Designation: N/A".

CONTRACT TYPE is absent in 46 rows. Same rule.

POC is a display name in facility detail for AFSVC and admin only. It is not an
identity, not a permission, not an email. Do not derive a mail link from it. Do
not show it to base users.

==================================================
10. FIELDS THAT ARE NOT IN THE SOURCE
==================================================

DoDAAC, DoDAAD, accounting strings, fund cites, account numbers, contract
identifiers, org boxes, personal contact details, CAC or EDIPI.

Omit them from the design entirely. No labelled empty row, no dash, no lock
icon, no explanatory note. A labelled blank reads as missing data and sends
someone looking for it.

==================================================
11. INCOMPLETE DATA, SHOWN HONESTLY
==================================================

Never silently fill a blank. Twenty rows have no portfolio; they are unassigned,
not Portfolio 1.

In AFSVC tables a missing value renders as "Not assigned" in secondary text.

Admin registry health, computed from the file, not hardcoded:

  103 installations · 153 facility records · 261 source rows
  Exact duplicate rows                107
  Portfolio assigned                  241 of 261
  Feeding type assigned               241 of 261
  Contract type assigned              215 of 261
  Program records needing review       20
  Bases split across program records    4

Drill-downs: duplicate rows · missing portfolio · missing feeding type · missing
contract type · split installations · unmapped feeding model.

Base users never see any of this.

==================================================
12. SELECTORS AT THIS SCALE
==================================================

103 installations rules out a plain dropdown for enterprise users. Search-first
combo box: type to filter, up to eight results, each showing
"JBSA Lackland · Texas (TX) · Portfolio 2" so similar names are
distinguishable.

Base users get a static label or a two-to-three item selector.

==================================================
13. REPRESENTATIVE DATA FOR FRAMES
==================================================

Use real rows, the same ones across every frame:

  single-facility Legacy base       ANDERSEN AB (Legacy, PACAF, Portfolio 1)
  multi-facility Legacy base        JBSA LACKLAND (6 Legacy facilities)
  Food 2.0, enterprise view only    ALTUS AFB (Portfolio 2, AETC, Aramark)
  the rename case                   JB Lindsey Graham, formerly JB Charleston
  split base                        MINOT AFB (2.0) and MINOT AFB (MAF)
  duplicate rows, admin frame       FAIRCHILD AFB Ross DFAC, 4 identical rows

Base-user frames use JBSA Lackland or Andersen. Never populate a screen with all
103.

==================================================
14. FRAMES
==================================================

Update with real data: Base Home · Submit · My Package · AFSVC Overview ·
Review · Calendar · Admin health.

Add: Landing with AFSVC emblem · Installation Directory · Installation
Workspace · Facility Detail · Registry Health.

Twelve frames. Do not produce more.

==================================================
15. UNCHANGED FROM THE CURRENT BUILD
==================================================

Keep: 2px panel radius, 4px controls, 1px hairline borders, no shadows, no
floating cards, restrained accent (#0F548C light, #4EA0D4 dark), light-weight
large headings, compact tables, six status states with text and icon, dark theme
as a token swap.

Production font is Segoe UI Variable. Inter is a Figma substitute only.

==================================================
16. THE BAR
==================================================

The application should read as though it knows this enterprise. A base user
never meets the data model. An AFSVC manager goes from enterprise to a single
submission version without touching a manually maintained mapping.
```

---

## Two things worth deciding before this goes further

**The duplicate rows are a data problem, not a display problem.** 107 of 261 are
byte-identical. Either the QRG is a flattened export of something with a
finer grain that got lost, or it genuinely has duplicates. If it is the former —
say, one row per POS terminal or per meal period — then collapsing them loses
real information. Worth one look at the source before the import pipeline
dedupes them permanently. The prompt tells Figma to show 153 and surface the
duplicates in admin, which is safe either way.

**The four split bases contradict the schema, and the schema is right.** Minot
appearing as `MINOT AFB (2.0)` and `MINOT AFB (MAF)` is the enterprise encoding
"one base, two operating models" into the installation name because it had
nowhere else to put it. `MF_Facility.Operating_Model` is exactly that place.

I would not fix this in the import — keep the source strings as-is for R1, carry
the physical base as an alias, and let the crosswalk hold both. But it is worth
knowing that the QRG's installation column is doing two jobs, and that is why no
installation in the file appears to have mixed feeding types when the enterprise
plainly does.

If you want, send me the word and I will generate `configuration/installations.csv`,
`configuration/facilities.csv` and `configuration/qrg-data-quality.csv` from this
file, plus `docs/qrg-registry-mapping.md` documenting every normalization rule.
I have the data loaded.
