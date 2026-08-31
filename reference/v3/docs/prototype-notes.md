# Prototype — what it demonstrates, and what changed

`docs/mf-operations-prototype.html` is a single file with no dependencies. It is
the executable specification for the status engine, the security model and the
information architecture. Codex should port its domain boundaries, not its
markup.

## No sign-in

On the network CAC identifies the user before the app loads. There is no login
screen, no sign-in button, and no "welcome back" state. The app resolves
identity, scope and permissions from `MF_Security_Mapping` on open, and a user
with no mapping gets a clear route to fix that — not an empty app.

The identity selector in the dark bar is **test harness only**. It does not
exist in the built app.

## Changes from the first prototype

**Upload is no longer a top-level destination.** Documents normally go into the
Portfolio Teams FY folder. Attaching through the app is a secondary action
inside the package screen, not a tab that implies it is the standard workflow.
It still declares installation, facility, requirement and period at upload, so
an attached document needs no classification — that decision stands.

**One status engine.** `itemStatus()` returns
`{status, code, label, actionOwner, actionRequired}` from a single evaluation.
The previous build had two parallel decision trees, which is how a status engine
starts lying.

**Five visual states.** Blue separates *not due yet* and *informational* from
*not applicable*. The old four-state model displayed an installation whose
requirements simply had not come due as "Not applicable".

**Package rollup runs over semantic statuses.** `[ACCEPTED, NOT_DUE, NOT_DUE]`
is now IN PROGRESS. The old colour rollup called it Complete.

**Wrong document is no longer permanently red.** It means the requirement is
unmet; urgency depends on the suspense date. Before the due date it is
NOT_SATISFIED (amber), after it is OVERDUE (red).

**Action ownership drives Home.** Amber covers both *correction needed* (the
facility's action) and *awaiting review* (AFSVC's). A submitter's "needs your
attention" list no longer contains documents sitting in someone else's queue —
those appear under *Waiting on AFSVC*.

**Security leak fixed.** A facility-scoped user previously received an
installation package rollup computed from every facility at that base. Rollups
now run over what the viewer may see. A contract-scope item is visible only when
the contract actually covers a facility in their scope.

**Home is role-shaped.** A DFAC manager sees their facility, what needs doing,
what is waiting on AFSVC, and what was accepted — no portfolio arithmetic. A
Portfolio Manager sees the portfolio. Navigation follows permissions: three tabs
for a facility user, six for an admin.

**Period selector in the app chrome.** Changing it re-renders everything, which
removes most of the reason History existed as a destination. History became
Activity — business events, stamped with the app version.

**Classification uses progressive disclosure.** Confidence first, Confirm or
Change, dropdowns only on request. Cascading works: choosing Creech no longer
offers Lackland's facilities, and requirements filter to the chosen facility's
operating model.

**Configuration health check.** Missile Field MAF runs MAFFO/MAF and no seeded
requirement matches that model, so it generates nothing. Previously it rendered
an empty package and read as compliant. Admin → System health now surfaces it as
a configuration warning. Open the Admin tab as K. Sandoval to see it.

**Provisional requirements are demoted for normal users.** They show as
Informational. The UNVERIFIED label and its authority reference live in Admin,
where governance language belongs.

**Code is organised by domain.** `/domain` (statusEngine, requirementEngine,
securityEngine, dateUtil), `/services`, `/ui`, `/state`. One delegated event
handler on the document instead of rewiring the DOM on every render. Canvas
Power Apps will not use JS modules, but Codex must preserve these boundaries as
components, named formulas and flows.

**Dates go through one utility.** Comparisons slice to `YYYY-MM-DD` first, so a
timestamp on `Uploaded_DateTime` cannot leak into a day number.

## Worth exercising

| Try | Shows |
|---|---|
| T. Alvarez → Home | Facility-shaped home, three tabs, no portfolio numbers |
| Change date to 5 Sep, then 20 Sep | NOT_DUE → OVERDUE, blue → red |
| D. Reyes → Home | "Needs your attention" holds reviews; corrections sit under Waiting |
| Minot SIK, as D. Reyes | Wrong document, past due, shows Overdue not a stuck red flag |
| Lackland SIK | Two versions, v1 returned, correction comment retained |
| Review → Return for correction | Comment and suspense appear only when relevant |
| Exceptions → scan_0091.pdf | Unresolved confidence routes straight to manual |
| Exceptions → Change classification | Cascade filters facilities and requirements |
| K. Sandoval → Admin | Missile Field MAF configuration warning |
| Narrow the window | Tables become cards |
