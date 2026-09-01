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
    item_status, package_state, days_late, nominal_date, effective_date,
    resolve_dates, is_non_duty_day, on_time_facts,
    STATUSES, PACKAGE_STATES, CODE_COLOUR, QC_RETURNING, ADVERSE,
)
import eom_schema as S  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


with open(os.path.join(ROOT, "tests", "fixtures", "status_cases.json")) as _fh:
    FIXTURES = json.load(_fh)


class TestFixtureCases(unittest.TestCase):
    def test_every_case(self):
        for case in FIXTURES["cases"]:
            with self.subTest(case["name"]):
                dates = case.get("dates", {})
                r = item_status(
                    today=case["today"],
                    effective_due_date=dates.get("effective_due_date",
                                                 FIXTURES["effective_due_date"]),
                    effective_final_call_date=dates.get(
                        "effective_final_call_date",
                        FIXTURES["effective_final_call_date"]),
                    **case["input"])
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

    DUE = dt.date(2026, 9, 8)
    FINAL = dt.date(2026, 9, 10)

    def ev(self, today, **kw):
        kw.setdefault("authority_status", "VERIFIED")
        return item_status(today=today, effective_due_date=self.DUE,
                           effective_final_call_date=self.FINAL, **kw)

    def test_six_visual_states_not_five(self):
        codes = {v[0] for v in STATUSES.values()}
        self.assertEqual(codes, {0, 1, 2, 3, 4, 5})
        self.assertEqual(CODE_COLOUR[5], "Amber")
        self.assertEqual(CODE_COLOUR[2], "Yellow")

    def test_amber_and_yellow_are_different_states(self):
        # Amber means TIME RISK and belongs to the base. Yellow means SOMEBODY
        # ELSE HAS IT. Collapsing them tells a DFAC manager that a document
        # they filed on time and one they never sent are the same problem.
        late = self.ev(dt.date(2026, 9, 9))
        review = self.ev(dt.date(2026, 9, 9), received_flag=True,
                         qc_status="Pending Review")
        self.assertEqual(late.code, 5)
        self.assertEqual(review.code, 2)
        self.assertNotEqual(late.code, review.code)
        self.assertEqual(late.actionOwner, "Facility")
        self.assertEqual(review.actionOwner, "Reviewer")

    def test_colour_carries_ownership(self):
        owners = {}
        for status, (code, _label, owner, _req) in STATUSES.items():
            owners.setdefault(code, set()).add(owner)
        # Red, Amber: always the base. Yellow: always the reviewer.
        self.assertEqual(owners[1], {"Facility"})
        self.assertEqual(owners[5], {"Facility"})
        self.assertEqual(owners[2], {"Reviewer"})
        self.assertEqual(owners[3], {"None"})
        self.assertEqual(owners[0], {"None"})

    def test_the_late_window_exists(self):
        # The only week in the cycle where a reminder still changes the outcome.
        self.assertEqual(self.ev(dt.date(2026, 9, 8)).status, "NOT_DUE")
        self.assertEqual(self.ev(dt.date(2026, 9, 9)).status, "LATE")
        self.assertEqual(self.ev(dt.date(2026, 9, 10)).status, "LATE")
        self.assertEqual(self.ev(dt.date(2026, 9, 11)).status, "OVERDUE")

    def test_an_unverified_requirement_never_drives_an_adverse_status(self):
        for status in ("UNVERIFIED", "PROPOSED"):
            for today in (dt.date(2026, 9, 11), dt.date(2027, 6, 1)):
                r = item_status(today=today, effective_due_date=self.DUE,
                                effective_final_call_date=self.FINAL,
                                authority_status=status)
                self.assertEqual(r.status, "PENDING_VALIDATION", f"{status} {today}")
                self.assertEqual(r.code, 4, "provisional is Blue, not Red and not Gray")
                self.assertEqual(r.actionOwner, "Admin",
                                 "the action is to verify the requirement")
                self.assertFalse(r.actionRequired)

    def test_the_seeded_catalogue_is_mostly_verified_now(self):
        # Eleven of thirteen moved to VERIFIED when the procedures deck landed,
        # so rule 2 now applies to almost nothing and a missed 1119 turns red.
        import csv
        with open(os.path.join(ROOT, "configuration", "requirements.csv"),
                  encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 13)
        verified = [r for r in rows if r["Authority_Status"] == "VERIFIED"]
        self.assertGreaterEqual(len(verified), 9)
        for row in verified:
            self.assertTrue(row["Authority_Reference"].strip(),
                            f"{row['Requirement_ID']} is VERIFIED with no citation")
        # An active, required, verified requirement CAN go red.
        live = [r for r in rows if r["Active_Flag"] == "TRUE"
                and r["Required_Flag"] == "TRUE" and r["Authority_Status"] == "VERIFIED"]
        self.assertTrue(live)
        r = self.ev(dt.date(2026, 9, 30))
        self.assertEqual(r.code, 1)

    def test_the_four_returning_verdicts_collapse_to_one_status(self):
        # The engine does not need four states to say "it came back"; the
        # submitter needs four reasons, and those live on the submission.
        for verdict in QC_RETURNING:
            r = self.ev(dt.date(2026, 9, 9), received_flag=True, qc_status=verdict)
            self.assertEqual(r.status, "RETURNED", verdict)
            self.assertEqual(r.code, 1, verdict)
            self.assertEqual(r.actionOwner, "Facility", verdict)

    def test_a_recall_reverts_to_the_date_state(self):
        # A recall is the submitter withdrawing before review, not a rejection.
        for today, want in ((dt.date(2026, 9, 3), "NOT_DUE"),
                            (dt.date(2026, 9, 9), "LATE"),
                            (dt.date(2026, 9, 15), "OVERDUE")):
            r = self.ev(today, received_flag=True, qc_status="Recalled")
            self.assertEqual(r.status, want, str(today))

    def test_wrong_document_is_not_permanently_red_by_fiat(self):
        before = self.ev(dt.date(2026, 9, 9), received_flag=True,
                         qc_status="Wrong Document")
        after = self.ev(dt.date(2026, 9, 15), received_flag=True,
                        qc_status="Wrong Document")
        self.assertEqual(before.status, "NOT_SATISFIED")
        self.assertEqual(after.status, "OVERDUE")

    def test_final_status_and_status_code_are_independent(self):
        by_code = {}
        for status, (code, *_rest) in STATUSES.items():
            by_code.setdefault(code, []).append(status)
        self.assertGreater(len(by_code[1]), 1, "Red covers more than one status")
        self.assertGreater(len(by_code[4]), 1, "Blue covers more than one status")

    def test_every_status_carries_a_label(self):
        for status, (code, label, owner, required) in STATUSES.items():
            self.assertTrue(label.strip(), f"{status} has no label")
            self.assertIn(owner, ("Facility", "Reviewer", "Admin", "None"))

    # ---- dates ---------------------------------------------------------

    def test_nominal_date_comes_from_the_requirement(self):
        self.assertEqual(nominal_date("2026-08", 5, 1), dt.date(2026, 9, 5))
        self.assertEqual(nominal_date("2026-08", 10, 1), dt.date(2026, 9, 10))
        self.assertEqual(nominal_date("2026-12", 5, 1), dt.date(2027, 1, 5))
        # A Due_Day of 31 in a 30-day month clamps rather than rolling over.
        self.assertEqual(nominal_date("2026-03", 31, 1), dt.date(2026, 4, 30))
        self.assertIsNone(nominal_date("2026-08", None, 1))

    def test_a_weekend_suspense_moves_to_the_next_duty_day(self):
        # 5 Sep 2026 is a Saturday. A nominal suspense landing on a Saturday
        # cannot be the date someone is held to.
        self.assertEqual(effective_date(dt.date(2026, 9, 5)), dt.date(2026, 9, 7))

    def test_a_holiday_moves_it_further(self):
        holidays = [{"Date": "2026-09-07", "Name": "Labor Day",
                     "Scope_Type": "Enterprise", "Scope_ID": "", "Active_Flag": True}]
        self.assertEqual(effective_date(dt.date(2026, 9, 5), non_duty_days=holidays),
                         dt.date(2026, 9, 8))

    def test_a_wing_down_day_applies_only_in_scope(self):
        down = [{"Date": "2026-09-07", "Name": "Wing down day",
                 "Scope_Type": "Installation", "Scope_ID": "ALTUS_AFB",
                 "Active_Flag": True}]
        self.assertTrue(is_non_duty_day("2026-09-07", down, {"ALTUS_AFB"}))
        self.assertFalse(is_non_duty_day("2026-09-07", down, {"KADENA_AB"}))

    def test_no_adjustment_policy_leaves_the_date_alone(self):
        self.assertEqual(effective_date(dt.date(2026, 9, 5), policy="NO_ADJUSTMENT"),
                         dt.date(2026, 9, 5))

    def test_a_runaway_non_duty_run_raises_rather_than_looping(self):
        forever = [{"Date": (dt.date(2026, 9, 5) + dt.timedelta(days=n)).isoformat(),
                    "Name": "bad import", "Scope_Type": "Enterprise",
                    "Scope_ID": "", "Active_Flag": True} for n in range(30)]
        with self.assertRaises(ValueError):
            effective_date(dt.date(2026, 9, 5), non_duty_days=forever)

    def test_resolve_dates_flags_the_adjustment(self):
        d = resolve_dates("2026-08", {"Due_Day": 5, "Final_Due_Day": 10})
        self.assertEqual(d["Nominal_Due_Date"], dt.date(2026, 9, 5))
        self.assertEqual(d["Effective_Due_Date"], dt.date(2026, 9, 7))
        self.assertTrue(d["Due_Date_Adjusted"])
        # The 10th is a Thursday, so the final call does not move.
        self.assertEqual(d["Nominal_Final_Call_Date"], d["Effective_Final_Call_Date"])

    def test_status_evaluates_against_the_effective_date(self):
        # 7 Sep, the effective date, is not yet late even though 5 Sep passed.
        d = resolve_dates("2026-08", {"Due_Day": 5, "Final_Due_Day": 10})
        r = item_status(today=dt.date(2026, 9, 7),
                        effective_due_date=d["Effective_Due_Date"],
                        effective_final_call_date=d["Effective_Final_Call_Date"],
                        authority_status="VERIFIED")
        self.assertEqual(r.status, "NOT_DUE")

    # ---- on time is two questions --------------------------------------

    def test_on_time_is_two_independent_facts(self):
        # Uploaded 4 Sep, returned, accepted 12 Sep: submitted on time AND
        # final evidence late. Both true.
        facts = on_time_facts(initial_submitted="2026-09-04",
                              acceptable_evidence="2026-09-12",
                              effective_due_date=self.DUE,
                              effective_final_call_date=self.FINAL)
        self.assertTrue(facts["Initial_Submission_On_Time"])
        self.assertFalse(facts["Final_Evidence_On_Time"])

    def test_on_time_is_unknown_before_anything_arrives(self):
        facts = on_time_facts(initial_submitted=None, acceptable_evidence=None,
                              effective_due_date=self.DUE,
                              effective_final_call_date=self.FINAL)
        self.assertIsNone(facts["Initial_Submission_On_Time"])
        self.assertIsNone(facts["Final_Evidence_On_Time"])

    def test_days_late_measures_against_the_final_call(self):
        self.assertEqual(days_late(self.FINAL, today=dt.date(2026, 9, 15)), 5)
        self.assertEqual(days_late(self.FINAL, today=dt.date(2026, 9, 1)), 0)

    # ---- rollups --------------------------------------------------------

    def test_a_colour_rollup_would_be_wrong(self):
        statuses = ["ACCEPTED", "NOT_DUE", "NOT_DUE"]
        codes = [STATUSES[s][0] for s in statuses]
        self.assertNotIn(1, codes)
        self.assertNotIn(2, codes)
        self.assertEqual(package_state(statuses)["state"], "IN_PROGRESS")

    def test_late_and_returned_are_adverse_for_the_rollup(self):
        for status in ("LATE", "RETURNED", "OVERDUE", "NOT_SATISFIED"):
            self.assertIn(status, ADVERSE)
            self.assertEqual(package_state(["ACCEPTED", status])["state"],
                             "ACTION_REQUIRED", status)

    def test_rollup_respects_the_viewers_scope(self):
        rows = [self.ev(dt.date(2026, 9, 9), received_flag=True, qc_status="Accepted")
                for _ in range(3)]
        rows += [self.ev(dt.date(2026, 9, 15)) for _ in range(7)]
        self.assertEqual(package_state(rows)["state"], "ACTION_REQUIRED")
        mine = package_state(rows, visible_predicate=lambda r: r.status == "ACCEPTED")
        self.assertEqual(mine["state"], "COMPLETE")
        self.assertEqual(mine["total"], 3)

    def test_schema_vocabulary_matches_the_engine(self):
        self.assertEqual(set(S.FINAL_STATUS), set(STATUSES))
        self.assertEqual(set(S.PACKAGE_STATE), set(PACKAGE_STATES))
        self.assertEqual(set(S.ACTION_OWNER), {v[2] for v in STATUSES.values()})
        self.assertEqual(set(S.STATUS_CODE_VALUES), {v[0] for v in STATUSES.values()})
        self.assertEqual(set(S.QC_RETURNING), set(QC_RETURNING))


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
                    "NOT_APPLICABLE", "RETURNED", "OVERDUE", "NOT_SATISFIED",
                    "RECEIVED_PENDING_QC"]
        # Rule 5 (Recalled) and rules 10-12 delegate to MF_DateState and so
        # name no status literal here; MF_DateState is asserted separately.
        # Split at the DEFINITION of MF_DateState, not its call site in rule 5,
        # so the whole evaluation body is covered.
        body = self.fx.split("MF_EvaluateStatus(")[1].split("MF_DateState(Today: Date")[0]
        found = [m.group(1) for m in re.finditer(r'"([A-Z_]+)"', body)
                 if m.group(1) in STATUSES]
        self.assertEqual(found, expected)

    def test_fx_date_state_covers_the_three_time_branches(self):
        body = self.fx.split("MF_DateState(Today: Date")[1]
        for status in ("NOT_DUE", "LATE", "OVERDUE"):
            self.assertIn(f'"{status}"', body, status)

    def test_fx_evaluates_against_effective_dates(self):
        # Reporting uses nominal; evaluation must not.
        sig = self.fx.split("MF_EvaluateStatus(")[1].split("):")[0]
        self.assertIn("EffectiveDueDate", sig)
        self.assertIn("EffectiveFinalCallDate", sig)
        self.assertNotIn("NominalDueDate", sig,
                         "the engine must not evaluate against the policy date")

    def test_fx_package_rollup_is_semantic_not_colour(self):
        body = self.fx.split("MF_PackageState")[1]
        # The adverse set is named explicitly rather than tested as "any code 1".
        for status in ADVERSE:
            self.assertIn(status, body, f"package rollup must name {status}")
        self.assertIn("PENDING_VALIDATION", body,
                      "a provisional row must be excluded from the all-accepted test")
        self.assertNotIn("Status_Code = 1", body, "that would be a colour rollup")

    def test_fx_declares_all_six_codes(self):
        # Every version up to v11 had no Blue branch at all.
        for name, value in (("MF_CodeNA", 0), ("MF_CodeRed", 1), ("MF_CodeYellow", 2),
                            ("MF_CodeGreen", 3), ("MF_CodeBlue", 4), ("MF_CodeAmber", 5)):
            self.assertTrue(
                re.search(rf"^{name}\s*=\s*{value};", self.fx, re.M),
                f"{name} must be declared as {value}")
        colour = self.fx.split("MF_StatusColor")[1].split("MF_StatusBackground")[0]
        for name in ("MF_CodeBlue", "MF_CodeAmber", "MF_CodeYellow"):
            self.assertIn(name, colour, f"MF_StatusColor must have a {name} branch")

    def test_the_prototype_is_marked_stale(self):
        # docs/mf-operations-prototype.html is the V3 prototype and predates the
        # six-state model, the two suspenses and the seven QC verdicts. It is
        # kept because its information architecture and security model are still
        # the reference, but it must not be mistaken for the current engine —
        # that is exactly how the Power Fx stayed wrong across four releases.
        notes = read("docs", "prototype-notes.md")
        self.assertIn("STALE", notes,
                      "prototype-notes.md must say plainly which parts of the "
                      "prototype no longer match the engine")
        html = read("docs", "mf-operations-prototype.html")
        self.assertIn("STALE", html[:4000],
                      "the prototype must carry the staleness banner in its own head")

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
                if name.endswith(".msapp"):
                    continue     # binary; the vendored donor -- see donor/README.md
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
                if name.endswith(".msapp"):
                    continue     # binary; the vendored donor -- see donor/README.md
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

    def test_item_carries_the_columns_earlier_versions_omitted(self):
        cols = {c.name for c in S.LISTS_BY_NAME["MF_EOM_Item"].columns}
        # C5 became the two on-time timestamps: a single Received_DateTime
        # cannot express "submitted on time, evidence late", which is the whole
        # point of tracking both.
        for name in ("Initial_Submitted_DateTime", "Acceptable_Evidence_DateTime",
                     "Initial_Submission_On_Time", "Final_Evidence_On_Time",
                     "Days_Late", "Last_Reconciled_DateTime"):
            self.assertIn(name, cols, name)
        self.assertNotIn("Received_DateTime", cols,
                         "superseded by the two on-time timestamps")

    def test_the_fact_has_one_semantic_column(self):
        # C8.
        cols = {c.name for c in S.LISTS_BY_NAME["MF_EOM_Status"].columns}
        self.assertIn("Final_Status", cols)
        self.assertNotIn("Status_Semantic", cols)

    def test_flow_specs_say_blue_not_gray_for_provisional(self):
        # C2. Every earlier EOM-03 spec said Status_Code = 0 here.
        spec = read("flows", "EOM03-Reconciliation", "definition.md")
        self.assertIn("`Status_Code = 4`", spec)
        self.assertNotIn("stays at `Status_Code = 0`", spec)

    def test_item_carries_both_date_pairs(self):
        cols = {c.name for c in S.LISTS_BY_NAME["MF_EOM_Item"].columns}
        for name in ("Nominal_Due_Date", "Effective_Due_Date",
                     "Nominal_Final_Call_Date", "Effective_Final_Call_Date",
                     "Due_Date_Adjusted"):
            self.assertIn(name, cols, name)

    def test_final_status_can_store_what_the_engine_produces(self):
        # C11. v11's choice list omitted LATE and RETURNED while its own
        # decision order produced both.
        choices = set(S.LISTS_BY_NAME["MF_EOM_Item"].columns[
            [c.name for c in S.LISTS_BY_NAME["MF_EOM_Item"].columns].index("Final_Status")].choices)
        self.assertEqual(choices, set(STATUSES))

    def test_no_internal_name_exceeds_the_sharepoint_limit(self):
        # C12. Current_Acceptable_Evidence_DateTime was 35 characters.
        for lst in S.LISTS:
            for col in lst.columns:
                self.assertLessEqual(len(col.name), 32, f"{lst.name}.{col.name}")

    def test_the_reconciliation_record_exists_and_names_its_corrections(self):
        rec = read("docs", "handoffs", "RECONCILIATION.md")
        for marker in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"):
            self.assertIn(f"| {marker} |", rec, f"{marker} missing from the record")


if __name__ == "__main__":
    unittest.main(verbosity=2)
