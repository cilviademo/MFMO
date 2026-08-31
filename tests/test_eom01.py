#!/usr/bin/env python3
"""EOM-01 acceptance tests.

Build order step 4: EOM-01 must produce correct rows before any screen is
built. Every UI decision downstream depends on the shape of this data, so the
three properties that matter are asserted here rather than discovered later.
"""

import csv
import datetime as dt
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from generate_expected_items import (  # noqa: E402
    generate, load_csv, item_key, applies_to_operating_model,
    FREQUENCY_TO_PERIOD_TYPE,
)

CONFIG = os.path.join(ROOT, "configuration")
AS_OF = dt.date(2026, 9, 20)


def seeds():
    return dict(
        requirements=load_csv(os.path.join(CONFIG, "requirements.csv")),
        installations=load_csv(os.path.join(CONFIG, "installations.sample.csv")),
        facilities=load_csv(os.path.join(CONFIG, "facilities.sample.csv")),
        contracts=load_csv(os.path.join(CONFIG, "contracts.sample.csv")),
        periods=load_csv(os.path.join(CONFIG, "reporting_periods.sample.csv")),
    )


class TestIdempotency(unittest.TestCase):
    def test_second_run_creates_nothing(self):
        rows1, stats1 = generate(**seeds(), as_of=AS_OF, run_id="run-1")
        self.assertGreater(stats1["created"], 0)

        rows2, stats2 = generate(**seeds(), as_of=AS_OF, run_id="run-2", existing=rows1)
        self.assertEqual(stats2["created"], 0, "a second run created rows")
        self.assertEqual(set(rows1), set(rows2), "the key set changed between runs")

    def test_item_ids_survive_a_second_run(self):
        rows1, _ = generate(**seeds(), as_of=AS_OF, run_id="run-1")
        rows2, _ = generate(**seeds(), as_of=AS_OF, run_id="run-2", existing=rows1)
        for key in rows1:
            self.assertEqual(rows1[key]["EOM_Item_ID"], rows2[key]["EOM_Item_ID"], key)

    def test_a_run_does_not_reset_a_submission_or_a_qc_return(self):
        rows, _ = generate(**seeds(), as_of=AS_OF, run_id="run-1")
        key = next(iter(rows))
        # Simulate an uploaded, then returned, item with a moved suspense date.
        rows[key]["Current_Submission_ID"] = "sub-123"
        rows[key]["Current_Version_Number"] = 2
        rows[key]["Suspense_Date"] = "2026-12-31"
        rows[key]["_qc_status"] = "RETURNED"

        rows2, _ = generate(**seeds(), as_of=AS_OF, run_id="run-2", existing=rows)
        self.assertEqual(rows2[key]["Current_Submission_ID"], "sub-123")
        self.assertEqual(rows2[key]["Current_Version_Number"], 2)
        self.assertEqual(rows2[key]["Suspense_Date"], "2026-12-31")
        self.assertEqual(rows2[key]["Status_Code"], "RETURNED")


class TestFacilityIdIsNullNotEmptyString(unittest.TestCase):
    def test_installation_and_contract_rows_carry_none(self):
        rows, _ = generate(**seeds(), as_of=AS_OF)
        checked = 0
        for row in rows.values():
            if row["Requirement_Scope"] in ("Installation", "Contract"):
                checked += 1
                self.assertIsNone(row["Facility_ID"], row["Title"])
                # The distinction that matters: not "" and not "  ".
                self.assertNotEqual(row["Facility_ID"], "", row["Title"])
        self.assertGreater(checked, 0, "no installation- or contract-scope rows were generated")

    def test_facility_rows_carry_a_real_id(self):
        rows, _ = generate(**seeds(), as_of=AS_OF)
        for row in rows.values():
            if row["Requirement_Scope"] == "Facility":
                self.assertTrue(row["Facility_ID"], row["Title"])

    def test_scope_is_a_delegable_substitute_for_asking_about_null(self):
        # Delegation.fx: IsBlank(Facility_ID) does not delegate, so the app
        # asks about Requirement_Scope instead. The two must agree exactly.
        rows, _ = generate(**seeds(), as_of=AS_OF)
        by_null = {k for k, r in rows.items() if r["Facility_ID"] is None}
        by_scope = {k for k, r in rows.items()
                    if r["Requirement_Scope"] in ("Installation", "Contract")}
        self.assertEqual(by_null, by_scope)

    def test_installation_id_is_populated_on_every_row(self):
        rows, _ = generate(**seeds(), as_of=AS_OF)
        for row in rows.values():
            self.assertTrue(row["Installation_ID"], row["Title"])
            self.assertTrue(row["Portfolio_ID"], row["Title"])


class TestOperatingModelFollowsTheFacility(unittest.TestCase):
    """One base can run a legacy DFAC and a Food 2.0 cafe."""

    def test_the_two_liberty_facilities_generate_different_sets(self):
        s = seeds()
        # Activate the Food 2.0-only requirement so the split is visible with
        # both model-scoped rows in play, then confirm it again with the
        # shipped seed below.
        rows, _ = generate(**s, as_of=AS_OF)

        dfac = {r["Requirement_ID"] for r in rows.values()
                if r["Facility_ID"] == "FAC-FTLIB-01"}
        cafe = {r["Requirement_ID"] for r in rows.values()
                if r["Facility_ID"] == "FAC-FTLIB-02"}

        self.assertTrue(dfac, "the legacy DFAC generated no requirements")
        self.assertTrue(cafe, "the Food 2.0 cafe generated no requirements")
        self.assertNotEqual(dfac, cafe, "both facilities generated the same set")

        # REQ-002 is scoped Legacy_DFAC;Contractor_Operated.
        self.assertIn("REQ-002", dfac)
        self.assertNotIn("REQ-002", cafe)

    def test_the_operating_model_filter_is_only_applied_at_facility_scope(self):
        # An installation has no operating model, and a contract may span
        # facilities running different ones.
        s = seeds()
        rows, _ = generate(**s, as_of=AS_OF)
        contract_rows = [r for r in rows.values() if r["Requirement_Scope"] == "Contract"]
        self.assertTrue(contract_rows, "REQ-008 generated no contract-scope rows")

    def test_empty_applies_to_means_every_model(self):
        req = {"Applies_To_Operating_Model": ""}
        for model in ("Legacy_DFAC", "Food_2_0", "Hybrid", "Contractor_Operated"):
            self.assertTrue(applies_to_operating_model(req, model))

    def test_a_scoped_requirement_excludes_other_models(self):
        req = {"Applies_To_Operating_Model": "Food_2_0;Hybrid"}
        self.assertTrue(applies_to_operating_model(req, "Food_2_0"))
        self.assertTrue(applies_to_operating_model(req, "Hybrid"))
        self.assertFalse(applies_to_operating_model(req, "Legacy_DFAC"))


class TestCatalogueRespected(unittest.TestCase):
    def test_inactive_requirements_generate_nothing(self):
        s = seeds()
        inactive = {r["Requirement_ID"] for r in s["requirements"] if r["Is_Active"] == "FALSE"}
        self.assertEqual(len(inactive), 3)
        rows, _ = generate(**s, as_of=AS_OF)
        for row in rows.values():
            self.assertNotIn(row["Requirement_ID"], inactive, row["Title"])

    def test_inactive_facilities_and_installations_generate_nothing(self):
        s = seeds()
        rows, _ = generate(**s, as_of=AS_OF)
        self.assertFalse(any(r["Facility_ID"] == "FAC-FTLIB-99" for r in rows.values()))
        self.assertFalse(any(r["Installation_ID"] == "INST-FTEXM" for r in rows.values()))

    def test_frequency_selects_the_period_type(self):
        s = seeds()
        # The open period in the seed is a Month, so no Annual or Quarterly
        # requirement should expand against it.
        rows, _ = generate(**s, as_of=AS_OF)
        by_id = {r["Requirement_ID"]: r for r in s["requirements"]}
        for row in rows.values():
            freq = by_id[row["Requirement_ID"]]["Frequency"]
            self.assertEqual(FREQUENCY_TO_PERIOD_TYPE[freq], "Month", row["Title"])

    def test_the_eoy_requirement_expands_against_the_fiscal_year_period(self):
        s = seeds()
        # Open the fiscal-year period and confirm REQ-011 generates against it.
        for p in s["periods"]:
            if p["Period_ID"] == "FY26-EOY":
                p["Period_State"] = "OPEN"
        rows, _ = generate(**s, as_of=dt.date(2026, 10, 15))
        eoy = [r for r in rows.values() if r["Reporting_Period_ID"] == "FY26-EOY"]
        self.assertTrue(eoy, "the EOY period generated no items")
        self.assertEqual({r["Requirement_ID"] for r in eoy}, {"REQ-011"})
        # REQ-011 is Installation scope, so Facility_ID is null.
        for r in eoy:
            self.assertIsNone(r["Facility_ID"])
            self.assertEqual(r["Requirement_Scope"], "Installation")


class TestGeneratedStatus(unittest.TestCase):
    def test_a_provisional_requirement_past_suspense_stays_gray(self):
        rows, _ = generate(**seeds(), as_of=dt.date(2026, 12, 31))
        past = [r for r in rows.values()
                if r["Suspense_Date"] < "2026-12-31"]
        self.assertTrue(past)
        for row in past:
            self.assertEqual(row["Requirement_Verification_Status"], "UNVERIFIED")
            self.assertEqual(row["Status_Code"], "PROVISIONAL_OVERDUE", row["Title"])
            self.assertEqual(row["Final_Status"], "Gray", row["Title"])
            self.assertEqual(row["Action_Owner_Role"], "Program", row["Title"])

    def test_no_generated_row_is_red_today(self):
        rows, _ = generate(**seeds(), as_of=dt.date(2027, 6, 1))
        self.assertFalse(any(r["Final_Status"] == "Red" for r in rows.values()))

    def test_every_row_carries_all_four_status_fields(self):
        rows, _ = generate(**seeds(), as_of=AS_OF)
        for row in rows.values():
            for field in ("Status_Code", "Status_Semantic", "Final_Status",
                          "Action_Owner_Role", "Action_Required"):
                self.assertIn(field, row, row["Title"])
                self.assertIsNotNone(row[field], f"{row['Title']}.{field}")


class TestItemKey(unittest.TestCase):
    def test_the_key_is_the_idempotency_key(self):
        self.assertEqual(
            item_key("Facility", "FAC-FTLIB-01", "HCR", "FY26-P11"),
            "Facility|FAC-FTLIB-01|HCR|FY26-P11",
        )

    def test_keys_are_unique_across_a_run(self):
        rows, _ = generate(**seeds(), as_of=AS_OF)
        titles = [r["Title"] for r in rows.values()]
        self.assertEqual(len(titles), len(set(titles)))

    def test_scope_prefixes_prevent_a_collision(self):
        # An installation and a facility could share an id string; the scope
        # prefix is what keeps their keys distinct.
        self.assertNotEqual(
            item_key("Facility", "X", "HCR", "FY26-P11"),
            item_key("Installation", "X", "HCR", "FY26-P11"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
