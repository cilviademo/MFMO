# Build notes — programme answers, 26 Aug 2026

Twenty questions answered by the programme. This file records what is now
settled, what changed as a result, what is deferred, and the two contradictions
that need a ruling.

Everything here overrides earlier assumptions in the handoff.

---

## Read this first: two contradictions

**1. SIK is missing from the confirmed EOM list.**

Earlier discussion named 1119, 1119-1 and **SIK** as verified current
requirements for Legacy and MAFFO. The confirmed EOM document list is:

> 1119, SF 1080, SAIIT, GPC Purchases (bank statements), 1119-1, 1038 (quarterly)

No SIK. No DAF 79. And SF 1080, SAIIT and GPC — none of which were previously
treated as Legacy monthly requirements — are all in.

I have **not** silently dropped SIK. `REQ-007` is seeded **inactive** with the
discrepancy recorded in `Authority_Reference`. One of the two statements is
wrong and the programme should say which before the first generation run. If SIK
is real and inactive, 89 installations stop being asked for it. If it is not
real and active, every base goes red on a document that does not exist.

**2. Scope is proposed, not confirmed, for four of the six.**

The list says *what*, not *at what grain*. My proposals, each marked PROPOSED in
the seed:

| Document | Proposed scope | Reasoning |
|---|---|---|
| 1119 | Facility | The form initialises one facility and one month |
| 1119-1 | Facility | Accompanies the facility 1119 |
| SAIIT | Facility | Inventory accountability is tied to the operation |
| GPC bank statement | Facility | The card is normally held at the operation |
| SF 1080 | Installation | Reimbursement is normally consolidated |
| 1038 | Installation | Quarterly, and administrative rather than operational |

Getting these wrong is not cosmetic: facility scope on a three-DFAC base means
three expected rows and three uploads; installation scope means one. **Confirm
before the first generation run**, because changing scope after items exist
means regenerating a period.

---

## Settled

### Suspense — now concrete

**First suspense: 5 days after month end. Final call: the 10th.**

This replaces the placeholder 10th-of-month and it is a structural change, not a
value change. `Due_Day` and `Final_Due_Day` both live on the requirement and
both generate onto the item. Between the two dates an item is **LATE** (amber),
not OVERDUE (red).

That middle window is the only week in the cycle where a reminder still
changes the outcome. Collapsing it into one red state throws that away.

### On-time is two facts

Both stored. Uploaded 8 Sep → returned 9 Sep → corrected 13 Sep is *submitted on
time* and *evidence late*. Show the first to the base and the second to
leadership. `Initial_Submission_On_Time` and `Final_Acceptance_On_Time`.

### Security — CAC and GAL, not provisioning

Nobody is provisioned for their own base. CAC identifies the user, the GAL gives
their installation, and **anyone at Lackland can view and edit all Lackland EOM
submissions regardless of unit**. That is the model.

This substantially simplifies the earlier design and dissolves the facility
rollup leak — installation is the unit of access, so a facility-scoped rollup is
no longer something to defend.

The exception path is `MF_Access_Request`, modelled on how Teams handles a
request to join: someone who PCS'd but still owes their losing base a package
requests that installation, with a justification and an expiry. **Requested
access expires.** Sixty days by default. A departing member needs a handover
window, not permanent rights to a base they left.

`MF_Security_Mapping.Grant_Type` distinguishes GAL derived / Requested / Manual.

### QC — who, and what it means

Anyone with owner access to the DAF Mission Feeding Teams (AFSVC/VMF) can QC
**all four portfolios**. Base users see only their own installation's folders.

Accept means the reviewer **opened the file** — in Teams or downloaded — and
verified it is the right document, complete and correct. This is substantive
review, not presence checking. Two consequences:

- Review takes real time. Bulk-accept is therefore valuable but must never be
  the default action, and a bulk accept should be an explicit multi-select, not
  a "select all" button.
- Review throughput is a real metric. `PendingReviewAging` matters.

### QC verdicts — seven, not four

Accept · Correction Required · **Incomplete** · Wrong Document · **Wrong
Reporting Period** · **Wrong Facility** · Not Applicable. Plus **Recalled** for
a submitter withdrawing before review.

These behave like ticket tags: the base sees the specific reason in red on their
dashboard, not a generic "returned". The status engine collapses the returning
verdicts into one `RETURNED` state — the engine does not need four states to say
"it came back", but the submitter needs four reasons to know what to fix. The
reason lives on `MF_EOM_Submission.QC_Status`.

### Notifications — built now, mostly off

`MF_Notification_Rule` is a list, not code. Two rules ship **enabled**:

1. **Submission created** → the portfolio org box. Reviewers learn something
   arrived without watching a folder.
2. **Status changed** → the submitter. A base learns their document came back
   without opening the app.

Everything else ships disabled and gets tuned once the queue behaves. Every rule
has an `Enabled` toggle and a `Digest` flag, and the toggles are on an admin
screen, not in a flow.

**Digest is on by default for anything recurring.** One message per recipient
per run listing everything they owe. Per-item mail across 89 installations is
how a notification system gets muted in week one.

### Folder structure

> **Superseded on 31 Aug 2026.** The programme's answer here said one Teams
> site with four portfolio channels. It is **four separate SharePoint site
> collections**, with four different root folder names and one inconsistent
> slug. `deployment/site-bindings.md` carries the real structure; everything
> below about *what the path tells you* still holds. Kept because the reasoning
> about signals is the part that mattered and is unaffected.

Four site collections, one per portfolio. Within each: a Monthly Data Call
folder → fiscal year → month. No naming conventions anywhere, and none assumed —
which is exactly why the FY and month folders are **matched** against what is on
the site rather than constructed.

The path gives **portfolio and month**. It does not give installation. That
matters, and it resolves neatly:

```
folder path        → portfolio, reporting period
uploader's GAL     → installation
app declaration    → facility, document type
```

The uploader's GAL location is the strongest installation signal available and
it is already trustworthy, because it is the same thing driving access. That
plus an app upload means nothing has to be inferred from a filename or a
document's contents.

Food 2.0 installations currently sit under Aramark/Sodexo breakdowns and
**reorganise into Portfolios 1–4 in October**. Build for the post-October shape;
do not encode the current vendor split anywhere.

### Intake metadata

The nine-column intake metadata scheme was designed for a Power-Automate-first
build. With the app as the front door it is largely unnecessary — declared
uploads carry their own context. Keep `Source_Path`, `SharePoint_File_ID` and
`Portfolio_ID` on the submission for diagnostics; drop the rest.

### Expected checklist — yes, generate it

Confirmed. The checklist exists before any file arrives, which is the only way
to distinguish *nothing was submitted* from *the system has no record*. It also
feeds the calendar directly: every expected row is a dated event, so a base sees
what is due and when without being told.

`EOM-01 Expected Package Generator` stays.

### Who the app is for

**Base-level users first** — DFAC managers, accountants, GMs — submitting
documents. AFSVC portfolio and ops managers use the same app as a tracker.
Power BI carries the leadership COP.

This inverts the earlier assumption that the app was primarily an AFSVC tool. It
raises the bar considerably: the base experience has to be *obvious*, because
those users open it once a month under time pressure. Green / amber / red / gray
status must be legible at a glance with no training.

### Corrected versions

v1 stays in SharePoint permanently. v2 supersedes. Nothing is overwritten or
deleted. Already the design.

### Unclassified files

Confidence-first, streamlined: show what the system thinks with a confidence
level, offer Confirm / Change / Not an EOM document. Full dropdowns only on
request. Already built in the prototype.

---

## Deferred — TO-DO

**Food 2.0 package.** Deferred by decision. Framework and go-ahead are for
Legacy feeding facilities first. The Food 2.0 handbook is to be uploaded later
and its requirements added then. `REQ-010` and `REQ-011` are seeded inactive as
placeholders so the scope machinery is exercised without asserting content.

**MAFFO/MAF package.** Not addressed. No requirements seeded. A MAFFO facility
will currently generate nothing — the `MF_App_Config` health check surfaces this
as a configuration warning rather than letting it read as compliant.

**EOY.** Same flow, not a second application. It runs as requirements with
`Frequency = Annual` landing in the September period. `REQ-020` is seeded
inactive as the shape. Detail to follow.

**Installation → Facility → Operating Model dataset.** There is no trustworthy
source. CrunchTime, Aloha Enterprise and Teams all differ and none tracks what
EOM needs.

**This is the largest open dependency in R1.** The requirement engine cannot
generate anything without it. It has to be built by hand, and it should be built
once, in `MF_Installation` and `MF_Facility`, as the authoritative record — not
maintained in a spreadsheet and copied. Budget an admin screen for it, and
expect the first version to be wrong at a handful of bases.

---

## What changed in the repo

| Change | Where |
|---|---|
| Real Legacy/APF requirement matrix, 6 active | `configuration/requirements.csv` |
| SIK and DAF 79 seeded inactive with the discrepancy recorded | same |
| Two-stage suspense: `Due_Day` 5, `Final_Due_Day` 10 | `MF_EOM_Requirement`, `MF_EOM_Item` |
| LATE state between the two dates | `docs/status-calculation.md` |
| `Initial_Submission_On_Time` / `Final_Acceptance_On_Time` | `MF_EOM_Item` |
| Seven QC verdicts plus Recalled | `MF_EOM_Submission` |
| RETURNED collapses verdicts, reason preserved | `docs/status-calculation.md` |
| `Grant_Type`, `Granted_By`, `Expires_Date` | `MF_Security_Mapping` |
| `MF_Access_Request` | new list |
| `MF_Notification_Rule` | new list |
| Food 2.0 / MAFFO / EOY placeholders inactive | `configuration/requirements.csv` |

Schema is now **15 lists, 209 columns**.

---

## Before the first generation run

1. Rule on SIK.
2. Confirm scope for SF 1080, GPC, 1038, and confirm the facility proposals.
3. Build `MF_Installation` and `MF_Facility` with operating model per facility.
4. Confirm the two enabled notification rules and the portfolio org box
   addresses.
5. Confirm the 5th and the 10th are calendar days, not duty days. A weekend
   suspense with no rule produces a monthly argument.

Item 5 is small and will otherwise surface in month one.

---

# Addendum — AFSVC End of Month/Year Procedures, 31 Aug 2026

The authoritative deck resolves both open questions and corrects three things.

## Resolved

**SIK is retired.** The Required Documents slide lists 1119, SF 1080, SAIIT,
Bank Statement (GPC purchases), 1119-1 and 1038 quarterly. No SIK, no DAF 79.
The discrepancy is closed against the source. `REQ-007` stays in the seed as
inactive with the reasoning recorded — a record of the decision, not a
requirement.

**Authority references are real now.** Eleven of thirteen rows moved from
UNVERIFIED to VERIFIED with citations: the AFSVC procedures deck, DAFMAN 34-131
ch 7.14, DFAC Manager Handbook 1.7.5, Storeroom Handbook 5.3.4. Only the two
deferred Food 2.0 placeholders remain unverified. **This means rule 2 of the
status engine — provisional requirements never drive Red — now applies to almost
nothing.** A missed 1119 turns red as it should.

## Three corrections

**1. The 1119-1 is FIELD FEEDING, not a 1119 continuation.**

I had it as a required monthly companion to the 1119 at every facility. The
source names it "1119-1 (Field feeding)". It is **conditional** — required only
where field feeding actually occurred in the period. It is now
`Frequency = Conditional, Required_Flag = FALSE`, and **EOM-01 must not generate
it.** Auto-generating it would put a permanent red row on every DFAC that never
ran a field feeding exercise, which is precisely the kind of false overdue that
teaches people to ignore the dashboard.

The base or the reviewer adds it when it applies. That needs an "Add a
requirement for this period" action on the package screen, scoped to
conditional requirements only.

**2. EOY is defined and is no longer a to-do.**

Two documents, both landing in the September period, both with citations:

- **EOY MFR** — the disinterested party memorandum identifying inventory
  officers, outlining inventory and physical value, signed by FSO/FSSC, copy to
  the Food Service Accountant. DAFMAN 34-131 7.14.5.
- **EOY inventory, signed last page** — to AFSVC/VMF.

Both are seeded active as `Frequency = Annual` with
`Applicable_Period_Month = 9`. Same engine, same screens, same status logic. No
second application, as intended.

Context worth knowing: the EOY physical inventory happens **30 September**,
conducted by an Inventory Officer **from outside Food Service**, assigned in
writing by the FSO/FSSC. Count sheets are signed by the inventory officer, DFAC
manager and storeroom manager. The app tracks the *submission*, not the count —
but the reviewer opening an EOY MFR should expect those signatures.

**3. ANG routes to NGB/A1X, not AFSVC/VMF.**

7.14.5 is explicit: ANG DFAC managers provide the inventory last page to
NGB/A1X. Added `MF_Installation.Component` (Active / ANG / AFRC) and
`MF_EOM_Requirement.Routing_Org`. Without this the EOY requirement sends ANG
submissions to the wrong organisation, and nobody notices until someone asks
where they went.

## A timing distinction to settle

The programme gave the EOM suspense as **5 days after month end, final call the
10th**. The source documents contain two other "5 days" that are *not* that:

- **DAFMAN 34-131 7.14.4** — the DFAC manager posts the financial period within
  5 days of the last day of the **fiscal year**. That is an EOY posting rule.
- **DFAC Manager Handbook 1.7.5.3 / SAIIT** — storeroom and DFAC management
  complete the inventory review **NLT 5 days after the inventory date**. That is
  an internal review deadline, not a submission suspense.

Three different five-day clocks. The one configured in `Due_Day` is the
programme's submission suspense. Worth confirming that is a policy the programme
sets rather than something derived from 7.14.4, because if it is derived, the
EOY suspense should key off 30 September rather than month end.

## Colour semantics changed

Adopted from the MVP direction note, and it is a genuine improvement:

```
RED     the base owns the next action   late, overdue, returned
AMBER   AFSVC owns the next action      submitted, awaiting review
GREEN   accepted
BLUE    not due yet
GRAY    not applicable this period
```

Colour now carries **ownership**, not severity. For a DFAC manager opening the
app once a month, "which rows are my problem" is the first question and this
answers it without reading a single label.

The trade is that Late and Overdue share a colour. Acceptable — both are the
base's action, the label distinguishes them, and `Days_Late` carries magnitude.
The alternative mixes ownership and severity in one channel and forces the user
to read every row.

## Mid-month inventory — noted, out of scope

DFAC Manager Handbook 1.7.5.3: inventories are completed on the **15th and the
last day** of every month. Only the month-end cycle is an EOM submission today.
`REQ-012` is seeded inactive so the requirement exists on the record if the
programme later wants mid-month visibility.

## On starting at installation grain

The MVP note recommends dropping to installation grain and adding `Facility_ID`
only where needed. I would **keep facility in the schema and seed at whatever
grain you can confirm per base** rather than collapsing it.

The source is explicit that multi-facility installations are normal — the SAIIT
slide describes transfers between a second DFAC and a flight kitchen at the same
installation — and the 1119 initialises one facility and one month. Collapsing
1119, SAIIT and GPC to installation grain would mean a three-DFAC base files one
1119, which does not match the form.

`Facility_ID` is already nullable, so nothing forces you to model every facility
on day one. Seed installation-level rows where the facility list is unknown, add
facilities as they are confirmed, and regenerate forward. That gets the
simplification without encoding something the source contradicts.

---

# Addendum 2 — rulings, 31 Aug 2026

Two of these correct the previous addendum.

## Authority and scope are separate claims

I marked eleven rows VERIFIED after the procedure deck arrived. That was
sloppy. The deck confirms **which documents are in the package**. It says
nothing about **at what grain each is filed**. Marking a scope guess as
VERIFIED because the document is verified turns a proposal into policy by
accident.

Split into two columns:

| Column | Answers |
|---|---|
| `Authority_Status` | Does this requirement exist? |
| `Scope_Confidence` | At what grain is it filed? |
| `Scope_Basis` | Why that grain — a reason, not a hunch |

Current state:

| Requirement | Scope | Confidence | Authority |
|---|---|---|---|
| 1119 | Facility | **High** | VERIFIED |
| SAIIT | Facility | **High** | VERIFIED |
| 1119-1 | Facility | Medium | VERIFIED |
| EOY MFR | Facility | Medium | VERIFIED |
| EOY inventory | Facility | Medium | VERIFIED |
| SF 1080 | Installation | **Proposed** | VERIFIED |
| GPC statement | Installation | **Proposed** | VERIFIED |
| 1038 | Installation | **Low** | VERIFIED |

`Authority_Status` gained `MANAGEMENT_RULE`, `PROPOSED` and
`RETIRED_OR_NOT_APPLICABLE`. SIK now carries the last of those with the
programme's wording, so later guidance can reactivate it without a schema
change.

**GPC moved from facility to installation.** If an installation has multiple
cardholders this may eventually need an account or cardholder grain. Hard-wiring
it to facility now would make that a schema change instead of a configuration
change.

## Amber and yellow are different states

Adopted, and it corrects the five-state model from the previous addendum.

```
BLUE     not due — the submission window is open
AMBER    past the initial suspense, final call not reached — base owns, has runway
RED      past the final call, or returned — base owns, out of runway
YELLOW   received, awaiting AFSVC review — AFSVC owns
GREEN    accepted
GRAY     not applicable this period
```

Amber means **time risk**. Yellow means **somebody else has it**. Collapsing
them tells a DFAC manager that a document they filed on time and a document they
never sent are the same kind of problem.

Six is the ceiling. A seventh would stop being scannable.

## Calendar days, with an effective date

**Baseline is CALENDAR.** The source says "within 5 days" and does not say duty
days, business days or workdays. Do not infer duty days without a citation.

The two suspenses have different standing and the model records it: 5 days after
month end is VERIFIED from the procedure language; the 10th is a
**MANAGEMENT_RULE** from the programme, not from the deck. Labelling the 10th as
source-verified would be a small lie that becomes load-bearing the first time
someone challenges it.

Every item now carries four dates — `Nominal_Due_Date`, `Effective_Due_Date`,
`Nominal_Final_Call_Date`, `Effective_Final_Call_Date` — with
`NonDutyDay_Policy` defaulting to `NEXT_DUTY_DAY` and resolved against the new
`MF_Non_Duty_Day` list (federal holidays, wing down days, scoped
enterprise/portfolio/installation).

**Status evaluation always uses effective dates. Reporting uses nominal ones.**
Leadership still sees "the 5th"; the base sees "Due 5 Sep (Mon 8 Sep)".

## EOY is partially defined, not defined

The previous addendum overstated this. Corrected in the backlog:

```
EOY — PARTIALLY DEFINED

Reuses the normal EOM workflow. September / FY close adds:
  - disinterested party memorandum (MFR)
  - final inventory / last page of inventory
  - associated EOY inventory evidence

Still to determine:
  - exact expected-row grain
  - QC checklist for EOY documents
  - whether count sheets themselves must be retained or submitted
  - EOY status and closeout rules
```

Both requirements are seeded active with citations, so the schema supports
annual requirements now. **Do not implement a complete EOY workflow until those
four are answered.**

## Registry is a dependency, not a blocker — corrected

I said the missing Installation → Facility → Operating Model dataset "blocks
R1". That was wrong, and the correction is better:

> The canonical installation/facility registry is the critical R1 configuration
> dependency. Pilot data must be populated before expected-package generation is
> enabled **for those locations**.

`MF_Installation` and `MF_Facility` become the authoritative EOM operational
registry until an enterprise source supersedes them. R1 is Legacy-only, so no
Food 2.0, Aramark, Sodexo or MAFFO reconciliation is needed first.

The mechanism that makes this real: **`MF_Installation.Generation_Enabled`.**
EOM-01 generates only where it is TRUE. A base with it FALSE reads as *not yet
onboarded*, never as compliant. `Registry_Validated_By` and
`Registry_Validated_Date` record who signed off.

Onboarding becomes: populate the base's facilities and operating models →
validate → flip the flag → the next generation run picks it up. Everything else
in the app can be built and tested against pilot bases meanwhile.

## Open ruling: is the 1119-1 conditional?

I seeded it `Conditional`, `Required_Flag = FALSE`, not auto-generated, because
the deck names it "1119-1 (Field feeding)" and auto-generating it would put a
permanent red row on every DFAC that ran no field feeding.

The scope table treats it as a normal facility requirement. These are
compatible — facility grain when it applies — but the generation question is
unresolved and I have not silently decided it. If the 1119-1 is a monthly
companion to the 1119, set `Frequency = Monthly` and `Required_Flag = TRUE`.
The note is on the row.
