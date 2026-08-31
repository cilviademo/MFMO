"""One implementation per concept, and transliterations held to their reference.

Every snapshot delivered to this programme shipped a current decision table and
stale code implementing it. These tests are the mechanism that stops it.
"""

import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from generate_expected_items import facility_type_applies, model_applies  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# --- a Python model of the Power Fx predicates ----------------------------
# Not a re-implementation of the RULE -- a model of what Power Fx does with the
# expression actually written in Cascade.fx, so the two can be compared on the
# same inputs. If the Fx text changes, this model must change with it, and the
# structural tests below check that the Fx still has the shape this assumes.

def fx_model_applies(applicable_model, operating_model):
    """MF_ModelApplies: !IsBlank(Trim(m)) && (a = "All" || a = m)"""
    if not (operating_model or "").strip():
        return False
    return applicable_model == "All" or applicable_model == operating_model


def fx_facility_type_applies(applicable_types, facility_type):
    """MF_FacilityTypeApplies: delimited exact term, Power Fx `in` semantics.

    Power Fx `in` on text is case-INSENSITIVE substring containment, so the
    model folds case.
    """
    if not (applicable_types or "").strip():
        return True
    if not (facility_type or "").strip():
        return True
    normalised = (applicable_types or "").strip().replace("; ", ";").replace(" ;", ";")
    haystack = f";{normalised};".casefold()
    needle = f";{(facility_type or '').strip()};".casefold()
    return needle in haystack


MODEL_CASES = [
    ("All", "Legacy/APF"), ("All", "Food 2.0"), ("All", ""), ("All", None),
    ("Legacy/APF", "Legacy/APF"), ("Legacy/APF", "Food 2.0"),
    ("Legacy/APF", ""), ("Legacy/APF", None), ("Legacy/APF", "  "),
    ("Food 2.0", "Food 2.0"), ("MAFFO/MAF", "MAFFO/MAF"),
    ("MAFFO/MAF", "AOR/CDS"),
]

TYPE_CASES = [
    ("", "Main DFAC"), ("", ""), (None, "Main DFAC"),
    ("Main DFAC", "Main DFAC"), ("Main DFAC", "Flight Kitchen"),
    ("Main DFAC", ""), ("Main DFAC", None), ("Main DFAC", "   "),
    ("Main DFAC;Flight Kitchen", "Flight Kitchen"),
    ("Main DFAC; Flight Kitchen", "Flight Kitchen"),
    ("Main DFAC ; Flight Kitchen", "Main DFAC"),
    ("MAFFO", "MAF"),                       # substring trap
    ("MAFFO;Satellite", "MAF"),             # substring trap, mid-list
    ("Main DFAC", "main dfac"),             # case
    ("Satellite", "Satellite Kitchen"),     # the reverse substring
]


class ApplicabilityAgrees(unittest.TestCase):
    """The dropdown and the generator answer different questions with the same
    predicate. A dropdown that offers a requirement EOM-01 would never generate
    argues with the checklist beside it."""

    def test_model_applies_agrees(self):
        for applicable, operating in MODEL_CASES:
            self.assertEqual(
                model_applies({"Applicable_Model": applicable}, operating),
                fx_model_applies(applicable, operating),
                f"Applicable_Model={applicable!r} Operating_Model={operating!r}")

    def test_facility_type_applies_agrees(self):
        for types, facility_type in TYPE_CASES:
            self.assertEqual(
                facility_type_applies({"Applicable_Facility_Types": types},
                                      facility_type),
                fx_facility_type_applies(types, facility_type),
                f"Applicable_Facility_Types={types!r} Facility_Type={facility_type!r}")

    def test_an_unknown_type_matches_on_both_sides(self):
        # Every QRG facility has a blank type today. Excluding on it would hide
        # every type-scoped requirement from every facility.
        req = {"Applicable_Facility_Types": "Main DFAC;Flight Kitchen"}
        self.assertTrue(facility_type_applies(req, ""))
        self.assertTrue(fx_facility_type_applies("Main DFAC;Flight Kitchen", ""))

    def test_a_substring_is_not_a_match_on_either_side(self):
        # The old inline Fx matched "MAF" inside "MAFFO".
        req = {"Applicable_Facility_Types": "MAFFO"}
        self.assertFalse(facility_type_applies(req, "MAF"))
        self.assertFalse(fx_facility_type_applies("MAFFO", "MAF"))

    def test_a_facility_with_no_model_matches_nothing(self):
        # The 20 NO_DFAC registry rows. A base with no feeding facility owes
        # no 1119.
        self.assertFalse(model_applies({"Applicable_Model": "All"}, ""))
        self.assertFalse(fx_model_applies("All", ""))


class TheFxStillHasTheShapeTheModelAssumes(unittest.TestCase):
    def setUp(self):
        self.fx = read("canvas-app", "formulas", "Cascade.fx")

    def test_the_predicates_are_named_functions(self):
        self.assertRegex(self.fx, r"(?m)^MF_ModelApplies\(")
        self.assertRegex(self.fx, r"(?m)^MF_FacilityTypeApplies\(")

    def test_the_dropdown_calls_them_rather_than_inlining(self):
        block = self.fx.split("MF_RequirementChoices(")[1].split(";")[0]
        self.assertIn("MF_ModelApplies(", block)
        self.assertIn("MF_FacilityTypeApplies(", block)

    def test_the_old_inline_predicate_is_gone(self):
        # `IsBlank(Applicable_Facility_Types) || FacilityType in ...` gave the
        # right answer for a blank type only because the empty string is a
        # substring of everything.
        self.assertNotIn("FacilityType in Applicable_Facility_Types", self.fx)
        self.assertNotIn("Applicable_Model = OperatingModel ||", self.fx)

    def test_the_type_match_is_delimited(self):
        block = self.fx.split("MF_FacilityTypeApplies(")[1].split(";\n\n")[0]
        self.assertIn('";"', block, "the match is not wrapped in the separator")


class OneImplementationPerConcept(unittest.TestCase):
    def test_only_one_status_engine_is_executable(self):
        # Python reference plus one Fx transliteration. A third would be a
        # third opinion.
        engine = read("scripts", "status_engine.py")
        self.assertEqual(len(re.findall(r"(?m)^def item_status\(", engine)), 1)
        fx = read("canvas-app", "formulas", "StatusEngine.fx")
        self.assertEqual(len(re.findall(r"(?m)^MF_EvaluateStatus\(", fx)), 1)

    def test_no_screen_evaluates_status_with_its_own_switch(self):
        for base, _, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for name in files:
                if not name.endswith(".pa.yaml"):
                    continue
                body = read(os.path.relpath(os.path.join(base, name), ROOT))
                self.assertNotRegex(
                    body, r"Switch\(\s*ThisItem\.Status_Code",
                    f"{name} derives from the code instead of calling the engine")

    def test_no_screen_supersedes_a_submission(self):
        # Supersession is EOM-02's. A screen that patched Is_Current could
        # leave two current versions for one item.
        for base, _, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for name in files:
                if not name.endswith(".pa.yaml"):
                    continue
                body = read(os.path.relpath(os.path.join(base, name), ROOT))
                for line in body.splitlines():
                    if "Patch(" in line and ("Is_Current" in line
                                             or "Superseded_By" in line):
                        self.fail(f"{name} supersedes a submission: {line.strip()}")

    def test_only_one_destination_resolver_exists(self):
        resolver = read("scripts", "folder_resolver.py")
        self.assertEqual(
            len(re.findall(r"(?m)^def resolve_destination_folder\(", resolver)), 1)
        # And the app has none: it supplies logical identifiers, never a path.
        for base, _, files in os.walk(os.path.join(ROOT, "canvas-app")):
            for name in files:
                if not name.endswith((".pa.yaml", ".fx")):
                    continue
                body = read(os.path.relpath(os.path.join(base, name), ROOT))
                self.assertNotIn("Root_Folder", body,
                                 f"{name} knows about a destination path")


class TheSecondUploadArchitectureIsGone(unittest.TestCase):
    """The central evidence library was a live second write target, not a stale
    document. Removed from the packaging path; only the explanation survives."""

    RETIRED = ("EvidenceRootPath", "EOM_Root_Path", "gblEOMRootPath",
               "New-EvidenceLibrary", "Mission Feeding Evidence")

    def live_files(self):
        skip = {"reference", "archive", ".git", "__pycache__", "dist"}
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in files:
                if name.endswith((".fx", ".pa.yaml", ".csv", ".json", ".ps1")):
                    yield os.path.relpath(os.path.join(base, name), ROOT)

    def test_no_live_artifact_references_the_retired_architecture(self):
        offenders = []
        for rel in self.live_files():
            body = read(rel)
            for token in self.RETIRED:
                if token in body:
                    offenders.append(f"{rel}: {token}")
        self.assertEqual(offenders, [])

    def test_provisioning_creates_no_document_library(self):
        ps1 = read("provisioning", "Provision-MFOpsLists.ps1")
        self.assertNotIn("Template DocumentLibrary", ps1)

    def test_the_decision_is_recorded(self):
        log = read("docs", "DECISION_LOG.md")
        self.assertIn("D-01", log)
        self.assertRegex(log, r"(?i)central evidence library retired")


if __name__ == "__main__":
    unittest.main()
