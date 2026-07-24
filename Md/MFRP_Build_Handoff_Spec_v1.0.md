# Mission Feeding Reconciliation Platform (MFRP)
## Build Handoff Specification v1.0

**Target build agents:** OpenAI Codex, Claude Code
**Deliverable:** Single Excel workbook (`MFRP_v1.xlsx`), formulas + Power Query, no VBA
**Downstream targets:** Microsoft Teams/SharePoint distribution → Power BI → Envision (Palantir Foundry)
**Prepared for:** AFSVC/VMFA Mission Feeding enterprise
**Date:** July 2026

---

## 0. How to use this document

This is a complete build specification. An agent with no prior context should be able to build
the workbook from this document alone.

- **Sections 1–3** establish why the product exists and the constraints it must respect. Read
  these before writing code; several design decisions look arbitrary without them.
- **Sections 4–9** are the build specification: tab-by-tab schemas, formulas, and logic.
- **Section 10** is the build sequence.
- **Sections 11–13** are instructions for use, test cases, and acceptance criteria.

**Do not skip Section 3 (Constraints).** Several ordinary approaches — VBA macros, Python
scripts, XLOOKUP, live API connections — are prohibited in the target environment for reasons
that are not negotiable.

---

## 1. Problem statement

DAF Mission Feeding operates ~180 appropriated-fund dining facilities (DFACs) across nine
MAJCOMs. Financial and operational data for these facilities lives in at least six systems that
do not reconcile against each other:

| System | Role | Data timing |
|---|---|---|
| **Aloha Enterprise** | POS; connected to Aloha Back-of-House computers | **Real time**, drill-down capable, 21-day local redundancy if connectivity lost |
| **CrunchTime** | Inventory management; bridge to DLA/vendors/STORES | **Lagged** — receives Aloha data on delay |
| **STORES** | DLA Subsistence Total Order and Receipt Electronic System — ordering/receipt | Per-order |
| **GPC** | Government Purchase Card — commissary/alternate-source purchases | Per-transaction |
| **CIR / Connected Payments** | Collections Information Repository — payment settlement | Per-batch |
| **DFAS** | Issues SF 1080 billing (Subsistence-in-Kind); ~150+ page PDF | Monthly |

**Ground truth ordering:** Aloha Enterprise is authoritative for sales. CrunchTime is
authoritative for inventory. Where CrunchTime sales data disagrees with Aloha, **Aloha wins.**

**Known causes of CrunchTime/Aloha divergence** (these are the exception taxonomy — see §7.1):

1. Item linked incorrectly between vendor catalog and inventory system
2. Incorrect POS price
3. Voids not propagated
4. Wrong inventory adjustments

Because nothing joins these systems, base-level DFAC accountants and managers manually
transcribe the same figures onto multiple forms: AF Form 1119, AF Form 1119-1, SF 1080, SAITT
(Sales/Adjustments/Inventory/Transfers/Totals) local reports, commissary orders, GPC purchase
records, and 5-page storeroom packets.

### 1.1 Core design principle

**The forms are outputs, not inputs.**

Every form listed above is a *view* over a reconciled transaction ledger. The accountant's job
should shift from *transcribing numbers into five documents* to *reviewing five pre-filled
documents and confirming or annotating exceptions.*

### 1.2 What this workbook is

A **reconciliation engine with a thin UI**. Dashboards are a byproduct, not the product.

The workbook must serve three audiences from one file:

| Audience | What they see | Design requirement |
|---|---|---|
| A1C / DFAC-level | Their facility, task-shaped: what's due, what's red | Openable and actionable in <60 seconds with no training |
| Base FSS / accountant | Exception work queue, dollar-ranked | Drill from exception to contributing source rows |
| MAJCOM / AFSVC / HAF | Enterprise rollup, compliance status | Filter by MAJCOM/base, no line-item noise |

Depth is reached by moving right through tabs (progressive disclosure), never by learning a
different tool.

---

## 2. Regulatory and compliance basis

These are load-bearing. Formulas encode them directly.

### 2.1 Governing references

| Reference | Title | Version |
|---|---|---|
| **DAFMAN 34-131** | Appropriated Fund (APF) Food Service Program Management | 10 Oct 2023, Incorporating Change 2, 17 Jun 2025 |
| DoDI 1338.10 | DoD Food Service Program (policy) | Current |
| DoDM 1338.10 | DoD Food Service Program (procedures) | Chg. 2, 17 Mar 2025 |
| DoD 7000.14-R Vol 12 Ch 19 | Financial Management Regulation — Food Service | Current |
| AFSVC/VMFA MFM SOP v3 | Mission Feeding Manager Handbook | Mar 2026 |
| AFMAN 48-147 | Tri-Service Food Code | Current |
| AFI 33-322 | Records Management and Information Governance Program | Current |
| **GAO-22-103949** | Food Program: DOD Should Formalize... Better Track Dining Facility Use and Costs | 24 Mar 2022 |
| GAO-24-106155 | DOD Food Program: Nutrition Efforts | Jun 2024 |
| **GAO-25-107721** | Standards for Internal Control in the Federal Government ("Green Book"), 2025 Revision | Effective FY2026 |

### 2.2 The tolerance standards — CRITICAL

DAFMAN 34-131 specifies **multiple, non-identical** gain/loss tolerances. This is the single
most important fact in this document. Encode all of them; do not assume 3% universally.

| Facility / operation type | Tolerance | DAFMAN cite | Tier |
|---|---|---|---|
| DFAC food account (legacy) | **3%** of monthly earned income | para 5.13 | T-2 |
| **CAFÉ facility** | **5%** of total earned income | para 6.6 | T-2 |
| **Food 2.0** | **45% cost of goods** (margin standard, NOT a variance tolerance) | para 6.6, 3.13.3 | T-2 |
| ANG DFAC | **10%** of total earned income | para 6.6 | T-2 |
| Field feeding / exercise >1 month | 3% of total earned income | para 5.18.6 | T-2 |
| Field feeding investigation trigger | Investigate gains/losses exceeding **5%** of total income vs purchases | para 5.18.5 | — |
| NGB — UTA (1–2 day feeding) | 10% gain or loss | para 5.13.1 | T-2 |
| NGB — Annual Training (3–17 days) | 5% gain or loss | para 5.13.1 | T-2 |
| NGB — operations >17 days | 3% gain or loss | para 5.13.1 | T-2 |

**Known regulatory inconsistency (surface this, do not resolve it):** Para 5.13 states DFACs
maintain 3%; para 6.6 states CAFÉ facilities maintain 5%. Both are T-2. Which standard applies
to a given facility depends on classification, and classification is not consistently applied
across installations. The workbook must **score each facility against its declared type and
display which standard was applied**, making the inconsistency visible rather than hidden.

**Food 2.0 gap:** 45% COG is a pricing/margin standard, not a variance tolerance. A Food 2.0
site can hit 45% COG exactly and still carry large theoretical-vs-actual variance. Food 2.0
locations therefore have **no AvT-equivalent control**. Flag this in the workbook; do not
fabricate a tolerance for them.

### 2.3 Escalation ladder (DAFMAN 34-131, para 5.13.2)

Failure to maintain the required standard for **three consecutive months** triggers:

| Consecutive months out of tolerance | Required action |
|---|---|
| 1 | DFAC manager submits MFR to AFSVC/VMF with justification of deficiencies, corrective and preventive measures |
| 2 | MFR must be signed by **FSS/CC** prior to AFSVC/VMF submission |
| 3 | FSS/CC or FSS/CL investigates the account; appropriate action **including report of survey**; commander informs **MSG/CC** with summary of deficiencies and corrective actions |
| (follow-on) | MSG/CC informs AFSVC/VM of actions taken |

This escalates to O-6 level by month three. Nobody currently aggregates this enterprise-wide.

### 2.4 Reporting and inventory cadence

- **Monthly Monetary Record** submitted NLT the **10th day of every month** via AFSVC Food and
  Beverage Portal (para 5.2.5). ANG submits to NGB/A1X (para 5.2.7).
- **Physical inventories** conducted on the **15th and last day of every month** (para 7.13).
  Financial period posted **within 5 days** of each.
- **Peacetime inventory levels** recommended **no more than 25% of earned income** (para 7.16).
- **DLA catalog change report** reviewed **weekly** (para 7.8.2).
- **Delivery receipts** turned in to Food Service Accountant **within 24 hours** (para 7.3).
- **STORES blocks new orders** if receipts not processed by the **5th day** after required
  delivery date (para 7.18.5).

The ledger's natural period boundary is **semi-monthly**, not monthly. Design period keys
accordingly.

### 2.5 Product linking authority (para 7.8.1–7.8.2)

> AFSVC/VMF maintains vendor and inventory management system data. Linking of products between
> the vendor and automated inventory management system, conversions, and any requests for
> changes in products are completed by AFSVC/VMF personnel.

**Implication:** Bases cannot self-correct item links. Mis-link exceptions route to AFSVC/VMF.
The mis-link exception queue is a *headquarters* work queue, not a base one.

### 2.6 DoDAAC authority (para 1.4.10)

AFSVC/VMF manages, coordinates, approves/disapproves DAF Type of Activity Code "FT" for APF
food and beverage operations for DoDAAC(s). FSS resource managers submit DoDAAC creation and
deletion requests **through AFSVC/VMF**.

**Implication:** AFSVC/VMF is already the de facto owner of the authoritative site list. The
crosswalk registry (§5.1) formalizes a registry that is currently implicit in an approval
workflow. **This resolves the "who owns the crosswalk" governance question — it is AFSVC/VMF.**

### 2.7 Records management constraint

DAFMAN 34-131 requires records generated under it adhere to **AFI 33-322** and be disposed IAW
the **Air Force Records Disposition Schedule (RDS)** in AFRIMS. Reconciliation documents, count
sheets, and supporting documentation are explicitly named.

**Implication:** Archiving to free storage space and disposing IAW RDS must be the *same*
operation. An archive routine that deletes outside RDS windows creates a records violation.
Pull the RDS for food service records before setting archive windows.

### 2.8 Green Book 2025 framing

The 2025 Green Book revision (GAO-25-107721) is **effective beginning FY2026** — currently in
force. Key changes name **improper payments** and **information security** as required risk
considerations, and the revision **emphasizes prioritizing preventive control activities**.

Frame this workbook accordingly:

- **Preventive controls:** validated dropdowns at entry, crosswalk-enforced keys, adapter
  assertions that fail loud
- **Detective controls:** exception queue, provenance checker, compliance tracker

SF 1080 SIK billing built from hand-transcribed figures is an improper-payment exposure. For
scale reference, the closest civilian analog — USDA National School Lunch/Breakfast Program —
estimated improper payments from meal counting and claiming errors at approximately **$860
million, or 8.6% of federal program reimbursements** (GAO-09-814), with aggregation errors
(totaling counts for reimbursement) a named cause.

### 2.9 GAO open recommendation — sponsorship hook

**GAO-22-103949, Recommendation 8** is **OPEN** and assigned to the Department of the Air Force:

> The Secretary of the Air Force should establish a requirement for food program officials to
> conduct assessments of the effectiveness and efficiency of installation-wide food programs...

Status as of February 2026: the Air Force chartered a working group but has not provided
documentation of completion. **Four years open.**

**Recommendation 10** (also open, DOD-wide): establish guidance identifying specific categories
of costs for common measures such as cost per meal. DOD estimate slipped to June 2026. Align
the ledger's cost categories to anticipate this.

**Recommendation 6 (Army) — CLOSED/IMPLEMENTED** using: Food Management Assistance Teams
(FMATs) + standardized metrics (ACTION) + **an integrating dashboard**. GAO accepted this
combination as satisfying installation-wide assessment. **This is a GAO-blessed template the
Air Force can replicate.** The user conducts FMAT assessments.

---

## 3. Environment constraints — NON-NEGOTIABLE

| Constraint | Detail |
|---|---|
| **No Python on GFE** | Python is not permitted on government-furnished equipment. Build tooling may use Python; the **delivered artifact must not require it**. |
| **No VBA in this build** | VBA is sanctioned in the environment but is excluded here to avoid macro-security friction on distribution. Formulas + Power Query only. Deliver `.xlsx`, not `.xlsm`. |
| **No API keys / paid connectors** | No enterprise API keys. All ingestion is file-drop or manual entry. |
| **Cross-app portability** | Must open and calculate in Excel, LibreOffice, and Google Sheets. Use explicit cell references, **not** `[@Column]` structured references. |
| **Offline-capable** | Must function with no network. Power Query refresh requires Excel desktop (not Excel Web). |
| **CUI handling** | Funding and facility status data is likely CUI. Offline copies on GFE only. Obtain ISSM determination in writing before designing toward off-network use. |
| **Formula compatibility** | See §3.1 — several common functions are prohibited. |

### 3.1 Prohibited and required formula constructs

**NEVER USE** — these fail in the LibreOffice-based verification runtime and/or break
portability:

- `XLOOKUP`, `XMATCH`, `SORT`, `FILTER`, `UNIQUE`, `SEQUENCE` — cannot be evaluated under any
  prefix; spilling array functions have no spill metadata in openpyxl-written files, so only
  the top-left cell populates while error checks report zero errors
- `TEXTAFTER`, `TEXTBEFORE`, `TEXTSPLIT` — Excel 365 only
- Structured references (`[@Column]`) — break LibreOffice/Sheets portability
- Merged cells — break programmatic writes and sorting

**PREFER** — Excel-2007-era functions, no prefix needed:

- `SUMIFS`, `COUNTIFS`, `INDEX`, `MATCH`, `IFERROR`, `SUMPRODUCT`, `IF`, `AND`, `OR`, `N()`

**USE WITH `_xlfn.` PREFIX** if needed (openpyxl writes formulas verbatim; Excel stores
post-2007 names prefixed):

- `_xlfn.TEXTJOIN`, `_xlfn.CONCAT`, `_xlfn.IFS`, `_xlfn.SWITCH`, `_xlfn.MAXIFS`, `_xlfn.MINIFS`

**REQUIRED PATTERNS:**

- **`IFERROR` on every formula.** No naked errors reach a user-facing cell.
- **`N()` coercion** for numeric cells that may contain blank strings. This resolves
  blank-string-vs-zero issues (proven pattern from the existing AF Form 1119 engine).
- **Explicit cell references** in all cross-sheet formulas. Quote sheet names containing
  spaces: `='Ref Crosswalk'!$B$5`.
- **Guard every denominator** that can be zero.
- **No hardcoded results.** Write the formula, never the computed value.

### 3.2 Existing assets — DO NOT REBUILD

The user has already built these. Reference them; do not recreate.

| Asset | Description | Status |
|---|---|---|
| **AF Form 1119 engine** | 7-tab hardened Excel engine, SUMIFS ledger architecture, IFERROR throughout, Auto/Adjustment/Displayed override columns, shadow cross-check columns, 14-rule Validation register, Data Dictionary, Health Dashboard (GREEN/YELLOW/RED), Formula Library tab, fillable PDF export | Built, validated to the cent, **not deployed** |
| **STORES→CrunchTime catalog automation** | VBA/Excel toolchain; three-tier matching (stock number exact → base item text search → keyword via AGGREGATE arrays); unit conversion with cross-unit handling; price/conversion change detection; 5 visible tabs, 4 hidden processing sheets | Built, **not deployed** |
| **FMAT assessment tool** | Food Management Assistance Team assessment instrument | Built, **not tested/used** |
| **MF-COP Envision build plan v1.0** | 14-section spec: 20+ Ontology object types across 4 tiers, link types, 3-tier integration strategy, 9 Functions, 10 Actions, 4 Workshop modules by rank tier, 20-week phasing, 16 acceptance criteria, 3 appendices | Documented, **not started** |

**The MF-COP defines four modules this workbook must map to:**

1. **Operational Integrity** — Are systems polling, reconciling, feeding data correctly?
2. **Inventory & Cost Control** — Do expected and actual inventory align? Within tolerance?
3. **Compliance & Audit Readiness** — Is the site posting, documenting, submitting on time?
4. **Quality & Readiness** — Is the facility trained, evaluated, prepared?

### 3.3 Deployment risk — read this

Four substantial builds exist and **none has reached a base**. This is a deployment problem, not
a design problem. Build order in §10 is sequenced so the workbook is usable at every stage
rather than only at completion. **Do not reorder it to finish "cleaner" layers first.**
---

## 4. Architecture

### 4.1 Layer model

Breakage must be contained. Parsing logic and business logic never mix.

```
LAYER 0  REFERENCE    Crosswalk, tolerances, calendar, manifests
                      Hand-maintained. No dependencies.

LAYER 1  ADAPTERS     One query per source, per format.
                      Knows ONLY: how to read THIS file → emit canonical schema.
                      CONTAINS NO BUSINESS LOGIC.

LAYER 2  LEDGER       Normalized transaction table, source-stamped,
                      crosswalk-resolved. KNOWS NOTHING ABOUT FILE FORMATS.

LAYER 3  RECON        Matching rules, tolerances, exception logic.

LAYER 4  OUTPUTS      Compliance tracker, forms, dashboards, Envision mapping.
```

**Enforcement rule:** Adapters may contain no business logic. Layer 3+ may contain no
file-format assumptions. If a tolerance rule appears inside a PDF parsing query, the layering
has failed.

**Why this matters:** when DFAS changes their 150-page SF 1080 PDF format, exactly one adapter
breaks. Write `DFAS_v3` alongside `DFAS_v2`, keep both, and the ledger never notices.

### 4.2 Naming convention

Power Query query names must encode layer:

- `adapter_ALOHA_Sales`, `adapter_CT_Inventory`, `adapter_DFAS_SIK_v2`
- `ledger_Transactions`
- `recon_CT_vs_Aloha`, `recon_Purchases_vs_1080`
- `out_ComplianceTracker`, `out_SF1080`

### 4.3 Provenance model (annotation-based)

Palantir Foundry captures lineage because the platform executes every transformation — lineage
is a byproduct of execution and cannot be opted out of. Power Query has no equivalent runtime,
so this build uses **annotation-based provenance**: every row carries its own origin, and
annotations must be propagated by every transformation.

**Consequence:** miss propagation on one join and provenance silently drops. The provenance
checker (§6.3) is therefore **mandatory, not optional** — it is the only thing standing between
"we have lineage" and "we had lineage."

**Note on Microsoft-native lineage:** Purview column-level lineage for Power BI is supported
only when the source is Azure SQL Database, and Power BI's own lineage view is limited to a
single workspace. Neither covers folder-based file ingestion. Build provenance **in-band as
data columns**, not as platform metadata. This is also more portable — provenance travels with
the rows into Power BI, Dataverse, or Envision.

### 4.4 Adapter resilience requirements

Every adapter must implement all three:

1. **Anchor on labels, not coordinates.** Find rows by searching for text (`"TOTAL SIK"`) and
   taking what follows — never "row 47, column 3." Layout shifts break position-based parsing
   immediately; label-based parsing survives most reformatting.
2. **Fail loud, not silent.** Every adapter ends with assertions: row count > 0, sum of details
   equals stated total, all base codes resolve in crosswalk, date range contiguous. On failure,
   return a structured error row — never partial data. *A blank cell that should have been $40K
   is the dangerous failure.*
3. **Version-detect on read.** First step inspects the file (page count, known header string)
   and branches to the right parsing logic. Unknown format → flag for human, never mangle.

**Parallel action (not a build task):** ask DFAS/SAF whether the SIK bill is available as a data
file rather than a rendered PDF. It is almost certainly generated from a table. A one-time
request for CSV delivery eliminates the entire parsing problem and costs a staff package, not
money.

---

## 5. LAYER 0 — Reference tabs

### 5.1 Tab: `Ref_Crosswalk`

**The highest-value artifact in the entire build.** Nothing joins without it. Owner: AFSVC/VMF
(established by DoDAAC authority, §2.6).

| Column | Type | Notes |
|---|---|---|
| `DFAC_ID` | Text | **Canonical primary key.** Format: `{BASE_ID}-{NN}`, e.g. `JBSA-01` |
| `DFAC_NAME` | Text | Common name, e.g. `Gateway Inn` |
| `BASE_ID` | Text | Installation code |
| `BASE_NAME` | Text | |
| `MAJCOM` | Text | Validated list |
| `FACILITY_TYPE` | Text | **Drives tolerance selection.** Validated list — see `Ref_Tolerance` |
| `DODAAC` | Text | Per para 1.4.10 |
| `ALOHA_STORE` | Text | *Placeholder — populate from Aloha Enterprise store list* |
| `CT_SITE` | Text | *Placeholder — populate from CrunchTime site list* |
| `CIR_MERCHANT` | Text | *Placeholder* |
| `STORES_ACCT` | Text | *Placeholder* |
| `ACTIVE` | Y/N | |
| `EFF_START` | Date | Supports site renames/renumbering without losing history |
| `EFF_END` | Date | Blank = current |
| `NOTES` | Text | |

**Design notes:**
- Mark placeholder columns visually (yellow fill per §9.2) so it is obvious they await real
  identifiers.
- Effective-dating matters: when Aloha reassigns a store number, you need the old mapping to
  interpret historical rows.
- **Do not enrich.** If the source says `Holton, MI`, file that — not `Holton, MI (Newaygo
  County)`.

### 5.2 Tab: `Ref_Tolerance`

Encodes §2.2. This is the tab that makes the regulatory inconsistency visible.

| Column | Type | Notes |
|---|---|---|
| `FACILITY_TYPE` | Text | Join key to `Ref_Crosswalk` |
| `TOLERANCE_PCT` | Number | Stored as **fraction** (0.03 renders 3.0%) |
| `BASIS` | Text | `MONTHLY_EARNED_INCOME` / `TOTAL_EARNED_INCOME` / `COST_OF_GOODS` |
| `METRIC_TYPE` | Text | `VARIANCE` or `MARGIN` — **Food 2.0 is MARGIN, not VARIANCE** |
| `DAFMAN_CITE` | Text | e.g. `5.13`, `6.6`, `5.13.1` |
| `TIER` | Text | e.g. `T-2` |
| `NOTES` | Text | Flag conflicts explicitly |

**Seed rows (build these exactly):**

| FACILITY_TYPE | TOLERANCE_PCT | BASIS | METRIC_TYPE | DAFMAN_CITE | TIER |
|---|---|---|---|---|---|
| `DFAC_LEGACY` | 0.03 | MONTHLY_EARNED_INCOME | VARIANCE | 5.13 | T-2 |
| `CAFE` | 0.05 | TOTAL_EARNED_INCOME | VARIANCE | 6.6 | T-2 |
| `FOOD_2_0` | 0.45 | COST_OF_GOODS | **MARGIN** | 6.6, 3.13.3 | T-2 |
| `ANG_DFAC` | 0.10 | TOTAL_EARNED_INCOME | VARIANCE | 6.6 | T-2 |
| `FIELD_FEEDING` | 0.03 | TOTAL_EARNED_INCOME | VARIANCE | 5.18.6 | T-2 |
| `NGB_UTA` | 0.10 | MONTHLY_EARNED_INCOME | VARIANCE | 5.13.1 | T-2 |
| `NGB_AT` | 0.05 | MONTHLY_EARNED_INCOME | VARIANCE | 5.13.1 | T-2 |
| `NGB_EXTENDED` | 0.03 | MONTHLY_EARNED_INCOME | VARIANCE | 5.13.1 | T-2 |

**In the NOTES column for `DFAC_LEGACY` and `CAFE`, state the conflict plainly:**

> Para 5.13 sets 3% for DFAC food accounts; para 6.6 sets 5% for CAFÉ facilities. Both T-2.
> Applied standard depends on facility classification. Inconsistency surfaced intentionally.

**In NOTES for `FOOD_2_0`:**

> 45% COG is a pricing/margin standard, not a variance tolerance. Food 2.0 sites have no
> AvT-equivalent variance control. A site can meet 45% COG exactly and still carry large
> theoretical-vs-actual variance.

### 5.3 Tab: `Ref_Calendar`

Semi-monthly period keys per §2.4.

| Column | Type | Notes |
|---|---|---|
| `PERIOD_KEY` | Text | `FY2026-P07A` (1st–15th), `FY2026-P07B` (16th–EOM) |
| `FY` | Number | |
| `MONTH` | Number | |
| `HALF` | Text | `A` or `B` |
| `START_DATE` | Date | |
| `END_DATE` | Date | |
| `INVENTORY_DUE` | Date | 15th or last day (para 7.13) |
| `POST_DUE` | Date | `INVENTORY_DUE + 5` (para 7.13) |
| `MMR_DUE` | Date | 10th of following month (para 5.2.5) |
| `STATUS` | Text | `OPEN` / `CLOSED` |

Populate FY2025 through FY2028.

### 5.4 Tab: `Ref_AdapterManifest`

The transformation graph — the edge list. Foundry generates this automatically; here it is
hand-maintained.

| Column | Type |
|---|---|
| `QUERY_NAME` | Text (e.g. `adapter_DFAS_SIK_v2`) |
| `LAYER` | Text (`ADAPTER`/`LEDGER`/`RECON`/`OUTPUT`) |
| `SOURCE_SYSTEM` | Text |
| `INPUT_PATH` | Text |
| `OUTPUT_TABLE` | Text |
| `ADAPTER_VER` | Text |
| `OWNER` | Text |
| `LAST_CHANGED` | Date |
| `STATUS` | Text (`ACTIVE`/`DEPRECATED`/`STUB`) |
| `TEST_FILE` | Text — path to a known-good sample |
| `NOTES` | Text |

Answers the two questions that matter: *what breaks if DFAS changes format*, and *where did this
number come from*.

### 5.5 Tab: `Ref_CrosswalkVersion`

| Column | Type |
|---|---|
| `CROSSWALK_VER` | Text (e.g. `CW-2026-07-01`) |
| `EFFECTIVE_DATE` | Date |
| `CHANGED_BY` | Text |
| `CHANGE_SUMMARY` | Text |
| `ROW_COUNT` | Number |

Every ledger row stamps the crosswalk version that resolved its `DFAC_ID`. This is what lets you
detect silent mapping drift.

### 5.6 Tab: `Ref_ExceptionTypes`

The exception taxonomy, seeded from known CrunchTime/Aloha drift causes (§1).

| EXC_CODE | EXC_NAME | CATEGORY | DEFAULT_OWNER | REMEDIATION |
|---|---|---|---|---|
| `LINK_ERR` | Item linked incorrectly | CT_VS_ALOHA | **AFSVC/VMF** | Route to VMF — bases cannot self-correct links (para 7.8.1) |
| `PRICE_ERR` | Incorrect POS price | CT_VS_ALOHA | AFSVC/VMF | Pricing centrally managed (para 3.13.1, 6.4) |
| `VOID_ERR` | Void not propagated | CT_VS_ALOHA | Base accountant | Verify POS void handling |
| `ADJ_ERR` | Wrong inventory adjustment | CT_VS_ALOHA | Base DFAC manager | Review raw/finished waste entries (para 7.10) |
| `PURCH_VAR` | Purchase vs SF 1080 mismatch | PURCHASES | Base accountant | Purchase Reconciliation Worksheet (para 7.18) |
| `MISSING_SRC` | Expected source file absent | INGEST | Base accountant | Check export/upload |
| `PROV_NULL` | Provenance incomplete | INTEGRITY | Build owner | **Adapter defect — fix immediately** |
| `XWALK_UNRESOLVED` | DFAC_ID not in crosswalk | INTEGRITY | AFSVC/VMF | Add to crosswalk registry |
| `TOL_BREACH` | Out of tolerance | COMPLIANCE | FSO/FSSC | See escalation ladder §2.3 |

---

## 6. LAYER 1–2 — Ingest and Ledger

### 6.1 Adapter tabs (STUBBED — schema pending)

Create one tab per source, each with a **three-band layout**:

```
BAND 1 (rows 1-3):    Adapter metadata — ADAPTER_VER, SOURCE_SYSTEM, last run, row count
BAND 2 (rows 5-6):    MAPPING ROW — canonical name in row 5, source column name in row 6
                      ← THIS IS WHERE REAL HEADERS GET DROPPED IN (yellow fill)
BAND 3 (rows 8+):     Data landing area
```

Tabs to create: `Adapter_Aloha`, `Adapter_CrunchTime`, `Adapter_STORES`, `Adapter_GPC`,
`Adapter_CIR`, `Adapter_DFAS1080`, `Adapter_Manual`

**Canonical output schema — every adapter emits exactly these columns:**

| Column | Type | Notes |
|---|---|---|
| `TXN_ID` | Text | Surrogate key: `{SRC_SYSTEM}-{SRC_FILE_HASH}-{SRC_ROW}` |
| `DFAC_ID` | Text | Resolved via crosswalk |
| `PERIOD_KEY` | Text | From `Ref_Calendar` |
| `BIZ_DATE` | Date | |
| `TXN_TYPE` | Text | `SALE`/`SIK`/`PURCHASE`/`TRANSFER_IN`/`TRANSFER_OUT`/`WASTE_RAW`/`WASTE_FIN`/`ADJUSTMENT`/`INVENTORY_COUNT` |
| `CATEGORY` | Text | Cost category — align to GAO-22-103949 Rec 10 anticipated categories |
| `ITEM_KEY` | Text | Stock number / vendor item |
| `ITEM_DESC` | Text | |
| `QTY` | Number | |
| `UOM` | Text | |
| `UNIT_COST` | Number | |
| `AMOUNT` | Number | |
| `SRC_SYSTEM` | Text | **Provenance** |
| `SRC_FILE` | Text | **Provenance** |
| `SRC_ROW` | Number | **Provenance** |
| `ADAPTER_VER` | Text | **Provenance** |
| `INGEST_TS` | DateTime | **Provenance** |
| `CROSSWALK_VER` | Text | **Provenance** |
| `RECON_STATUS` | Text | `MATCHED`/`EXCEPTION`/`OVERRIDE`/`UNRECONCILED` |
| `OVERRIDE_BY` | Text | |
| `OVERRIDE_RSN` | Text | Reason code |

**`Adapter_Manual` is the degraded-mode path.** Protected sheet, validated dropdowns pulling from
`Ref_Crosswalk`, locked columns, hidden sheet with identical schema. When Aloha is down or a base
has no connectivity, they fill this. Same pipeline, `SRC_SYSTEM = 'MANUAL'` stamped on every
row. **Every path lands in the same schema.** This preserves provenance and lets you later report
how much of a period was manually captured — itself useful evidence when arguing for system
fixes.

### 6.2 Tab: `Ledger_Transactions`

Union of all adapter outputs. Same schema. **No transformation logic here** — this tab only
unions and validates.

Power Query approach:
```
Source = Folder.Files(IngestPath)
→ filter by subfolder → route to matching adapter query
→ Table.Combine(all adapter outputs)
→ validate schema conformance
→ stamp INGEST_TS
```

### 6.3 Tab: `Ledger_ProvenanceCheck` — MANDATORY

Runs as part of refresh, **before** the exception queue populates. Approximately 30 lines of M.

Flags every row where:

| Check | Condition | Exception |
|---|---|---|
| Null provenance | Any of `SRC_SYSTEM`, `SRC_FILE`, `SRC_ROW`, `ADAPTER_VER`, `INGEST_TS`, `CROSSWALK_VER` is blank | `PROV_NULL` |
| Unresolved crosswalk | `DFAC_ID` not found in `Ref_Crosswalk` where `ACTIVE='Y'` | `XWALK_UNRESOLVED` |
| Unknown adapter | `ADAPTER_VER` not in `Ref_AdapterManifest` with `STATUS='ACTIVE'` | `PROV_NULL` |
| Stale crosswalk | `CROSSWALK_VER` older than current | Warning only |
| Orphan period | `PERIOD_KEY` not in `Ref_Calendar` | `PROV_NULL` |

**Output two metrics to the dashboard:**
- **Provenance completeness %** — must be 100%. Anything less means an adapter is dropping
  annotations.
- **Traceability %** — % of output-form figures traceable to source rows.

Both are auditable and both are exactly what an IG would ask for.
---

## 7. LAYER 3 — Reconciliation

### 7.1 Tab: `Recon_CT_vs_Aloha`

**Direction matters: Aloha is truth. Reconcile CrunchTime *against* Aloha, not the reverse.**

Join on `DFAC_ID` + `BIZ_DATE` + `ITEM_KEY`. Compute variance. Categorize by the four known
drift causes.

| Column | Notes |
|---|---|
| `DFAC_ID`, `BIZ_DATE`, `ITEM_KEY`, `ITEM_DESC` | Keys |
| `ALOHA_QTY`, `ALOHA_AMT` | Truth side |
| `CT_QTY`, `CT_AMT` | Comparison side |
| `VAR_QTY`, `VAR_AMT` | `CT − ALOHA` |
| `VAR_PCT` | `IFERROR(VAR_AMT / N(ALOHA_AMT), 0)` — guard the denominator |
| `EXC_CODE` | Inferred; see heuristics below |
| `EXC_RANK` | Rank by `ABS(VAR_AMT)` descending |
| `STATUS` | `OPEN`/`IN_WORK`/`RESOLVED`/`ACCEPTED` |
| `OWNER` | From `Ref_ExceptionTypes` |
| `NOTES` | |

**Categorization heuristics** (starting rules; refine with real data):

| Pattern | Likely code |
|---|---|
| Item present in Aloha, absent in CrunchTime (or vice versa) | `LINK_ERR` |
| Quantities match, amounts differ | `PRICE_ERR` |
| CrunchTime > Aloha on quantity, negative Aloha lines present | `VOID_ERR` |
| Variance concentrated on `ADJUSTMENT` transaction types | `ADJ_ERR` |

**Presentation — this is the accountant's primary screen:**
- Sort by `ABS(VAR_AMT)` descending. Dollar-ranked, per AvT best practice.
- Within tolerance → green, **collapsed, ignore it**.
- Outside tolerance → work queue.
- Drill from any exception to the contributing source rows from both systems side by side.
- **If nothing is out of tolerance, say so explicitly:** "Nothing to reconcile for 15 JUL — you're clear." Never show a blank state.

**Industry benchmark for context (do not hardcode):** commercial actual-vs-theoretical targets
run ±1–2%, with the goal driving toward zero; investigation starts with the largest variances by
dollar volume, then the site showing the largest variance for that item. DAFMAN's 3% is a
*monetary gain/loss against earned income* — a different measurement than ingredient-level AvT. A
facility can sit inside 3% overall while individual items run 20% off in opposite directions that
net out. **This workbook adds the diagnostic layer beneath the DAFMAN standard; it does not
propose changing the standard.** No waiver required.

### 7.2 Tab: `Recon_Purchases_vs_1080`

Per para 7.18: FSO must verify total food purchases monthly against SF 1080, using the Purchase
Reconciliation Worksheet or AFSVC/VMF-approved equivalent.

Join STORES + GPC purchases against DFAS SF 1080 lines by `DFAC_ID` + `PERIOD_KEY`.

| Column | Notes |
|---|---|
| `DFAC_ID`, `PERIOD_KEY` | Keys |
| `STORES_AMT` | Sum of STORES purchases |
| `GPC_AMT` | Sum of GPC purchases |
| `TOTAL_PURCH` | `STORES_AMT + GPC_AMT` |
| `SF1080_AMT` | From DFAS adapter |
| `VAR_AMT`, `VAR_PCT` | Guard denominator |
| `EXC_CODE` | `PURCH_VAR` where outside tolerance |
| `STATUS`, `OWNER`, `NOTES` | |

---

## 8. LAYER 4 — Outputs

### 8.1 Tab: `Out_ComplianceTracker` — BUILD THIS FIRST AMONG OUTPUTS

The highest-value module. Uses data AFSVC/VMF already receives monthly (para 5.2.5). No new
collection required.

**Input columns (user-entered or imported):**

| Column | Type | Source |
|---|---|---|
| `DFAC_ID` | Text | Dropdown from `Ref_Crosswalk` |
| `PERIOD_KEY` | Text | Dropdown from `Ref_Calendar` |
| `EARNED_INCOME` | Number | From Monthly Monetary Record |
| `GAIN_LOSS_AMT` | Number | From Monthly Monetary Record |
| `COST_OF_GOODS` | Number | Food 2.0 only |
| `MFR_SUBMITTED` | Y/N | |
| `FSS_CC_SIGNED` | Y/N | |
| `INVESTIGATION_OPENED` | Y/N | |
| `NOTES` | Text | |

**Calculated columns — formulas specified literally:**

Let row 8 be the first data row. `FACILITY_TYPE` is looked up from the crosswalk.

**1. Facility type:**
```
=IFERROR(INDEX('Ref_Crosswalk'!$F$2:$F$500,
   MATCH($A8,'Ref_Crosswalk'!$A$2:$A$500,0)),"UNKNOWN")
```

**2. Applied tolerance:**
```
=IFERROR(INDEX('Ref_Tolerance'!$B$2:$B$20,
   MATCH($J8,'Ref_Tolerance'!$A$2:$A$20,0)),"")
```
(where `$J8` holds `FACILITY_TYPE`)

**3. Metric type** — determines which test applies:
```
=IFERROR(INDEX('Ref_Tolerance'!$D$2:$D$20,
   MATCH($J8,'Ref_Tolerance'!$A$2:$A$20,0)),"")
```

**4. DAFMAN citation** — display the standard applied, always:
```
=IFERROR(INDEX('Ref_Tolerance'!$E$2:$E$20,
   MATCH($J8,'Ref_Tolerance'!$A$2:$A$20,0)),"")
```

**5. Variance percent** — guard the denominator:
```
=IFERROR(ABS(N($D8))/N($C8),0)
```
(`$D8` = `GAIN_LOSS_AMT`, `$C8` = `EARNED_INCOME`)

**6. COG percent** (Food 2.0 only):
```
=IFERROR(N($E8)/N($C8),0)
```

**7. Pass/fail** — branches on metric type:
```
=IFERROR(IF($L8="MARGIN",
   IF($N8<=$K8,"PASS","FAIL"),
   IF($M8<=$K8,"PASS","FAIL")),"CHECK")
```
(`$L8`=METRIC_TYPE, `$K8`=TOLERANCE_PCT, `$M8`=VAR_PCT, `$N8`=COG_PCT)

**8. Consecutive breach streak** — the core logic. Counts consecutive prior FAIL periods for the
same `DFAC_ID`. Implement in Power Query (sort by `DFAC_ID`, `PERIOD_KEY`; running counter that
resets on PASS) and surface the result as a column. A formula-only fallback using `COUNTIFS`
against a period-sequence index is acceptable but Power Query is preferred for correctness.

**9. Escalation state:**
```
=IFERROR(IF($O8=0,"CLEAR",
   IF($O8=1,"MFR DUE - MANAGER",
   IF($O8=2,"MFR DUE - FSS/CC SIGNATURE REQUIRED",
   "INVESTIGATION + REPORT OF SURVEY; MSG/CC NOTIFIED"))),"")
```
(`$O8` = streak)

**10. Watch flag** — the field that makes this preventive rather than merely reportorial:
```
=IF($O8=2,"WATCH - ONE MORE MISS TRIGGERS INVESTIGATION","")
```

**11. Action overdue** — cross-check that required action was actually taken:
```
=IFERROR(IF(AND($O8>=1,$F8<>"Y"),"MFR NOT SUBMITTED",
   IF(AND($O8>=2,$G8<>"Y"),"FSS/CC SIGNATURE MISSING",
   IF(AND($O8>=3,$H8<>"Y"),"INVESTIGATION NOT OPENED",""))),"")
```

### 8.2 Tab: `Out_Dashboard` — the "Today" screen

**Three tabs maximum in the user's mental model:** *What's Broken* · *Enter Manually* · *Look
Something Up*. This is *What's Broken*.

Layout, top to bottom:

```
MISSION FEEDING — STATUS AS OF [date]

  EXCEPTIONS OPEN:        [n]        DOLLARS AT RISK:   $[n]
  DFACs OUT OF TOLERANCE: [n]

  ESCALATION STATUS
    Month 1 (MFR due):                    [n]
    Month 2 (FSS/CC signature required):  [n]
    Month 3+ (investigation triggered):   [n]

  WATCH LIST — one more miss triggers investigation
    [DFAC_ID] [DFAC_NAME] [BASE] [MAJCOM]

  DATA INTEGRITY
    Provenance completeness:  [n]%    ← must be 100%
    Traceability:             [n]%
    Sources ingested:         [n] of [n] expected

  ACTIONS OVERDUE
    [list]
```

**Filters:** MAJCOM, BASE_ID, PERIOD_KEY. Nothing else.

**Rules:**
- **Color means one thing.** Red = you must act. Yellow = watch it. Nothing else is colored.
- **Plain-language headers.** "Missing from DFAS" — not `DFAS_RECON_FLAG_N`.
- **No blank states.** Zero exceptions → "Nothing to reconcile — you're clear."
- **One button.** A single Data → Refresh All. Not a sequence.

**Design test:** an A1C should open it, hit refresh, and see a list of five things to fix,
without training. If it needs a job aid longer than one page, redesign it.

### 8.3 Tab: `Out_FormMap`

Declares which ledger aggregations produce which form. Forms are views, not inputs.

| Form | Derivation |
|---|---|
| **AF Form 1119** | Meal counts by category, period-summed from ledger. **Existing engine owns this — map to its output schema, do not rebuild.** |
| AF Form 1119-1 | Same, field feeding detail |
| SF 1080 | SIK/SOD billing totals, cross-checked against DFAS |
| SAITT | Five aggregations of the ledger: Sales, Adjustments, Inventory, Transfers, Totals |
| Storeroom packet | Inventory transaction detail + opening/closing balance |
| DAF Form 3516 | Transfer records (non-automated ops) |

Each generated form carries a **validation block**: source of each figure, whether it reconciled,
and any manual override with reason code. That override trail is what makes the output auditable
and answers "how do we know the automated number is right."

### 8.4 Tab: `Out_EnvisionMap`

Migration bridge to the MF-COP Ontology (§3.2).

| Column | Notes |
|---|---|
| `WORKBOOK_TABLE` | Tab/table name here |
| `ONTOLOGY_OBJECT` | Target Envision object type |
| `OBJECT_TIER` | `REFERENCE`/`TRANSACTION`/`COMPLIANCE`/`ANALYTIC` |
| `PRIMARY_KEY` | |
| `LINKS_TO` | Related object types |
| `MF_COP_MODULE` | 1=Operational Integrity, 2=Inventory & Cost, 3=Compliance & Audit, 4=Quality & Readiness |
| `NOTES` | |

Seed mappings: `Ref_Crosswalk` → Installation + DFAC (REFERENCE); `Ledger_Transactions` →
Transaction objects (TRANSACTION); `Out_ComplianceTracker` → Compliance/Reporting (COMPLIANCE,
Module 3); `Recon_CT_vs_Aloha` → Analytic (ANALYTIC, Module 2).

**Dataverse note:** if licensed, Dataverse is the better near-term home for transactional records
than SharePoint Lists — no 5,000-item list view threshold, native relationships, audit trail,
row-level security by base. It is also structurally closest to the Envision Ontology (objects,
links, actions), making eventual migration a mapping exercise rather than a rebuild.

### 8.5 Tab: `Out_DataDictionary`

Every column in every tab: name, type, source, definition, validation rule, owner. Match the
convention already established in the AF Form 1119 engine.

### 8.6 Tab: `Out_ValidationRegister`

Numbered rules with pass/fail status, modeled on the 1119 engine's 14-rule register. Minimum
rules:

1. All `DFAC_ID` values in ledger resolve in `Ref_Crosswalk`
2. Provenance completeness = 100%
3. All `ADAPTER_VER` values present in `Ref_AdapterManifest` as ACTIVE
4. No `PERIOD_KEY` outside `Ref_Calendar`
5. Sum of adapter row counts = ledger row count
6. Every `FACILITY_TYPE` resolves in `Ref_Tolerance`
7. No `TOLERANCE_PCT` blank where `METRIC_TYPE='VARIANCE'`
8. Streak counter monotonic (never decreases without an intervening PASS)
9. Escalation state consistent with streak value
10. No naked formula errors anywhere in workbook
11. Inventory count dates align to 15th/EOM per `Ref_Calendar`
12. `AMOUNT` = `QTY × UNIT_COST` within rounding tolerance
13. No duplicate `TXN_ID`
14. All `EXC_CODE` values resolve in `Ref_ExceptionTypes`

---

## 9. Build standards

### 9.1 Typography and structure

- **Font:** Arial throughout
- **No merged cells anywhere**
- **Freeze panes** below header rows on all data tabs
- **Tab order** matches layer order: Ref_* → Adapter_* → Ledger_* → Recon_* → Out_*
- **Tab colors:** Reference = grey · Adapter = blue · Ledger = green · Recon = amber · Output = dark blue

### 9.2 Cell color convention

| Color | Meaning |
|---|---|
| Blue text (0,0,255) | Hardcoded input / user-editable |
| Black text | Formula |
| Green text (0,128,0) | Cross-sheet link |
| **Yellow fill (255,255,0)** | **Cells the user must fill in — including all schema placeholder columns** |
| Red fill | Exception requiring action |
| Amber fill | Watch — approaching threshold |

### 9.3 Number formats

- Currency: `$#,##0;($#,##0);-`
- Percentages: `0.0%` — **stored as fractions** (0.03 renders 3.0%; storing 3 renders 300.0%)
- Zeros render as `-`
- Negatives in parentheses
- Years as text (`"2026"`, never `2,026`)

### 9.4 Documentation requirements

- Every assumption in its own labeled cell, referenced by formulas that use it
  (`=B5*$B$6`, never `=B5*0.03`)
- Every hardcoded number annotated with its source, including DAFMAN paragraph
- Legend on every user-facing tab naming which cells to edit
- **One example row of realistic values** on every input tab showing expected format

### 9.5 Verification — mandatory before delivery

If building with `openpyxl`:

1. openpyxl writes formulas as strings with **no cached values**. Recalculate before any
   validation that reads values.
2. Run the recalculation step; **zero formula errors required**. `errors_found` is not
   shippable.
3. A clean recalc proves formulas *evaluate*, not that they are *right*. Write 2–3 formulas
   first, verify they pull expected values, then build out the grid.
4. Reading a model takes two loads: `data_only=True` for cached values, default for formula
   strings. One pass cannot give both. **`data_only=True` is destructive if saved.**
5. Deliver `.xlsx`. No macros.

---

## 10. Build sequence

**Do not reorder.** Sequenced so the workbook is usable at every stage.

### Stage 1 — Foundation (usable immediately, zero unknowns)
1. `Ref_Tolerance` — seed all 8 rows exactly per §5.2, including conflict notes
2. `Ref_Calendar` — FY2025–FY2028
3. `Ref_Crosswalk` — full schema, placeholder columns yellow-filled
4. `Ref_ExceptionTypes`, `Ref_AdapterManifest`, `Ref_CrosswalkVersion`
5. `Out_ComplianceTracker` — full formula set, manual entry + paste-import area
6. `Out_Dashboard` — compliance sections live; integrity sections show "no data"
7. `Out_DataDictionary`, `Out_ValidationRegister`

**Stage 1 exit criterion: the workbook is deployable.** Hand-entered variance data produces a
working enterprise compliance picture. Ship this before building Stage 2.

### Stage 2 — Provenance scaffolding
8. Adapter tabs, three-band layout, schema-marked
9. `Ledger_Transactions` skeleton with full canonical schema
10. `Ledger_ProvenanceCheck` with all five checks
11. Wire integrity metrics into `Out_Dashboard`

### Stage 3 — Reconciliation (requires real source headers)
12. `Recon_CT_vs_Aloha` with categorization heuristics
13. `Recon_Purchases_vs_1080`
14. Wire exception counts and dollars-at-risk into dashboard

### Stage 4 — Forms and migration
15. `Out_FormMap` — map to existing 1119 engine output, do not rebuild it
16. `Out_EnvisionMap` — seed all mappings

### Blocked pending user input
- Real column headers from: Aloha Enterprise sales export, CrunchTime inventory/purchases
  export, STORES order/receipt, SF 1080 (redacted), existing 1119 engine output schema
- MFM SOP v3 roles/responsibilities section (ownership fields)
- Monthly variance data path — portal export, emailed 1119s, or maintained roll-up

**Until headers arrive, adapters remain stubs. Do not invent column names — schema guesses are
the expensive kind of wrong.**
---

## 11. Instructions for use

### 11.1 First-time setup (build owner, ~2 hours)

1. Open `MFRP_v1.xlsx` in **Excel desktop**. Power Query refresh does not work in Excel Web.
2. Go to `Ref_Crosswalk`. Populate one row per DFAC:
   - `DFAC_ID` — assign canonical IDs now. Format `{BASE_ID}-{NN}`. **Once assigned, never
     change one.** Retire and reissue instead, using `EFF_START`/`EFF_END`.
   - `FACILITY_TYPE` — must match a value in `Ref_Tolerance` exactly. This determines which
     standard the facility is scored against.
   - `DODAAC` — from the AFSVC/VMF DoDAAC registry.
   - Leave yellow placeholder columns blank until you have real system exports.
3. Record the initial version in `Ref_CrosswalkVersion` (e.g. `CW-2026-08-01`).
4. Confirm `Ref_Calendar` covers your reporting periods.
5. Review `Ref_Tolerance`. **Do not edit tolerance values** — they are regulatory. If your
   organization decides a facility is misclassified, change `FACILITY_TYPE` in the crosswalk,
   not the tolerance table.

### 11.2 Monthly cycle (accountant / analyst, ~20 min)

**By the 10th** (aligns with MMR submission deadline, para 5.2.5):

1. Open the workbook.
2. Go to `Out_ComplianceTracker`.
3. Add one row per DFAC for the closing period:
   - `DFAC_ID` (dropdown), `PERIOD_KEY` (dropdown)
   - `EARNED_INCOME`, `GAIN_LOSS_AMT` from each facility's Monthly Monetary Record
   - `COST_OF_GOODS` for Food 2.0 sites only
   - Mark `MFR_SUBMITTED` / `FSS_CC_SIGNED` / `INVESTIGATION_OPENED` as actions occur
4. Press **Data → Refresh All**.
5. Go to `Out_Dashboard`. Read top to bottom.

Everything else — tolerance selection, pass/fail, streak counting, escalation state — is
computed. Do not hand-calculate any of it.

### 11.3 Reading the dashboard

| Section | What to do |
|---|---|
| **Month 3+** | Investigation and report of survey are required. MSG/CC must be informed. Confirm `INVESTIGATION_OPENED = Y`. |
| **Month 2** | The MFR needs an FSS/CC signature before submission. Confirm `FSS_CC_SIGNED = Y`. |
| **Month 1** | Manager MFR due to AFSVC/VMF. |
| **Watch list** | Call these facilities **now**. One more miss triggers investigation. This is the preventive action. |
| **Provenance completeness < 100%** | An adapter is dropping annotations. **Stop and fix before trusting any figure.** |
| **Actions overdue** | Required escalation step not recorded. Chase it. |

### 11.4 Adding a source system (build owner)

1. Obtain one export from the system. **The header row is sufficient** to start.
2. Open the relevant `Adapter_*` tab.
3. In Band 2, row 6, type the real source column name beneath each canonical name in row 5.
4. Build the Power Query for that adapter following §4.4 rules: label-anchored, fail-loud,
   version-detecting.
5. Register it in `Ref_AdapterManifest` with `STATUS='ACTIVE'` and a path to a known-good test
   file.
6. Refresh. Confirm `Ledger_ProvenanceCheck` shows 100% completeness.
7. Confirm `Out_ValidationRegister` rules 1–5 pass.

### 11.5 When a source changes format

1. **Do not edit the existing adapter.** Create `adapter_{SOURCE}_v{N+1}` alongside it.
2. Set the old version's `STATUS='DEPRECATED'` in the manifest. Keep it — historical rows
   reference it.
3. Add version detection to route files to the correct adapter.
4. Refresh and verify.

Layers 2–4 should require **zero changes**. If they do, the layering has been violated.

### 11.6 Degraded mode (base user, no connectivity)

1. Open `Adapter_Manual`.
2. Enter transactions using validated dropdowns.
3. Save to the ingest folder when connectivity returns.
4. Rows flow through the identical pipeline with `SRC_SYSTEM='MANUAL'` stamped.

Nothing is lost and provenance is preserved. The workbook can later report what percentage of a
period was manually captured.

### 11.7 Deployment to Teams/SharePoint

- **Files** (exports, packets, PDFs) → **SharePoint document library.** Handles 30M+ items.
- **Structured records** → **not** a single SharePoint List. Lists degrade past ~5,000 items in
  one view.

**Storage note:** Teams does not have separate storage from SharePoint. Every Teams channel is
backed by a SharePoint site; the Files tab *is* a document library. Moving to Teams does not
change capacity. The 5,000 threshold is the **list view threshold**, and it applies to Lists,
not libraries.

**Options for structured records, in order of preference:**

1. **Partition by fiscal year** — `Submissions_FY26`, `Submissions_FY27`; Power Query unions
   them. Never approaches 5,000 in one list. History stays live and queryable. Simplest thing
   that works.
2. **Index the filtered columns** (`DFAC_ID`, `PERIOD_KEY`, `MAJCOM`). Indexed columns return
   under-threshold subsets from much larger lists.
3. **Dataverse** — no threshold, relationships, audit trail, row-level security by base. Best
   long-term home and structurally closest to the Envision Ontology.
4. **Cold archive to a library** — export closed periods to dated files, drop from live list,
   Power Query reads both. Matches the existing folder-drop pattern.

**Retention constraint:** archiving and disposition must be the same operation. Pull the Air
Force Records Disposition Schedule for food service records from AFRIMS before setting any
archive window (§2.7).

**Distribution:** master workbook in a SharePoint document library, surfaced as a Teams tab in
the channel where the work already happens. Users open in Excel desktop. Version control via
SharePoint history. For read-only leadership consumption, a published view or scheduled PDF
snapshot posted to a Teams channel.

---

## 12. Test cases

Run all of these. Each specifies inputs and the exact expected output. A build that passes
recalculation but fails these is not correct.

### TC-01 — Tolerance selection: legacy DFAC (3%)

**Setup:** `Ref_Crosswalk`: `TEST-01`, `FACILITY_TYPE = DFAC_LEGACY`
**Input:** `EARNED_INCOME = 100000`, `GAIN_LOSS_AMT = 2500`
**Expected:** `TOLERANCE_PCT = 0.03` (renders 3.0%) · `VAR_PCT = 0.025` (2.5%) · `RESULT = PASS`
· `DAFMAN_CITE = 5.13`

### TC-02 — Tolerance selection: CAFÉ (5%) — the inconsistency test

**Setup:** `TEST-02`, `FACILITY_TYPE = CAFE`
**Input:** Identical to TC-01 — `EARNED_INCOME = 100000`, `GAIN_LOSS_AMT = 2500`
**Expected:** `TOLERANCE_PCT = 0.05` · `VAR_PCT = 0.025` · `RESULT = PASS` · `DAFMAN_CITE = 6.6`

**Then change both to `GAIN_LOSS_AMT = 4000`:**
- TEST-01 (legacy, 3%): `VAR_PCT = 0.04` → **FAIL**
- TEST-02 (CAFÉ, 5%): `VAR_PCT = 0.04` → **PASS**

**This is the critical test.** Identical financial performance, opposite compliance outcomes,
driven solely by facility classification. If both return the same result, the tolerance lookup is
broken and the workbook's central finding is invisible.

### TC-03 — Food 2.0 margin logic (not variance)

**Setup:** `TEST-03`, `FACILITY_TYPE = FOOD_2_0`
**Input:** `EARNED_INCOME = 100000`, `COST_OF_GOODS = 44000`, `GAIN_LOSS_AMT = 8000`
**Expected:** `METRIC_TYPE = MARGIN` · `COG_PCT = 0.44` · `RESULT = PASS` (44% ≤ 45%)
**Critical:** the 8% gain/loss must **not** drive the result. If it returns FAIL, the metric-type
branch is wrong.
**Also verify:** notes surface that Food 2.0 has no AvT-equivalent variance control.

### TC-04 — ANG tolerance (10%)

**Setup:** `TEST-04`, `FACILITY_TYPE = ANG_DFAC`
**Input:** `EARNED_INCOME = 50000`, `GAIN_LOSS_AMT = 4000`
**Expected:** `TOLERANCE_PCT = 0.10` · `VAR_PCT = 0.08` · `RESULT = PASS`

### TC-05 — Streak counter: clean

**Setup:** `TEST-01`, three consecutive periods, all PASS
**Expected:** streak = 0 for all three · `ESCALATION = CLEAR` · no watch flag

### TC-06 — Streak counter: escalation ladder

**Setup:** `TEST-05`, `DFAC_LEGACY`, `EARNED_INCOME = 100000` each period:

| Period | GAIN_LOSS_AMT | Expected result | Expected streak | Expected escalation |
|---|---|---|---|---|
| P01A | 1000 | PASS | 0 | CLEAR |
| P01B | 5000 | FAIL | 1 | MFR DUE - MANAGER |
| P02A | 6000 | FAIL | 2 | MFR DUE - FSS/CC SIGNATURE REQUIRED |
| P02B | 7000 | FAIL | 3 | INVESTIGATION + REPORT OF SURVEY; MSG/CC NOTIFIED |
| P03A | 1000 | PASS | 0 | CLEAR |
| P03B | 5000 | FAIL | 1 | MFR DUE - MANAGER |

**Critical:** the reset at P03A. If streak continues to 4, the counter is not resetting on PASS.

### TC-07 — Watch list

**Setup:** From TC-06, at period P02A (streak = 2)
**Expected:** `TEST-05` appears on the dashboard watch list with text "one more miss triggers
investigation." Facilities at streak 0, 1, or 3 must **not** appear.

### TC-08 — Action overdue

**Setup:** `TEST-05` at streak = 2, `FSS_CC_SIGNED = N`
**Expected:** `ACTION_OVERDUE = "FSS/CC SIGNATURE MISSING"`
**Then set `FSS_CC_SIGNED = Y`:** field clears.

### TC-09 — Unknown facility type

**Setup:** `TEST-06`, `FACILITY_TYPE = WIDGET_SHOP` (not in `Ref_Tolerance`)
**Expected:** `TOLERANCE_PCT` blank · `RESULT = "CHECK"` · **no `#N/A` visible anywhere** ·
`Out_ValidationRegister` rule 6 FAILS

### TC-10 — Zero earned income (denominator guard)

**Setup:** `TEST-07`, `EARNED_INCOME = 0`, `GAIN_LOSS_AMT = 500`
**Expected:** `VAR_PCT = 0` · **no `#DIV/0!` anywhere** · row flagged for review

### TC-11 — Blank vs zero coercion

**Setup:** `TEST-08`, `EARNED_INCOME = 100000`, `GAIN_LOSS_AMT` left **blank** (empty string,
not zero)
**Expected:** `VAR_PCT = 0` · `RESULT = PASS` · no error. Verifies the `N()` coercion pattern.

### TC-12 — Crosswalk resolution failure

**Setup:** Ledger row with `DFAC_ID = "GHOST-99"` (not in crosswalk)
**Expected:** `Ledger_ProvenanceCheck` flags `XWALK_UNRESOLVED` · provenance completeness < 100%
· dashboard integrity section turns red · `Out_ValidationRegister` rule 1 FAILS

### TC-13 — Provenance completeness

**Setup:** Ledger row with `SRC_ROW` blank, all other provenance columns populated
**Expected:** flagged `PROV_NULL` · completeness < 100% · dashboard red
**Then populate `SRC_ROW`:** completeness returns to 100%, dashboard clears.

### TC-14 — Adapter version not registered

**Setup:** Ledger row with `ADAPTER_VER = "DFAS_v9"`, absent from `Ref_AdapterManifest`
**Expected:** flagged `PROV_NULL` · `Out_ValidationRegister` rule 3 FAILS

### TC-15 — Manual entry path

**Setup:** Three rows in `Adapter_Manual` using dropdowns only
**Expected:** rows appear in `Ledger_Transactions` with `SRC_SYSTEM = 'MANUAL'` · full
provenance present · completeness stays 100% · rows are indistinguishable in downstream logic
from system-sourced rows

### TC-16 — Reconciliation direction (Aloha is truth)

**Setup:** Aloha: item `X`, qty 100, $500. CrunchTime: item `X`, qty 100, $550.
**Expected:** `VAR_AMT = +50` (CT minus Aloha) · `EXC_CODE = PRICE_ERR` (quantities match,
amounts differ) · appears in exception queue
**Critical:** the sign must be CT − Aloha. Reversed sign means the direction is wrong.

### TC-17 — Exception ranking

**Setup:** Three exceptions: $50, $5,000, $200
**Expected:** ranked $5,000 → $200 → $50. Dollar-ranked descending, per AvT best practice.

### TC-18 — Exception ownership routing

**Setup:** One `LINK_ERR`, one `ADJ_ERR`
**Expected:** `LINK_ERR` owner = **AFSVC/VMF** (bases cannot self-correct links, para 7.8.1) ·
`ADJ_ERR` owner = base DFAC manager

### TC-19 — Empty state

**Setup:** All facilities PASS, zero exceptions
**Expected:** dashboard displays "Nothing to reconcile — you're clear" or equivalent. **Never a
blank screen or a bare zero.**

### TC-20 — Period boundary (semi-monthly)

**Setup:** Transactions dated 14 Jul, 15 Jul, 16 Jul, 31 Jul
**Expected:** 14 and 15 Jul → `P07A` · 16 and 31 Jul → `P07B`. Verifies the 15th/EOM inventory
cadence (para 7.13).

### TC-21 — Cross-application portability

**Setup:** Open the delivered `.xlsx` in **LibreOffice Calc**
**Expected:** all formulas calculate · no `#NAME?` anywhere · dashboard renders
**Critical:** a `#NAME?` here means a prohibited function survived (§3.1). Also verify no
lowercased formulas — that is the tell for a formula LibreOffice could not parse.

### TC-22 — No naked errors

**Setup:** Full workbook, populated
**Expected:** zero `#N/A`, `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?` in any user-visible cell.
`Out_ValidationRegister` rule 10 PASSES.

### TC-23 — Refresh idempotence

**Setup:** Press Data → Refresh All three times consecutively, no input changes
**Expected:** identical results each time · no duplicate ledger rows · no `TXN_ID` collisions ·
`Out_ValidationRegister` rule 13 PASSES

### TC-24 — Enterprise rollup filter

**Setup:** 10 test DFACs across 3 MAJCOMs, mixed facility types, mixed pass/fail
**Expected:** filtering to one MAJCOM shows only its facilities · counts recompute correctly ·
each facility still scored against **its own** tolerance, not a single blanket rate

---

## 13. Acceptance criteria

The build is complete when all of these are true.

**Regulatory correctness**
1. All 8 tolerance rows present with correct DAFMAN citations
2. Facility type drives tolerance selection — TC-02 demonstrates divergent outcomes on identical inputs
3. Food 2.0 evaluated on margin, not variance (TC-03)
4. Escalation ladder matches para 5.13.2 exactly, including MSG/CC notification at month 3
5. Streak resets on PASS (TC-06)

**Data integrity**
6. Provenance completeness reports 100% on clean data, <100% on any missing annotation
7. Provenance checker runs before exception queue populates
8. All 14 validation register rules implemented and reporting
9. No duplicate `TXN_ID` after repeated refresh

**Robustness**
10. Zero naked formula errors anywhere (TC-22)
11. Every denominator guarded (TC-10)
12. Blank-vs-zero handled via `N()` coercion (TC-11)
13. Unknown lookup values degrade gracefully to "CHECK", never `#N/A` (TC-09)

**Portability**
14. Opens and calculates correctly in LibreOffice Calc (TC-21)
15. No prohibited functions present (§3.1)
16. No merged cells
17. No VBA — delivered as `.xlsx`
18. No structured references (`[@Column]`)

**Usability**
19. Dashboard readable top-to-bottom with no scrolling on a standard screen
20. Single refresh action, not a sequence
21. Empty states show text, never blanks (TC-19)
22. Every input tab has a legend and one realistic example row
23. Color used only for action (red) and watch (amber)

**Deployability**
24. Stage 1 tabs function standalone with hand-entered data, before any adapter exists
25. Placeholder columns visually marked (yellow) and documented as pending
26. `Out_EnvisionMap` populated for all existing tables

---

## 14. Open items requiring user input

| # | Item | Blocks |
|---|---|---|
| 1 | Real column headers: Aloha Enterprise sales export | `Adapter_Aloha`, `Recon_CT_vs_Aloha` |
| 2 | Real column headers: CrunchTime inventory/purchases export | `Adapter_CrunchTime`, `Recon_CT_vs_Aloha` |
| 3 | Real column headers: STORES order/receipt | `Adapter_STORES`, `Recon_Purchases_vs_1080` |
| 4 | SF 1080 sample (redacted) | `Adapter_DFAS1080`, `Recon_Purchases_vs_1080` |
| 5 | Existing AF Form 1119 engine output schema | `Out_FormMap` |
| 6 | MFM SOP v3 roles/responsibilities section | Ownership fields, `Ref_ExceptionTypes` |
| 7 | Monthly variance data path (portal export / emailed 1119s / roll-up) | `Out_ComplianceTracker` import method |
| 8 | Air Force RDS retention windows for food service records | Archive strategy (§11.7) |
| 9 | Dataverse licensing status in tenant | Storage decision (§11.7) |
| 10 | Aloha Enterprise report catalog — what canned exports exist, granularity, schedule | Adapter design |

**Item 10 note:** confirm whether the Aloha → CrunchTime feed carries **item-level detail or
summary only**. Item-level is what makes ingredient-granularity AvT possible. If summary-only,
that is a CrunchTime configuration question, not a development effort.

---

## 15. Parallel non-build actions

These are staff actions, not code. They have higher leverage than additional development.

1. **Formalize the crosswalk registry owner.** AFSVC/VMF already owns this implicitly via DoDAAC
   approval authority (para 1.4.10). Make it explicit with a documented change process.
2. **Ask DFAS/SAF for the SIK bill as a data file** rather than a rendered PDF. Eliminates the
   entire parsing problem. Costs a staff package, not money.
3. **Confirm whether CrunchTime's Aloha connector is in the AFSVC contract** and whether it was
   ever enabled. Vendor-delivered, not customer-developed.
4. **Raise the 3% vs 5% tolerance conflict** via DAF Form 847, Recommendation for Change of
   Publication. Para 5.13 and para 6.6 both T-2, inconsistent application.
5. **Frame the effort against GAO-22-103949 Rec 8** (open, Air Force-assigned, four years) and
   the FY2026 Green Book revision's preventive-control emphasis.
6. **Baseline before deploying.** Capture cycle time, error rate, and rework rate at 3 DFACs now.
   Without a baseline there is no defensible ROI case. Suggested metrics: hours per DFAC per
   month on reconciliation; first-pass yield (submissions accepted without correction);
   provenance completeness; traceability.
7. **Field-test the existing FMAT tool** on the next assessment. It is built but untested.

---

## 16. Framing for leadership

This is not a dashboard project. It is a **Green Book-compliant internal control system** built
in tools already owned, in the first fiscal year the 2025 revision applies.

- **Preventive controls:** validated entry, crosswalk-enforced keys, fail-loud adapters
- **Detective controls:** exception queue, provenance checker, compliance tracker
- **Improper payment exposure addressed:** SF 1080 SIK billing from hand-transcribed figures
- **Open GAO recommendation addressed:** GAO-22-103949 Rec 8, Air Force-assigned, open since 2022
- **Proven template:** the Army closed the equivalent recommendation with FMAT + standardized
  metrics + integrating dashboard — a combination GAO explicitly accepted

The value proposition is **hours returned to food operations per DFAC per month** and **reduction
in erroneous SIK billing** — not better visualizations.

**The honest risk is not technical.** Power Query can do all of this. The risk is building
something that works and is entirely dependent on one person. Decide early whether the goal is a
tool one person maintains or a capability AFSVC owns — the second requires writing down the
boring parts and training a bench, and that is most of the real work.
