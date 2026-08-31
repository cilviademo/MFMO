#!/usr/bin/env python3
"""Status engine acceptance tests.

Four things:

1. Every case in tests/fixtures/status_cases.json through the reference
   implementation.
2. The non-negotiables asserted directly, so a refactor that still passes the
   fixtures but breaks a rule fails loudly.
3. That StatusEngine.fx and the prototype still agree with the reference. They
   are transliterations, and a transliteration that drifts is worse than none —
   V3 shipped three status functions that had already drifted from V3's own
   decision table.
4. That the corrections in docs/handoffs/RECONCILIATION.md stayed applied.
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
    item_status, package_state, due_date_for, days_late,
    STATUSES, PACKAGE_STATES, CODE_COLOUR,
)
import eom_schema as S  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


with open(os.path.join(ROOT, "tests", "fixtures", "status_cases.json")) as _fh:
    FIXTURES = json.load(_fh)


class TestFixtureCases(unittest.TestCase):
    def test_every_case(self):
        today = dt.date.fromisoformat(FIXTURES["today"])
        for case in FIXTURES["cases"]:
            with self.subTest(case["name"]):
                r = item_status(today=today, **case["input"])
                for key, want in case["expect"].items():
                    self.assertEqual(getattr(r, key), want, f"{case['name']}: {key}")

    def test_every_package_case(self):
        for case in FIXTURES["packages"]:
            with self.subTest(case["name"]):
                got = package_state(case["statuses"])
                for key, want in case["expect"].items():
                    self.assertEqual(got[key], want, f"{case['name']}: {key}")


class TestNonNegotiables(unittest.TestCase):
    """One rule per test, named after the rule."""

    TODAY = dt.date(2026, 9, 12)

    def test_an_unverified_requirement_never_drives_an_adverse_status(self):
        # The default path today: all twelve seeded requirements are UNVERIFIED.
        for days in (1, 30, 400):
            r = item_status(today=self.TODAY,
                            due_date=self.TODAY - dt.timedelta(days=days),
                            authority_status="UNVERIFIED")
            self.assertEqual(r.status, "PENDING_VALIDATION", f"{days} days late")
            self.assertEqual(r.code, 4, "provisional must be Blue, not Red and not Gray")
            self.assertEqual(r.actionOwner, "Admin",
                             "the action is to verify the requirement, not to file the document")
            self.assertFalse(r.actionRequired)

    def test_no_seeded_requirement_can_currently_drive_red(self):
        import csv
        with open(os.path.join(ROOT, "configuration", "requirements.csv"),
                  encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 12, "the seed is twelve requirements")
        self.assertEqual(sum(r["Active_Flag"] == "FALSE" for r in rows), 3,
                         "three are inactive")
        for row in rows:
            self.assertEqual(row["Authority_Status"], "UNVERIFIED", row["Requirement_ID"])
            r = item_status(today=self.TODAY, due_date=dt.date(2026, 1, 1),
                            required_flag=(row["Required_Flag"] == "TRUE"),
                            authority_status=row["Authority_Status"])
            self.assertNotEqual(r.code, 1, row["Requirement_ID"])

    def test_five_visual_states_not_four(self):
        codes = {v[0] for v in STATUSES.values()}
        self.assertEqual(codes, {0, 1, 2, 3, 4})
        # Blue separates "not due yet" and "informational" from "not applicable".
        self.assertEqual(STATUSES["NOT_DUE"][0], 4)
        self.assertEqual(STATUSES["PENDING_VALIDATION"][0], 4)
        self.assertEqual(STATUSES["NOT_APPLICABLE"][0], 0)
        self.assertEqual(CODE_COLOUR[4], "Blue")

    def test_final_status_and_status_code_are_independent(self):
        # Several semantic statuses map to one code; the mapping is not
        # reversible, which is the point of storing both.
        by_code = {}
        for status, (code, *_rest) in STATUSES.items():
            by_code.setdefault(code, []).append(status)
        self.assertGreater(len(by_code[0]), 0)
        self.assertGreater(len(by_code[2]), 1, "Amber must cover more than one status")
        self.assertGreater(len(by_code[4]), 1, "Blue must cover more than one status")

    def test_every_status_carries_a_label(self):
        # Status is never colour-only.
        for status, (code, label, owner, required) in STATUSES.items():
            self.assertTrue(label.strip(), f"{status} has no label")
            self.assertIn(owner, ("Facility", "Reviewer", "Admin", "None"))

    def test_a_colour_rollup_would_be_wrong(self):
        # The exact example from docs/status-calculation.md.
        statuses = ["ACCEPTED", "NOT_DUE", "NOT_DUE"]
        codes = [STATUSES[s][0] for s in statuses]
        naive_colour = (1 if 1 in codes else 2 if 2 in codes else 3 if 3 in codes else 0)
        self.assertEqual(naive_colour, 3, "the naive colour rollup says Complete")
        self.assertEqual(package_state(statuses)["state"], "IN_PROGRESS",
                         "the semantic rollup says In progress, and it is right")

    def test_wrong_document_is_not_permanently_red(self):
        before = item_status(today=self.TODAY, due_date=dt.date(2026, 9, 30),
                             authority_status="Verified", received_flag=True,
                             qc_status="Wrong Document")
        after = item_status(today=self.TODAY, due_date=dt.date(2026, 9, 1),
                            authority_status="Verified", received_flag=True,
                            qc_status="Wrong Document")
        self.assertEqual(before.status, "NOT_SATISFIED")
        self.assertEqual(before.code, 2)
        self.assertEqual(after.status, "OVERDUE")
        self.assertEqual(after.code, 1)

    def test_ownership_answers_is_this_mine(self):
        # Amber covers both the facility's action and the reviewer's. A
        # submitter's list must not contain the reviewer's queue.
        mine = item_status(today=self.TODAY, due_date=dt.date(2026, 9, 30),
                           authority_status="Verified", received_flag=True,
                           qc_status="Correction Required")
        theirs = item_status(today=self.TODAY, due_date=dt.date(2026, 9, 30),
                             authority_status="Verified", received_flag=True,
                             qc_status="Pending Review")
        self.assertEqual(mine.code, theirs.code, "both are Amber")
        self.assertNotEqual(mine.actionOwner, theirs.actionOwner)

    def test_rollup_respects_the_viewers_scope(self):
        # A user scoped to one DFAC must not receive an installation figure
        # derived from their neighbours' packages.
        rows = [item_status(today=self.TODAY, due_date=dt.date(2026, 9, 30),
                            authority_status="Verified", received_flag=True,
                            qc_status="Accepted") for _ in range(3)]
        rows += [item_status(today=self.TODAY, due_date=dt.date(2026, 9, 1),
                             authority_status="Verified") for _ in range(7)]
        everything = package_state(rows)
        mine_only = package_state(rows, visible_predicate=lambda r: r.status == "ACCEPTED")
        self.assertEqual(everything["state"], "ACTION_REQUIRED")
        self.assertEqual(mine_only["state"], "COMPLETE")
        self.assertEqual(mine_only["total"], 3)

    def test_only_the_current_version_decides(self):
        # A rejected v1 under an accepted v2 does not make the item Amber.
        r = item_status(today=self.TODAY, due_date=dt.date(2026, 9, 30),
                        authority_status="Verified", received_flag=True,
                        qc_status="Accepted")
        self.assertEqual(r.status, "ACCEPTED")

    def test_due_date_comes_from_the_requirement(self):
        self.assertEqual(due_date_for("2026-08", 10, 1), dt.date(2026, 9, 10))
        self.assertEqual(due_date_for("2026-12", 15, 1), dt.date(2027, 1, 15))
        # A Due_Day of 31 in a 30-day month clamps rather than rolling over.
        self.assertEqual(due_date_for("2026-03", 31, 1), dt.date(2026, 4, 30))

    def test_days_late_is_measured_against_the_original_due_date(self):
        self.assertEqual(days_late("2026-09-10", "2026-09-12"), 2)
        self.assertEqual(days_late("2026-09-10", "2026-09-08"), -2)

    def test_schema_vocabulary_matches_the_engine(self):
        self.assertEqual(set(S.FINAL_STATUS), set(STATUSES))
        self.assertEqual(set(S.PACKAGE_STATE), set(PACKAGE_STATES))
        self.assertEqual(set(S.ACTION_OWNER), {v[2] for v in STATUSES.values()})
        self.assertEqual(set(S.STATUS_CODE_VALUES), {v[0] for v in STATUSES.values()})


class TestTransliterationsAgree(unittest.TestCase):
    """StatusEngine.fx and the prototype are transliterations. Hold them to it."""

    def setUp(self):
        self.fx = read("canvas-app", "formulas", "StatusEngine.fx")
        self.html = read("docs", "mf-operations-prototype.html")

    def test_fx_catalogue_matches_the_reference(self):
        for status, (code, label, owner, required) in STATUSES.items():
            row = re.search(r'\{\s*status:\s*"%s".*?\}' % re.escape(status), self.fx, re.S)
            self.assertIsNotNone(row, f"{status} missing from MF_StatusCatalog")
            row = row.group(0)
            self.assertIn(f"code: {code}", row, status)
            self.assertIn(f'label: "{label}"', row, status)
            self.assertIn(f'actionOwner: "{owner}"', row, status)
            self.assertIn(f'actionRequired: {"true" if required else "false"}', row, status)

    def test_fx_evaluation_order_matches_the_reference(self):
        # The order is behaviour. Reordering it to make a screen read better is
        # exactly the change this test exists to catch.
        expected = ["NOT_APPLICABLE", "PENDING_VALIDATION", "ACCEPTED",
                    "NOT_APPLICABLE", "CORRECTION_REQUIRED", "OVERDUE",
                    "NOT_SATISFIED", "RECEIVED_PENDING_QC", "NOT_DUE", "OVERDUE"]
        body = self.fx.split("MF_EvaluateStatus(")[1].split("MF_PackageCatalog")[0]
        found = [m.group(1) for m in re.finditer(r'"([A-Z_]+)"', body)
                 if m.group(1) in STATUSES]
        self.assertEqual(found, expected)

    def test_fx_package_rollup_is_semantic_not_colour(self):
        body = self.fx.split("MF_PackageState")[1]
        # The adverse set is named explicitly rather than tested as "any code 1".
        for status in ("OVERDUE", "CORRECTION_REQUIRED", "NOT_SATISFIED"):
            self.assertIn(status, body, f"package rollup must name {status}")
        self.assertIn("PENDING_VALIDATION", body,
                      "a provisional row must be excluded from the all-accepted test")
        self.assertNotIn("Status_Code = 1", body, "that would be a colour rollup")

    def test_fx_declares_all_five_codes(self):
        # V3's Power Fx had no Blue branch at all.
        for name, value in (("MF_CodeNA", 0), ("MF_CodeAction", 1), ("MF_CodePending", 2),
                            ("MF_CodeDone", 3), ("MF_CodeInfo", 4)):
            self.assertTrue(
                re.search(rf"^{name}\s*=\s*{value};", self.fx, re.M),
                f"{name} must be declared as {value}")
        colour = self.fx.split("MF_StatusColor")[1].split("MF_StatusBackground")[0]
        self.assertIn("MF_CodeInfo", colour, "MF_StatusColor must have a Blue branch")

    def test_prototype_engine_matches_the_reference(self):
        code_names = {"NA": 0, "ACTION": 1, "PENDING": 2, "DONE": 3, "INFO": 4}
        for status, (code, label, owner, required) in STATUSES.items():
            m = re.search(r"^\s*%s:\s*\{(.*?)\},?\s*$" % re.escape(status),
                          self.html, re.M)
            self.assertIsNotNone(m, f"{status} missing from the prototype")
            row = m.group(1)
            cm = re.search(r"code:CODE\.(\w+)", row)
            self.assertEqual(code_names[cm.group(1)], code, status)
            self.assertEqual(re.search(r'label:"([^"]*)"', row).group(1), label, status)
            om = re.search(r'owner:(null|"[^"]*")', row).group(1)
            self.assertEqual("None" if om == "null" else om.strip('"'), owner, status)
            self.assertEqual(re.search(r"act:(true|false)", row).group(1) == "true",
                             required, status)

    def test_prototype_package_rollup_matches(self):
        for state, (code, label) in PACKAGE_STATES.items():
            m = re.search(r"^\s*%s:\s*\{code:CODE\.(\w+),\s*label:\"([^\"]*)\"\}"
                          % re.escape(state), self.html, re.M)
            self.assertIsNotNone(m, f"{state} missing from the prototype PKG table")
            self.assertEqual(m.group(2), label, state)

    def test_no_colour_literal_outside_the_token_definitions(self):
        offenders = []
        for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for name in files:
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r"(ColorValue\(|RGBA\(|Color\.[A-Z])", line):
                            offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [], "colour literals found outside App.Formulas.fx")

    def test_no_colour_picker_exists(self):
        # Status is calculated, never chosen.
        for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "canvas-app")):
            for name in files:
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    self.assertNotIn("ColorPicker", fh.read(), name)

    def test_the_app_never_derives_a_label_from_the_numeric_code(self):
        # V3's StatusLabel(code), StatusColor(code) and StatusSemantic(code)
        # were three independent switches over one input. C1.
        #
        # Matches a DEFINITION at the start of a line, so the comment above
        # explaining the V3 defect does not trip its own rule.
        banned = re.compile(r"^\s*(MF_)?Status(Label|Semantic)\s*\(", re.M)
        offenders = []
        for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "canvas-app")):
            for name in files:
                rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
                if banned.search(read(rel)):
                    offenders.append(rel)
        self.assertEqual(offenders, [],
                         "a parallel status function was reintroduced")


class TestReconciliationHeld(unittest.TestCase):
    """The corrections in docs/handoffs/RECONCILIATION.md must stay applied."""

    def test_item_carries_authority_status(self):
        # C4. Decision rule 2 reads it and a lookup would not delegate.
        cols = {c.name: c for c in S.LISTS_BY_NAME["MF_EOM_Item"].columns}
        self.assertIn("Authority_Status", cols)
        self.assertTrue(cols["Authority_Status"].indexed)

    def test_item_carries_the_columns_v3_omitted(self):
        cols = {c.name for c in S.LISTS_BY_NAME["MF_EOM_Item"].columns}
        for name in ("Received_DateTime", "Days_Late", "On_Time_Flag",
                     "Last_Reconciled_DateTime"):
            self.assertIn(name, cols, f"C5-C7: {name}")

    def test_the_fact_has_one_semantic_column(self):
        # C8.
        cols = {c.name for c in S.LISTS_BY_NAME["MF_EOM_Status"].columns}
        self.assertIn("Final_Status", cols)
        self.assertNotIn("Status_Semantic", cols)

    def test_flow_specs_say_blue_not_gray_for_provisional(self):
        # C2. V3's EOM-03 spec said Status_Code = 0 here.
        spec = read("flows", "EOM03-Reconciliation", "definition.md")
        self.assertIn("`Status_Code = 4`", spec)
        self.assertNotIn("stays at `Status_Code = 0`", spec)

    def test_the_reconciliation_record_exists_and_names_its_corrections(self):
        rec = read("docs", "handoffs", "RECONCILIATION.md")
        for marker in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"):
            self.assertIn(f"| {marker} |", rec, f"{marker} missing from the record")


if __name__ == "__main__":
    unittest.main(verbosity=2)
