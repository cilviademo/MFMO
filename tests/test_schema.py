#!/usr/bin/env python3
"""Schema, seed and repository-hygiene tests.

scripts/eom_schema.py is the single source of truth. These hold the seeds, the
provisioning script, the flow specs and the app source to it.
"""

import csv
import glob
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eom_schema as S  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def read_csv(name):
    with open(os.path.join(ROOT, "configuration", name), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class TestSchemaItself(unittest.TestCase):
    def test_validates(self):
        self.assertEqual(S.validate(), [])

    def test_sixteen_lists(self):
        self.assertEqual(len(S.LISTS), 16)
        self.assertEqual(
            {l.name for l in S.LISTS},
            {"MF_Installation", "MF_Facility", "MF_EOM_Requirement", "MF_EOM_Item",
             "MF_EOM_Submission", "MF_Unmatched_File", "MF_Security_Mapping",
             "MF_EOM_Audit", "MF_App_Config", "MF_Feature_Flags",
             "MF_App_Event_Log", "MF_EOM_Status", "MF_Non_Duty_Day",
             "MF_Calendar_Event", "MF_Access_Request", "MF_Notification_Rule"})

    def test_every_list_declares_a_grain_and_a_unique_key(self):
        for l in S.LISTS:
            self.assertTrue(l.grain.strip(), l.name)
            self.assertTrue(l.unique_key, f"{l.name} has no unique key")

    def test_every_list_stays_within_the_sharepoint_index_limit(self):
        for l in S.LISTS:
            self.assertLessEqual(len(l.indexed_columns), 20, l.name)

    def test_the_high_volume_lists_index_what_they_filter_on(self):
        # Indexes must exist before a list crosses 5,000 items. SharePoint will
        # not add them after, so this is checked at build time.
        required = {
            "MF_EOM_Item": ["Reporting_Period", "Portfolio_ID", "Installation_ID",
                            "Facility_ID", "Requirement_ID", "Final_Status",
                            "Status_Code", "Authority_Status", "Action_Required",
                            "Effective_Due_Date", "Effective_Final_Call_Date",
                            "EOM_Item_Key"],
            "MF_EOM_Submission": ["EOM_Item_ID", "Is_Current", "QC_Status",
                                  "Uploaded_DateTime", "SharePoint_File_ID"],
            "MF_EOM_Status": ["Reporting_Period", "Portfolio_ID", "Installation_ID",
                              "Facility_ID", "Final_Status", "Status_Code"],
            "MF_App_Event_Log": ["Event_DateTime", "Event_Type", "Record_ID", "User_UPN"],
            "MF_EOM_Audit": ["Entity_ID", "Action", "Action_DateTime"],
            "MF_Unmatched_File": ["Resolution_Status", "Discovered_DateTime"],
            "MF_Non_Duty_Day": ["Date", "Scope_ID", "Active_Flag"],
            "MF_Access_Request": ["Requester_UPN", "Requested_Installation_ID", "Status"],
            "MF_Calendar_Event": ["Event_Date", "Scope_ID", "Active_Flag"],
        }
        for list_name, columns in required.items():
            indexed = S.LISTS_BY_NAME[list_name].indexed_columns
            for column in columns:
                self.assertIn(column, indexed, f"{list_name}.{column} is not indexed")

    def test_no_stored_percentage_anywhere(self):
        for l in S.LISTS:
            for c in l.columns:
                low = c.name.lower()
                self.assertNotIn("percent", low, f"{l.name}.{c.name}")
                self.assertFalse(low.endswith(("_pct", "_rate")), f"{l.name}.{c.name}")

    def test_facility_id_is_nullable_wherever_it_is_a_reference(self):
        # MF_Facility.Facility_ID is the facility's own key and is required
        # there. Everywhere else the column points AT a facility and must be
        # able to point at none.
        checked = 0
        for l in S.LISTS:
            if l.name == "MF_Facility":
                continue
            for c in l.columns:
                if c.name == "Facility_ID":
                    checked += 1
                    self.assertFalse(c.required, f"{l.name}.Facility_ID is required")
        self.assertGreaterEqual(checked, 3)

    def test_final_status_and_status_code_are_both_stored_on_item_and_fact(self):
        for list_name in ("MF_EOM_Item", "MF_EOM_Status"):
            cols = {c.name for c in S.LISTS_BY_NAME[list_name].columns}
            self.assertIn("Final_Status", cols, list_name)
            self.assertIn("Status_Code", cols, list_name)

    def test_generated_artifacts_are_current(self):
        # A stale generated file is a lie about the schema.
        self.assertEqual(S.to_markdown().strip(), read("docs", "data-model.md").strip(),
                         "docs/data-model.md is stale: regenerate with --markdown")
        self.assertEqual(S.to_dictionary_csv().strip(),
                         read("docs", "MF_EOM_Data_Dictionary.csv").strip(),
                         "docs/MF_EOM_Data_Dictionary.csv is stale: regenerate with --dictionary")

    def test_json_is_serialisable_for_the_provisioning_script(self):
        d = S.to_dict()
        json.dumps(d)
        self.assertEqual(d["list_count"], 16)
        self.assertEqual(d["column_count"], S.total_columns())


class TestRequirementSeed(unittest.TestCase):
    def setUp(self):
        self.rows = read_csv("requirements.csv")

    def test_thirteen_rows_mostly_verified_five_inactive(self):
        # The AFSVC procedures deck moved eleven of thirteen from UNVERIFIED to
        # VERIFIED with citations, so rule 2 of the status engine now applies to
        # almost nothing and a missed 1119 turns red as it should.
        self.assertEqual(len(self.rows), 13)
        verified = [r for r in self.rows if r["Authority_Status"] == "VERIFIED"]
        self.assertGreaterEqual(len(verified), 9)
        self.assertEqual(sum(r["Active_Flag"] == "FALSE" for r in self.rows), 5)

    def test_authority_and_scope_are_separate_claims(self):
        # The deck confirms WHICH documents are in the package. It says nothing
        # about the GRAIN each is filed at. Marking a scope guess VERIFIED
        # because the document is verified turns a proposal into policy.
        for r in self.rows:
            self.assertIn(r["Scope_Confidence"], S.SCOPE_CONFIDENCE, r["Requirement_ID"])
            self.assertTrue(r["Scope_Basis"].strip(),
                            f"{r['Requirement_ID']} states a grain with no reason")
        proposed = [r for r in self.rows if r["Scope_Confidence"] == "Proposed"]
        self.assertTrue(proposed, "the seed must still carry unconfirmed grains")

    def test_the_two_suspense_days_are_seeded(self):
        for r in self.rows:
            if r["Active_Flag"] != "TRUE":
                continue
            self.assertTrue(r["Due_Day"], r["Requirement_ID"])
            self.assertIn(r["Due_Basis"], S.DUE_BASIS, r["Requirement_ID"])
            if r["Final_Due_Day"]:
                self.assertGreaterEqual(int(r["Final_Due_Day"]), int(r["Due_Day"]),
                                        r["Requirement_ID"])
            self.assertIn(r["NonDutyDay_Policy"], S.NON_DUTY_DAY_POLICY,
                          r["Requirement_ID"])

    def test_the_field_feeding_form_is_conditional(self):
        # The 1119-1 is field feeding, not a 1119 continuation. Auto-generating
        # it would put a permanent red row on every DFAC that ran none.
        f = [r for r in self.rows if r["Document_Code"] == "1119-1"]
        self.assertTrue(f)
        for r in f:
            self.assertEqual(r["Frequency"], "Conditional")
            self.assertEqual(r["Required_Flag"], "FALSE")

    def test_the_eoy_requirements_land_in_september(self):
        eoy = [r for r in self.rows if r["Frequency"] == "Annual"]
        self.assertTrue(eoy, "EOY reuses the same engine, not a second app")
        for r in eoy:
            self.assertEqual(r["Applicable_Period_Month"], "9", r["Requirement_ID"])

    def test_columns_match_the_schema_exactly(self):
        declared = [c.name for c in S.LISTS_BY_NAME["MF_EOM_Requirement"].columns]
        self.assertEqual(list(self.rows[0].keys()), declared)

    def test_choice_values_are_in_the_vocabulary(self):
        for r in self.rows:
            self.assertIn(r["Applicable_Model"], S.APPLICABLE_MODEL, r["Requirement_ID"])
            self.assertIn(r["Requirement_Scope"], S.REQUIREMENT_SCOPE, r["Requirement_ID"])
            self.assertIn(r["Frequency"], S.FREQUENCY, r["Requirement_ID"])
            self.assertIn(r["Authority_Status"], S.AUTHORITY_STATUS, r["Requirement_ID"])
            for t in filter(None, r["Applicable_Facility_Types"].split(";")):
                self.assertIn(t, S.FACILITY_TYPE, r["Requirement_ID"])

    def test_every_requirement_records_what_is_unresolved(self):
        # An empty Authority_Reference on an UNVERIFIED row tells a reader
        # nothing. Each one says what is missing.
        for r in self.rows:
            self.assertTrue(r["Authority_Reference"].strip(), r["Requirement_ID"])

    def test_all_three_scopes_are_exercised(self):
        self.assertEqual({r["Requirement_Scope"] for r in self.rows},
                         set(S.REQUIREMENT_SCOPE))

    def test_the_real_air_force_forms_are_present(self):
        codes = {r["Document_Code"] for r in self.rows}
        for code in ("1119", "1119-1", "SIK", "SAIIT", "CONTRACTOR-INV"):
            self.assertIn(code, codes)

    def test_ids_are_unique_and_due_days_are_sane(self):
        ids = [r["Requirement_ID"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        for r in self.rows:
            self.assertTrue(1 <= int(r["Due_Day"]) <= 31, r["Requirement_ID"])


class TestConfigurationSeeds(unittest.TestCase):
    def test_all_seed_headers_match_the_schema(self):
        pairs = {
            "app-config.csv": "MF_App_Config",
            "feature-flags.csv": "MF_Feature_Flags",
            "notification-rules.csv": "MF_Notification_Rule",
            "non-duty-days.sample.csv": "MF_Non_Duty_Day",
            "installations.csv": "MF_Installation",
            "facilities.csv": "MF_Facility",
            "security-mapping.sample.csv": "MF_Security_Mapping",
        }
        for filename, list_name in pairs.items():
            rows = read_csv(filename)
            declared = [c.name for c in S.LISTS_BY_NAME[list_name].columns]
            self.assertEqual(list(rows[0].keys()), declared, filename)

    def test_the_two_gating_answers_ship_unknown(self):
        cfg = {r["Config_Key"]: r["Config_Value"] for r in read_csv("app-config.csv")}
        self.assertEqual(cfg["TenantCloud"], "UNKNOWN")
        self.assertEqual(cfg["PacCliAuthorized"], "UNKNOWN")

    def test_the_kill_switch_ships_off(self):
        cfg = {r["Config_Key"]: r["Config_Value"] for r in read_csv("app-config.csv")}
        self.assertEqual(cfg["MaintenanceMode"], "False")
        self.assertEqual(cfg["ReadOnlyMode"], "False")

    def test_the_ai_config_keys_ship_false(self):
        cfg = {r["Config_Key"]: r["Config_Value"] for r in read_csv("app-config.csv")}
        self.assertEqual(cfg["EnableAIBuilder"], "False")
        self.assertEqual(cfg["EnableDocumentContentAI"], "False")

    def test_no_powerbi_url_is_baked_into_the_seed(self):
        # The government service URL differs by cloud and none may be baked in.
        cfg = {r["Config_Key"]: r["Config_Value"] for r in read_csv("app-config.csv")}
        self.assertEqual(cfg["PowerBIReportURL"], "")

    def test_the_ai_and_developer_flags_are_off_in_prod(self):
        flags = {r["Feature_Key"]: r for r in read_csv("feature-flags.csv")}
        for key in ("EOM_DIAGNOSTICS", "EOM_CONTENT_CLASSIFY", "EOM_AI_BUILDER",
                    "FMAT_MODULE"):
            self.assertEqual(flags[key]["Enabled_Prod"], "FALSE", key)
        # AI Builder must never become a dependency, so it is off for testers too.
        for key in ("EOM_CONTENT_CLASSIFY", "EOM_AI_BUILDER"):
            self.assertEqual(flags[key]["Enabled_Testers"], "FALSE", key)

    def test_flag_roles_are_in_the_vocabulary(self):
        for r in read_csv("feature-flags.csv"):
            self.assertIn(r["Minimum_Role"], S.FLAG_ROLE, r["Feature_Key"])

    def test_the_registry_has_a_base_running_two_operating_models(self):
        # Operating_Model lives on the facility precisely because this happens.
        from collections import defaultdict
        by_base = defaultdict(set)
        for f in read_csv("facilities.csv"):
            if f["Active_Flag"] == "TRUE" and f["Operating_Model"]:
                by_base[f["Installation_ID"]].add(f["Operating_Model"])
        mixed = [b for b, m in by_base.items() if len(m) > 1]
        self.assertTrue(mixed, "no base in the registry runs two operating models")

    def test_registry_models_are_normalised_to_the_vocabulary(self):
        # The QRG says "Legacy"; the requirements say "Legacy/APF". Unmapped,
        # nothing would ever match and every base would read as nothing-due.
        for f in read_csv("facilities.csv"):
            model = f["Operating_Model"]
            if model:
                self.assertIn(model, S.OPERATING_MODEL, f["Facility_ID"])

    def test_the_onboarding_gate_starts_closed_for_all_but_the_pilot(self):
        rows = read_csv("installations.csv")
        enabled = [i for i in rows if i["Generation_Enabled"] == "TRUE"]
        self.assertTrue(enabled, "a pilot set must be onboarded to exercise EOM-01")
        self.assertLess(len(enabled), len(rows) // 2,
                        "onboarding is per base, after the registry is validated")
        for i in enabled:
            self.assertTrue(i["Registry_Validated_By"].strip(),
                            f"{i['Installation_ID']} is enabled with no sign-off")
            self.assertTrue(i["Registry_Validated_Date"].strip(), i["Installation_ID"])

    def test_two_notification_rules_ship_enabled(self):
        rows = read_csv("notification-rules.csv")
        enabled = [r for r in rows if r["Enabled"] == "TRUE"]
        self.assertEqual(len(enabled), 2)
        self.assertEqual({r["Trigger_Event"] for r in enabled},
                         {"SubmissionCreated", "StatusChanged"})
        # Digest is on by default for anything recurring: per-item mail across
        # 103 installations is how a notification system gets muted.
        for r in rows:
            if r["Cadence_Days"].strip():
                self.assertEqual(r["Digest"], "TRUE", r["Rule_ID"])

    def test_the_sample_security_covers_the_scope_types_in_use(self):
        rows = read_csv("security-mapping.sample.csv")
        self.assertTrue({"Installation", "Portfolio", "Enterprise"}
                        <= {r["Scope_Type"] for r in rows})
        devs = [r for r in rows if r["Developer_Flag"] == "TRUE"]
        self.assertEqual(len(devs), 1, "Developer_Flag is never granted by a role")

    def test_qc_and_granting_are_limited_to_the_granted_role(self):
        for r in read_csv("security-mapping.sample.csv"):
            if r["Can_QC"] == "TRUE" or r["Can_Grant_Access"] == "TRUE":
                self.assertEqual(r["Role"], "PORTFOLIO_MANAGER", r["Security_ID"])

    def test_granting_is_limited_to_enterprise_scope(self):
        # Stops the role self-propagating: without this, one grant makes the
        # population monotonically increasing.
        for r in read_csv("security-mapping.sample.csv"):
            if r["Can_Grant_Access"] == "TRUE":
                self.assertEqual(r["Scope_Type"], "Enterprise", r["Security_ID"])
                self.assertEqual(r["Grant_Scope"], "Enterprise", r["Security_ID"])

    def test_requested_access_carries_an_expiry(self):
        # A departing member needs a handover window, not permanent rights to
        # a base they left.
        requested = [r for r in read_csv("security-mapping.sample.csv")
                     if r["Grant_Type"] == "Requested"]
        self.assertTrue(requested, "the seed must exercise the requested path")
        for r in requested:
            self.assertTrue(r["Expires_Date"].strip(),
                            f"{r['Security_ID']} is requested access with no expiry")

    def test_environment_variables_have_a_config_fallback(self):
        # Neither path may be load-bearing alone.
        with open(os.path.join(ROOT, "configuration", "environment-variables.json")) as fh:
            env = json.load(fh)["environmentVariables"]
        self.assertGreater(len(env), 10)
        for v in env:
            self.assertTrue(v["schemaName"].startswith("mfops_"), v["schemaName"])
            self.assertEqual(v["defaultValue"], "", "no environment value is baked in")


class TestNoHardCodedEnvironment(unittest.TestCase):
    SEARCHED = ("canvas-app", "flows", "provisioning", "configuration", "powerbi")

    def _files(self):
        for top in self.SEARCHED:
            for path in glob.glob(os.path.join(ROOT, top, "**", "*"), recursive=True):
                if os.path.isfile(path):
                    yield path

    def test_no_sharepoint_or_powerbi_urls(self):
        pattern = re.compile(r"https://[\w.-]*(sharepoint\.(com|us)|app\.powerbi\.com)", re.I)
        offenders = []
        for path in self._files():
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if pattern.search(line):
                        offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [])

    def test_no_bare_guids(self):
        pattern = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
        offenders = []
        for path in self._files():
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    for m in pattern.findall(line):
                        if set(m.replace("-", "")) <= {"0"}:
                            continue        # an explicit all-zero placeholder
                        offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [])

    def test_provisioning_takes_the_site_url_as_a_mandatory_parameter(self):
        for name in ("Provision-MFOpsLists.ps1", "Seed-MFOpsConfiguration.ps1",
                     "Verify-MFOpsCapabilities.ps1"):
            self.assertIn("[Parameter(Mandatory = $true)][string] $SiteUrl",
                          read("provisioning", name), name)

    def test_provisioning_declares_no_columns_of_its_own(self):
        text = read("provisioning", "Provision-MFOpsLists.ps1")
        self.assertIn("schema.generated.json", text)
        self.assertIn("Schema version mismatch", text)
        self.assertIn(f"'{S.SCHEMA_VERSION}'", text)
        self.assertIn(str(S.total_columns()), text,
                      "the provisioning script's expected column count is stale")
        self.assertIn(str(len(S.LISTS)), text,
                      "the provisioning script's expected list count is stale")


class TestFlowSpecs(unittest.TestCase):
    FLOWS = ("EOM01-ExpectedPackage", "EOM02-FileIntake", "EOM03-Reconciliation",
             "EOM04-Notifications", "EOM05-AppUpload")

    def test_all_five_specs_exist(self):
        for flow in self.FLOWS:
            self.assertTrue(os.path.exists(os.path.join(ROOT, "flows", flow, "definition.md")),
                            flow)

    def test_no_fabricated_flow_json_remains(self):
        # An export that has never been imported is a drawing of source, not
        # source. RECONCILIATION.md section 8.
        stray = glob.glob(os.path.join(ROOT, "flows", "**", "*.json"), recursive=True)
        self.assertEqual(stray, [])

    def test_the_intake_flow_binds_at_library_level(self):
        text = read("flows", "EOM02-FileIntake", "definition.md")
        self.assertIn("Library level, not folder level", text)
        self.assertIn("does not fire recursively", text)

    def test_no_flow_creates_a_requirement_from_a_file(self):
        text = read("flows", "EOM02-FileIntake", "definition.md")
        self.assertIn("Never invent a requirement", text)
        self.assertIn("There is no branch in this flow that creates an `MF_EOM_Item`", text)

    def test_the_upload_flow_checks_read_only_server_side(self):
        # The disabled control is a courtesy; the flow check is the control.
        text = read("flows", "EOM05-AppUpload", "definition.md")
        self.assertIn("ReadOnlyMode", text)
        self.assertIn("READ_ONLY", text)

    def test_notification_rules_are_data_not_code(self):
        text = read("flows", "EOM04-Notifications", "definition.md")
        self.assertIn("MF_Notification_Rule", text)
        self.assertIn("not code", text)
        # A provisional requirement never generates a nag: the action sits with
        # the programme, and mailing a base about an obligation nobody has
        # confirmed exists is what the Blue state prevents on screen.
        self.assertIn("PENDING_VALIDATION", text)
        # Digest, not per-item, for anything recurring.
        self.assertIn("Digest", text)

    def test_only_two_notification_rules_ship_enabled(self):
        rows = read_csv("notification-rules.csv")
        enabled = {r["Trigger_Event"] for r in rows if r["Enabled"] == "TRUE"}
        self.assertEqual(enabled, {"SubmissionCreated", "StatusChanged"},
                         "everything else is tuned once the queue behaves")

    def test_the_upload_flow_does_not_use_the_attachments_control(self):
        text = read("flows", "EOM05-AppUpload", "definition.md")
        self.assertIn("Attachments control", text)
        app = read("canvas-app", "src", "Screens", "scrUpload.pa.yaml")
        self.assertNotIn("Control: Attachments", app)
        self.assertIn("EOM05_AppUpload.Run", app)


class TestAppSource(unittest.TestCase):
    def _screens(self):
        return glob.glob(os.path.join(ROOT, "canvas-app", "src", "Screens", "*.pa.yaml"))

    def test_the_screen_set_matches_the_navigation(self):
        on_disk = {os.path.basename(p).replace(".pa.yaml", "") for p in self._screens()}
        self.assertEqual(on_disk, {
            "scrHome", "scrUpload", "scrInstallation", "scrReview", "scrUnmatched",
            "scrActivity", "scrCalendar", "scrAccessRequest",
            "scrAdminRequirements", "scrMaintenance", "scrNoAccess",
            "scrDiagnostics"})
        # History became Activity.
        self.assertNotIn("scrHistory", on_disk)

    def test_every_screen_is_registered_in_the_app_object(self):
        app = read("canvas-app", "src", "App.pa.yaml")
        for path in self._screens():
            name = os.path.basename(path).replace(".pa.yaml", "")
            self.assertIn(f"  - {name}", app, name)

    def test_no_positive_tabindex(self):
        # A positive TabIndex detaches tab order from visual order the moment a
        # container reflows. Accessibility gate.
        offenders = []
        for path in glob.glob(os.path.join(ROOT, "canvas-app", "src", "**", "*.pa.yaml"),
                              recursive=True):
            for i, line in enumerate(read(os.path.relpath(path, ROOT)).splitlines(), 1):
                m = re.search(r"TabIndex:\s*=\s*(-?\d+)", line)
                if m and int(m.group(1)) > 0:
                    offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [])

    def test_no_absolute_positioning(self):
        # Button.X = 475 is the signature of a brittle app and breaks at 200% zoom.
        offenders = []
        for path in glob.glob(os.path.join(ROOT, "canvas-app", "src", "**", "*.pa.yaml"),
                              recursive=True):
            for i, line in enumerate(read(os.path.relpath(path, ROOT)).splitlines(), 1):
                if re.search(r"^\s+(X|Y):\s*=\s*\d", line):
                    offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [])

    def test_every_gallery_screen_has_an_empty_state(self):
        # An empty gallery with no explanation is indistinguishable from a
        # failed load.
        for path in self._screens():
            rel = os.path.relpath(path, ROOT)
            text = read(rel)
            if "Control: Gallery" in text and "scrDiagnostics" not in rel:
                self.assertIn("cmpEmptyState", text, rel)

    def test_the_status_badge_takes_a_status_not_a_colour(self):
        badge = read("canvas-app", "src", "Components", "cmpStatusBadge.pa.yaml")
        self.assertIn("FinalStatus:", badge)
        self.assertNotIn("StatusCode:", badge.split("CustomProperties:")[1].split("Properties:")[0])

    def test_high_volume_queries_live_in_delegation_fx(self):
        stray = []
        for path in glob.glob(os.path.join(ROOT, "canvas-app", "src", "**", "*.pa.yaml"),
                              recursive=True):
            rel = os.path.relpath(path, ROOT)
            for i, line in enumerate(read(rel).splitlines(), 1):
                if re.search(r"(Filter|SortByColumns)\(\s*'MF EOM (Item|Status|Audit)'", line):
                    stray.append(f"{rel}:{i}")
        self.assertEqual(stray, [],
                         "query a high-volume list through Delegation.fx, not inline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
