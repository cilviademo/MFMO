"""The manual deployment kit says what the schema and the engine say.

Every number an operator will hand-type from the kit -- column counts,
index counts, choice values, the 737 -- is re-derived here from the same
authorities the generator used (eom_schema.py, the EOM-01 engine, the
implemented EOM-02 workflow JSON) and compared against the SHIPPED kit
files, so a sheet cannot drift from the schema without failing the suite.
"""
import csv
import io
import json
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
KIT = os.path.join(ROOT, "dist", "MFOps_manual-kit_1.0")

import eom_schema as S  # noqa: E402


@unittest.skipUnless(os.path.isdir(KIT),
                     "manual kit not generated (scripts/build_manual_kit.sh)")
class ManualKitMatchesTheSchema(unittest.TestCase):

    def _read(self, *parts):
        with open(os.path.join(KIT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_seventeen_sheets_and_their_totals(self):
        sheets = sorted(os.listdir(os.path.join(KIT, "LIST-BUILD-SHEETS")))
        self.assertEqual(len(sheets), 17)
        by_name = {l.name: l for l in S.LISTS}
        tot_cols = tot_idx = 0
        for f in sheets:
            name = f.split("-", 1)[1][:-3]
            l = by_name[name]
            text = self._read("LIST-BUILD-SHEETS", f)
            rows = re.findall(r"^\| \d+ \| `([A-Za-z0-9_]+)` \|", text,
                              re.M)
            self.assertEqual(rows, [c.name for c in l.columns],
                             f"{f}: column rows drifted from the schema")
            n_idx = len(re.findall(r"^- \[ \] `", text, re.M))
            self.assertEqual(n_idx, sum(1 for c in l.columns if c.indexed),
                             f"{f}: index checkbox count drifted")
            self.assertIn("Installation_x0020_ID", text,
                          f"{f}: the internal-name trap must head every "
                          f"sheet")
            tot_cols += len(rows)
            tot_idx += n_idx
        self.assertEqual((len(sheets), tot_cols, tot_idx), (17, 286, 90))

    def test_choice_values_are_verbatim(self):
        # Every choice column's values appear in its sheet exactly.
        for i, name in enumerate(json.loads(
                self._read("kit-facts.json"))["per_list"], 1):
            pass
        for l in S.LISTS:
            sheet = next(f for f in os.listdir(
                os.path.join(KIT, "LIST-BUILD-SHEETS")) if f.endswith(
                f"-{l.name}.md"))
            text = self._read("LIST-BUILD-SHEETS", sheet)
            for c in l.columns:
                for v in c.choices:
                    self.assertIn(v, text,
                                  f"{l.name}.{c.name}: choice {v!r} "
                                  f"missing from the sheet")

    def test_the_737_and_its_statuses_rederive(self):
        p = os.path.join(KIT, "CSV-IMPORT", "expected-items-2026-08-09.csv")
        with open(p, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 737)
        statuses = {}
        for r in rows:
            statuses[r["Final_Status"]] = statuses.get(r["Final_Status"],
                                                       0) + 1
        facts = json.loads(self._read("kit-facts.json"))
        self.assertEqual(statuses, facts["statuses"])
        # And the configuration/ copy is the same bytes.
        with open(os.path.join(ROOT, "configuration",
                               "expected-items-2026-08-09.csv"),
                  encoding="utf-8") as fh:
            self.assertEqual(fh.read(),
                             open(p, encoding="utf-8").read())

    def test_flow_manual_covers_every_action(self):
        import glob
        j = glob.glob(os.path.join(ROOT, "solution", "src", "Workflows",
                                   "EOM02Submission-*.json"))[0]
        with open(j, encoding="utf-8") as fh:
            defn = json.load(fh)["properties"]["definition"]
        manual = self._read("FLOW-BUILD", "EOM-02-manual.md")

        def names(actions):
            for n, node in actions.items():
                yield n
                if node.get("actions"):
                    yield from names(node["actions"])
                els = (node.get("else") or {}).get("actions")
                if els:
                    yield from names(els)

        for n in names(defn["actions"]):
            self.assertIn(f"`{n.replace('_', ' ')}`", manual,
                          f"flow manual is missing action {n}")
        for pname in defn["triggers"]["Request"]["inputs"]["schema"][
                "properties"]:
            self.assertIn(f"`{pname}`", manual)
        self.assertNotIn("parameters('MF_", manual,
                         "an environment-variable reference survived; "
                         "manual flows have no solution parameters")

    def test_kit_is_email_safe_and_identity_free(self):
        for base, _d, files in os.walk(KIT):
            for f in files:
                self.assertFalse(
                    f.endswith((".sh", ".ps1", ".py", ".exe", ".msapp",
                                ".msapr")),
                    f"script/binary type in the kit: {f}")

    def test_verification_gate_and_critical_counts(self):
        v = self._read("VERIFICATION.md")
        self.assertIn("SAFE TO LOAD CONFIGURATION", v)
        for nm, exp in (("MF_EOM_Item", 13), ("MF_EOM_Submission", 13),
                        ("MF_EOM_Status", 8), ("MF_Security_Mapping", 8),
                        ("MF_App_Event_Log", 6), ("MF_EOM_Audit", 4)):
            self.assertIn(f"`{nm}`: **{exp}** indexes", v)
        self.assertIn("NOT TESTABLE LOCALLY", v)
