reference the QRG for all installation/naming data and the logo (AFSVC Shield) attached... AFSVC MISSION FEEDING — LANDING SCREEN REDESIGN

Two files are attached. Use both as authoritative.

  QRG\_\_Scrubbed\_.csv  (below)  every installation, facility, portfolio, MAJCOM,
                        feeding type, program type, contract type and prime
                        vendor. Invent no name that is not in this file.

  AFSVC shield          the Air Force Services Center emblem. Reproduce it
                        unaltered — no recolour, no crop, no rotation, no
                        effects, not inside another shape, never on a gradient
                        or a photograph, never as a background watermark.
                        Clear space on all sides equal to a quarter of its
                        height. Never below 24px.

==================================================
REPLACE THE CURRENT LAUNCH SCREEN
==================================================

Delete the two role tiles ("Portfolio Manager" / "Facility Manager") and their
Start links. Delete the four ghost screenshot panels on the right. Delete the
"FOUO" marking in the footer.

Role is never chosen. The user arrives already identified by CAC, and their role
and installation scope come from the access mapping. A screen that asks someone
to pick a role is a role selector, and a role selector on the front door is an
access bypass wearing a friendly face.

--------------------------------------------------
LEFT — identity
--------------------------------------------------

AFSVC shield, 96-120px tall, on the plain deep navy field. Beneath it:

  AFSVC Mission Feeding                    48px, weight 300, white
  DAF Mission Feeding monthly document     16px, weight 400, 90% white
  tracking and submissions
  AFSVC/VMF                                14px, 70% white

Then a single primary action:

  [ Enter ]

One button. Full stop. No secondary link, no "learn more", no tagline.

--------------------------------------------------
RIGHT — the current cycle, not screenshots
--------------------------------------------------

Replace the four grey placeholder panels with one panel showing what is actually
scheduled. This is the reason to have a landing screen at all: the user learns
where they stand before they click.

Light surface, 2px radius, 1px border, on the navy field. No shadow.

  AUGUST 2026 EOM

  31 Aug    Reporting period closed
  5 Sep     Initial suspense              ← today marker sits here when relevant
  10 Sep    Final call

  Your package         4 of 5 submitted
  [thin progress bar]

  1 awaiting AFSVC review · 1 not yet submitted

The three dates are a compact vertical timeline with a thin rule connecting
them. Past dates are muted, the next one is emphasised, future ones are normal
weight. No calendar grid — this is a cycle, not a month.

Content varies by who is looking, resolved before the screen renders:

  base user       their installation's package counts
  AFSVC user      portfolio totals — "38 of 43 installations complete"
  unmapped user   the dates only, no counts, and Enter leads to the No Access
                  screen

If the reporting period has no data yet, show the dates and omit the counts
entirely. Do not render an empty progress bar.

--------------------------------------------------
FOOTER
--------------------------------------------------

  Version 0.6.0 · August 2026

Nothing else. No "FOUO" — that marking is superseded by the CUI programme, a
legacy marking is not equivalent to a CUI designation, and Mission Feeding EOM
tracking has not been designated CUI. A decorative sensitivity marking is a
policy error, not a design detail.

--------------------------------------------------
AFTER ENTER
--------------------------------------------------

Enter goes straight to Home. Which Home depends on the access mapping:

  installation scope    base Home — three tabs, their facility only
  portfolio scope       AFSVC Home — portfolio totals and the review queue
  enterprise scope      AFSVC Home with the installation directory
  no mapping            No Access

The navigation tabs are already filtered to the role by the time the user sees
them. Nobody is offered a tab they cannot use, and nothing is hidden behind a
disabled control.

--------------------------------------------------
DARK THEME
--------------------------------------------------

The landing screen is already dark. Remove the "DARK THEME" toggle from it — a
theme switch belongs in the app shell, not on the front door, and the navy panel
does not have a light variant --- and then add the security framework/items as needed: SECURITY STATES — MISSION FEEDING OPERATIONS

Add these to the existing build. Do not redesign anything.

1. NO SIGN-IN, EVER
No login screen, no password field, no PIN, no "select a user" control, no
simulated CAC prompt. The user is already identified. The role selector in the
prototype is a test harness and must be visibly labelled as one — a dark strip
outside the app frame, never a control inside it.

2. FAIL-CLOSED SCREENS — three new frames
Design these as ordinary, calm screens. They are not errors.

  NO ACCESS
    "Your account isn't mapped to an installation yet."
    [ Request access ]  [ Contact your Portfolio Manager ]

  SCOPE UNRESOLVED
    "We couldn't verify which installation you work at."
    Reference: MF-20260831-A7F4
    [ Request access ]

  CONFIGURATION REQUIRED  (admin only)
    "This environment hasn't been configured yet."
    A checklist of what is unset. No data visible anywhere on the screen.

None of these shows a portfolio total, an installation name, or any record.
Failing closed means showing nothing, not showing a locked-looking dashboard.

3. REQUEST ACCESS FLOW — one frame
  Installation [ search ] · Reason [ text ] · Needed until [ date ]
  "Your Portfolio Manager will review this."
Plus a pending state on the No Access screen: "Requested 2 Sep · awaiting
review."

4. ERROR MESSAGES CARRY NO INTERNALS
Never show an HTTP status, a URL, a GUID, a token, a connector name or a stack
trace. The pattern is:

  We couldn't save your submission. No data was changed.
  Reference: MF-20260831-A7F4

The reference is selectable so a user can quote it. That is the only technical
element on screen.

5. ADMIN HEALTH SPLITS IN TWO
Two sections with a visible divider and different treatment:

  APPLICATION HEALTH — things the app observes
    3 installations missing facility mapping
    August generation completed for 41 of 43 installations
    2 submissions need classification

  TENANT SECURITY — things the app cannot observe
    Power Platform DLP        Requires tenant admin verification
    Tenant isolation          Requires tenant admin verification
    Purview audit retention   Requires tenant admin verification
    SharePoint permissions    Requires tenant admin verification

Tenant rows are neutral gray with no status chip. Never render them "Healthy" —
a fabricated green there is worse than no row at all.

6. ENVIRONMENT BANNERS
A thin full-width strip above the top bar, only when not normal production:

  PILOT ENVIRONMENT
  READ ONLY — MAINTENANCE

Neutral background, dark text, no icon, no colour alarm. Nothing in normal
production.

7. CUI BANNER COMPONENT — designed, rendering nothing
Build cmpInformationBanner with a blank marking string and show it in the
component library only. Do not place it on a screen. Do not invent a marking.
Most Mission Feeding information is not CUI, and a decorative CUI banner is a
policy error, not a design flourish.

8. THINGS THAT MUST NOT APPEAR
No DoDAAC, DoDAAD, account number, fund cite, contract identifier, org box,
personal contact detail or CAC identifier — not populated, not as an empty
labelled row, not as a lock icon, not as a note. If the value cannot be shown,
the row does not exist.

No external fonts. The build currently loads Inter from Google Fonts; that CDN
is a release blocker. Production font is Segoe UI Variable — note Inter as a
Figma substitute in the file, not as a dependency.

9. FRAMES TO ADD
No Access · Scope Unresolved · Configuration Required · Request Access ·
Admin Health with the tenant split · Read-only banner state.

Six frames.