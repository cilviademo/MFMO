#!/usr/bin/env python3
"""EOM-01 acceptance tests.

Build order step 4: EOM-01 must produce correct rows before any screen is
built. The three properties that matter are asserted here rather than
discovered in a tenant.
"""

import datetime as dt
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from generate_expected_items import (  # noqa: E402
    generate, load_csv, item_id_for, frequency_applies,
    model_applies, facility_type_applies,
)

CONFIG = os.path.join(ROOT, "configuration")
PERIOD = "2026-08"
TODAY = dt.date(2026, 9, 12)


def seeds():
    return dict(
        requirements=load_csv(os.path.join(CONFIG, "requirements.csv")),
        installations=load_csv(os.path.join(CONFIG, "installations.sample.csv")),
        facilities=load_csv(os.path.join(CONFIG, "facilities.sample.csv")),
    )


def run(period=PERIOD, today=TODAY, existing=None, **overrides):
    s = seeds()
    s.update(overrides)
    return generate(period=period, today=today, existing=existing, **s)


class TestIdempotency(unittest.TestCase):
    def test_a_second_run_creates_nothing(self):
        rows1, stats1 = run()
        self.assertGreater(stats1["created"], 0)
        rows2, stats2 = run(existing=rows1)
        self.assertEqual(stats2["created"], 0, "a second run created rows")
        self.assertEqual(set(rows1), set(rows2), "the key set changed between runs")

    def test_the_item_id_is_deterministic(self):
        self.assertEqual(item_id_for("2026-08", "FAC-LACK-1234", "REQ-001"),
                         "2026-08|FAC-LACK-1234|REQ-001")
        # Re-generating produces identical ids, which is what makes the upsert
        # safe after a partial failure.
        a, _ = run()
        b, _ = run()
        self.assertEqual(sorted(a), sorted(b))

    def test_a_run_never_resets_a_submission_or_a_qc_decision(self):
        rows, _ = run()
        key = next(iter(rows))
        rows[key].update({
            "Current_Submission_ID": "SUB-123",
            "Received_Flag": True,
            "Final_Status": "CORRECTION_REQUIRED",
            "Status_Code": 2,
            "Correction_Due": "2026-10-01",
            "Waived_Flag": True,
        })
        rows2, _ = run(existing=rows)
        for field in ("Current_Submission_ID", "Received_Flag", "Final_Status",
                      "Status_Code", "Correction_Due", "Waived_Flag"):
            self.assertEqual(rows2[key][field], rows[key][field], field)


class TestFacilityIdIsNullNotEmptyString(unittest.TestCase):
    def test_installation_and_contract_rows_carry_none(self):
        rows, _ = run()
        checked = 0
        for row in rows.values():
            if row["Requirement_Scope"] in ("Installation", "Contract"):
                checked += 1
                self.assertIsNone(row["Facility_ID"], row["EOM_Item_ID"])
                # The distinction that matters: not "" and not "  ".
                self.assertNotEqual(row["Facility_ID"], "", row["EOM_Item_ID"])
        self.assertGreater(checked, 0, "no installation- or contract-scope rows generated")

    def test_facility_rows_carry_a_real_id(self):
        rows, _ = run()
        for row in rows.values():
            if row["Requirement_Scope"] == "Facility":
                self.assertTrue(row["Facility_ID"], row["EOM_Item_ID"])

    def test_scope_is_a_delegable_substitute_for_asking_about_null(self):
        # IsBlank(Facility_ID) does not delegate, so the app filters on
        # Requirement_Scope instead. The two must agree exactly, and the
        # DEPLOYMENT.md two-view check is this assertion in the tenant.
        rows, _ = run()
        by_null = {k for k, r in rows.items() if r["Facility_ID"] is None}
        by_scope = {k for k, r in rows.items()
                    if r["Requirement_Scope"] in ("Installation", "Contract")}
        self.assertEqual(by_null, by_scope)

    def test_contract_rows_carry_a_contract_and_an_installation(self):
        rows, _ = run()
        contract_rows = [r for r in rows.values() if r["Requirement_Scope"] == "Contract"]
        self.assertTrue(contract_rows, "no contract-scope rows generated")
        for r in contract_rows:
            self.assertTrue(r["Contract_ID"])
            self.assertTrue(r["Installation_ID"])
            self.assertIsNone(r["Facility_ID"])

    def test_every_row_carries_portfolio_and_installation(self):
        # Both are denormalized because the portfolio filter is the first
        # server-side filter on every query.
        rows, _ = run()
        for r in rows.values():
            self.assertTrue(r["Installation_ID"], r["EOM_Item_ID"])
            self.assertTrue(r["Portfolio_ID"], r["EOM_Item_ID"])


class TestOperatingModelFollowsTheFacility(unittest.TestCase):
    """One base can run a legacy DFAC and a Food 2.0 cafe."""

    def test_the_two_lackland_facilities_generate_different_sets(self):
        rows, _ = run()
        dfac = {r["Requirement_ID"] for r in rows.values()
                if r["Facility_ID"] == "FAC-LACK-1234"}
        cafe = {r["Requirement_ID"] for r in rows.values()
                if r["Facility_ID"] == "FAC-LACK-CAFE"}
        self.assertTrue(dfac, "the legacy DFAC generated nothing")
        self.assertTrue(cafe, "the Food 2.0 cafe generated nothing")
        self.assertNotEqual(dfac, cafe, "both facilities generated the same set")
        # REQ-001 (1119) is Legacy/APF; REQ-011 (SAIIT) is Food 2.0.
        self.assertIn("REQ-001", dfac)
        self.assertNotIn("REQ-001", cafe)
        self.assertIn("REQ-011", cafe)
        self.assertNotIn("REQ-011", dfac)

    def test_facility_type_narrows_further(self):
        # Kiosks rarely file a 1119.
        rows, _ = run()
        kiosk = {r["Requirement_ID"] for r in rows.values()
                 if r["Facility_ID"] == "FAC-LACK-KIOSK"}
        self.assertNotIn("REQ-001", kiosk)
        self.assertEqual(kiosk, set(), "the kiosk should generate nothing in this seed")

    def test_a_facility_with_no_requirement_set_is_reported(self):
        # A configuration gap, not a facility with nothing to do. It would
        # otherwise sit silently green forever.
        _rows, stats = run()
        self.assertIn("FAC-LACK-KIOSK", stats["facilities_with_no_requirements"])

    def test_the_model_filter_is_applied_at_facility_scope_only(self):
        # An installation has no operating model, and a contract may span
        # facilities running different ones.
        rows, _ = run()
        self.assertTrue([r for r in rows.values() if r["Requirement_Scope"] == "Installation"])
        self.assertTrue([r for r in rows.values() if r["Requirement_Scope"] == "Contract"])

    def test_installation_scope_needs_a_matching_facility(self):
        # A base with no Food 2.0 operation does not owe a Food 2.0
        # installation return.
        rows, _ = run()
        sf1080_bases = {r["Installation_ID"] for r in rows.values()
                        if r["Requirement_ID"] == "REQ-007"}
        self.assertEqual(sf1080_bases, set(), "REQ-007 is inactive and must generate nothing")
        sik_legacy = {r["Installation_ID"] for r in rows.values()
                      if r["Requirement_ID"] == "REQ-003"}
        # Creech runs only Food 2.0, so it owes no Legacy/APF SIK bill.
        self.assertNotIn("INST-CREECH", sik_legacy)

    def test_all_applies_to_every_model(self):
        for model in ("Legacy/APF", "Food 2.0", "MAFFO/MAF", "AOR/CDS"):
            self.assertTrue(model_applies({"Applicable_Model": "All"}, model))
        self.assertFalse(model_applies({"Applicable_Model": "Food 2.0"}, "Legacy/APF"))

    def test_blank_facility_types_means_every_type(self):
        self.assertTrue(facility_type_applies({"Applicable_Facility_Types": ""}, "Kiosk"))
        self.assertFalse(facility_type_applies(
            {"Applicable_Facility_Types": "Main DFAC;MAF"}, "Kiosk"))


class TestCatalogueRespected(unittest.TestCase):
    def test_inactive_requirements_generate_nothing(self):
        s = seeds()
        inactive = {r["Requirement_ID"] for r in s["requirements"] if r["Active_Flag"] == "FALSE"}
        self.assertEqual(len(inactive), 3)
        rows, _ = run()
        for row in rows.values():
            self.assertNotIn(row["Requirement_ID"], inactive)

    def test_inactive_facilities_and_installations_generate_nothing(self):
        rows, _ = run()
        self.assertFalse(any(r["Facility_ID"] == "FAC-LACK-OLD" for r in rows.values()))
        self.assertFalse(any(r["Installation_ID"] == "INST-CLOSED" for r in rows.values()))

    def test_frequency_gates_the_period(self):
        self.assertTrue(frequency_applies("Monthly", "2026-08"))
        self.assertTrue(frequency_applies("Quarterly", "2026-09"))
        self.assertFalse(frequency_applies("Quarterly", "2026-08"))
        self.assertTrue(frequency_applies("Annual", "2026-09"))
        self.assertFalse(frequency_applies("Annual", "2026-08"))
        self.assertTrue(frequency_applies("Semiannual", "2026-03"))
        # Conditional requirements are never auto-generated.
        self.assertFalse(frequency_applies("Conditional", "2026-08"))

    def test_due_date_comes_from_the_requirement_row(self):
        rows, _ = run()
        by_req = {r["Requirement_ID"]: r for r in seeds()["requirements"]}
        for row in rows.values():
            req = by_req[row["Requirement_ID"]]
            self.assertTrue(row["Due_Date"].endswith(f"-{int(req['Due_Day']):02d}"),
                            f"{row['EOM_Item_ID']} due {row['Due_Date']}")


class TestGeneratedStatus(unittest.TestCase):
    def test_every_generated_row_is_provisional_today(self):
        # All twelve seeded requirements are UNVERIFIED, so rule 2 catches
        # every new row. This is the default path, not an edge case.
        rows, _ = run(today=dt.date(2027, 6, 1))
        for row in rows.values():
            self.assertEqual(row["Authority_Status"], "UNVERIFIED")
            self.assertEqual(row["Final_Status"], "PENDING_VALIDATION", row["EOM_Item_ID"])
            self.assertEqual(row["Status_Code"], 4, row["EOM_Item_ID"])
            self.assertEqual(row["Action_Owner"], "Admin")
            self.assertFalse(row["Action_Required"])

    def test_nothing_is_red_however_late_the_run(self):
        rows, _ = run(today=dt.date(2030, 1, 1))
        self.assertFalse(any(r["Status_Code"] == 1 for r in rows.values()))

    def test_verifying_a_requirement_changes_the_outcome(self):
        s = seeds()
        for r in s["requirements"]:
            if r["Requirement_ID"] == "REQ-001":
                r["Authority_Status"] = "Verified"
        rows, _ = run(today=dt.date(2026, 10, 1), requirements=s["requirements"])
        verified = [r for r in rows.values() if r["Requirement_ID"] == "REQ-001"]
        self.assertTrue(verified)
        for row in verified:
            self.assertEqual(row["Final_Status"], "OVERDUE")
            self.assertEqual(row["Status_Code"], 1)

    def test_every_row_carries_all_four_status_fields(self):
        rows, _ = run()
        for row in rows.values():
            for field in ("Final_Status", "Status_Code", "Action_Owner", "Action_Required"):
                self.assertIn(field, row)
                self.assertIsNotNone(row[field], f"{row['EOM_Item_ID']}.{field}")

    def test_generated_rows_match_the_schema(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import eom_schema as S
        declared = {c.name for c in S.LISTS_BY_NAME["MF_EOM_Item"].columns}
        rows, _ = run()
        for row in rows.values():
            extra = set(row) - declared
            self.assertEqual(extra, set(), f"undeclared columns: {extra}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
