# MFRP_v1.xlsx — Build & Verification Report

**Deliverable:** `../MFRP_v1.xlsx` — Stage 1 (spec §10). Formulas + data validation
only. No VBA, no macros, `.xlsx`.

## What was built (10 Stage 1 tabs)

| Tab | Notes |
|---|---|
| `Ref_Tolerance` | All 8 seed rows exactly per §5.2, DAFMAN cites, 3%-vs-5% conflict notes, Food 2.0 MARGIN note. Regulatory — locked convention. |
| `Ref_Calendar` | Semi-monthly period keys `FY{n}-P{MM}{A/B}`, FY2025–FY2028, inventory/post/MMR due dates (paras 7.13, 5.2.5). |
| `Ref_Crosswalk` | Full 15-col schema. Placeholder columns (ALOHA_STORE/CT_SITE/CIR_MERCHANT/STORES_ACCT) yellow-filled. One example row (JBSA-01). |
| `Ref_ExceptionTypes` | 9-row taxonomy (§5.6) with AFSVC/VMF routing. |
| `Ref_AdapterManifest` | Hand-maintained edge list, STUB example row (adapters are Stage 2+). |
| `Ref_CrosswalkVersion` | Version history for drift detection. |
| `Out_ComplianceTracker` | The engine: facility-type→tolerance lookup, MARGIN-vs-VARIANCE branch, VAR%/COG% (guarded, N()-coerced), streak counter, escalation ladder, watch/overdue flags. First data row = 8 per spec. |
| `Out_Dashboard` | "What's Broken" screen: out-of-tolerance count, escalation buckets, watch list, actions overdue, integrity section ("no data" until Stage 2). MAJCOM/BASE/PERIOD filters. Empty-state text, not blanks. |
| `Out_DataDictionary` | Every column: type, source, definition, validation, owner. |
| `Out_ValidationRegister` | 14 numbered rules; 8 live in Stage 1, 6 marked N/A (ledger/provenance = Stage 2+). |

## Hard constraints honored (spec §3.1)

- INDEX/MATCH for all lookups — **no** XLOOKUP/XMATCH/SORT/FILTER/UNIQUE/SEQUENCE/TEXTAFTER/…
- No structured references (`[@Column]`); explicit cell refs, sheet names quoted.
- No merged cells. Arial throughout. IFERROR on every formula. `N()` coercion on
  numeric cells that may be blank. Every denominator guarded.
- Percentages stored as fractions (0.03 → 3.0%).
- `fullCalcOnLoad` set so Excel/LibreOffice recalculate on open (openpyxl writes no
  cached values).

## Test results — 19/19 passed

Recalculated with the `formulas` Python engine (Excel-2007 semantics). See
`run_tests.py`.

```
TC-01  PASS  legacy DFAC 3% -> PASS, cite 5.13
TC-02a PASS  identical 2500 -> both PASS, cites 5.13 vs 6.6
TC-02b PASS  CRITICAL: identical 4% -> legacy FAIL, CAFE PASS (divergent outcome)
TC-03  PASS  Food 2.0 MARGIN branch: 44% COG -> PASS; 8% gain/loss does NOT drive it
TC-04  PASS  ANG 10% -> 8% PASS
TC-05  PASS  three PASS periods -> streak 0, escalation CLEAR
TC-06  PASS  escalation ladder 0-1-2-3, resets to 0 on PASS at P03A
TC-07  PASS  watch flag only at streak 2; appears on dashboard watch list
TC-08  PASS  "FSS/CC SIGNATURE MISSING" clears when FSS_CC_SIGNED set to Y
TC-09  PASS  unknown facility type -> blank tolerance, RESULT CHECK, rule 6 FAIL (no #N/A)
TC-10  PASS  zero earned income -> VAR% 0, no #DIV/0
TC-11  PASS  blank gain/loss -> VAR% 0, PASS (N() coercion)
TC-12  PASS  unknown DFAC -> FACILITY_TYPE UNKNOWN, RESULT CHECK, rule 1 FAIL (tracker analog)
TC-19  PASS  empty state shows text, not blanks
TC-20  PASS  semi-monthly boundary: 14/15 Jul -> P07A, 16/31 Jul -> P07B
TC-21  PASS  static scan: 0 prohibited functions, 0 structured references
TC-22  PASS  zero naked error cells across recalculated workbook
TC-23  PASS  recalc idempotent (identical results)
TC-24  PASS  10 DFACs / 3 MAJCOMs; MAJCOM filter recomputes; each scored on own tolerance
```

**Not run (out of scope — Stage 2 features):** TC-13 (provenance completeness),
TC-14 (adapter-version), TC-15–18 (ledger/reconciliation). These depend on
`Ledger_ProvenanceCheck` and the adapters, which Stage 1 deliberately does not build.

## Environment note on TC-21 (LibreOffice)

The spec's TC-21 asks for a live open in LibreOffice Calc. LibreOffice is present in
this build environment but **cannot load any file** here (headless convert fails with
"source file could not be loaded" even for a trivial file — an environment/sandbox
limitation, not a workbook defect), and its UNO socket bridge is blocked. TC-21 is
therefore verified by **static analysis**: every formula string in the workbook was
scanned and contains none of the prohibited functions and no structured references.
The `formulas` engine (strict Excel-2007 semantics, the same 2007-era function set the
spec mandates) recalculates the entire workbook with **zero errors**, which
corroborates portability. A live LibreOffice open is still recommended as a final
gate on a normal workstation before distribution.

## Reproduce

```bash
pip install openpyxl formulas
python3 build/build_mfrp.py MFRP_v1.xlsx          # build the deliverable

# fast test build (identical formulas, fewer tracker rows) + run the suite
MFRP_CT_LAST=57 MFRP_CW_LAST=40 python3 build/build_mfrp.py /tmp/MFRP_test.xlsx
MFRP_TEST_BOOK=/tmp/MFRP_test.xlsx MFRP_CT_LAST=57 MFRP_CW_LAST=40 \
    python3 build/run_tests.py
```
