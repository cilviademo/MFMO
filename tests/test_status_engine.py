#!/usr/bin/env python3
"""Status engine acceptance tests.

These do three things:

1. Run every case in tests/fixtures/status_cases.json through the reference
   implementation.
2. Assert the non-negotiables directly, so a future refactor that still
   passes the fixtures but breaks a rule fails loudly.
3. Assert that canvas-app/formulas/StatusEngine.fx and the flow definitions
   still agree with the reference. They are transliterations, and a
   transliteration that drifts is worse than no transliteration.
"""

import datetime as dt
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from status_engine import (  # noqa: E402
    evaluate, rollup, due_and_suspense, CODES,
    COMPLETE_CODES, OUT_OF_DENOMINATOR_CODES,
)
import eom_schema  # noqa: E402

with open(os.path.join(ROOT, "tests", "fixtures", "status_cases.json")) as _fh:
    FIXTURES = json.load(_fh)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class TestFixtureCases(unittest.TestCase):
    def test_every_case(self):
        as_of = dt.date.fromisoformat(FIXTURES["as_of"])
        for case in FIXTURES["cases"]:
            with self.subTest(case["name"]):
                r = evaluate(as_of=as_of, **case["input"])
                for key, want in case["expect"].items():
                    if key == "is_complete":
                        got = r.is_complete
                    elif key == "is_in_denominator":
                        got = r.is_in_denominator
                    else:
                        got = getattr(r, key)
                    self.assertEqual(got, want, f"{case['name']}: {key}")

    def test_rollups(self):
        for case in FIXTURES["rollups"]:
            with self.subTest(case["name"]):
                got = rollup(case["codes"])
                for key, want in case["expect"].items():
                    self.assertEqual(got[key], want, f"{case['name']}: {key}")


class TestNonNegotiables(unittest.TestCase):
    """One rule per test, named after the rule."""

    def test_an_unverified_requirement_never_drives_red(self):
        # The default path today: all twelve seeded requirements are UNVERIFIED.
        for status in ("UNVERIFIED", "RETIRED"):
            for days_late in (1, 5, 400):
                r = evaluate(
                    as_of=dt.date(2026, 11, 10),
                    suspense_date=dt.date(2026, 11, 10) - dt.timedelta(days=days_late),
                    requirement_verification_status=status,
                )
                self.assertNotEqual(r.status, "Red", f"{status} at {days_late} days late went Red")

    def test_no_seeded_requirement_can_currently_drive_red(self):
        import csv
        path = os.path.join(ROOT, "configuration", "requirements.csv")
        with open(path, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 12, "the seed is twelve requirements")
        self.assertEqual(sum(r["Is_Active"] == "FALSE" for r in rows), 3, "three are inactive")
        for row in rows:
            self.assertEqual(row["Verification_Status"], "UNVERIFIED", row["Requirement_ID"])
            r = evaluate(
                as_of=dt.date(2026, 11, 10),
                suspense_date=dt.date(2026, 1, 1),
                requirement_verification_status=row["Verification_Status"],
                requirement_is_active=(row["Is_Active"] == "TRUE"),
            )
            self.assertNotEqual(r.status, "Red", row["Requirement_ID"])

    def test_five_visual_states_not_four(self):
        states = {v[0] for v in CODES.values()}
        self.assertEqual(states, {"Blue", "Amber", "Red", "Green", "Gray"})
        # Blue separates "not due yet" from "not applicable".
        self.assertEqual(CODES["NOT_DUE"][0], "Blue")
        self.assertEqual(CODES["NOT_APPLICABLE"][0], "Gray")

    def test_every_code_carries_a_label(self):
        # Status is never colour-only.
        for code, (status, label, owner, required) in CODES.items():
            self.assertTrue(label.strip(), f"{code} has no label")
            self.assertIn(owner, ("Facility", "Reviewer", "Program", "None"))

    def test_final_status_and_status_code_are_independent(self):
        # Several codes map to one visual state; the mapping is not reversible.
        gray = [c for c, v in CODES.items() if v[0] == "Gray"]
        amber = [c for c, v in CODES.items() if v[0] == "Amber"]
        self.assertGreater(len(gray), 1)
        self.assertGreater(len(amber), 1)

    def test_a_colour_rollup_would_be_wrong(self):
        # The exact example from docs/status-calculation.md.
        codes = ["ACCEPTED", "NOT_DUE", "NOT_DUE"]
        naive_colour_rollup = sum(CODES[c][0] == "Green" for c in codes) / len(codes)
        semantic = rollup(codes)["complete_ratio"]
        self.assertAlmostEqual(naive_colour_rollup, 1 / 3)
        self.assertEqual(semantic, 1.0)

    def test_nothing_due_is_neither_zero_nor_one_hundred(self):
        self.assertIsNone(rollup(["NOT_DUE", "WAIVED"])["complete_ratio"])

    def test_rollup_respects_the_viewers_scope(self):
        # A facility user must not receive an installation figure derived from
        # their neighbours. The visibility filter is applied BEFORE aggregation.
        rows = [evaluate(as_of=dt.date(2026, 11, 10), suspense_date=dt.date(2026, 11, 20),
                         has_current_submission=True, qc_status="ACCEPTED") for _ in range(3)]
        rows += [evaluate(as_of=dt.date(2026, 11, 10), suspense_date=dt.date(2026, 11, 1),
                          requirement_verification_status="VERIFIED") for _ in range(7)]
        everything = rollup(rows)
        mine_only = rollup(rows, visible_predicate=lambda r: r.code == "ACCEPTED")
        self.assertEqual(everything["in_denominator"], 10)
        self.assertEqual(mine_only["in_denominator"], 3)
        self.assertEqual(mine_only["complete_ratio"], 1.0)

    def test_only_the_current_version_decides(self):
        # A rejected v1 under an accepted v2 does not make the item Amber.
        r = evaluate(as_of=dt.date(2026, 11, 10), suspense_date=dt.date(2026, 11, 20),
                     has_current_submission=True, qc_status="ACCEPTED")
        self.assertEqual(r.code, "ACCEPTED")

    def test_suspense_may_not_precede_due(self):
        with self.assertRaises(ValueError):
            due_and_suspense("2026-09-30", 10, 5)

    def test_schema_vocabulary_matches_the_engine(self):
        self.assertEqual(set(eom_schema.STATUS_CODE), set(CODES))
        self.assertEqual(set(eom_schema.FINAL_STATUS), {v[0] for v in CODES.values()})
        self.assertEqual(set(eom_schema.ACTION_OWNER), {v[2] for v in CODES.values()})

    def test_rollup_flag_sets_are_disjoint_and_total(self):
        self.assertTrue(COMPLETE_CODES.isdisjoint(OUT_OF_DENOMINATOR_CODES))
        self.assertTrue(set(CODES).issuperset(COMPLETE_CODES | OUT_OF_DENOMINATOR_CODES))


class TestTransliterationsAgree(unittest.TestCase):
    """StatusEngine.fx and the flows are transliterations. Hold them to it."""

    def setUp(self):
        self.fx = read("canvas-app", "formulas", "StatusEngine.fx")

    def test_fx_catalogue_matches_the_reference(self):
        for code, (status, label, owner, required) in CODES.items():
            row = re.search(r'\{\s*code:\s*"%s".*?\}' % re.escape(code), self.fx, re.S)
            self.assertIsNotNone(row, f"{code} missing from MF_StatusCatalog")
            row = row.group(0)
            self.assertIn(f'status: "{status}"', row, code)
            self.assertIn(f'label: "{label}"', row, code)
            self.assertIn(f'actionOwner: "{owner}"', row, code)
            self.assertIn(f'actionRequired: {"true" if required else "false"}', row, code)

    def test_fx_evaluation_order_matches_the_reference(self):
        # The order is behaviour. Reordering to make a screen read better is
        # exactly the change this test exists to catch.
        expected_order = [
            "NOT_APPLICABLE", "WAIVED", "SUPERSEDED",
            "ACCEPTED", "RETURNED", "IN_REVIEW", "SUBMITTED",
            "NOT_DUE", "OVERDUE", "PROVISIONAL_OVERDUE", "DUE_SOON",
        ]
        body = self.fx.split("MF_EvaluateStatus(")[1]
        found, seen = [], set()
        for m in re.finditer(r'"([A-Z_]+)"', body):
            code = m.group(1)
            if code in CODES and code not in seen:
                seen.add(code)
                found.append(code)
        self.assertEqual(found[:len(expected_order)], expected_order)

    def test_fx_declares_the_same_rollup_sets(self):
        m = re.search(r"MF_IsInDenominator.*?\[(.*?)\]", self.fx, re.S)
        self.assertIsNotNone(m)
        declared = set(re.findall(r'"([A-Z_]+)"', m.group(1)))
        self.assertEqual(declared, set(OUT_OF_DENOMINATOR_CODES))
        self.assertIn('MF_IsComplete(StatusCode: Text): Boolean =\n    StatusCode = "ACCEPTED"', self.fx)

    def test_no_colour_literal_outside_the_token_definitions(self):
        # No screen or component may declare a colour literal; only
        # App.Formulas.fx defines the tokens.
        app_dir = os.path.join(ROOT, "canvas-app", "src")
        offenders = []
        for dirpath, _, files in os.walk(app_dir):
            for name in files:
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r'(ColorValue\(|RGBA\(|Color\.[A-Z])', line):
                            offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [], "colour literals found outside App.Formulas.fx")

    def test_no_colour_picker_exists(self):
        # Status is calculated, never chosen.
        app_dir = os.path.join(ROOT, "canvas-app")
        for dirpath, _, files in os.walk(app_dir):
            for name in files:
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    text = fh.read()
                self.assertNotIn("ColorPicker", text, os.path.join(dirpath, name))

    def test_flows_write_all_four_status_fields_together(self):
        # A flow that writes Status_Code without Status_Semantic, Final_Status
        # and Action_Owner_Role has derived one of them somewhere else.
        import glob
        for path in glob.glob(os.path.join(ROOT, "flows", "**", "*.json"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if '"Status_Code"' not in text:
                continue
            for field in ("Status_Semantic", "Final_Status", "Action_Owner_Role", "Action_Required"):
                self.assertIn(field, text, f"{os.path.basename(path)} writes Status_Code without {field}")

    def test_the_prototype_engine_matches_the_reference(self):
        # docs/mf-operations-prototype.html implements the engine live rather
        # than mocking it up. A prototype that has drifted from the reference
        # is a prototype that settles the wrong argument.
        html = read("docs", "mf-operations-prototype.html")
        for code, (status, label, owner, required) in CODES.items():
            row = re.search(r"^  %s:\s*\{(.*?)\},\s*$" % re.escape(code), html, re.M)
            self.assertIsNotNone(row, f"{code} missing from the prototype")
            row = row.group(1)
            self.assertIn(f'status: "{status}"', row, code)
            self.assertIn(f'owner: "{owner}"', row, code)
            self.assertIn(f"required: {'true' if required else 'false'}", row, code)
            # The label may carry a typographic dash the plain-text sources do
            # not; compare on the part before any dash.
            head = label.split(" - ")[0]
            self.assertIn(head, row, code)

    def test_the_prototype_declares_the_same_denominator_set(self):
        html = read("docs", "mf-operations-prototype.html")
        m = re.search(r"OUT_OF_DENOMINATOR\s*=\s*\[(.*?)\]", html, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(set(re.findall(r'"([A-Z_]+)"', m.group(1))),
                         set(OUT_OF_DENOMINATOR_CODES))

    def test_fact_flow_copies_rather_than_recomputes(self):
        text = read("flows", "EOM03-StatusFact", "definition.json")
        # The two rollup flags are computed; everything else is copied.
        self.assertIn("Is_Complete", text)
        self.assertIn("Is_In_Denominator", text)
        for code in OUT_OF_DENOMINATOR_CODES:
            self.assertIn(code, text, f"EOM-03 denominator set is missing {code}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
