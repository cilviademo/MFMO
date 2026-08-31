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
        installations=load_csv(os.path.join(CONFIG, "installations.csv")),
        facilities=load_csv(os.path.join(CONFIG, "facilities.csv")),
        non_duty_days=load_csv(os.path.join(CONFIG, "non-duty-days.sample.csv")),
    )


def run(period=PERIOD, today=TODAY, existing=None, **overrides):
    s = seeds()
    s.update(overrides)
    return generate(period=period, today=today, existing=existing, **s)


ONBOARDED = {i["Installation_ID"] for i in
             load_csv(os.path.join(CONFIG, "installations.csv"))
             if i["Generation_Enabled"] == "TRUE"}


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

    def test_contract_scope_is_dormant_in_r1_but_well_formed(self):
        # The only Contract-scope requirement is the Food 2.0 contractor
        # invoice, and Food 2.0 is deferred by decision, so nothing generates
        # today. The machinery is still asserted so it does not rot before the
        # handbook lands.
        s = seeds()
        contract_reqs = [r for r in s["requirements"]
                         if r["Requirement_Scope"] == "Contract"]
        self.assertTrue(contract_reqs, "the catalogue must still model contract scope")
        self.assertTrue(all(r["Active_Flag"] == "FALSE" for r in contract_reqs),
                        "R1 is Legacy-only; contract scope is Food 2.0")

        rows, _ = run()
        for r in rows.values():
            if r["Requirement_Scope"] == "Contract":
                self.assertTrue(r["Contract_ID"])
                self.assertTrue(r["Installation_ID"])
                self.assertIsNone(r["Facility_ID"])

    def test_activating_contract_scope_produces_null_facility_rows(self):
        # Prove the path rather than trusting it: activate the contractor
        # invoice and give a pilot facility a contract.
        s = seeds()
        for r in s["requirements"]:
            if r["Requirement_Scope"] == "Contract":
                r["Active_Flag"] = "TRUE"
                r["Required_Flag"] = "TRUE"
                r["Applicable_Model"] = "Legacy/APF"
        for f in s["facilities"]:
            if f["Installation_ID"] == "KADENA_AB" and f["Operating_Model"] == "Legacy/APF":
                f["Contract_ID"] = "CTR-TEST-001"
        rows, _ = run(requirements=s["requirements"], facilities=s["facilities"])
        contract_rows = [r for r in rows.values() if r["Requirement_Scope"] == "Contract"]
        self.assertTrue(contract_rows, "activating the requirement generated nothing")
        for r in contract_rows:
            self.assertEqual(r["Contract_ID"], "CTR-TEST-001")
            self.assertTrue(r["Installation_ID"])
            self.assertIsNone(r["Facility_ID"], "contract scope carries a NULL facility")

    def test_every_row_carries_portfolio_and_installation(self):
        # Both are denormalized because the portfolio filter is the first
        # server-side filter on every query.
        rows, _ = run()
        for r in rows.values():
            self.assertTrue(r["Installation_ID"], r["EOM_Item_ID"])
            self.assertTrue(r["Portfolio_ID"], r["EOM_Item_ID"])


class TestOnboardingGate(unittest.TestCase):
    """EOM-01 generates only where Generation_Enabled is TRUE."""

    def test_only_onboarded_installations_generate(self):
        rows, _ = run()
        self.assertTrue(rows, "the pilot set must generate something")
        for row in rows.values():
            self.assertIn(row["Installation_ID"], ONBOARDED, row["EOM_Item_ID"])

    def test_a_base_awaiting_onboarding_is_reported_not_silent(self):
        # FALSE reads as "not yet onboarded", never as compliant.
        _rows, stats = run()
        self.assertGreater(len(stats["installations_not_onboarded"]), 50)
        for iid in stats["installations_not_onboarded"]:
            self.assertNotIn(iid, ONBOARDED)

    def test_turning_the_gate_off_stops_generation_for_that_base(self):
        s = seeds()
        for i in s["installations"]:
            i["Generation_Enabled"] = "FALSE"
        rows, stats = run(installations=s["installations"])
        self.assertEqual(rows, {})
        self.assertEqual(stats["created"], 0)


class TestOperatingModelFollowsTheFacility(unittest.TestCase):
    """One base can run a legacy DFAC and a Food 2.0 cafe."""

    def test_a_mixed_model_base_generates_only_its_legacy_facilities(self):
        # Eglin runs Legacy/APF and Food 2.0 side by side. R1 is Legacy-only,
        # so the Food 2.0 facilities correctly generate nothing.
        rows, _ = run()
        facs = {f["Facility_ID"]: f for f in seeds()["facilities"]}
        generated = {r["Facility_ID"] for r in rows.values()
                     if r["Facility_ID"] and r["Installation_ID"] == "EGLIN_AFB"}
        self.assertTrue(generated, "Eglin generated no facility rows")
        for fid in generated:
            self.assertEqual(facs[fid]["Operating_Model"], "Legacy/APF", fid)
        food20 = {fid for fid, f in facs.items()
                  if f["Installation_ID"] == "EGLIN_AFB"
                  and f["Operating_Model"] == "Food 2.0"}
        self.assertTrue(food20, "the seed must contain a Food 2.0 facility at Eglin")
        self.assertEqual(generated & food20, set())

    def test_a_facility_with_no_operating_model_generates_nothing(self):
        # The twenty NO_DFAC registry rows. Recorded, not a fault, and never
        # read as compliant.
        rows, stats = run()
        self.assertEqual(len(stats["facilities_without_model"]), 20)
        no_model = set(stats["facilities_without_model"])
        for row in rows.values():
            self.assertNotIn(row["Facility_ID"], no_model)

    def test_an_unknown_facility_type_generates_rather_than_disappearing(self):
        # The QRG carries no facility type. Excluding on it would drop every
        # facility from every type-scoped requirement, and a base with no
        # expected rows is indistinguishable from a base with nothing due.
        self.assertTrue(facility_type_applies(
            {"Applicable_Facility_Types": "Main DFAC;MAF"}, ""))
        rows, stats = run()
        self.assertTrue([r for r in rows.values() if r["Requirement_Scope"] == "Facility"],
                        "type-scoped requirements generated no facility rows")
        self.assertTrue(stats["facilities_without_type"],
                        "facilities with no confirmed type must be reported")

    def test_a_known_type_outside_the_list_is_excluded(self):
        self.assertFalse(facility_type_applies(
            {"Applicable_Facility_Types": "Main DFAC;MAF"}, "Kiosk"))

    def test_the_model_filter_is_applied_at_facility_scope_only(self):
        rows, _ = run()
        self.assertTrue([r for r in rows.values()
                         if r["Requirement_Scope"] == "Installation"])

    def test_all_applies_to_every_model(self):
        for model in ("Legacy/APF", "Food 2.0", "MAFFO/MAF", "AOR/CDS"):
            self.assertTrue(model_applies({"Applicable_Model": "All"}, model))
        self.assertFalse(model_applies({"Applicable_Model": "Food 2.0"}, "Legacy/APF"))
        # A blank model matches nothing: a base with no feeding facility owes
        # no 1119.
        self.assertFalse(model_applies({"Applicable_Model": "All"}, ""))

    def test_installation_scope_needs_a_matching_facility(self):
        # A base with no Legacy operation does not owe a Legacy installation
        # return.
        rows, _ = run()
        facs = seeds()["facilities"]
        for row in rows.values():
            if row["Requirement_Scope"] != "Installation":
                continue
            models = {f["Operating_Model"] for f in facs
                      if f["Installation_ID"] == row["Installation_ID"]
                      and f["Active_Flag"] == "TRUE"}
            self.assertIn("Legacy/APF", models, row["EOM_Item_ID"])


class TestCatalogueRespected(unittest.TestCase):
    def test_inactive_requirements_generate_nothing(self):
        # Five are inactive: SIK and DAF 79 (retired against the procedures
        # deck), the two Food 2.0 placeholders (deferred by decision), and
        # mid-month inventory (on the record, not yet in scope).
        s = seeds()
        inactive = {r["Requirement_ID"] for r in s["requirements"]
                    if r["Active_Flag"] == "FALSE"}
        self.assertEqual(len(inactive), 5)
        rows, _ = run()
        for row in rows.values():
            self.assertNotIn(row["Requirement_ID"], inactive)

    def test_a_retired_requirement_stays_on_the_record(self):
        # SIK carries RETIRED_OR_NOT_APPLICABLE with the programme's wording,
        # so later guidance can reactivate it without a schema change. It is a
        # record of the decision, not a requirement.
        s = seeds()
        sik = [r for r in s["requirements"] if r["Document_Code"] == "SIK"]
        self.assertTrue(sik, "SIK must remain in the catalogue as a record")
        for r in sik:
            self.assertEqual(r["Active_Flag"], "FALSE")
            self.assertEqual(r["Authority_Status"], "RETIRED_OR_NOT_APPLICABLE")
            self.assertTrue(r["Authority_Reference"].strip())

    def test_inactive_facilities_and_installations_generate_nothing(self):
        s = seeds()
        inactive_f = {f["Facility_ID"] for f in s["facilities"] if f["Active_Flag"] != "TRUE"}
        inactive_i = {i["Installation_ID"] for i in s["installations"]
                      if i["Active_Flag"] != "TRUE"}
        rows, _ = run()
        for row in rows.values():
            self.assertNotIn(row["Facility_ID"], inactive_f)
            self.assertNotIn(row["Installation_ID"], inactive_i)

    def test_frequency_gates_the_period(self):
        def f(freq, period, month=None):
            return frequency_applies(
                {"Frequency": freq, "Applicable_Period_Month": month}, period)
        self.assertTrue(f("Monthly", "2026-08"))
        self.assertTrue(f("Quarterly", "2026-09"))
        self.assertFalse(f("Quarterly", "2026-08"))
        self.assertTrue(f("Semiannual", "2026-03"))
        # Annual keys off Applicable_Period_Month, defaulting to September.
        self.assertTrue(f("Annual", "2026-09"))
        self.assertFalse(f("Annual", "2026-08"))
        self.assertTrue(f("Annual", "2026-06", month="6"))
        self.assertFalse(f("Annual", "2026-09", month="6"))

    def test_conditional_requirements_are_never_auto_generated(self):
        # The 1119-1 is FIELD FEEDING, not a 1119 continuation. Auto-generating
        # it would put a permanent red row on every DFAC that ran no field
        # feeding exercise - the false overdue that teaches people to ignore
        # the dashboard.
        self.assertFalse(frequency_applies({"Frequency": "Conditional"}, "2026-08"))
        rows, stats = run()
        conditional = {r["Requirement_ID"] for r in seeds()["requirements"]
                       if r["Frequency"] == "Conditional"}
        self.assertTrue(conditional, "the seed must exercise the conditional path")
        for row in rows.values():
            self.assertNotIn(row["Requirement_ID"], conditional, row["EOM_Item_ID"])
        self.assertGreater(stats["skipped_conditional"], 0)

    def test_nominal_dates_come_from_the_requirement_row(self):
        rows, _ = run()
        by_req = {r["Requirement_ID"]: r for r in seeds()["requirements"]}
        for row in rows.values():
            req = by_req[row["Requirement_ID"]]
            self.assertTrue(
                row["Nominal_Due_Date"].endswith(f"-{int(req['Due_Day']):02d}"),
                f"{row['EOM_Item_ID']} nominal due {row['Nominal_Due_Date']}")

    def test_every_row_carries_both_date_pairs(self):
        rows, _ = run()
        for row in rows.values():
            for field in ("Nominal_Due_Date", "Effective_Due_Date",
                          "Nominal_Final_Call_Date", "Effective_Final_Call_Date"):
                self.assertTrue(row[field], f"{row['EOM_Item_ID']}.{field}")
            self.assertGreaterEqual(row["Effective_Due_Date"], row["Nominal_Due_Date"])

    def test_a_weekend_suspense_is_adjusted_and_flagged(self):
        # 5 Sep 2026 is a Saturday and 7 Sep is Labor Day in the seed, so the
        # 2026-08 first suspense lands on Tuesday 8 September.
        rows, _ = run()
        due5 = [r for r in rows.values() if r["Nominal_Due_Date"] == "2026-09-05"]
        self.assertTrue(due5, "no requirement with a 5th suspense generated")
        for row in due5:
            self.assertEqual(row["Effective_Due_Date"], "2026-09-08")
            self.assertTrue(row["Due_Date_Adjusted"])


class TestGeneratedStatus(unittest.TestCase):
    def test_a_verified_requirement_goes_red_when_missed(self):
        # Eleven of thirteen requirements moved to VERIFIED when the AFSVC
        # procedures deck landed, so a missed 1119 turns red as it should.
        rows, _ = run(today=dt.date(2026, 10, 1))
        verified = [r for r in rows.values() if r["Authority_Status"] == "VERIFIED"]
        self.assertTrue(verified, "the seed must contain verified requirements")
        for row in verified:
            self.assertEqual(row["Final_Status"], "OVERDUE", row["EOM_Item_ID"])
            self.assertEqual(row["Status_Code"], 1, row["EOM_Item_ID"])

    def test_the_three_time_states_at_generation(self):
        for today, want in ((dt.date(2026, 9, 3), "NOT_DUE"),
                            (dt.date(2026, 9, 9), "LATE"),
                            (dt.date(2026, 9, 13), "OVERDUE")):
            rows, _ = run(today=today)
            statuses = {r["Final_Status"] for r in rows.values()}
            self.assertEqual(statuses, {want}, str(today))

    def test_a_provisional_requirement_would_stay_blue(self):
        s = seeds()
        for r in s["requirements"]:
            r["Authority_Status"] = "UNVERIFIED"
        rows, _ = run(today=dt.date(2027, 6, 1), requirements=s["requirements"])
        self.assertTrue(rows)
        for row in rows.values():
            self.assertEqual(row["Final_Status"], "PENDING_VALIDATION")
            self.assertEqual(row["Status_Code"], 4)
            self.assertEqual(row["Action_Owner"], "Admin")

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
