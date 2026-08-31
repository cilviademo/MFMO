#!/usr/bin/env python3
"""Schema and configuration-seed tests.

scripts/eom_schema.py is the single source of truth. These tests hold the
seeds, the provisioning script and the flows to it.
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

    def test_declared_size(self):
        self.assertEqual(len(S.LISTS), 12)
        self.assertEqual(S.total_columns(), 164)

    def test_every_list_stays_within_the_sharepoint_index_limit(self):
        for l in S.LISTS:
            self.assertLessEqual(len(l.indexed_columns), 20, l.name)

    def test_the_high_volume_lists_index_what_they_filter_on(self):
        # Indexes must exist before a list crosses 5,000 items. You cannot add
        # them afterward, so this is checked at build time, not at deploy time.
        required = {
            "MF_EOM_Item": ["Reporting_Period_ID", "Facility_ID", "Installation_ID",
                            "Portfolio_ID", "Status_Code", "Suspense_Date", "Action_Required"],
            "MF_EOM_Submission": ["EOM_Item_ID", "Is_Current_Version",
                                  "Classification_Status", "QC_Status", "Submitted_On"],
            "MF_EOM_Status": ["Snapshot_Date", "Reporting_Period_ID", "Facility_ID",
                              "Installation_ID", "Portfolio_ID", "Status_Code"],
            "MF_App_Event_Log": ["Event_Time", "Event_Type", "Correlation_ID"],
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
                self.assertFalse(low.endswith("_pct"), f"{l.name}.{c.name}")
                self.assertFalse(low.endswith("_rate"), f"{l.name}.{c.name}")

    def test_facility_id_is_nullable_wherever_it_is_a_reference(self):
        # Null, not empty string, for installation and contract scope.
        # MF_Facility.Facility_ID is the facility's own key and is required
        # there; everywhere else the column points AT a facility and must be
        # able to point at none.
        checked = 0
        for l in S.LISTS:
            if l.name == "MF_Facility":
                continue
            for c in l.columns:
                if c.name == "Facility_ID":
                    checked += 1
                    self.assertFalse(c.required, f"{l.name}.Facility_ID is required")
                    self.assertTrue(c.nullable, f"{l.name}.Facility_ID is not nullable")
        self.assertGreaterEqual(checked, 2)

    def test_the_submission_list_is_versioned(self):
        self.assertTrue(S.LISTS_BY_NAME["MF_EOM_Submission"].versioning)

    def test_json_and_markdown_render(self):
        d = S.to_dict()
        self.assertEqual(d["column_count"], 164)
        json.dumps(d)          # must be serialisable for the provisioning script
        self.assertIn("164 columns", S.to_markdown())

    def test_the_generated_data_model_doc_is_current(self):
        # docs/data-model.md is generated. A stale one is a lie about the schema.
        current = S.to_markdown().strip()
        on_disk = read("docs", "data-model.md").strip()
        self.assertEqual(
            current, on_disk,
            "docs/data-model.md is stale. Regenerate: "
            "python3 scripts/eom_schema.py --markdown > docs/data-model.md",
        )


class TestRequirementSeed(unittest.TestCase):
    def setUp(self):
        self.rows = read_csv("requirements.csv")

    def test_twelve_rows_all_unverified_three_inactive(self):
        self.assertEqual(len(self.rows), 12)
        self.assertTrue(all(r["Verification_Status"] == "UNVERIFIED" for r in self.rows))
        self.assertEqual(sum(r["Is_Active"] == "FALSE" for r in self.rows), 3)

    def test_no_seeded_requirement_claims_a_verification_date(self):
        for r in self.rows:
            self.assertEqual(r["Verification_Date"].strip(), "", r["Requirement_ID"])

    def test_every_requirement_states_that_it_is_provisional(self):
        # An empty Authority_Reference on an UNVERIFIED row tells a reader
        # nothing. Each one says what it is and what is missing.
        for r in self.rows:
            self.assertIn("PROVISIONAL", r["Authority_Reference"], r["Requirement_ID"])

    def test_columns_match_the_schema(self):
        declared = {c.name for c in S.LISTS_BY_NAME["MF_Requirement"].columns}
        self.assertEqual(set(self.rows[0].keys()), declared)

    def test_choice_values_are_in_the_vocabulary(self):
        for r in self.rows:
            self.assertIn(r["Requirement_Scope"], S.REQUIREMENT_SCOPE, r["Requirement_ID"])
            self.assertIn(r["Frequency"], S.FREQUENCY, r["Requirement_ID"])
            self.assertIn(r["Verification_Status"], S.VERIFICATION_STATUS, r["Requirement_ID"])
            self.assertIn(r["Requirement_Category"], S.REQUIREMENT_CATEGORY, r["Requirement_ID"])
            for model in filter(None, r["Applies_To_Operating_Model"].split(";")):
                self.assertIn(model, S.OPERATING_MODEL, r["Requirement_ID"])

    def test_suspense_is_never_before_due(self):
        for r in self.rows:
            self.assertGreaterEqual(
                int(r["Suspense_Offset_Days"]), int(r["Due_Offset_Days"]), r["Requirement_ID"]
            )

    def test_all_three_scopes_and_the_eoy_frequency_are_exercised(self):
        self.assertEqual({r["Requirement_Scope"] for r in self.rows},
                         set(S.REQUIREMENT_SCOPE))
        self.assertIn("Annual", {r["Frequency"] for r in self.rows})

    def test_ids_and_codes_are_unique(self):
        for field in ("Requirement_ID", "Requirement_Code"):
            values = [r[field] for r in self.rows]
            self.assertEqual(len(values), len(set(values)), field)


class TestConfigurationSeeds(unittest.TestCase):
    def test_config_columns_match_the_schema(self):
        rows = read_csv("app_config.csv")
        declared = {c.name for c in S.LISTS_BY_NAME["MF_App_Config"].columns}
        self.assertEqual(set(rows[0].keys()), declared)

    def test_the_two_gating_answers_ship_unknown(self):
        # docs/government-environment-mode.md: which cloud, and whether PAC CLI
        # is authorized. Do not guess either one.
        rows = {r["Title"]: r["Config_Value"] for r in read_csv("app_config.csv")}
        self.assertEqual(rows["TenantCloud"], "UNKNOWN")
        self.assertEqual(rows["PacCliAuthorized"], "UNKNOWN")

    def test_the_kill_switch_ships_off(self):
        rows = {r["Title"]: r["Config_Value"] for r in read_csv("app_config.csv")}
        self.assertEqual(rows["MaintenanceMode"], "false")
        self.assertEqual(rows["ReadOnlyMode"], "false")

    def test_no_site_url_is_baked_into_the_seed(self):
        rows = {r["Title"]: r["Config_Value"] for r in read_csv("app_config.csv")}
        self.assertEqual(rows["SiteUrl"], "SET_AT_DEPLOY")

    def test_flag_columns_match_the_schema(self):
        rows = read_csv("feature_flags.csv")
        declared = {c.name for c in S.LISTS_BY_NAME["MF_Feature_Flags"].columns}
        self.assertEqual(set(rows[0].keys()), declared)

    def test_the_ai_flags_ship_false_in_value_and_default(self):
        rows = {r["Title"]: r for r in read_csv("feature_flags.csv")}
        for flag in ("EnableDocumentContentAI", "EnableAIBuilder", "EnableNotifications",
                     "EnablePowerBIEmbed"):
            self.assertEqual(rows[flag]["Flag_Value"], "FALSE", flag)
            self.assertEqual(rows[flag]["Default_Value"], "FALSE", flag)

    def test_no_optional_dependency_defaults_true(self):
        # Default_Value is what the app uses when the flag list is unreachable.
        # An outage must never turn an optional dependency on.
        for row in read_csv("feature_flags.csv"):
            if row["Requires_Capability"].startswith(("Capability.6", "Capability.7", "Capability.9")):
                self.assertEqual(row["Default_Value"], "FALSE", row["Title"])

    def test_capability_gated_flags_name_a_real_gate(self):
        for row in read_csv("feature_flags.csv"):
            gate = row["Requires_Capability"].strip()
            if gate:
                self.assertRegex(gate, r"^Capability\.\d+\.[A-Za-z]+$", row["Title"])

    def test_sample_dimension_columns_match_the_schema(self):
        pairs = {
            "installations.sample.csv": "MF_Installation",
            "facilities.sample.csv": "MF_Facility",
            "contracts.sample.csv": "MF_Contract",
            "reporting_periods.sample.csv": "MF_Reporting_Period",
            "security_mapping.sample.csv": "MF_Security_Mapping",
        }
        for filename, list_name in pairs.items():
            rows = read_csv(filename)
            declared = {c.name for c in S.LISTS_BY_NAME[list_name].columns}
            self.assertEqual(set(rows[0].keys()), declared, filename)

    def test_the_sample_has_a_base_running_both_operating_models(self):
        facilities = read_csv("facilities.sample.csv")
        liberty = [f for f in facilities if f["Installation_ID"] == "INST-FTLIB" and f["Is_Active"] == "TRUE"]
        models = {f["Operating_Model"] for f in liberty}
        self.assertIn("Legacy_DFAC", models)
        self.assertIn("Food_2_0", models)


class TestNoHardCodedEnvironment(unittest.TestCase):
    """No hard-coded URLs, site GUIDs or list names. Anywhere."""

    SEARCHED = ("canvas-app", "flows", "provisioning", "configuration", "docs", "solution")

    def _files(self):
        for top in self.SEARCHED:
            for path in glob.glob(os.path.join(ROOT, top, "**", "*"), recursive=True):
                if os.path.isfile(path) and not path.endswith((".png", ".zip", ".msapp")):
                    yield path

    def test_no_sharepoint_urls(self):
        pattern = re.compile(r"https://[\w.-]*sharepoint\.(com|us)/sites/\S+", re.I)
        offenders = []
        for path in self._files():
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    if "example" in line.lower() or "contoso" in line.lower():
                        continue    # documented example in a .EXAMPLE block
                    if pattern.search(line):
                        offenders.append(f"{os.path.relpath(path, ROOT)}:{i}")
        self.assertEqual(offenders, [])

    def test_no_bare_guids(self):
        # An all-zero placeholder in the sample security mapping is fine; a
        # real environment or site id is not.
        pattern = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
        offenders = []
        for path in self._files():
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    for match in pattern.findall(line):
                        if set(match) <= set("0-9abcdef".replace("9", "0123456789")) and \
                                match.replace("-", "").strip("0123456789abcdef") == "":
                            if match.replace("-", "").strip("0") == "" or \
                               re.fullmatch(r"0{8}-0{4}-0{4}-0{4}-0{11}\d", match):
                                continue
                        offenders.append(f"{os.path.relpath(path, ROOT)}:{i} {match}")
        self.assertEqual(offenders, [])

    def test_flows_read_the_site_from_a_parameter(self):
        for path in glob.glob(os.path.join(ROOT, "flows", "**", "*.json"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("parameters('siteUrl')", text, os.path.basename(path))

    def test_provisioning_takes_the_site_url_as_a_mandatory_parameter(self):
        for name in ("Provision-MFOpsLists.ps1", "Seed-MFOpsConfiguration.ps1",
                     "Verify-MFOpsCapabilities.ps1"):
            text = read("provisioning", name)
            self.assertIn("[Parameter(Mandatory = $true)][string] $SiteUrl", text, name)

    def test_provisioning_does_not_declare_columns_of_its_own(self):
        # The single source of truth is eom_schema.py. The script consumes the
        # generated JSON and adds nothing.
        text = read("provisioning", "Provision-MFOpsLists.ps1")
        self.assertIn("schema.generated.json", text)
        self.assertIn("Schema version mismatch", text)


class TestFlowDefinitions(unittest.TestCase):
    def _flows(self):
        for path in glob.glob(os.path.join(ROOT, "flows", "**", "*.json"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                yield os.path.basename(os.path.dirname(path)), json.load(fh)

    def test_all_definitions_parse(self):
        # Five flows; EOM-02 ships two definitions, the library trigger and
        # the app-called companion that resolves a queued row.
        self.assertEqual(len(list(self._flows())), 6)

    def test_every_flow_has_a_trigger_and_actions(self):
        for name, flow in self._flows():
            self.assertTrue(flow["triggers"], name)
            self.assertTrue(flow["actions"], name)

    def test_the_write_flows_check_read_only_mode_server_side(self):
        for folder in ("EOM04-QCDecision", "EOM05-AppUpload"):
            text = read("flows", folder, "definition.json")
            self.assertIn("READ_ONLY", text, folder)
            self.assertIn("ReadOnlyMode", text, folder)

    def test_the_intake_flow_binds_at_library_level(self):
        # A folder-level trigger silently misses every folder created after
        # the flow was authored.
        text = read("flows", "EOM02-FileIntake", "definition.json")
        self.assertIn("LIBRARY-LEVEL", text)
        self.assertIn("onnewfileitems", text)

    def test_no_flow_creates_an_eom_item_from_a_file(self):
        # Never invent a requirement.
        for folder in ("EOM02-FileIntake",):
            for path in glob.glob(os.path.join(ROOT, "flows", folder, "*.json")):
                with open(path, encoding="utf-8") as fh:
                    flow = json.load(fh)
                text = json.dumps(flow)
                self.assertNotIn(
                    '"listId_MF_EOM_Item\'))}/items",\n', text,
                    f"{os.path.basename(path)} may create an item",
                )
                # A post to the item list would be a create. Only patches are
                # allowed from the intake path.
                for match in re.finditer(r'"method":\s*"post".{0,400}?listId_MF_EOM_Item', text, re.S):
                    self.fail(f"{os.path.basename(path)} posts to MF_EOM_Item")

    def test_the_upload_flow_never_uses_the_attachments_control(self):
        text = read("flows", "EOM05-AppUpload", "README.md")
        self.assertIn("Attachments control", text)
        app = read("canvas-app", "src", "Screens", "scrUpload.pa.yaml")
        self.assertNotIn("Control: Attachments", app)
        self.assertIn("EOM05_AppUpload.Run", app)


if __name__ == "__main__":
    unittest.main(verbosity=2)
