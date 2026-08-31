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
    generate, load_csv, onboard, item_id_for, frequency_applies,
    model_applies, facility_type_applies,
)

CONFIG = os.path.join(ROOT, "configuration")
PERIOD = "2026-08"
TODAY = dt.date(2026, 9, 12)


def installations():
    """The generated registry with the pilot onboarding applied.

    installations.csv is GENERATED and ships every row Generation_Enabled
    FALSE. Onboarding is a human decision recorded in pilot-onboarding.csv, and
    applying it here rather than editing the generated file is what keeps
    `python3 scripts/gen_registry.py` idempotent.
    """
    return onboard(load_csv(os.path.join(CONFIG, "installations.csv")),
                   load_csv(os.path.join(CONFIG, "pilot-onboarding.csv")))


def seeds():
    return dict(
        requirements=load_csv(os.path.join(CONFIG, "requirements.csv")),
        installations=installations(),
        facilities=load_csv(os.path.join(CONFIG, "facilities.csv")),
        non_duty_days=load_csv(os.path.join(CONFIG, "non-duty-days.sample.csv")),
    )


def run(period=PERIOD, today=TODAY, existing=None, **overrides):
    s = seeds()
    s.update(overrides)
    return generate(period=period, today=today, existing=existing, **s)


ONBOARDED = {i["Installation_ID"] for i in installations()
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
        """Prove the path rather than trusting it.

        Since the 31 Aug 2026 ruling every ACTIVE requirement is facility
        scope, so the live seed generates no installation- or contract-scope
        rows at all. That does not make the distinction less load-bearing: a
        Facility_ID of "" instead of null is invisible in a gallery and breaks
        every delegable Filter downstream. So the test activates one of each
        and checks what comes out.
        """
        s = seeds()
        activated = 0
        for r in s["requirements"]:
            if r["Requirement_Scope"] in ("Installation", "Contract"):
                r["Active_Flag"] = "TRUE"
                r["Required_Flag"] = "TRUE"
                r["Applicable_Model"] = "Legacy/APF"
                r["Frequency"] = "Monthly"
                activated += 1
        self.assertGreater(activated, 0, "the catalogue no longer models them")
        for f in s["facilities"]:
            if (f["Installation_ID"] == "JBSA_LACKLAND"
                    and f["Operating_Model"] == "Legacy/APF"):
                f["Contract_ID"] = "CTR-TEST-001"

        rows, _ = run(requirements=s["requirements"], facilities=s["facilities"])
        checked = 0
        for row in rows.values():
            if row["Requirement_Scope"] in ("Installation", "Contract"):
                checked += 1
                self.assertIsNone(row["Facility_ID"], row["EOM_Item_ID"])
                # The distinction that matters: not "" and not "  ".
                self.assertNotEqual(row["Facility_ID"], "", row["EOM_Item_ID"])
        self.assertGreater(checked, 0,
                           "activating them generated nothing, so the scope "
                           "machinery is broken rather than merely unused")

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
            # An ONBOARDED base, or the row is filtered out before scope is
            # ever considered and the test proves nothing.
            if f["Installation_ID"] == "JBSA_LACKLAND" and f["Operating_Model"] == "Legacy/APF":
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

    def test_installation_scope_still_expands_when_activated(self):
        # Every active requirement is facility scope after the 31 Aug 2026
        # ruling, so this proves the installation path survives unused.
        s = seeds()
        for r in s["requirements"]:
            if r["Requirement_ID"] == "REQ-007":       # SIK, Installation scope
                r["Active_Flag"] = "TRUE"
                r["Required_Flag"] = "TRUE"
                r["Applicable_Model"] = "Legacy/APF"
                r["Frequency"] = "Monthly"
        rows, _ = run(requirements=s["requirements"])
        inst = [r for r in rows.values()
                if r["Requirement_Scope"] == "Installation"]
        self.assertTrue(inst, "activating an installation-scope requirement "
                              "generated nothing")
        # One row per onboarded installation that has a matching facility,
        # not one per facility.
        self.assertEqual(len(inst), len({r["Installation_ID"] for r in inst}))

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


class TheBackfillWindowIsEnforced(unittest.TestCase):
    """A config key nothing reads is a decision that was never applied.

    The pilot window is 2026-08 to 2026-09: 737 rows across the full R1 scope
    instead of 3,618. A stray --period 2025-10 would quietly create the other
    2,881, and a fresh list you cannot read is one every verification step gets
    slower against.
    """

    def setUp(self):
        from generate_expected_items import period_window
        self.cfg = load_csv(os.path.join(CONFIG, "app-config.csv"))
        self.lo, self.hi = period_window(self.cfg)

    def test_the_window_is_configured(self):
        self.assertEqual(self.lo, "2026-08")
        self.assertEqual(self.hi, "2026-09")

    def test_a_period_before_the_window_is_refused(self):
        from generate_expected_items import (
            PeriodOutsideBackfillWindow, check_window)
        with self.assertRaises(PeriodOutsideBackfillWindow) as ctx:
            check_window("2025-10", self.lo, self.hi)
        # The message must say how to widen it, or somebody edits the code.
        self.assertIn("one-cell edit", str(ctx.exception))
        self.assertIn("idempotent", str(ctx.exception))

    def test_a_period_after_the_window_is_refused(self):
        from generate_expected_items import (
            PeriodOutsideBackfillWindow, check_window)
        with self.assertRaises(PeriodOutsideBackfillWindow):
            check_window("2026-10", self.lo, self.hi)

    def test_both_window_periods_are_allowed(self):
        from generate_expected_items import check_window
        for p in ("2026-08", "2026-09"):
            check_window(p, self.lo, self.hi)

    def test_the_window_expands_to_exactly_two_periods(self):
        from generate_expected_items import periods_in_window
        self.assertEqual(periods_in_window(self.lo, self.hi),
                         ["2026-08", "2026-09"])

    def test_an_implausibly_wide_window_raises_rather_than_looping(self):
        from generate_expected_items import periods_in_window
        with self.assertRaises(ValueError):
            periods_in_window("1990-01", "2099-12")

    def test_the_full_r1_backfill_is_737_rows(self):
        """The number the programme sized the pilot against.

        43 R1 installations, 67 Legacy facilities, six active requirements of
        which the 1119-1 generates nothing and the 1038 only lands in
        September. If this changes, the pilot was resized and somebody should
        know it.
        """
        from generate_expected_items import periods_in_window
        facs = load_csv(os.path.join(CONFIG, "facilities.csv"))
        insts = load_csv(os.path.join(CONFIG, "installations.csv"))
        r1 = {f["Installation_ID"] for f in facs if f["In_R1_Scope"] == "TRUE"}
        self.assertEqual(len(r1), 43)
        self.assertEqual(sum(1 for f in facs if f["In_R1_Scope"] == "TRUE"), 67)

        full = [dict(i, Generation_Enabled=("TRUE" if i["Installation_ID"] in r1
                                            else "FALSE"),
                     Registry_Validated_By="test",
                     Registry_Validated_Date="2026-08-31")
                for i in insts]
        rows = {}
        for p in periods_in_window("2026-08", "2026-09"):
            r, _ = generate(load_csv(os.path.join(CONFIG, "requirements.csv")),
                            full, facs, p, existing=dict(rows), today=TODAY,
                            non_duty_days=load_csv(
                                os.path.join(CONFIG, "non-duty-days.sample.csv")))
            rows.update(r)
        self.assertEqual(len(rows), 737)

    def test_a_full_fiscal_year_would_be_far_larger(self):
        # Why the window exists. Not run in the pilot; asserted so the ratio
        # stays visible.
        from generate_expected_items import periods_in_window
        self.assertEqual(len(periods_in_window("2025-10", "2026-09")), 12)


class EverySixActiveRequirementIsFacilityScope(unittest.TestCase):
    """Programme ruling, 31 Aug 2026. A six-DFAC base files six, not one."""

    def setUp(self):
        self.reqs = load_csv(os.path.join(CONFIG, "requirements.csv"))
        self.active = [r for r in self.reqs if r["Active_Flag"] == "TRUE"]

    def test_every_active_requirement_is_facility_scope(self):
        for r in self.active:
            self.assertEqual(r["Requirement_Scope"], "Facility",
                             r["Requirement_ID"])

    def test_the_three_ruled_requirements_are_recorded_as_verified(self):
        # They were Proposed. A ruling that does not change Scope_Confidence
        # leaves a decision looking like a guess.
        by_id = {r["Requirement_ID"]: r for r in self.reqs}
        for rid in ("REQ-003", "REQ-005", "REQ-006"):
            self.assertEqual(by_id[rid]["Scope_Confidence"], "Verified", rid)
            self.assertIn("31 Aug 2026", by_id[rid]["Scope_Basis"], rid)

    def test_no_generated_row_carries_a_null_facility(self):
        # Facility scope everywhere means every expected row names a facility.
        rows, _ = run()
        self.assertTrue(rows)
        for r in rows.values():
            self.assertIsNotNone(r["Facility_ID"], r["EOM_Item_ID"])

    def test_the_inactive_installation_scope_rows_still_model_it(self):
        # SIK and DAF 79 are Installation scope and inactive. The machinery
        # must survive for when a requirement is ruled the other way.
        inst = [r for r in self.reqs if r["Requirement_Scope"] == "Installation"]
        self.assertTrue(inst)
        for r in inst:
            self.assertEqual(r["Active_Flag"], "FALSE", r["Requirement_ID"])
