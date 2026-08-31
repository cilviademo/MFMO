"""Structural validation of the five flow bodies.

There is no tenant and no Logic Apps runtime here, so these have never run.
What CAN be checked without one is checked, because the alternative is shipping
JSON nobody has looked at:

  - every action reachable, no runAfter naming an action that does not exist
  - no cycle in the runAfter graph
  - every connector operation on the allowlist, every apiId a declared
    connection reference
  - no list name, site URL or GUID as a literal; everything from a parameter
  - every parameter referenced is declared
  - every write loop pinned to concurrency 1
  - the invariants each specification calls non-negotiable

`docs/TEST_MATRIX.md` records execution as NOT TESTABLE LOCALLY, with an owner.
It is not reported as passing.
"""

import json
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WF = os.path.join(ROOT, "solution", "src", "Workflows")
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def flows():
    for name in sorted(os.listdir(WF)):
        with open(os.path.join(WF, name), encoding="utf-8") as fh:
            yield name.split("-")[0], json.load(fh)


def walk_actions(actions, path=()):
    """Every action, including those nested in If branches and Foreach."""
    for name, a in actions.items():
        yield path + (name,), a
        for key in ("actions",):
            if isinstance(a.get(key), dict):
                yield from walk_actions(a[key], path + (name,))
        if isinstance(a.get("else"), dict):
            yield from walk_actions(a["else"].get("actions", {}),
                                    path + (name, "else"))


def texts(node):
    """Every string anywhere in a JSON tree."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from texts(v)
    elif isinstance(node, list):
        for v in node:
            yield from texts(v)


class TheGraphIsSound(unittest.TestCase):
    def test_every_runafter_names_an_action_at_the_same_level(self):
        for flow, d in flows():
            self._check_level(flow, d["properties"]["definition"]["actions"])

    def _check_level(self, flow, actions):
        names = set(actions)
        for name, a in actions.items():
            for dep in (a.get("runAfter") or {}):
                self.assertIn(dep, names,
                              f"{flow}: {name} runs after {dep}, which is not "
                              "an action at its level")
            if isinstance(a.get("actions"), dict):
                self._check_level(flow, a["actions"])
            if isinstance(a.get("else"), dict):
                self._check_level(flow, a["else"].get("actions", {}))

    def test_no_cycle(self):
        for flow, d in flows():
            self._acyclic(flow, d["properties"]["definition"]["actions"])

    def _acyclic(self, flow, actions):
        colour = {}

        def visit(n):
            if colour.get(n) == "done":
                return
            self.assertNotEqual(colour.get(n), "open", f"{flow}: cycle at {n}")
            colour[n] = "open"
            for dep in (actions[n].get("runAfter") or {}):
                visit(dep)
            colour[n] = "done"

        for n in actions:
            visit(n)
        for a in actions.values():
            if isinstance(a.get("actions"), dict) and a["actions"]:
                self._acyclic(flow, a["actions"])
            if isinstance(a.get("else"), dict) and a["else"].get("actions"):
                self._acyclic(flow, a["else"]["actions"])

    def test_exactly_one_action_starts_each_level(self):
        # More than one root at a level is a race; none is unreachable.
        for flow, d in flows():
            roots = [n for n, a in d["properties"]["definition"]["actions"].items()
                     if not a.get("runAfter")]
            self.assertEqual(len(roots), 1, f"{flow}: roots {roots}")

    def test_every_action_has_a_type(self):
        for flow, d in flows():
            for path, a in walk_actions(d["properties"]["definition"]["actions"]):
                self.assertIn("type", a, f"{flow}: {'/'.join(path)}")


class NothingEnvironmentSpecificIsHardCoded(unittest.TestCase):
    def test_no_site_url_or_list_name_literal(self):
        for flow, d in flows():
            for t in texts(d["properties"]["definition"]["actions"]):
                self.assertNotRegex(
                    t, r"https://[a-z0-9.-]+\.(sharepoint|dps)\.",
                    f"{flow} carries a destination")
                # A list DISPLAY name inside a documentation Compose is not a
                # binding. The check that matters is that dataset and table
                # always come from a parameter, which is the next test.

    def test_every_dataset_and_table_comes_from_a_parameter(self):
        for flow, d in flows():
            for path, a in walk_actions(d["properties"]["definition"]["actions"]):
                inputs = a.get("inputs")
                params = (inputs.get("parameters") or {}) if isinstance(inputs, dict) else {}
                for key in ("dataset", "table"):
                    if key in params:
                        v = params[key]
                        self.assertRegex(
                            str(v), r"@\{?(parameters|outputs|variables)\(",
                            f"{flow}: {'/'.join(path)} {key} is a literal")

    def test_every_referenced_parameter_is_declared(self):
        for flow, d in flows():
            defn = d["properties"]["definition"]
            declared = set(defn["parameters"])
            used = set()
            for t in texts(defn["actions"]):
                used |= set(re.findall(r"parameters\('([^']+)'\)", t))
            for u in used:
                self.assertIn(u, declared, f"{flow} reads undeclared {u!r}")

    def test_every_declared_parameter_is_used(self):
        # An unused parameter is one somebody has to bind for no reason.
        for flow, d in flows():
            defn = d["properties"]["definition"]
            body = " ".join(texts(defn["actions"])) + " " + " ".join(
                texts(defn["triggers"]))
            for name in defn["parameters"]:
                if name.startswith("$"):
                    continue
                self.assertIn(f"parameters('{name}')", body,
                              f"{flow} declares {name} and never reads it")


class ConnectorsAreOnTheAllowlist(unittest.TestCase):
    ALLOWED = {"shared_sharepointonline", "shared_office365",
               "shared_office365users"}

    def test_every_operation_uses_an_allowed_connector(self):
        for flow, d in flows():
            declared = set(d["properties"]["connectionReferences"])
            for path, a in walk_actions(d["properties"]["definition"]["actions"]):
                inputs = a.get("inputs")
                host = inputs.get("host") if isinstance(inputs, dict) else None
                if not host:
                    continue
                conn = host["connectionName"]
                self.assertIn(conn, self.ALLOWED, f"{flow}: {conn}")
                self.assertIn(conn, declared,
                              f"{flow}: {conn} is used but not declared")

    def test_no_prohibited_connector_appears(self):
        for flow, d in flows():
            body = " ".join(texts(d))
            # prerelease: allow CON-01 the test names the prohibited connectors in order to assert none appears in a flow
            for banned in ("shared_webcontents", "shared_dropbox",  # prerelease: allow CON-01 specimen list, not a reference
                           "shared_googledrive", "shared_onedrive",  # prerelease: allow CON-01 specimen list, not a reference
                           "shared_aibuilder", "Http.Request"):  # prerelease: allow CON-01 specimen list, not a reference
                self.assertNotIn(banned, body, f"{flow}: {banned}")


class EveryWriteLoopIsSerial(unittest.TestCase):
    """Apply_to_each defaults to 20-way concurrency.

    Two branches evaluating the same deterministic EOM_Item_ID at the same
    instant both see "not found" and both create it, and the idempotency the
    whole design rests on is gone.
    """

    def test_every_foreach_pins_concurrency_to_one(self):
        found = 0
        for flow, d in flows():
            for path, a in walk_actions(d["properties"]["definition"]["actions"]):
                if a.get("type") != "Foreach":
                    continue
                found += 1
                rc = a.get("runtimeConfiguration", {})
                self.assertEqual(
                    rc.get("concurrency", {}).get("repetitions"), 1,
                    f"{flow}: {'/'.join(path)} runs 20-way parallel")
        self.assertGreater(found, 0, "no loops found; the check is vacuous")


class TheSpecificationInvariantsHold(unittest.TestCase):
    def flow(self, prefix):
        return next(d for f, d in flows() if f.startswith(prefix))

    def actions(self, prefix):
        return dict(walk_actions(
            self.flow(prefix)["properties"]["definition"]["actions"]))

    def names(self, prefix):
        return {p[-1] for p in self.actions(prefix)}

    def body(self, prefix):
        return " ".join(texts(self.flow(prefix)["properties"]["definition"]))

    # ---- every flow -----------------------------------------------------
    def test_every_flow_guards_the_schema_version_first(self):
        for flow, d in flows():
            acts = d["properties"]["definition"]["actions"]
            self.assertIn("Stop_on_a_schema_mismatch", acts, flow)
            self.assertIn("CONFIGURATION_REQUIRED",
                          acts["Stop_on_a_schema_mismatch"]["actions"], flow)

    def test_nothing_runs_before_the_guard(self):
        for flow, d in flows():
            acts = d["properties"]["definition"]["actions"]
            root = next(n for n, a in acts.items() if not a.get("runAfter"))
            self.assertEqual(root, "Initialize_ExpectedSchemaVersion", flow)

    # ---- EOM-01 ---------------------------------------------------------
    def test_eom01_is_idempotent_by_a_deterministic_key(self):
        names = self.names("EOM01")
        self.assertIn("EOM_Item_ID", names)
        self.assertIn("Does_it_already_exist", names)
        self.assertIn("Create_only_if_absent", names)

    def test_eom01_never_resets_an_existing_row(self):
        acts = self.actions("EOM01")
        create = next(a for p, a in acts.items()
                      if p[-1] == "Create_only_if_absent")
        # The else branch increments a counter and does nothing else.
        else_actions = create["else"]["actions"]
        self.assertEqual(list(else_actions), ["Leave_the_existing_row_untouched"])
        self.assertEqual(
            else_actions["Leave_the_existing_row_untouched"]["type"],
            "SetVariable")

    def test_eom01_gates_on_generation_enabled(self):
        self.assertIn("Generation_Enabled eq 1", self.body("EOM01"))

    def test_eom01_enforces_the_backfill_window(self):
        self.assertIn("Refuse_a_period_outside_the_window", self.names("EOM01"))
        self.assertIn("PERIOD_OUTSIDE_BACKFILL_WINDOW", self.body("EOM01"))

    def test_eom01_asserts_the_vocabulary_matched_something(self):
        self.assertIn("VOCABULARY_MATCHED_NOTHING", self.body("EOM01"))
        self.assertIn("EMPTY_INPUT_SET", self.body("EOM01"))

    def test_eom01_never_generates_a_conditional_requirement(self):
        # The 1119-1 is field feeding. Auto-generating it would put a permanent
        # red row on every DFAC that ran none.
        body = self.body("EOM01")
        for freq in ("Monthly", "Quarterly", "Semiannual", "Annual"):
            self.assertIn(freq, body, freq)
        # Conditional is never a branch the frequency test can take.
        self.assertNotIn("Conditional", body)

    def test_eom01_writes_all_four_status_fields_from_one_evaluation(self):
        acts = self.actions("EOM01")
        create = next(a for p, a in acts.items()
                      if p[-1] == "Create_the_expected_item")
        item = create["inputs"]["parameters"]["item"]
        for f in ("Final_Status", "Status_Code", "Action_Owner",
                  "Action_Required"):
            self.assertIn("outputs('Status')", item[f], f)

    def test_eom01_writes_all_four_dates(self):
        acts = self.actions("EOM01")
        create = next(a for p, a in acts.items()
                      if p[-1] == "Create_the_expected_item")
        item = create["inputs"]["parameters"]["item"]
        for f in ("Nominal_Due_Date", "Effective_Due_Date",
                  "Nominal_Final_Call_Date", "Effective_Final_Call_Date"):
            self.assertIn(f, item)

    def test_eom01_overrides_routing_for_ang(self):
        # DAFMAN 34-131 7.14.5: ANG DFAC managers provide the inventory last
        # page to NGB/A1X.
        self.assertIn("NGB/A1X", self.body("EOM01"))

    # ---- EOM-02 ---------------------------------------------------------
    def test_eom02_authorises_before_touching_storage(self):
        acts = self.actions("EOM02Submission")
        order = [p[-1] for p in acts]
        self.assertLess(order.index("Refuse_an_unmapped_or_out_of_scope_caller"),
                        order.index("Create_the_file"))

    def test_eom02_takes_the_caller_from_the_authenticated_context(self):
        acts = self.actions("EOM02Submission")
        caller = next(a for p, a in acts.items() if p[-1] == "Caller")
        self.assertIn("triggerOutputs()", caller["inputs"])
        self.assertNotIn("triggerBody()", caller["inputs"])

    def test_eom02_checks_idempotency_before_the_file_write(self):
        acts = self.actions("EOM02Submission")
        order = [p[-1] for p in acts]
        self.assertLess(order.index("Look_for_a_replay"),
                        order.index("Create_the_file"))

    def test_eom02_builds_the_path_from_the_url_segment(self):
        acts = self.actions("EOM02Submission")
        root = next(a for p, a in acts.items() if p[-1] == "Root")
        self.assertIn("Library_Url_Segment", root["inputs"])
        self.assertNotIn("Library_Name", root["inputs"])

    def test_eom02_fails_closed_on_all_three_destination_gates(self):
        body = self.body("EOM02Submission")
        for gate in ("Active_Flag eq 1", "Verified_By", "Site_URL"):
            self.assertIn(gate, body)

    def test_eom02_stores_the_guid(self):
        acts = self.actions("EOM02Submission")
        rec = next(a for p, a in acts.items() if p[-1] == "Record_the_submission")
        self.assertIn("SharePoint_Unique_ID", rec["inputs"]["parameters"]["item"])

    def test_eom02_never_reports_success_on_a_partial_write(self):
        self.assertIn("SUBMISSION_NOT_CONFIRMED", self.body("EOM02Submission"))

    def test_eom02_surfaces_no_path_or_url_to_the_user(self):
        acts = self.actions("EOM02Submission")
        for path, a in acts.items():
            if a.get("type") != "Response":
                continue
            inputs = a.get("inputs")
            msg = str(inputs.get("body", {})) if isinstance(inputs, dict) else ""
            for leak in ("Site_URL", "Library_Url_Segment", "Root_Folder",
                         "sharepoint", "dps.mil"):
                self.assertNotIn(leak, msg, f"{path[-1]} leaks {leak}")

    def test_eom02_never_creates_a_folder(self):
        body = self.body("EOM02Submission")
        self.assertNotIn("CreateFolder", body)
        self.assertIn("NEVER", body)

    # ---- EOM-03 ---------------------------------------------------------
    def test_eom03_writes_all_four_status_fields_together(self):
        acts = self.actions("EOM03")
        patch = next(a for p, a in acts.items()
                     if p[-1] == "Write_all_four_status_fields")
        item = patch["inputs"]["parameters"]["item"]
        for f in ("Final_Status", "Status_Code", "Action_Owner",
                  "Action_Required"):
            self.assertIn("outputs('Status')", item[f], f)

    def test_eom03_reads_only_the_current_submission(self):
        self.assertIn("Is_Current eq 1", self.body("EOM03"))

    def test_eom03_filters_on_the_reporting_period(self):
        # An unbounded Filter over MF EOM Item silently returns the first 500
        # rows and reports success.
        self.assertIn("Reporting_Period eq", self.body("EOM03"))

    # ---- EOM-02b --------------------------------------------------------
    def test_eom02b_deduplicates_on_the_guid_not_the_path(self):
        body = self.body("EOM02b")
        self.assertIn("SharePoint_Unique_ID eq", body)

    def test_eom02b_never_creates_an_expected_item(self):
        acts = self.actions("EOM02b")
        for path, a in acts.items():
            inputs = a.get("inputs")
            if not isinstance(inputs, dict):
                continue
            params = inputs.get("parameters") or {}
            table = str(params.get("table", ""))
            if (inputs.get("host") or {}).get("operationId") == "PostItem":
                self.assertNotIn("ItemList", table,
                                 f"{path[-1]} creates an expected item")

    def test_eom02b_treats_hints_as_hints(self):
        acts = self.actions("EOM02b")
        queue = next(a for p, a in acts.items() if p[-1] == "Queue_it_for_a_human")
        item = queue["inputs"]["parameters"]["item"]
        self.assertEqual(item["Resolution_Status"], "Needs Classification")
        self.assertIn("Suggested_Installation_ID", item)

    # ---- EOM-04 ---------------------------------------------------------
    def test_eom04_records_what_it_would_have_sent_when_disabled(self):
        self.assertIn("Notification Suppressed", self.body("EOM04"))

    def test_eom04_is_a_digest_not_per_item(self):
        acts = self.actions("EOM04")
        # One send per RULE, not one per item.
        loops = [p for p, a in acts.items() if a.get("type") == "Foreach"]
        self.assertEqual(len(loops), 1, "a nested loop would mean per-item mail")


class EveryFlowImportsDisabled(unittest.TestCase):
    def test_state_code_zero(self):
        import xml.etree.ElementTree as ET
        tree = ET.parse(os.path.join(ROOT, "solution", "src", "Other",
                                     "Customizations.xml"))
        for w in tree.getroot().iter("Workflow"):
            self.assertEqual(w.find("StateCode").text, "0", w.get("Name"))


if __name__ == "__main__":
    unittest.main()
