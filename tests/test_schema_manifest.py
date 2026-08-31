"""Every SharePoint reference in the build exists in the schema.

SharePoint internal names are immutable and everything binds to them. A
reference to a column that does not exist does not raise in Power Apps -- it
reads blank. A required document then quietly stops being tracked, and nobody
finds out until an inspection.

So the check runs the other way round from the usual one: not "does the schema
have what we wrote", but "did we write anything the schema does not have".
"""

import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import eom_schema as S  # noqa: E402


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


ALL_COLUMNS = {c.name for l in S.LISTS for c in l.columns}
ALL_LISTS = {l.name for l in S.LISTS}
# SharePoint's own columns, plus the Power Fx record fields the engine returns.
BUILTIN = {"ID", "Id", "Title", "Created", "Modified", "Author", "Editor",
           "Value", "Result", "Name", "Version"}
ENGINE_FIELDS = {"status", "code", "label", "actionOwner", "actionRequired",
                 "state", "Period", "Low", "High", "Late", "Ord"}


def display_to_internal(display):
    """'MF EOM Item' -> 'MF_EOM_Item'. The app quotes DISPLAY names."""
    return display.replace(" ", "_")


def extract_record(text, start):
    """Return the first brace-delimited record literal in this Patch call.

    Brace-matched rather than regex-matched: a lazy `\\{(.*?)\\}` walks past the
    end of the call and into an unrelated block further down the file, which is
    how a Patch whose record comes from a helper function gets blamed for a
    gallery's Items property.

    Returns None when the call passes a helper rather than a literal -- those
    are checked where the helper is defined, not here.
    """
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return None           # call closed with no record literal
            depth -= 1
        elif ch == "{" and depth == 0:
            brace = 0
            for j in range(i, len(text)):
                if text[j] == "{":
                    brace += 1
                elif text[j] == "}":
                    brace -= 1
                    if brace == 0:
                        return text[i + 1:j]
            return None
        i += 1
    return None


class ListsReferencedExist(unittest.TestCase):
    """The app quotes list display names: Filter('MF EOM Item', ...)."""

    def sources(self):
        for sub in ("canvas-app",):
            for base, _, files in os.walk(os.path.join(ROOT, sub)):
                for name in files:
                    if name.endswith((".fx", ".pa.yaml")):
                        yield os.path.join(base, name)

    def test_every_quoted_list_is_in_the_schema(self):
        known_display = {l.title for l in S.LISTS}
        offenders = []
        for path in self.sources():
            for m in re.finditer(r"'(MF [A-Za-z0-9 ]+)'", read(path)):
                display = m.group(1)
                if display not in known_display:
                    offenders.append(
                        f"{os.path.relpath(path, ROOT)}: '{display}' "
                        f"-> {display_to_internal(display)} is not a schema list")
        self.assertEqual(sorted(set(offenders)), [])

    def test_every_schema_list_display_name_maps_cleanly(self):
        # A display name whose internal form is not the list name would mean a
        # provisioning script and an app pointing at different things.
        for l in S.LISTS:
            self.assertEqual(display_to_internal(l.title), l.name,
                             f"{l.name} display name does not map to it")


class ColumnsReferencedExist(unittest.TestCase):
    def sources(self):
        for sub in ("canvas-app", "flows", "powerbi", "provisioning"):
            for base, _, files in os.walk(os.path.join(ROOT, sub)):
                for name in files:
                    if name.endswith((".fx", ".pa.yaml", ".md", ".ps1")):
                        yield os.path.join(base, name)

    # A typo does not raise in Power Apps -- it reads blank. These are the
    # three positions where that happens, and they are the only positions where
    # a bare identifier is unambiguously a COLUMN rather than a named formula,
    # a vocabulary constant or an error code.
    #
    #   SortByColumns(t, "X", ...)   a missing column does not sort and does
    #                                not complain
    #   Patch(list, r, { X: ... })   a missing key writes nothing
    #   Filter(list, X = ...)        a missing column matches nothing
    # Anchored on SortOrder, because a loose match walks into the nested
    # Filter and picks up a string literal from a predicate.
    SORT_KEY = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*,\s*SortOrder\.')
    PATCH_HEAD = re.compile(r"Patch\(\s*'(MF [A-Za-z0-9 ]+)'")
    FILTER_HEAD = re.compile(r"Filter\(\s*'(MF [A-Za-z0-9 ]+)'\s*,(.*?)\)", re.S)

    def columns_of(self, display):
        name = display_to_internal(display)
        table = S.LISTS_BY_NAME.get(name)
        return {c.name for c in table.columns} if table else None

    def test_every_sort_column_exists_somewhere_in_the_schema(self):
        offenders = []
        for path in self.sources():
            if not path.endswith((".fx", ".pa.yaml")):
                continue
            for m in self.SORT_KEY.finditer(read(path)):
                col = m.group(1)
                if col not in ALL_COLUMNS and col not in BUILTIN:
                    offenders.append(f"{os.path.relpath(path, ROOT)}: "
                                     f'SortByColumns on "{col}"')
        self.assertEqual(sorted(set(offenders)), [],
                         "SortByColumns against a missing column does not "
                         "error -- it does not sort, and nobody notices")

    def test_every_patch_key_is_a_column_of_the_list_being_patched(self):
        offenders = []
        for path in self.sources():
            if not path.endswith((".fx", ".pa.yaml")):
                continue
            body = read(path)
            for m in self.PATCH_HEAD.finditer(body):
                cols = self.columns_of(m.group(1))
                if cols is None:
                    offenders.append(f"{os.path.relpath(path, ROOT)}: "
                                     f"Patch on unknown list '{m.group(1)}'")
                    continue
                record = extract_record(body, m.end())
                if record is None:
                    continue          # the record came from a helper, not a literal
                for key in re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:",
                                      record):
                    if key not in cols and key not in BUILTIN:
                        offenders.append(
                            f"{os.path.relpath(path, ROOT)}: "
                            f"Patch '{m.group(1)}' sets {key}, which it has no column for")
        self.assertEqual(sorted(set(offenders)), [],
                         "a Patch key that is not a column writes nothing")

    def test_every_filter_predicate_names_a_column_of_its_list(self):
        offenders = []
        for path in self.sources():
            if not path.endswith((".fx", ".pa.yaml")):
                continue
            for m in self.FILTER_HEAD.finditer(read(path)):
                cols = self.columns_of(m.group(1))
                if cols is None:
                    continue
                for key in re.findall(
                        r"(?:^|,|&&|\|\|)\s*([A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\s*(?:=|<>|<|>)",
                        m.group(2)):
                    if key not in cols and key not in BUILTIN:
                        offenders.append(
                            f"{os.path.relpath(path, ROOT)}: "
                            f"Filter '{m.group(1)}' on {key}, which it has no column for")
        self.assertEqual(sorted(set(offenders)), [],
                         "a Filter on a missing column matches nothing and "
                         "reports success")

    def test_the_checks_are_actually_looking_at_something(self):
        # A test that silently checks nothing is worse than no test.
        sorts = patches = filters = 0
        for path in self.sources():
            if not path.endswith((".fx", ".pa.yaml")):
                continue
            body = read(path)
            sorts += len(self.SORT_KEY.findall(body))
            patches += len(self.PATCH_HEAD.findall(body))
            filters += len(self.FILTER_HEAD.findall(body))
        self.assertGreater(sorts, 3, "no SortByColumns found")
        self.assertGreater(patches, 3, "no Patch found")
        self.assertGreater(filters, 10, "no Filter found")

    def test_the_retired_due_date_column_is_referenced_nowhere(self):
        # It was the sort key in Delegation.fx until the four-date split, and
        # SortByColumns against a missing column fails silently.
        self.assertNotIn("Due_Date", ALL_COLUMNS)
        for path in self.sources():
            body = read(path)
            for m in re.finditer(r'"Due_Date"', body):
                self.fail(f"{os.path.relpath(path, ROOT)} still sorts on Due_Date")


class InternalNamesAreSafe(unittest.TestCase):
    """The whole reason the manifest exists."""

    def test_no_column_name_contains_a_space(self):
        # A space becomes _x0020_ in the internal name, permanently.
        for l in S.LISTS:
            for c in l.columns:
                self.assertNotIn(" ", c.name, f"{l.name}.{c.name}")

    def test_no_column_name_exceeds_the_sharepoint_limit(self):
        for l in S.LISTS:
            for c in l.columns:
                self.assertLessEqual(len(c.name), S.MAX_INTERNAL_NAME,
                                     f"{l.name}.{c.name} is {len(c.name)} chars")

    def test_every_name_is_a_plain_identifier(self):
        for l in S.LISTS:
            for c in l.columns:
                self.assertRegex(c.name, r"^[A-Za-z][A-Za-z0-9_]*$",
                                 f"{l.name}.{c.name}")

    def test_provisioning_pins_the_internal_name(self):
        ps1 = read(os.path.join(ROOT, "provisioning", "Provision-MFOpsLists.ps1"))
        # StaticName is what makes the internal name deterministic rather than
        # derived from the display name at creation.
        self.assertIn("StaticName='$name'", ps1.replace(" ", ""))


class TheManifestIsCurrent(unittest.TestCase):
    def setUp(self):
        self.doc = read(os.path.join(ROOT, "docs",
                                     "SHAREPOINT_SCHEMA_MANIFEST.md"))

    def test_it_states_the_current_version_and_counts(self):
        self.assertIn(f"**{S.SCHEMA_VERSION}**", self.doc)
        self.assertIn(f"**{len(S.LISTS)} lists**", self.doc)
        self.assertIn(f"**{S.total_columns()} columns**", self.doc)

    def test_every_list_appears(self):
        for l in S.LISTS:
            self.assertIn(f"## `{l.name}`", self.doc)

    def test_every_column_appears(self):
        for l in S.LISTS:
            for c in l.columns:
                self.assertIn(f"| `{c.name}` |", self.doc,
                              f"{l.name}.{c.name} is missing from the manifest")

    def test_it_says_the_internal_name_is_immutable(self):
        self.assertRegex(self.doc, r"(?i)internal names are \*\*immutable\*\*")

    def test_it_names_the_pre_existing_list_hazard(self):
        self.assertRegex(self.doc, r"(?i)already exists on the destination side")


class SchemaVersionIsGated(unittest.TestCase):
    """A newer app must never write against an older SharePoint schema.

    It would patch columns that do not exist yet, which does not error in Power
    Apps -- it writes nothing. A document reads as submitted while nothing was
    recorded.
    """

    def setUp(self):
        self.fx = read(os.path.join(ROOT, "canvas-app", "formulas",
                                    "App.Formulas.fx"))

    def test_the_app_declares_the_version_it_was_built_against(self):
        m = re.search(r'MF_ExpectedSchemaVersion\s*=\s*"([^"]+)"', self.fx)
        self.assertIsNotNone(m, "the app does not declare an expected schema")
        self.assertEqual(m.group(1), S.SCHEMA_VERSION,
                         "the app expects a different schema than eom_schema.py "
                         "declares. Bump both in the same commit.")

    def test_the_expected_version_is_a_literal_not_a_config_read(self):
        # Reading it from the environment would compare a value with itself.
        block = self.fx.split("MF_ExpectedSchemaVersion")[1].split(";")[0]
        self.assertNotIn("MF_Config", block)

    def test_the_seeded_config_matches(self):
        import csv
        with open(os.path.join(ROOT, "configuration", "app-config.csv"),
                  encoding="utf-8-sig") as fh:
            cfg = {r["Config_Key"]: r["Config_Value"] for r in csv.DictReader(fh)}
        self.assertEqual(cfg["SchemaVersion"], S.SCHEMA_VERSION)

    def test_a_mismatch_disables_writes(self):
        m = re.search(r"(?m)^gblCanWrite\s*=(.*)$", self.fx)
        self.assertIsNotNone(m)
        self.assertIn("gblSchemaMatches", m.group(1),
                      "writes are not gated on the schema version")

    def test_a_mismatch_disables_writes_for_developers_too(self):
        # Read-only mode is an operational decision a developer may need to
        # work around. A schema mismatch says this build does not know the
        # shape of the data.
        expr = re.search(r"(?m)^gblCanWrite\s*=(.*)$", self.fx).group(1)
        self.assertRegex(expr, r"gblSchemaMatches\s*&&",
                         "the developer override must not bypass the schema gate")

    def test_the_user_facing_message_says_nothing_is_lost(self):
        banner = self.fx.split("MF_ReadOnlyBanner")[1].split(";")[0]
        self.assertIn("gblSchemaMatches", banner)
        self.assertRegex(banner, r"(?i)already submitted is affected|nothing you have")

    def test_the_admin_message_names_both_versions_and_the_remedy(self):
        detail = self.fx.split("MF_SchemaMismatchDetail")[1].split(";")[0]
        self.assertIn("CONFIGURATION_REQUIRED", detail)
        self.assertIn("MF_ExpectedSchemaVersion", detail)
        self.assertIn("gblSchemaVersion", detail)
        self.assertIn("Seed-MFOpsConfiguration.ps1", detail)

    def test_every_flow_checks_independently(self):
        # A flow can be invoked directly, and a scheduled flow has no app in
        # front of it at all.
        import glob
        specs = glob.glob(os.path.join(ROOT, "flows", "EOM*", "definition.md"))
        self.assertGreaterEqual(len(specs), 5)
        for spec in specs:
            body = read(spec)
            self.assertIn("Schema compatibility", body,
                          f"{os.path.basename(os.path.dirname(spec))} does not "
                          "check the schema version")
            self.assertIn("CONFIGURATION_REQUIRED", body)

    def test_the_solution_version_and_app_version_agree(self):
        import csv
        with open(os.path.join(ROOT, "configuration", "app-config.csv"),
                  encoding="utf-8-sig") as fh:
            cfg = {r["Config_Key"]: r["Config_Value"] for r in csv.DictReader(fh)}
        solution = read(os.path.join(ROOT, "solution", "src", "Other",
                                     "Solution.xml"))
        m = re.search(r"<Version>([^<]+)</Version>", solution)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), cfg["AppVersion"],
                         "solution version and MF_App_Config.AppVersion differ")


if __name__ == "__main__":
    unittest.main()


class SubmissionIsRequestIdempotent(unittest.TestCase):
    """A retried submission must produce exactly one logical submission.

    On a government network a user pressing Submit twice after a timeout is the
    NORMAL case: the request usually succeeded and the response was lost.
    Disabling the button is not protection -- the flow can be invoked directly,
    and the client that timed out is the one that cannot know what happened.
    """

    KEY = "Submission_Request_ID"

    def setUp(self):
        self.sub = S.LISTS_BY_NAME["MF_EOM_Submission"]
        self.by_name = {c.name: c for c in self.sub.columns}
        self.spec = read(os.path.join(ROOT, "flows", "EOM02-Submission",
                                      "definition.md"))
        self.screen = read(os.path.join(ROOT, "canvas-app", "src", "Screens",
                                        "scrUpload.pa.yaml"))

    def test_the_key_exists_and_is_required(self):
        self.assertIn(self.KEY, self.by_name)
        self.assertTrue(self.by_name[self.KEY].required,
                        "an optional idempotency key is not one")

    def test_the_key_is_indexed(self):
        # The lookup runs on every submission against a list that crosses the
        # delegation ceiling. Unindexed, it would scan 500 rows and miss.
        self.assertTrue(self.by_name[self.KEY].indexed)

    def test_the_key_is_part_of_the_declared_unique_constraint(self):
        # The index makes the lookup fast. The constraint is what stops two
        # calls that race past the lookup.
        self.assertIn(self.KEY, self.sub.unique_key)

    def test_the_flow_checks_before_writing_anything(self):
        # A check after the upload has already created the duplicate.
        idx_check = self.spec.index(self.KEY)
        idx_create = self.spec.index("## Step 5 — Create the file")
        self.assertLess(idx_check, idx_create,
                        "the idempotency check runs after the file write")

    def test_the_flow_returns_the_first_result_rather_than_creating_a_second(self):
        block = self.spec.split("## Step 1a")[1].split("## Step 2")[0]
        self.assertIn("SUBMISSION_REPLAY", block)
        self.assertRegex(block, r"(?i)create no file")
        self.assertRegex(block, r"(?i)create no row")

    def test_the_spec_says_a_disabled_button_is_not_protection(self):
        self.assertRegex(self.spec,
                         r"(?i)disabling the button[^.]*is not protection")

    def test_the_app_mints_the_key_when_the_file_is_chosen(self):
        # Minting at Submit would give a second press a second GUID.
        picker = self.screen.split("- addFile:")[1].split("- lblChosenFile:")[0]
        self.assertIn("Set(locRequestId, GUID())", picker)

    def test_the_app_sends_the_key(self):
        self.assertIn("submissionRequestId: locRequestId", self.screen)

    def test_submit_is_disabled_without_a_key(self):
        self.assertIn("IsBlank(locRequestId)", self.screen)

    def test_the_key_is_cleared_when_the_picker_resets(self):
        # The next file is a new request and must not reuse the key.
        self.assertIn("Set(locRequestId, Blank())", self.screen)

    def test_the_app_does_not_name_its_own_user(self):
        # A client that can name its own user is not an authorisation system.
        self.assertNotIn("uploadedBy:", self.screen)
        # The spec is hard-wrapped, so match across the line break.
        self.assertRegex(
            " ".join(self.spec.split()),
            r"(?i)UPN comes from the flow's authenticated context, never from "
            r"the app payload")


class OneCurrentSubmissionPerItem(unittest.TestCase):
    def test_the_flow_supersedes_before_creating(self):
        spec = read(os.path.join(ROOT, "flows", "EOM02-Submission",
                                 "definition.md"))
        block = spec.split("## Step 6")[1]
        self.assertLess(block.index("supersede any Is_Current"),
                        block.index("create MF_EOM_Submission"))

    def test_is_current_is_indexed(self):
        by_name = {c.name: c
                   for c in S.LISTS_BY_NAME["MF_EOM_Submission"].columns}
        self.assertTrue(by_name["Is_Current"].indexed)
        self.assertTrue(by_name["Is_Current"].required)


class ReportIndexTableMatchesTheSchema(unittest.TestCase):
    """The report states a per-list index count. It is a claim about the
    provisioning payloads, and BUILD_INSTRUCTION.md asks for it before those
    payloads are considered final -- so it is held to the schema, not typed."""

    TABLE_ROW = re.compile(
        r"\|\s*`?(MF_[A-Za-z_]+)`?\s*\|\s*\**(\d+)\**\s*\|"
        r"\s*\**(\d+)\**\s*\|")

    def setUp(self):
        self.report = read(os.path.join(ROOT, "FINAL_RELEASE_REPORT.md"))
        self.truth = {l.name: (len(l.columns),
                               sum(1 for c in l.columns if c.indexed))
                      for l in S.LISTS}

    def test_every_list_appears_with_the_right_counts(self):
        stated = {m.group(1): (int(m.group(2)), int(m.group(3)))
                  for m in self.TABLE_ROW.finditer(self.report)
                  if m.group(1) in self.truth}
        self.assertEqual(set(stated), set(self.truth),
                         "the report's index table is missing a list")
        for name in sorted(self.truth):
            self.assertEqual(stated[name], self.truth[name],
                             f"{name}: report states {stated[name]}, schema "
                             f"says {self.truth[name]}")

    def test_no_list_exceeds_the_sharepoint_index_cap(self):
        # 20 per list. Over the cap the provisioning run fails partway and
        # leaves the list half-configured, and an index cannot be added at all
        # once a list passes 5,000 items.
        for name, (_, indexed) in sorted(self.truth.items()):
            self.assertLessEqual(indexed, 20, f"{name} has {indexed} indexes")

    def test_the_totals_are_stated_correctly(self):
        self.assertIn(f"**{sum(v[0] for v in self.truth.values())}**",
                      self.report)
        self.assertIn(f"**{sum(v[1] for v in self.truth.values())}**",
                      self.report)


class NoDocumentStatesAStaleTotal(unittest.TestCase):
    """The column and index totals are transliterated into a dozen documents.

    They went stale in eight of them at once -- the release report, the release
    notes, the changelog, the dependency manifest, the correctness record, the
    provisioning guide and the import checklist all said 284 columns and 89
    indexes while the schema said 286 and 90. Nothing was wrong with any of
    those sentences when they were written; they simply were not attached to
    the thing they describe. This attaches them.
    """

    SKIP_DIRS = {".git", "node_modules", "__pycache__", "reference",
                 "handoffs", "archive", "figma-build"}
    # A three-digit count preceding "column" is a whole-schema total. Per-list
    # counts are two digits, so they cannot collide.
    COLUMNS = re.compile(r"\b(\d{3})\s+column")
    # Per-list index counts top out at 13, so anything at or above 40 claiming
    # to be a number of indexes is a whole-schema total.
    INDEXES = re.compile(r"\b(\d{2,})\s+index(?:es|ed columns)\b")

    def setUp(self):
        self.columns = sum(len(l.columns) for l in S.LISTS)
        self.indexes = sum(1 for l in S.LISTS for c in l.columns if c.indexed)

    def _is_historical(self, line):
        """A changelog entry for a superseded schema states that schema's
        totals, and correcting it would be falsifying the record. Such a line
        names the version it belongs to, so a stated version other than the
        current one marks the claim as history rather than a stale fact."""
        if "<!-- historical -->" in line:
            return True
        for m in re.finditer(r"schema version\s+(\d+\.\d+)", line, re.I):
            if m.group(1) != S.SCHEMA_VERSION:
                return True
        return False

    def _docs(self):
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for f in files:
                if f.endswith((".md", ".csv")):
                    yield os.path.join(base, f)

    def test_every_stated_total_matches_the_schema(self):
        bad = []
        for path in self._docs():
            rel = os.path.relpath(path, ROOT)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            lines = text.splitlines()
            for m in self.COLUMNS.finditer(text):
                line = text[:m.start()].count("\n") + 1
                if self._is_historical(lines[line - 1]):
                    continue
                if int(m.group(1)) != self.columns:
                    bad.append(f"{rel}:{line} says {m.group(1)} columns, "
                               f"schema has {self.columns}")
            for m in self.INDEXES.finditer(text):
                n = int(m.group(1))
                line = text[:m.start()].count("\n") + 1
                if self._is_historical(lines[line - 1]):
                    continue
                if n >= 40 and n != self.indexes:
                    bad.append(f"{rel}:{line} says {n} indexes, "
                               f"schema has {self.indexes}")
        self.assertEqual(bad, [], "\n".join(bad))


class EveryTestIsClassified(unittest.TestCase):
    """`scripts/classify_tests.py` declares what each test class proves.

    The classification is the point: a suite that passes in full while the
    tests and the generator share one wrong premise looks identical to a suite
    that proves something. A new test class with no declared kind would be
    counted in a total that implies coverage it may not have, so an
    unclassified class fails here.
    """

    def test_the_classifier_accounts_for_every_class(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "classify_tests.py")],
            capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("UNCLASSIFIED", r.stdout)

    def test_the_counts_add_up_to_the_suite(self):
        import subprocess
        import re as _re
        c = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "classify_tests.py")],
            capture_output=True, text=True, cwd=ROOT).stdout
        total = int(_re.search(r"TOTAL\s+(\d+)", c).group(1))
        parts = sum(int(_re.search(rf"{k}\s+(\d+)", c).group(1))
                    for k in ("BEHAVIOURAL", "STRUCTURAL", "POLICY"))
        self.assertEqual(total, parts)
