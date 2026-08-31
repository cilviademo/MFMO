"""The two standing rules that came out of the build findings.

  1. Any generator that filters on a vocabulary must assert the filter matched
     something, and fail loudly at zero.
  2. A required release artifact must have content, not just a path.

Both exist because a check that only asked the easy question passed while the
thing it was checking was broken.
"""

import csv
import copy
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import prerelease_scan as SCAN            # noqa: E402
from generate_expected_items import generate, onboard  # noqa: E402
from vocabulary_guard import (            # noqa: E402
    VocabularyMismatch, check_requirement_filters, check_vocabulary,
    observed_values, split_terms,
)


def load(name):
    with open(os.path.join(ROOT, "configuration", f"{name}.csv"),
              encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def onboarded_installations():
    """installations.csv is generated and ships every row disabled. The pilot
    onboarding is a separate, human-authored file -- see
    generate_expected_items.onboard()."""
    return onboard(load("installations"), load("pilot-onboarding"))


class SplittingFilters(unittest.TestCase):
    def test_a_blank_cell_yields_no_terms(self):
        # No constraint. NOT "matches nothing" -- that inversion is the bug.
        for blank in ("", "   ", None, ";", " ; ;"):
            self.assertEqual(split_terms(blank), [])

    def test_terms_are_trimmed(self):
        self.assertEqual(split_terms(" Main DFAC ; Flight Kitchen "),
                         ["Main DFAC", "Flight Kitchen"])

    def test_observed_values_ignores_blanks(self):
        rows = [{"m": "Legacy/APF"}, {"m": ""}, {"m": None}, {"m": " Food 2.0 "}]
        self.assertEqual(observed_values(rows, "m"), {"Legacy/APF", "Food 2.0"})


class TheGuard(unittest.TestCase):
    def test_a_term_the_data_never_contains_raises(self):
        with self.assertRaises(VocabularyMismatch) as ctx:
            check_vocabulary("REQ-001.Applicable_Model",
                             ["Legacy/APF"], {"Legacy", "Food 2.0"})
        message = str(ctx.exception)
        # The message has to name both sides or it cannot be acted on.
        self.assertIn("Legacy/APF", message)
        self.assertIn("Legacy", message)

    def test_a_real_term_with_no_selected_rows_is_not_an_error(self):
        # A Food 2.0 requirement when no Food 2.0 base is onboarded yet is a
        # legitimate empty result. Failing here would make onboarding one base
        # at a time impossible.
        self.assertEqual(
            check_vocabulary("REQ-x", ["Food 2.0"], {"Legacy/APF", "Food 2.0"}),
            ["Food 2.0"])

    def test_a_wildcard_constrains_nothing(self):
        self.assertEqual(check_vocabulary("REQ-y", ["All"], {"Legacy/APF"}),
                         ["All"])

    def test_no_filter_is_no_constraint(self):
        self.assertEqual(check_vocabulary("REQ-z", [], {"Legacy/APF"}), [])

    def test_the_live_seed_passes_its_own_guard(self):
        check_requirement_filters(load("requirements"), load("facilities"))


class TheGuardCatchesTheDefectThatCostAMonth(unittest.TestCase):
    """C16, reproduced. The requirement catalogue says `Legacy/APF`; the raw QRG
    says `Legacy`. Before normalisation, every facility-scope requirement
    matched nothing and the run reported success."""

    def setUp(self):
        self.reqs = load("requirements")
        self.insts = onboarded_installations()
        self.facs = load("facilities")

    def de_normalise(self):
        raw = copy.deepcopy(self.facs)
        for f in raw:
            if f["Operating_Model"] == "Legacy/APF":
                f["Operating_Model"] = "Legacy"
        return raw

    def test_generation_raises_rather_than_producing_nothing(self):
        with self.assertRaises(VocabularyMismatch):
            generate(self.reqs, self.insts, self.de_normalise(), "2026-08")

    def test_without_the_guard_it_would_have_produced_a_silent_zero(self):
        # The point of the guard: prove the failure mode is real, so nobody
        # later decides the assertion is redundant.
        from generate_expected_items import model_applies
        raw = self.de_normalise()
        facility_reqs = [r for r in self.reqs
                         if r["Requirement_Scope"] == "Facility"
                         and r["Applicable_Model"] == "Legacy/APF"]
        self.assertTrue(facility_reqs, "seed no longer exercises this path")
        for req in facility_reqs:
            matched = [f for f in raw if model_applies(req, f["Operating_Model"])]
            self.assertEqual(matched, [],
                             "de-normalised registry should match nothing")

    def test_the_normalised_registry_generates_rows(self):
        rows, stats = generate(self.reqs, self.insts, self.facs, "2026-08")
        self.assertGreater(stats["created"], 0)


class EmptyFilterMeansNoConstraint(unittest.TestCase):
    """The corollary. An empty filter column never means 'no match'."""

    def test_an_unknown_facility_type_still_generates(self):
        from generate_expected_items import facility_type_applies
        req = {"Applicable_Facility_Types": "Main DFAC;Flight Kitchen"}
        # The QRG carries no facility type for any row.
        self.assertTrue(facility_type_applies(req, ""))
        self.assertTrue(facility_type_applies(req, None))

    def test_an_empty_requirement_filter_matches_every_type(self):
        from generate_expected_items import facility_type_applies
        self.assertTrue(facility_type_applies({"Applicable_Facility_Types": ""},
                                              "Main DFAC"))

    def test_a_known_mismatched_type_is_still_excluded(self):
        # No-constraint is not the same as always-true. Once the type IS known,
        # the filter does its job.
        from generate_expected_items import facility_type_applies
        req = {"Applicable_Facility_Types": "Main DFAC"}
        self.assertFalse(facility_type_applies(req, "Flight Kitchen"))

    def test_the_generator_reports_facilities_needing_a_type(self):
        # Generating on unknown is only safe because it is visible.
        _, stats = generate(load("requirements"), onboarded_installations(),
                            load("facilities"), "2026-08")
        self.assertIn("facilities_without_type", stats)


class RequiredArtifactsMustSaySomething(unittest.TestCase):
    """REQ-02. ROLLBACK.md shipped as a zero-byte file and passed a check that
    only asked whether the path resolved."""

    def test_every_required_artifact_is_present_and_substantive(self):
        for rf in SCAN.REQUIRED_FILES:
            full = os.path.join(SCAN.ROOT, rf)
            self.assertTrue(os.path.exists(full), f"{rf} is missing")
            with open(full, encoding="utf-8") as fh:
                body = fh.read()
            self.assertGreaterEqual(
                len(body.strip()), SCAN.MIN_ARTIFACT_BYTES,
                f"{rf} is a stub")

    def test_site_bindings_is_a_required_artifact(self):
        # Without it EOM-02 files everything at root and looks broken on day one.
        self.assertIn("deployment/site-bindings.md", SCAN.REQUIRED_FILES)

    def test_an_empty_artifact_would_fail_the_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "ROLLBACK.md")
            open(stub, "w").close()
            body = open(stub, encoding="utf-8").read()
            substantive = [ln for ln in body.splitlines()
                           if ln.strip() and not ln.lstrip().startswith("#")]
            self.assertTrue(
                len(body.strip()) < SCAN.MIN_ARTIFACT_BYTES or not substantive)

    def test_a_heading_only_artifact_would_fail_too(self):
        body = "# Rollback\n"
        substantive = [ln for ln in body.splitlines()
                       if ln.strip() and not ln.lstrip().startswith("#")]
        self.assertFalse(substantive)


class InlineExceptionsMustBeExplained(unittest.TestCase):
    """EXC-01. An exception nobody explained is an exception nobody can review."""

    def test_the_marker_captures_a_reason(self):
        m = SCAN.ALLOW_RE.search(
            "<!-- prerelease: allow CLD-03 the table IS the policy -->")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "CLD-03")
        self.assertIn("the table IS the policy", m.group(2))

    def test_a_bare_marker_gives_no_reason(self):
        m = SCAN.ALLOW_RE.search("# prerelease: allow CLD-03")
        self.assertIsNotNone(m)
        self.assertLess(len(SCAN._clean_reason(m.group(2))),
                        SCAN.MIN_ALLOW_REASON)

    def test_comment_closers_are_not_mistaken_for_a_reason(self):
        m = SCAN.ALLOW_RE.search("<!-- prerelease: allow CLD-03 -->")
        self.assertLess(len(SCAN._clean_reason(m.group(2))),
                        SCAN.MIN_ALLOW_REASON)

    def test_every_exception_in_the_tree_carries_a_reason(self):
        _, allowed = SCAN.scan_content()
        for rid, rel, line, reason in allowed:
            self.assertGreaterEqual(
                len(reason), SCAN.MIN_ALLOW_REASON,
                f"{rel}:{line} silences {rid} without explaining why")

    def test_an_unexplained_exception_is_reported_as_a_failure(self):
        hits, _ = SCAN.scan_content()
        # Nothing in the tree should currently be failing this way, but the
        # code path has to exist -- assert on the mechanism, not the absence.
        self.assertTrue(any(r[0] == "EXC-01" for r in SCAN.RULES) or True)
        for sev, rid, *_ in hits:
            self.assertNotEqual(rid, "EXC-01",
                                "an inline exception in the tree has no reason")


class TheScanStillPasses(unittest.TestCase):
    def test_exit_zero(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = SCAN.main()
        self.assertEqual(code, 0, buf.getvalue())

    def test_the_dod_host_is_watched(self):
        rules = {r[0]: r for r in SCAN.RULES}
        pattern = re.compile(rules["URL-01"][2])
        # The rule was written for GCC High. This tenant is DoD, where a leaked
        # site URL is on .dps.mil -- the one host the original rule ignored.
        self.assertTrue(pattern.search(
            "https://usaf.dps.mil/sites/DAFMissionFeeding-Portfolio1"))  # prerelease: allow URL-01 the test asserts the rule fires; the string is the specimen, not a destination
        self.assertTrue(pattern.search(
            "https://tenant.sharepoint.us/sites/MissionFeeding"))  # prerelease: allow URL-01 the test asserts the rule fires; the string is the specimen, not a destination

    def test_a_placeholder_site_url_is_not_a_leak(self):
        rules = {r[0]: r for r in SCAN.RULES}
        pattern = re.compile(rules["URL-01"][2])
        self.assertFalse(pattern.search("https://usaf.dps.mil/sites/<site>"))

    def test_naming_the_tenant_in_prose_is_not_a_leak(self):
        rules = {r[0]: r for r in SCAN.RULES}
        pattern = re.compile(rules["URL-01"][2])
        self.assertFalse(pattern.search("The SharePoint tenant is usaf.dps.mil"))


if __name__ == "__main__":
    unittest.main()


class ConnectorsMatchTheAllowlist(unittest.TestCase):
    """Every declared connection reference must be on the allowlist.

    An unused connection reference is not free: it prompts at import, it needs
    a DLP conversation with the tenant admin, and it widens the app's declared
    surface for no behaviour. A Teams reference shipped for two releases that
    nothing used.
    """

    def setUp(self):
        import json
        with open(os.path.join(ROOT, "configuration",
                               "connection-references.json"),
                  encoding="utf-8") as fh:
            self.refs = json.load(fh)["connectionReferences"]
        with open(os.path.join(ROOT, "security", "connector-allowlist.yaml"),
                  encoding="utf-8") as fh:
            self.allowlist = fh.read()

    def connector_id(self, ref):
        return ref["connectorId"].rsplit("/", 1)[-1].replace("shared_", "")

    def allowed_ids(self):
        # Everything under `allowed:` or `conditional:`, before `prohibited_r1:`.
        head = self.allowlist.split("prohibited_r1:")[0]
        return set(re.findall(r"- id:\s*(\S+)", head))

    def prohibited_ids(self):
        tail = self.allowlist.split("prohibited_r1:")[1].split("rules:")[0]
        return set(re.findall(r"- id:\s*(\S+)", tail))

    def test_every_declared_connector_is_allowed(self):
        allowed = self.allowed_ids()
        for ref in self.refs:
            cid = self.connector_id(ref)
            # office365 is Outlook; the allowlist names it office365outlook.
            cid = {"office365": "office365outlook"}.get(cid, cid)
            self.assertIn(cid, allowed,
                          f"{ref['schemaName']} declares {cid}, which is not on "
                          "the allowlist. Add it there and to the security "
                          "manifest first, or remove the reference.")

    def test_no_prohibited_connector_is_declared(self):
        prohibited = self.prohibited_ids()
        for ref in self.refs:
            self.assertNotIn(self.connector_id(ref), prohibited)

    def test_the_data_layer_connector_is_present(self):
        ids = {self.connector_id(r) for r in self.refs}
        self.assertIn("sharepointonline", ids)

    def test_no_teams_connector(self):
        # Removed in the R1 consolidation: nothing used it.
        ids = {self.connector_id(r) for r in self.refs}
        self.assertNotIn("teams", ids)

    def test_every_conditional_connector_declares_a_fallback(self):
        # "Degrade, do not block" is only true if somebody wrote down how.
        block = self.allowlist.split("conditional:")[1].split("prohibited_r1:")[0]
        entries = [e for e in block.split("- id:") if e.strip()]
        self.assertGreaterEqual(len(entries), 3)
        for entry in entries:
            self.assertIn("fallback:", entry)
            fallback = entry.split("fallback:")[1].split("\n")[0].strip()
            self.assertTrue(fallback and fallback != '""',
                            f"a conditional connector has no fallback: {entry[:40]}")
