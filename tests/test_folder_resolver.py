"""EOM-02 destination resolution.

These hold `scripts/folder_resolver.py`, `flows/EOM02-Submission/definition.md`
and `deployment/site-bindings.md` to one another. The v14 snapshot shipped a
flow spec that constructed the path and created folders under an action document
that said find-never-create; the tests exist so that cannot happen again
silently.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from folder_resolver import (  # noqa: E402
    DestinationNotUsable, Resolution, check_destination, fiscal_year, join_path,
    match_fiscal_year_folder, match_month_folder, next_version_name,
    resolve_destination_folder, sanitize_segment,
)

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read_text(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def read_destinations():
    import csv
    with open(os.path.join(ROOT, "configuration", "document-destinations.csv"),
              encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def read_env_vars():
    import json
    with open(os.path.join(ROOT, "configuration",
                           "environment-variables.json"), encoding="utf-8") as fh:
        return json.load(fh)


def destination(**over):
    row = {
        "Destination_ID": "PORT2-EOM",
        "Portfolio_ID": "PORTFOLIO 2",
        "Document_Domain": "EOM",
        "Site_URL": "https://example.invalid/sites/p2",
        "Library_Name": "Documents",
        "Library_Url_Segment": "Shared Documents",
        "Root_Folder": "Legacy_Portfolio 2/5. Monthly Data Call",
        "Folder_Template": "{FiscalYearShort}/{MonthFolder}",
        "Create_Missing_Folders": False,
        "Fallback_Policy": "FIND_OR_ROOT",
        "Verified_By": "TSgt Example",
        "Active_Flag": True,
    }
    row.update(over)
    return row


def tree(mapping):
    """A fake SharePoint: path -> child folder names."""
    return lambda path: mapping.get(path, [])


class FiscalYear(unittest.TestCase):
    def test_october_starts_the_next_fiscal_year(self):
        self.assertEqual(fiscal_year("2025-10"), 2026)
        self.assertEqual(fiscal_year("2025-09"), 2025)

    def test_the_eom_period_in_question(self):
        self.assertEqual(fiscal_year("2026-08"), 2026)

    def test_a_malformed_period_raises_rather_than_guessing(self):
        for bad in ("2026-8", "aug-26", "2026", "2026-13", ""):
            with self.assertRaises(ValueError):
                fiscal_year(bad)


class FiscalYearFolder(unittest.TestCase):
    def test_the_spellings_that_exist_in_the_wild(self):
        for name in ("FY26", "FY 26", "FY-26", "FY2026", "FY 2026", "fy26"):
            self.assertEqual(match_fiscal_year_folder([name], "2026-08"), name)

    def test_a_trailing_word_does_not_defeat_the_match(self):
        self.assertEqual(
            match_fiscal_year_folder(["FY26 ARCHIVE"], "2026-08"), "FY26 ARCHIVE")

    def test_a_longer_number_is_not_this_fiscal_year(self):
        self.assertIsNone(match_fiscal_year_folder(["FY261", "DRAFT_FY2610"], "2026-08"))

    def test_the_wrong_year_does_not_match(self):
        self.assertIsNone(match_fiscal_year_folder(["FY25", "FY27"], "2026-08"))


class MonthFolder(unittest.TestCase):
    def test_the_four_namings_the_action_document_calls_plausible(self):
        for name in ("Aug 26", "August 2026", "08 Aug", "08. August"):
            self.assertEqual(match_month_folder([name], "2026-08"), name)

    def test_case_is_not_a_signal(self):
        for name in ("AUGUST", "august", "AuGuSt"):
            self.assertEqual(match_month_folder([name], "2026-08"), name)

    def test_a_bare_two_digit_month_matches(self):
        self.assertEqual(match_month_folder(["07", "08", "09"], "2026-08"), "08")

    def test_the_named_folder_wins_over_a_bare_number(self):
        # Both are present. A person who typed 'August 2026' meant that one.
        self.assertEqual(
            match_month_folder(["08", "August 2026"], "2026-08"), "August 2026")

    def test_a_different_month_never_matches(self):
        self.assertIsNone(match_month_folder(["July 2026", "Sep 26"], "2026-08"))

    def test_a_stated_year_must_be_the_right_one(self):
        # This is the failure that would quietly file August 2026 into last
        # year's folder and report success.
        self.assertIsNone(match_month_folder(["Aug 25"], "2026-08"))
        self.assertIsNone(match_month_folder(["August 2025"], "2026-08"))

    def test_a_folder_stating_no_year_is_accepted(self):
        # Plenty of sites keep the year only on the FY folder above.
        self.assertEqual(match_month_folder(["August"], "2026-08"), "August")

    def test_an_iso_style_folder_matches(self):
        self.assertEqual(match_month_folder(["2026-08"], "2026-08"), "2026-08")


class Resolve(unittest.TestCase):
    root = "Shared Documents/Legacy_Portfolio 2/5. Monthly Data Call"

    def test_the_happy_path_returns_the_matched_folder(self):
        children = tree({
            self.root: ["FY25", "FY26", "FY27"],
            f"{self.root}/FY26": ["Jul 26", "Aug 26", "Sep 26"],
        })
        r = resolve_destination_folder(destination(), "2026-08", children)
        self.assertEqual(r.path, f"{self.root}/FY26/Aug 26")
        self.assertFalse(r.needs_filing)
        self.assertEqual(r.note, "")

    def test_an_unmatched_month_lands_at_root_and_is_flagged(self):
        children = tree({
            self.root: ["FY26"],
            f"{self.root}/FY26": ["Q1", "Q2"],
        })
        r = resolve_destination_folder(destination(), "2026-08", children)
        self.assertEqual(r.path, self.root)
        self.assertTrue(r.needs_filing)
        # The note has to say what was looked for, or the person moving the
        # file cannot tell whether to move it or fix the configuration.
        self.assertIn("August 2026", r.note)
        self.assertIn("FY26", r.note)

    def test_an_unmatched_fiscal_year_lands_at_root_and_is_flagged(self):
        children = tree({self.root: ["FY24", "FY25"]})
        r = resolve_destination_folder(destination(), "2026-08", children)
        self.assertEqual(r.path, self.root)
        self.assertTrue(r.needs_filing)
        self.assertIn("FY26", r.note)

    def test_nothing_is_ever_created(self):
        # The resolver is handed a read-only view of the site on purpose: it has
        # no way to create a folder even if a future edit wanted to.
        created = []

        def children(path):
            created.append(path)
            return {self.root: ["FY26"], f"{self.root}/FY26": ["Aug 26"]}.get(path, [])

        resolve_destination_folder(destination(), "2026-08", children)
        self.assertTrue(all(p.startswith(self.root) for p in created))

    def test_find_or_fail_raises_instead_of_dropping_at_root(self):
        children = tree({self.root: ["FY26"], f"{self.root}/FY26": []})
        with self.assertRaises(DestinationNotUsable) as ctx:
            resolve_destination_folder(
                destination(Fallback_Policy="FIND_OR_FAIL"), "2026-08", children)
        self.assertEqual(ctx.exception.code, "DESTINATION_FOLDER_NOT_FOUND")

    def test_the_resolved_path_never_escapes_the_configured_root(self):
        children = tree({
            self.root: ["FY26"],
            f"{self.root}/FY26": ["Aug 26"],
        })
        r = resolve_destination_folder(destination(), "2026-08", children)
        self.assertTrue(r.path.startswith(self.root))


class FailClosed(unittest.TestCase):
    """All three gates default to 'no'. A site nobody walked gets no files."""

    def test_a_missing_row_is_not_configured(self):
        with self.assertRaises(DestinationNotUsable) as c:
            check_destination(None)
        self.assertEqual(c.exception.code, "DESTINATION_NOT_CONFIGURED")

    def test_an_inactive_row_is_not_configured(self):
        with self.assertRaises(DestinationNotUsable) as c:
            check_destination(destination(Active_Flag=False))
        self.assertEqual(c.exception.code, "DESTINATION_NOT_CONFIGURED")

    def test_an_unwalked_site_is_not_verified(self):
        with self.assertRaises(DestinationNotUsable) as c:
            check_destination(destination(Verified_By=""))
        self.assertEqual(c.exception.code, "DESTINATION_NOT_VERIFIED")

    def test_an_unbound_site_url_requires_configuration(self):
        with self.assertRaises(DestinationNotUsable) as c:
            check_destination(destination(Site_URL=""))
        self.assertEqual(c.exception.code, "CONFIGURATION_REQUIRED")

    def test_every_seeded_row_fails_closed_until_its_url_is_bound(self):
        # Eight rows: four PILOT and four PRODUCTION. The pilot four are
        # active and verified, so they clear two of the three gates -- and
        # still refuse, because Site_URL is bound at import and blank here.
        rows = read_destinations()
        self.assertEqual(len(rows), 8)
        for row in rows:
            row["Active_Flag"] = row["Active_Flag"] == "TRUE"
            with self.assertRaises(DestinationNotUsable) as ctx:
                check_destination(row)
            expected = ("CONFIGURATION_REQUIRED" if row["Active_Flag"]
                        else "DESTINATION_NOT_CONFIGURED")
            self.assertEqual(ctx.exception.code, expected,
                             row["Destination_ID"])


class SeededDestinations(unittest.TestCase):
    def setUp(self):
        self.rows = read_destinations()

    def test_no_site_url_is_committed(self):
        # A .mil site URL in source is a destination leak.
        for row in self.rows:
            self.assertEqual(row["Site_URL"], "")

    def test_folders_are_never_created(self):
        for row in self.rows:
            self.assertEqual(row["Create_Missing_Folders"], "FALSE")
            self.assertEqual(row["Fallback_Policy"], "FIND_OR_ROOT")

    def production(self):
        return [r for r in self.rows if r["Destination_ID"].startswith("PORT")]

    def pilot(self):
        return [r for r in self.rows if r["Destination_ID"].startswith("PILOT")]

    def test_there_are_four_of_each(self):
        self.assertEqual(len(self.production()), 4)
        self.assertEqual(len(self.pilot()), 4)

    def test_the_four_production_root_folders_are_all_different(self):
        # If they were derivable, the column would not need to exist.
        roots = [r["Root_Folder"] for r in self.production()]
        self.assertEqual(len(set(roots)), 4)

    def test_the_four_pilot_root_folders_are_all_different(self):
        # The pilot rows share one site and split by root folder, so routing
        # still exercises four destinations rather than a simplified single
        # one. If they collapsed to one folder the pilot would prove nothing
        # about the thing most likely to break.
        roots = [r["Root_Folder"] for r in self.pilot()]
        self.assertEqual(len(set(roots)), 4)

    def test_every_portfolio_has_exactly_one_active_destination(self):
        # Two active rows for one portfolio is an ambiguous route.
        active = [r for r in self.rows if r["Active_Flag"] == "TRUE"]
        seen = [r["Portfolio_ID"] for r in active]
        self.assertEqual(len(seen), len(set(seen)), "ambiguous routing")
        self.assertEqual(len(seen), 4)

    def test_the_pilot_rows_are_the_active_ones(self):
        for r in self.pilot():
            self.assertEqual(r["Active_Flag"], "TRUE", r["Destination_ID"])
        for r in self.production():
            self.assertEqual(r["Active_Flag"], "FALSE", r["Destination_ID"])

    def test_portfolio_two_keeps_its_odd_slug_on_the_record(self):
        # Three work and one 404s is the worst failure shape available, so the
        # irregularity is written down where somebody debugging will find it.
        p2 = next(r for r in self.production()
                  if r["Portfolio_ID"] == "PORTFOLIO 2")
        self.assertIn("Legacy_Portfolio2", p2["Site_Note"])

    def test_the_library_url_segment_is_recorded_separately(self):
        # A library displayed as "Documents" is "Shared Documents" in the URL.
        # Building a path from the display name 404s on a library that plainly
        # exists, which reads as a permissions problem.
        for r in self.rows:
            self.assertTrue(r["Library_Url_Segment"].strip(),
                            r["Destination_ID"])
        pilot = self.pilot()[0]
        self.assertNotEqual(pilot["Library_Name"], pilot["Library_Url_Segment"],
                            "the pilot site is the case this column exists for")

    def test_no_site_url_is_committed_even_for_the_pilot(self):
        # The pilot site IS known. It still does not go in source: this file is
        # committed and seeded, and a .mil site URL in a tracked file is a
        # destination leak. It is bound at import from MF_PilotSite_SiteURL.
        for r in self.rows:
            self.assertEqual(r["Site_URL"], "", r["Destination_ID"])

    def test_the_sort_prefixes_survive(self):
        by_id = {r["Destination_ID"]: r for r in self.rows}
        self.assertIn("H. Monthly Data Call", by_id["PORT1-EOM"]["Root_Folder"])
        self.assertIn("5. Monthly Data Call", by_id["PORT2-EOM"]["Root_Folder"])


class Sanitising(unittest.TestCase):
    def test_sharepoint_illegal_characters_are_removed(self):
        self.assertEqual(sanitize_segment('a"b*c:d<e>f?g|h'), "a b c d e f g h")

    def test_whitespace_is_collapsed_and_trimmed(self):
        self.assertEqual(sanitize_segment("  JB   Charleston  "), "JB Charleston")

    def test_a_trailing_dot_is_stripped(self):
        self.assertEqual(sanitize_segment("Monthly Data Call."), "Monthly Data Call")

    def test_join_skips_blanks_rather_than_doubling_separators(self):
        self.assertEqual(join_path("Shared Documents", "", "FY26"),
                         "Shared Documents/FY26")


class Versioning(unittest.TestCase):
    def test_an_uploaded_name_is_preserved_when_it_is_free(self):
        self.assertEqual(next_version_name("Scan0023948.pdf", []), "Scan0023948.pdf")

    def test_a_collision_is_disambiguated_not_overwritten(self):
        self.assertEqual(
            next_version_name("1119.pdf", ["1119.pdf"]), "1119 (v2).pdf")
        self.assertEqual(
            next_version_name("1119.pdf", ["1119.pdf", "1119 (v2).pdf"]),
            "1119 (v3).pdf")

    def test_a_name_with_no_extension_still_versions(self):
        self.assertEqual(next_version_name("report", ["report"]), "report (v2)")


class SpecAgreesWithTheCode(unittest.TestCase):
    """The v14 snapshot's spec contradicted its own action document. Hold ours."""

    def setUp(self):
        self.spec = read_text("flows", "EOM02-Submission", "definition.md")

    def test_the_spec_does_not_construct_the_retired_path(self):
        # {FiscalYear}/{ReportingPeriod}/{InstallationName}/{RequirementCode}
        # was the construct-and-create design. It is gone.
        self.assertNotIn("{InstallationName}", self.spec)
        self.assertNotIn("{RequirementCode}", self.spec)

    def test_the_spec_uses_the_tokens_the_seed_carries(self):
        self.assertIn("{FiscalYearShort}", self.spec)
        self.assertIn("{MonthFolder}", self.spec)

    def test_the_spec_never_creates_a_folder(self):
        self.assertRegex(self.spec, r"(?i)create_missing_folders[^\n]*false")
        self.assertNotRegex(self.spec, r"(?im)^\s*Create missing folders only when")

    def test_the_spec_fails_closed_on_the_three_live_gates(self):
        for gate in ("Active_Flag", "Verified_By", "Site_URL"):
            self.assertIn(gate, self.spec)

    def test_the_spec_does_not_gate_on_a_column_that_no_longer_exists(self):
        # Channel_Type went away with the four-channels-in-one-team model. A
        # spec that fails closed on an absent column fails open.
        self.assertNotIn("Channel_Type", self.spec)

    def test_the_spec_stores_the_guid(self):
        self.assertIn("SharePoint_Unique_ID", self.spec)

    def test_the_spec_flags_a_root_landing(self):
        self.assertIn("Needs_Filing", self.spec)

    def test_every_error_code_the_resolver_raises_is_documented(self):
        for code in ("DESTINATION_NOT_CONFIGURED", "DESTINATION_NOT_VERIFIED",
                     "CONFIGURATION_REQUIRED", "DESTINATION_FOLDER_NOT_FOUND"):
            self.assertIn(code, self.spec, f"{code} is unhandled by the app")


class BindingsAreDocumented(unittest.TestCase):
    def setUp(self):
        self.doc = read_text("deployment", "site-bindings.md")

    def test_the_four_sites_are_named_as_separate_collections(self):
        self.assertRegex(self.doc, r"(?i)four separate .{0,10}site collections")

    def test_the_month_folder_question_is_asked(self):
        self.assertRegex(self.doc, r"(?i)month folder")

    def test_the_cloud_is_dod_not_gcc_high(self):
        self.assertRegex(self.doc, r"(?i)\bDoD\b")
        self.assertRegex(self.doc, r"(?i)not GCC High")

    def test_the_four_environment_variables_exist(self):
        ev = read_env_vars()
        names = {v["schemaName"] for v in ev["environmentVariables"]}
        for n in range(1, 5):
            self.assertIn(f"mfops_MF_Portfolio{n}_SiteURL", names)
            self.assertIn(f"MF_Portfolio{n}_SiteURL", self.doc)

    def test_every_bound_variable_ships_blank(self):
        ev = read_env_vars()
        for v in ev["environmentVariables"]:
            self.assertEqual(v["defaultValue"], "",
                             f"{v['schemaName']} ships a value")


if __name__ == "__main__":
    unittest.main()


class ThePathUsesTheUrlSegment(unittest.TestCase):
    """A library displayed as "Documents" is "Shared Documents" in the URL.

    Building the path from the display name produces a URL that 404s on a
    library that plainly exists, and it gets debugged as a permissions problem.
    The pilot site is exactly this case.
    """

    def test_the_resolved_path_uses_the_segment_not_the_display_name(self):
        d = destination(Library_Name="Documents",
                        Library_Url_Segment="Shared Documents")
        root = f"Shared Documents/{d['Root_Folder']}"
        children = tree({root: ["FY26"], f"{root}/FY26": ["Aug 26"]})
        r = resolve_destination_folder(d, "2026-08", children)
        self.assertTrue(r.path.startswith("Shared Documents/"))
        self.assertFalse(r.path.startswith("Documents/"))

    def test_a_blank_segment_is_refused_rather_than_substituted(self):
        with self.assertRaises(DestinationNotUsable) as ctx:
            resolve_destination_folder(
                destination(Library_Url_Segment=""), "2026-08", tree({}))
        self.assertEqual(ctx.exception.code, "CONFIGURATION_REQUIRED")
        self.assertIn("not interchangeable", ctx.exception.detail)

    def test_the_fallback_also_uses_the_segment(self):
        d = destination(Library_Name="Documents",
                        Library_Url_Segment="Shared Documents")
        r = resolve_destination_folder(d, "2026-08", tree({}))
        self.assertTrue(r.needs_filing)
        self.assertTrue(r.path.startswith("Shared Documents/"))


class TheFallbackCeiling(unittest.TestCase):
    """A fallback that reaches a site root, a library root or another portfolio
    is a stop condition.

    A file above the approved root looks like it worked: it is in SharePoint,
    the upload returned success, and it is somewhere nobody will look. That is
    strictly worse than a failed upload, which gets retried.
    """

    root = "Shared Documents/Legacy_Portfolio 2/5. Monthly Data Call"

    def nothing_matches(self):
        return tree({})

    def test_the_fallback_lands_exactly_on_the_approved_root(self):
        r = resolve_destination_folder(destination(), "2026-08",
                                       self.nothing_matches())
        self.assertEqual(r.path, self.root)

    def test_the_fallback_never_rises_above_the_approved_root(self):
        r = resolve_destination_folder(destination(), "2026-08",
                                       self.nothing_matches())
        self.assertTrue(r.path.startswith(destination()["Library_Url_Segment"]))
        self.assertIn(destination()["Root_Folder"].split("/")[-1], r.path)
        # Not the library root, not the site root.
        self.assertNotEqual(r.path, destination()["Library_Url_Segment"])
        self.assertGreaterEqual(len(r.path.split("/")), 3)

    def test_a_blank_root_folder_is_refused_rather_than_widened(self):
        with self.assertRaises(DestinationNotUsable) as ctx:
            resolve_destination_folder(destination(Root_Folder=""), "2026-08",
                                       self.nothing_matches())
        self.assertEqual(ctx.exception.code, "DESTINATION_NOT_CONFIGURED")
        self.assertIn("above the library root", ctx.exception.detail)

    def test_the_fallback_cannot_reach_another_portfolio(self):
        # The root is built from THIS destination row and nothing else, so
        # there is no input that redirects it. Prove it across all four.
        import csv
        path = os.path.join(ROOT, "configuration", "document-destinations.csv")
        with open(path, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            live = destination(Root_Folder=row["Root_Folder"],
                               Library_Name=row["Library_Name"],
                               Library_Url_Segment=row["Library_Url_Segment"])
            r = resolve_destination_folder(live, "2026-08", self.nothing_matches())
            self.assertIn(row["Root_Folder"], r.path)
            for other in rows:
                if other["Destination_ID"] == row["Destination_ID"]:
                    continue
                self.assertNotIn(other["Root_Folder"], r.path)

    def test_the_fallback_is_always_flagged(self):
        # A file at root that nobody knows about is the failure this prevents.
        r = resolve_destination_folder(destination(), "2026-08",
                                       self.nothing_matches())
        self.assertTrue(r.needs_filing)
        self.assertTrue(r.note.strip())

    def test_find_or_fail_refuses_rather_than_falling_back(self):
        with self.assertRaises(DestinationNotUsable) as ctx:
            resolve_destination_folder(destination(Fallback_Policy="FIND_OR_FAIL"),
                                       "2026-08", self.nothing_matches())
        self.assertEqual(ctx.exception.code, "DESTINATION_FOLDER_NOT_FOUND")
