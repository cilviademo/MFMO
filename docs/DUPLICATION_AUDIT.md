# Duplication audit

Exactly one implementation of each concept. Where a concept necessarily exists
in two languages — Python for the reference, Power Fx for the app — one is the
**reference** and the other is a **transliteration held to it by a test**. That
is not duplication; two independently-authored implementations are.

Every snapshot delivered to this programme has shipped a current decision table
and stale code implementing it. This table is how that stops.

| Concept | Authoritative implementation | Transliterations, held by test | Notes |
|---|---|---|---|
| Status evaluation | `scripts/status_engine.py:229` `item_status()` | `canvas-app/formulas/StatusEngine.fx:102` `MF_EvaluateStatus` — `tests/test_status_engine.py` | Twelve ordered rules. Returns status, code, label, actionOwner, actionRequired in one pass. |
| Due date and final call | `scripts/status_engine.py:135` `nominal_date()`, `:178` `effective_date()`, `:201` `resolve_dates()` | none — dates are computed by EOM-01 and **stored**; the app reads four columns and never recomputes | The app having no date arithmetic at all is deliberate. |
| Authorisation check | `canvas-app/formulas/App.Formulas.fx:108` `MF_LiveScope` / `gblHasAccess` | none | Flow-side authorisation is EOM-02 step 1, which reads the caller's UPN from the authenticated context. Two *layers*, one *rule*. |
| Requirement applicability | `scripts/generate_expected_items.py:105` `model_applies()`, `:118` `facility_type_applies()` | `canvas-app/formulas/Cascade.fx:34` `MF_ModelApplies`, `:54` `MF_FacilityTypeApplies` — `tests/test_duplication.py` | **Consolidated in this pass.** See below. |
| Version supersession | `flows/EOM02-Submission/definition.md` step 6 | none — `scrUpload` only *displays* the next version number | No screen patches `Is_Current` or `Superseded_By`. |
| Package rollup | `scripts/status_engine.py:353` `package_state()` | `canvas-app/formulas/StatusEngine.fx:195` `MF_PackageState` — `tests/test_status_engine.py` | Runs over semantic statuses, never colour codes. |
| Destination resolution | `scripts/folder_resolver.py:213` `resolve_destination_folder()` | none — the app supplies logical identifiers and never a path | `tests/test_folder_resolver.py` also holds the flow spec to the code. |
| Colour from status | `canvas-app/formulas/App.Formulas.fx` colour tokens, read by `StatusEngine.fx` `MF_StatusColor` | none — `scripts/validate_solution.py` fails the build on a colour literal in a screen | `tests/test_design_tokens.py` measures the tokens rather than trusting a comment. |

## What was consolidated in this pass

**Requirement applicability had two independent implementations.**
`Cascade.fx` filtered the requirement dropdown with an inline predicate:

```
Applicable_Model = OperatingModel || Applicable_Model = "All",
IsBlank(Applicable_Facility_Types) || FacilityType in Applicable_Facility_Types
```

while `generate_expected_items.py` decided what EOM-01 generates. They answer
different questions — *what may a user file* versus *what is expected* — and
they must use the same predicate, or a dropdown offers a requirement the
checklist beside it says nothing about.

The inline version had two defects, both invisible:

* **It gave the right answer for an unknown facility type by accident.** Power
  Fx `in` is substring containment and the empty string is a substring of
  everything. Every QRG facility has a blank type today, so the whole
  behaviour rested on that coincidence.
* **It gave the wrong answer for a real type that is a substring of another.**
  `MAF` matched a list containing `MAFFO`.

Both are now named functions matching on a delimited exact term, and
`tests/test_duplication.py` runs the same cases through the Python predicate and
a Python model of the Fx one.

One divergence was resolved in the process: Power Fx `in` is case-insensitive
and the Python set comparison was case-sensitive. The Python side was made
case-insensitive to match. Two predicates that must agree should not disagree
about capitalisation, and matching more rather than fewer is the safe direction
— an extra row in a dropdown is visible.

**Nothing else was consolidated.** An edit that leaves behaviour unchanged was
not worth making, and several things that look like duplication are not:

* `scrReview` calls `MF_EvaluateStatus` — that is the single engine being
  *invoked* to produce a write, not a second evaluation.
* `scrUpload` computes "this will be version N" for display; supersession is
  EOM-02's.
* `scrAccessRequest` and `scrDiagnostics` filter on the current user's UPN —
  those are "show me mine" queries, not authorisation decisions.

## Removed from the packaging path

The central evidence library and its two root-path config rows were a **second
live upload architecture**, not merely a stale document. They are removed from
`provisioning/Provision-MFOpsLists.ps1`, `configuration/app-config.csv`,
`configuration/environment-variables.json` and
`canvas-app/formulas/App.Formulas.fx` in the same commit that records the
decision. Only the explanation survives, in `docs/DECISION_LOG.md` D-01.
