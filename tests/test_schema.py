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

    def test_twelve_lists(self):
        self.assertEqual(len(S.LISTS), 12)
        self.assertEqual(
            {l.name for l in S.LISTS},
            {"MF_Installation", "MF_Facility", "MF_EOM_Requirement", "MF_EOM_Item",
             "MF_EOM_Submission", "MF_Unmatched_File", "MF_Security_Mapping",
             "MF_EOM_Audit", "MF_App_Config", "MF_Feature_Flags",
             "MF_App_Event_Log", "MF_EOM_Status"})

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
                            "Due_Date", "EOM_Item_Key"],
            "MF_EOM_Submission": ["EOM_Item_ID", "Is_Current", "QC_Status",
                                  "Uploaded_DateTime", "SharePoint_File_ID"],
            "MF_EOM_Status": ["Reporting_Period", "Portfolio_ID", "Installation_ID",
                              "Facility_ID", "Final_Status", "Status_Code"],
            "MF_App_Event_Log": ["Event_DateTime", "Event_Type", "Record_ID", "User_UPN"],
            "MF_EOM_Audit": ["Entity_ID", "Action", "Action_DateTime"],
            "MF_Unmatched_File": ["Resolution_Status", "Discovered_DateTime"],
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
        self.assertEqual(d["list_count"], 12)
        self.assertEqual(d["column_count"], S.total_columns())


class TestRequirementSeed(unittest.TestCase):
    def setUp(self):
        self.rows = read_csv("requirements.csv")

    def test_twelve_rows_all_unverified_three_inactive(self):
        self.assertEqual(len(self.rows), 12)
        self.assertTrue(all(r["Authority_Status"] == "UNVERIFIED" for r in self.rows))
        self.assertEqual(sum(r["Active_Flag"] == "FALSE" for r in self.rows), 3)

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
            self.assertGreaterEqual(int(r["Due_Offset_Months"]), 0, r["Requirement_ID"])


class TestConfigurationSeeds(unittest.TestCase):
    def test_all_seed_headers_match_the_schema(self):
        pairs = {
            "app-config.csv": "MF_App_Config",
            "feature-flags.csv": "MF_Feature_Flags",
            "installations.sample.csv": "MF_Installation",
            "facilities.sample.csv": "MF_Facility",
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
        # The gov endpoint differs by cloud. Never hard-code app.powerbi.com.
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

    def test_the_sample_has_a_base_running_two_operating_models(self):
        lackland = [f for f in read_csv("facilities.sample.csv")
                    if f["Installation_ID"] == "INST-LACKLAND" and f["Active_Flag"] == "TRUE"]
        models = {f["Operating_Model"] for f in lackland}
        self.assertIn("Legacy/APF", models)
        self.assertIn("Food 2.0", models)

    def test_the_sample_security_covers_every_scope_type(self):
        rows = read_csv("security-mapping.sample.csv")
        self.assertEqual({r["Scope_Type"] for r in rows}, set(S.SCOPE_TYPE))
        # Developer_Flag is never granted by a role, so exactly one seeded row
        # carries it and it is not the Admin role by itself.
        devs = [r for r in rows if r["Developer_Flag"] == "TRUE"]
        self.assertEqual(len(devs), 1)

    def test_can_qc_is_limited_to_portfolio_manager_and_admin(self):
        for r in read_csv("security-mapping.sample.csv"):
            if r["Can_QC"] == "TRUE":
                self.assertIn(r["Role"], ("Portfolio Manager", "Admin"), r["Security_ID"])

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

    def test_the_write_flows_check_read_only_server_side(self):
        for flow in ("EOM04-Notifications", "EOM05-AppUpload"):
            text = read("flows", flow, "definition.md")
            self.assertTrue("ReadOnlyMode" in text or "Ships FALSE" in text, flow)

    def test_notifications_ship_disabled_and_skip_provisional_rows(self):
        text = read("flows", "EOM04-Notifications", "definition.md")
        self.assertIn("Ships FALSE", text)
        self.assertIn("PENDING_VALIDATION", text)

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
            "scrActivity", "scrAdminRequirements", "scrMaintenance", "scrNoAccess",
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
