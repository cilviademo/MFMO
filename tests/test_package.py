"""Offline package structure validation.

PAC CLI cannot authenticate here, so tenant-side import validation remains
outstanding — `docs/TEST_MATRIX.md` N1 and N2. Everything checkable without a
tenant is checked here.

The failure this prevents: an orphaned RootComponent. A flow that was renamed
or an environment variable that was retired fails the import with a message
naming the missing component and nothing else useful, at the worst possible
moment.
"""

import json
import os
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOLUTION = os.path.join(ROOT, "solution", "src", "Other")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def solution_xml():
    return ET.parse(os.path.join(SOLUTION, "Solution.xml")).getroot()


def components(type_id):
    return [c.get("schemaName") for c in solution_xml().iter("RootComponent")
            if c.get("type") == str(type_id)]


def workflows():
    """The Workflow entries in Customizations.xml."""
    tree = ET.parse(os.path.join(SOLUTION, "Customizations.xml"))
    return list(tree.getroot().iter("Workflow"))


def flow_json(rel):
    with open(os.path.join(ROOT, "solution", "src", rel.lstrip("/")),
              encoding="utf-8") as fh:
        return json.load(fh)


class TheFilesAreWellFormed(unittest.TestCase):
    def test_solution_xml_parses(self):
        solution_xml()

    def test_customizations_xml_parses(self):
        ET.parse(os.path.join(SOLUTION, "Customizations.xml"))

    def test_every_config_json_parses(self):
        for name in ("environment-variables.json", "connection-references.json"):
            with open(os.path.join(ROOT, "configuration", name),
                      encoding="utf-8") as fh:
                json.load(fh)


class TheManifestIsComplete(unittest.TestCase):
    def setUp(self):
        self.root = solution_xml()

    def test_it_declares_a_unique_name_and_publisher_prefix(self):
        self.assertEqual(self.root.find(".//UniqueName").text,
                         "MissionFeedingOperations")
        self.assertEqual(self.root.find(".//CustomizationPrefix").text, "mfops")

    def test_it_ships_unmanaged(self):
        # A managed solution cannot be edited in the maker portal, which is how
        # the four site bindings get set after import.
        self.assertEqual(self.root.find(".//Managed").text, "0")

    def test_it_declares_five_flows(self):
        self.assertEqual(len(components(29)) or len(
            [c for c in self.root.iter("RootComponent")
             if c.get("type") == "29"]), 5)

    def test_it_declares_no_missing_dependency(self):
        self.assertIsNotNone(self.root.find(".//MissingDependencies"))


class NoOrphanedReference(unittest.TestCase):
    """Every declared component must correspond to something that exists.

    An orphaned RootComponent fails the import with a message naming the
    missing component and nothing else useful, at the worst possible moment.
    """

    def test_every_declared_workflow_has_a_json_file(self):
        for w in workflows():
            rel = w.find("JsonFileName").text.lstrip("/")
            path = os.path.join(ROOT, "solution", "src", rel)
            self.assertTrue(os.path.exists(path),
                            f"{w.get('Name')} references {rel}, which is absent")

    def test_every_json_file_is_declared(self):
        declared = {w.find("JsonFileName").text.lstrip("/").split("/")[-1]
                    for w in workflows()}
        present = set(os.listdir(os.path.join(ROOT, "solution", "src",
                                              "Workflows")))
        self.assertEqual(present, declared,
                         "a workflow file exists that nothing declares, or vice "
                         "versa. Either will not be imported")

    def test_every_workflow_root_component_matches_a_workflow(self):
        ids = {c.get("id", "").strip("{}").lower()
               for c in solution_xml().iter("RootComponent")
               if c.get("type") == "29"}
        declared = {w.get("WorkflowId").strip("{}").lower() for w in workflows()}
        self.assertEqual(ids, declared)

    def test_the_five_flows_are_present(self):
        names = {w.get("Name") for w in workflows()}
        self.assertEqual(len(names), 5)
        for expected in ("EOM-01", "EOM-02 ", "EOM-02b", "EOM-03", "EOM-04"):
            self.assertTrue(any(expected in n for n in names), expected)

    def test_the_retired_flow_names_are_gone(self):
        body = read("solution", "src", "Other", "Customizations.xml")
        for retired in ("EOM02FileIntake", "EOM05AppUpload", "EOM-05"):
            self.assertNotIn(retired, body)

    def test_every_declared_connection_reference_exists(self):
        with open(os.path.join(ROOT, "configuration",
                               "connection-references.json"),
                  encoding="utf-8") as fh:
            defined = {c["schemaName"] for c in json.load(fh)["connectionReferences"]}
        self.assertEqual(set(components(10108)), defined)

    def test_every_declared_environment_variable_exists(self):
        with open(os.path.join(ROOT, "configuration",
                               "environment-variables.json"),
                  encoding="utf-8") as fh:
            defined = [v["schemaName"] for v in json.load(fh)["environmentVariables"]]
        self.assertEqual(components(380), defined)

    def test_the_retired_environment_variables_are_gone(self):
        declared = set(components(380))
        for retired in ("mfops_MF_EvidenceRootPath", "mfops_MF_FileIntakeLibrary"):
            self.assertNotIn(retired, declared)

    def test_the_four_site_bindings_are_declared(self):
        declared = set(components(380))
        for n in range(1, 5):
            self.assertIn(f"mfops_MF_Portfolio{n}_SiteURL", declared)


class ThePackageHasNoCanvasApp(unittest.TestCase):
    """A hand-authored .msapp that Studio rejects is worse than none.

    The import fails with an error naming an internal file and explaining
    nothing, and whoever is holding it spends an afternoon assuming the tenant
    is at fault.
    """

    def test_no_msapp_and_no_placeholder(self):
        for base, _, files in os.walk(os.path.join(ROOT, "solution")):
            for n in files:
                self.assertFalse(n.endswith(".msapp"),
                                 f"{n} is a canvas app binary this build "
                                 "cannot validate")

    def test_no_canvas_app_root_component_is_declared(self):
        # Type 300 is a canvas app. Declaring one the package does not contain
        # fails the import.
        self.assertEqual(components(300), [],
                         "the manifest declares a canvas app that is not here")

    def test_the_absence_is_stated_in_the_manifest(self):
        body = read("solution", "src", "Other", "Solution.xml")
        self.assertRegex(body, r"(?i)canvas app is not in this package")

    def test_the_assembly_guide_exists_and_is_substantive(self):
        path = os.path.join(ROOT, "CANVAS_APP_ASSEMBLY.md")
        self.assertTrue(os.path.exists(path),
                        "the app is excluded but nothing says how to build it")
        self.assertGreater(len(read("CANVAS_APP_ASSEMBLY.md").strip()), 3000)


class TheFlowsAreWiredEvenWhereTheyAreUnfinished(unittest.TestCase):
    def flows(self):
        for w in workflows():
            yield w.get("Name"), flow_json(w.find("JsonFileName").text)

    def test_every_flow_has_a_trigger(self):
        for name, d in self.flows():
            triggers = d["properties"]["definition"]["triggers"]
            self.assertEqual(len(triggers), 1, name)

    def test_every_flow_binds_its_connection_references(self):
        with open(os.path.join(ROOT, "configuration",
                               "connection-references.json"),
                  encoding="utf-8") as fh:
            known = {c["schemaName"] for c in json.load(fh)["connectionReferences"]}
        for name, d in self.flows():
            refs = d["properties"]["connectionReferences"]
            self.assertTrue(refs, f"{name} binds no connection")
            for r in refs.values():
                logical = r["connection"]["connectionReferenceLogicalName"]
                self.assertIn(logical, known,
                              f"{name} binds {logical}, which the solution "
                              "does not declare")

    def test_every_flow_reads_environment_variables_not_literals(self):
        with open(os.path.join(ROOT, "configuration",
                               "environment-variables.json"),
                  encoding="utf-8") as fh:
            known = {v["schemaName"] for v in json.load(fh)["environmentVariables"]}
        for name, d in self.flows():
            params = d["properties"]["definition"]["parameters"]
            bound = [p["metadata"]["schemaName"] for p in params.values()
                     if isinstance(p, dict) and "metadata" in p]
            self.assertTrue(bound, f"{name} reads no environment variable")
            for b in bound:
                self.assertIn(b, known, f"{name} reads unknown variable {b}")

    def test_no_flow_contains_a_site_url(self):
        for name, d in self.flows():
            body = json.dumps(d)
            self.assertNotRegex(body, r"https://[a-z0-9.-]+\.(sharepoint|dps)\.",
                                f"{name} carries a destination")

    def test_every_flow_checks_the_schema_version_before_writing(self):
        # A flow can be invoked directly, and a scheduled flow has no app in
        # front of it at all.
        for name, d in self.flows():
            actions = d["properties"]["definition"]["actions"]
            self.assertIn("Stop_on_a_schema_mismatch", actions, name)
            branch = actions["Stop_on_a_schema_mismatch"]["actions"]
            self.assertIn("CONFIGURATION_REQUIRED", branch, name)
            self.assertEqual(
                branch["CONFIGURATION_REQUIRED"]["type"], "Terminate", name)

    def test_the_expected_schema_version_matches_the_schema(self):
        import sys as _sys
        _sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import eom_schema as S
        for name, d in self.flows():
            init = d["properties"]["definition"]["actions"][
                "Initialize_ExpectedSchemaVersion"]
            self.assertEqual(init["inputs"]["variables"][0]["value"],
                             S.SCHEMA_VERSION, name)

    def test_every_flow_has_a_body_beyond_the_guard(self):
        # The bodies are implemented now. A flow carrying only the schema guard
        # would be a shell that imports and does nothing.
        guard = {"Initialize_ExpectedSchemaVersion",
                 "Get_the_deployed_schema_version", "Stop_on_a_schema_mismatch"}
        for name, d in self.flows():
            acts = set(d["properties"]["definition"]["actions"])
            self.assertTrue(acts - guard,
                            f"{name} is a shell: it has only the schema guard")
            self.assertGreaterEqual(len(acts), 5, name)

    def test_every_specification_still_exists(self):
        import glob
        for d in ("EOM01-ExpectedPackage", "EOM02-Submission",
                  "EOM02b-LegacyIntake", "EOM03-Reconciliation",
                  "EOM04-Notifications"):
            self.assertTrue(
                os.path.exists(os.path.join(ROOT, "flows", d, "definition.md")),
                f"flows/{d}/definition.md is the source for its body")

    def test_every_flow_imports_disabled(self):
        # Flows are enabled one at a time, in order, after EOM-01 is proven.
        for w in workflows():
            self.assertEqual(w.find("StateCode").text, "0", w.get("Name"))

    def test_the_submission_flow_does_not_accept_a_caller_identity(self):
        d = dict(self.flows())["EOM-02 Submission"]
        schema = d["properties"]["definition"]["triggers"]["Request"][
            "inputs"]["schema"]["properties"]
        self.assertNotIn("uploadedBy", schema)
        self.assertIn("submissionRequestId", schema)
        self.assertIn("submissionRequestId",
                      d["properties"]["definition"]["triggers"]["Request"][
                          "inputs"]["schema"]["required"])


class NothingEnvironmentSpecificIsBaked(unittest.TestCase):
    def test_no_url_appears_in_the_solution_files(self):
        for name in ("Solution.xml", "Customizations.xml"):
            body = read("solution", "src", "Other", name)
            self.assertNotRegex(body, r"https://[a-z0-9.-]+\.(sharepoint|dps)\.")

    def test_every_environment_variable_default_is_blank(self):
        with open(os.path.join(ROOT, "configuration",
                               "environment-variables.json"),
                  encoding="utf-8") as fh:
            for v in json.load(fh)["environmentVariables"]:
                self.assertEqual(v["defaultValue"], "", v["schemaName"])


class VersionsAgree(unittest.TestCase):
    """The artifact must trace to one version."""

    def versions(self):
        import csv
        with open(os.path.join(ROOT, "configuration", "app-config.csv"),
                  encoding="utf-8-sig") as fh:
            cfg = {r["Config_Key"]: r["Config_Value"] for r in csv.DictReader(fh)}
        return {
            "solution": solution_xml().find(".//Version").text,
            "app_config": cfg["AppVersion"],
            "changelog": re.search(r"(?m)^## \[([0-9.]+)\]",
                                   read("CHANGELOG.md")).group(1),
        }

    def test_one_version_everywhere(self):
        v = self.versions()
        self.assertEqual(len(set(v.values())), 1,
                         f"version drift: {v}")


class CustomizationsMatchesTheConfiguration(unittest.TestCase):
    """Customizations.xml declares the environment variable DEFINITIONS. It
    drifted: it still defined MF_FileIntakeLibrary and MF_EvidenceRootPath, the
    two variables belonging to the retired central-evidence architecture, and
    knew nothing of the four site bindings."""

    def defs(self):
        tree = ET.parse(os.path.join(SOLUTION, "Customizations.xml"))
        return [e.get("schemaname")
                for e in tree.getroot().iter("environmentvariabledefinition")]

    def declared(self):
        with open(os.path.join(ROOT, "configuration",
                               "environment-variables.json"),
                  encoding="utf-8") as fh:
            return [v["schemaName"] for v in json.load(fh)["environmentVariables"]]

    def test_the_definitions_match_the_configuration_exactly(self):
        self.assertEqual(self.defs(), self.declared())

    def test_the_retired_variables_are_gone(self):
        for retired in ("mfops_MF_EvidenceRootPath", "mfops_MF_FileIntakeLibrary"):
            self.assertNotIn(retired, self.defs())

    def test_the_four_site_bindings_are_defined(self):
        for n in range(1, 5):
            self.assertIn(f"mfops_MF_Portfolio{n}_SiteURL", self.defs())

    def test_no_retired_flow_is_named(self):
        body = read("solution", "src", "Other", "Customizations.xml")
        for retired in ("EOM-05", "EOM05", "EvidenceRootPath"):
            self.assertNotIn(retired, body)


class TheDependencyManifestIsUsable(unittest.TestCase):
    """A valid ZIP does not prove its dependencies exist."""

    CATEGORIES = ("PROVISIONED BY BUILD", "MUST ALREADY EXIST",
                  "CREATED BY DEPLOYMENT SCRIPT", "MANUAL .MIL CONFIGURATION",
                  "OPTIONAL / FEATURE-GATED")

    def setUp(self):
        self.doc = read("deployment", "DEPENDENCY_MANIFEST.md")

    def test_it_exists_and_is_substantive(self):
        self.assertGreater(len(self.doc.strip()), 2000)

    def test_every_category_is_used(self):
        for c in self.CATEGORIES:
            self.assertIn(f"## {c}", self.doc,
                          f"no resources are classified {c}")

    def test_every_row_has_an_owner(self):
        # A dependency with no owner is a dependency nobody will provision.
        in_table = False
        for line in self.doc.splitlines():
            if line.startswith("| Resource | Owner | Note |"):
                in_table = True
                continue
            if in_table:
                if not line.startswith("|"):
                    in_table = False
                    continue
                if set(line.replace("|", "").strip()) <= set("-: "):
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                self.assertGreaterEqual(len(cells), 3, line)
                self.assertTrue(cells[1], f"no owner: {line}")

    def test_every_list_in_the_schema_is_accounted_for(self):
        import sys as _sys
        _sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import eom_schema as S
        for l in S.LISTS:
            self.assertIn(f"`{l.name}`", self.doc,
                          f"{l.name} is not in the dependency manifest")

    def test_all_four_site_collections_must_already_exist(self):
        block = self.doc.split("## MUST ALREADY EXIST")[1].split("\n## ")[0]
        for n in range(1, 5):
            self.assertIn(f"PORTFOLIO {n}", block,
                          f"Portfolio {n}'s site is not listed as pre-existing")

    def test_the_pre_existing_list_hazard_is_named_with_a_detection_and_an_owner(self):
        block = self.doc.split("## The pre-existing list hazard")[1]
        self.assertIn("-WhatIf", block, "no detection method")
        self.assertIn("Get-PnPField", block, "no way to compare internal names")
        self.assertRegex(block, r"(?i)who resolves it")
        self.assertRegex(block, r"(?i)build team")
        # And the wrong fix is named as wrong.
        self.assertRegex(block, r"(?i)never resolve this by editing")

    def test_it_says_what_the_import_does_not_do(self):
        block = self.doc.split("## What importing the ZIP does not do")[1]
        for claim in ("SharePoint lists", "document libraries", "month folders",
                      "security groups", "DLP", "site URLs", "enable the flows"):
            self.assertIn(claim, block, f"the manifest does not disclaim {claim}")

    def test_it_is_a_required_release_artifact(self):
        import sys as _sys
        _sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import prerelease_scan as SCAN
        self.assertIn("deployment/DEPENDENCY_MANIFEST.md", SCAN.REQUIRED_FILES,
                      "a missing dependency manifest must block the release")


if __name__ == "__main__":
    unittest.main()


class LegacyIntakeShipsUnbound(unittest.TestCase):
    """EOM-02b is a template, and the package must not disguise that.

    A SharePoint trigger watches ONE site and ONE library. The four portfolios
    are four separate site collections, so no single instance can cover them.
    Shipping it bound to Portfolio 1 would import, activate, run, and discover
    nothing in Portfolios 2-4 -- partial coverage that looks exactly like full
    coverage until an inspection asks. It ships unbound so the designer shows
    an unset field, and it is duplicated once per portfolio at import.
    """

    def setUp(self):
        path = os.path.join(
            ROOT, "solution", "src", "Workflows",
            "EOM02bLegacyIntake-323616FA-0B7F-52FF-B827-CFECD58890D3.json")
        with open(path, encoding="utf-8") as fh:
            self.flow = json.load(fh)
        self.trigger = self.flow["properties"]["definition"]["triggers"][
            "SharePointFileCreated"]

    def test_the_trigger_names_no_site_and_no_library(self):
        params = self.trigger["inputs"]["parameters"]
        self.assertEqual(params["dataset"], "")
        self.assertEqual(params["table"], "")

    def test_it_does_not_single_out_one_portfolio(self):
        body = json.dumps(self.flow)
        for n in (1, 2, 3, 4):
            self.assertNotIn(f"MF_Portfolio{n}_SiteURL", body,
                             "the legacy intake template must not bind to a "
                             "single portfolio site")

    def test_the_import_checklist_gives_the_four_imperative_steps(self):
        """A template nobody duplicates leaves three portfolios unmonitored and
        looking exactly like three portfolios with nothing to report. The
        checklist has to say so as instructions, not as background."""
        with open(os.path.join(ROOT, "dist", "MissionFeedingOperations_1.0.0",
                               "IMPORT_CHECKLIST.md"), encoding="utf-8") as fh:
            text = " ".join(fh.read().split())
        self.assertIn("EOM-02b", text)
        for step in (r"(?i)duplicate it three times",
                     r"(?i)bind each copy to a different site collection",
                     r"(?i)verify the four copies point at four distinct sites",
                     r"(?i)leave all four disabled"):
            self.assertRegex(text, step)


class ImportChecklistIsSequenced(unittest.TestCase):
    """The order is load-bearing, not editorial. Indexes cannot be added once a
    list passes 5,000 items, so verification has to precede any data; and
    nothing downstream has anything to act on until EOM-01 has run."""

    STEPS = [
        "Provision the 17 lists",
        "Verify the indexes",
        "Import the six configuration CSVs",
        "Add the first user to MF Security Mapping",
        "Import the solution ZIP",
        "Bind the connection reference and all 24 environment variables",
        "Duplicate EOM-02b three times",
        "Build the canvas app",
        "Enable EOM-01 only, and run it twice",
    ]

    def setUp(self):
        with open(os.path.join(ROOT, "dist", "MissionFeedingOperations_1.0.0",
                               "IMPORT_CHECKLIST.md"), encoding="utf-8") as fh:
            self.text = fh.read()

    def test_every_step_appears_in_order(self):
        at = -1
        for step in self.STEPS:
            found = self.text.find(step)
            self.assertNotEqual(found, -1, f"missing step: {step}")
            self.assertGreater(found, at, f"step out of order: {step}")
            at = found

    def test_index_verification_precedes_any_data_load(self):
        self.assertLess(self.text.find("Verify the indexes"),
                        self.text.find("Import the six configuration CSVs"))

    def test_it_routes_provisioning_away_from_powershell(self):
        flat = " ".join(self.text.split())
        self.assertIn("PROVISION-WITHOUT-POWERSHELL.md", flat)
        self.assertRegex(flat, r"(?i)PowerShell is unavailable on this network")

    def test_it_states_both_737_expectations(self):
        flat = " ".join(self.text.split())
        self.assertRegex(flat, r"(?i)737 .{0,30}rows")
        self.assertRegex(flat, r"(?i)still 737")
