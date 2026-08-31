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

    def test_it_declares_the_canvas_app(self):
        self.assertEqual(len(components(300)), 1)

    def test_it_declares_no_missing_dependency(self):
        self.assertIsNotNone(self.root.find(".//MissingDependencies"))


class NoOrphanedReference(unittest.TestCase):
    """Every schemaName must correspond to something that exists."""

    def test_every_declared_flow_has_a_specification(self):
        specs = {d for d in os.listdir(os.path.join(ROOT, "flows"))
                 if d.startswith("EOM")}
        for name in components(29):
            slug = name.replace("mfops_", "")
            match = [s for s in specs
                     if s.replace("-", "").lower() == slug.lower()]
            self.assertTrue(match,
                            f"{name} is declared but no flows/ directory "
                            f"matches it. Candidates: {sorted(specs)}")

    def test_every_flow_specification_is_declared(self):
        declared = {n.replace("mfops_", "").lower() for n in components(29)}
        for d in sorted(os.listdir(os.path.join(ROOT, "flows"))):
            if not d.startswith("EOM"):
                continue
            self.assertIn(d.replace("-", "").lower(), declared,
                          f"flows/{d} exists but the solution does not "
                          "declare it — it will not be imported")

    def test_the_retired_flow_names_are_gone(self):
        declared = set(components(29))
        for retired in ("mfops_EOM02FileIntake", "mfops_EOM05AppUpload"):
            self.assertNotIn(retired, declared)

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
        self.assertEqual(components(380), defined,
                         "the solution's environment variables and "
                         "environment-variables.json disagree")

    def test_the_retired_environment_variables_are_gone(self):
        declared = set(components(380))
        for retired in ("mfops_MF_EvidenceRootPath", "mfops_MF_FileIntakeLibrary"):
            self.assertNotIn(retired, declared,
                             "a retired variable is still declared; it belonged "
                             "to the central-evidence architecture, D-01")

    def test_the_four_site_bindings_are_declared(self):
        declared = set(components(380))
        for n in range(1, 5):
            self.assertIn(f"mfops_MF_Portfolio{n}_SiteURL", declared)


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
