"""The blank-slate kit, replayed offline against a mock SharePoint.

The BUILD flow's semantics are simple enough to simulate exactly: three
create shapes, in order, concurrency 1, fail-stop. So the mock enforces
what the real service enforces — a list must exist before its fields, a
field must exist before its index MERGE, duplicate titles and duplicate
internal names are rejected, and internal names are derived the way
SharePoint derives them (space -> _x0020_, frozen at creation). Every
payload in SCHEMA-PAYLOADS.json is replayed; then the VERIFY flow's reads
are replayed against the mock's end state and the audit must render YES.

What this proves: the payloads are correct and the flows' logic is sound.
What it cannot prove: the live run in a tenant (auth, throttling, real
REST behaviour) — NOT TESTABLE LOCALLY, stated in the kit's README, and
this suite never claims the flows "ran in Power Automate."
"""
import json
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KIT = os.path.join(ROOT, "dist", "MFOps_blankslate-provisioning_1.0")
CRITICAL = {"MF EOM Item": 13, "MF EOM Submission": 13, "MF EOM Status": 8,
            "MF Security Mapping": 8, "MF App Event Log": 6,
            "MF EOM Audit": 4}


def sharepoint_internal_name(title):
    """How SharePoint freezes an internal name from a creation Title."""
    out = []
    for ch in title:
        if ch == " ":
            out.append("_x0020_")
        elif ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append(f"_x{ord(ch):04x}_")
    return "".join(out)


class MockSharePoint:
    """Enforces the dependencies and rejections the real service would."""

    def __init__(self):
        self.lists = {}   # title -> {internal_name: {"indexed": bool}}

    def create_list(self, payload):
        title = payload["Title"]
        if title in self.lists:
            raise AssertionError(f"duplicate list {title!r}")
        if payload.get("BaseTemplate") != 100:
            raise AssertionError(f"{title}: BaseTemplate must be 100")
        self.lists[title] = {}

    def create_field(self, list_title, payload):
        if list_title not in self.lists:
            raise AssertionError(
                f"field {payload.get('Title')!r} before list {list_title!r}"
                f" — create-order violation")
        internal = sharepoint_internal_name(payload["Title"])
        fields = self.lists[list_title]
        if internal in fields:
            raise AssertionError(
                f"{list_title}: duplicate internal name {internal!r}")
        fields[internal] = {"indexed": False}

    def merge_index(self, path, payload, headers):
        m = re.match(r"_api/web/lists/getbytitle\('([^']+)'\)/fields/"
                     r"getbyinternalnameortitle\('([^']+)'\)$", path)
        if not m:
            raise AssertionError(f"unparseable index path {path!r}")
        lt, internal = m.group(1), m.group(2)
        if lt not in self.lists:
            raise AssertionError(f"index on missing list {lt!r}")
        if internal not in self.lists[lt]:
            raise AssertionError(
                f"{lt}: index MERGE before field {internal!r} exists "
                f"— create-order violation")
        if headers.get("X-HTTP-Method") != "MERGE" or \
                headers.get("IF-MATCH") != "*":
            raise AssertionError(f"{lt}.{internal}: wrong MERGE headers")
        if payload.get("Indexed") is not True:
            raise AssertionError(f"{lt}.{internal}: payload must set "
                                 f"Indexed true")
        self.lists[lt][internal]["indexed"] = True


@unittest.skipUnless(os.path.isdir(KIT),
                     "kit not generated (scripts/build_blankslate_kit.sh)")
class BlankSlateKitReplays(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(KIT, "SCHEMA-PAYLOADS.json"),
                  encoding="utf-8") as fh:
            cls.kit = json.load(fh)   # JSON parses, or this whole class fails

    def test_totals_are_17_286_90(self):
        self.assertEqual(len(self.kit), 17)
        self.assertEqual(sum(l["fieldsExpected"] for l in self.kit), 286)
        self.assertEqual(sum(l["indexesExpected"] for l in self.kit), 90)
        for l in self.kit:
            self.assertEqual(len(l["fields"]), l["fieldsExpected"])
            self.assertEqual(len(l["indexOps"]), l["indexesExpected"])

    def test_every_field_title_is_the_internal_name(self):
        for l in self.kit:
            for f in l["fields"]:
                self.assertEqual(f["createPayload"]["Title"],
                                 f["internalName"])
                self.assertNotIn(" ", f["internalName"],
                                 f"{l['listTitle']}.{f['internalName']}: a "
                                 f"space would freeze _x0020_ forever")

    def test_every_index_path_targets_the_internal_name(self):
        for l in self.kit:
            names = {f["internalName"] for f in l["fields"]}
            for op in l["indexOps"]:
                self.assertIn(op["field"], names)
                self.assertIn(f"getbyinternalnameortitle('{op['field']}')",
                              op["path"])
                self.assertIn(f"getbytitle('{l['listTitle']}')", op["path"])

    def _replay_build(self):
        """The BUILD flow, exactly: per list, create -> fields -> indexes,
        in payload order, concurrency 1, first failure raises."""
        sp = MockSharePoint()
        for l in self.kit:
            sp.create_list(l["createListPayload"])
            for f in l["fields"]:
                sp.create_field(l["listTitle"], f["createPayload"])
            for op in l["indexOps"]:
                sp.merge_index(op["path"], op["payload"],
                               {"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})
        return sp

    def test_build_replay_zero_failures_and_final_counts(self):
        sp = self._replay_build()
        self.assertEqual(len(sp.lists), 17)
        all_fields = [n for flds in sp.lists.values() for n in flds]
        self.assertEqual(len(all_fields), 286)
        self.assertEqual(sum(1 for flds in sp.lists.values()
                             for meta in flds.values() if meta["indexed"]),
                         90)
        self.assertEqual([n for n in all_fields if "_x0020_" in n], [],
                         "an internal name with _x0020_ means a Title "
                         "carried a space")

    def test_verify_replay_renders_yes(self):
        sp = self._replay_build()
        results, lines = [], []
        for l in self.kit:
            fields = sp.lists[l["listTitle"]]
            cols_found = sum(1 for f in l["fields"]
                             if f["internalName"] in fields)
            idx_found = sum(1 for op in l["indexOps"]
                            if fields.get(op["field"], {}).get("indexed"))
            results.append((l["listTitle"], cols_found, l["fieldsExpected"],
                            idx_found, l["indexesExpected"]))
            lines.append(f"{l['listTitle']}: columns {cols_found}/"
                         f"{l['fieldsExpected']} indexes {idx_found}/"
                         f"{l['indexesExpected']}")
        mismatches = [r for r in results if r[1] != r[2] or r[3] != r[4]]
        by_title = {r[0]: r for r in results}
        for title, exp in CRITICAL.items():
            self.assertEqual(by_title[title][3], exp,
                             f"critical index count for {title}")
        audit = "\n".join(lines) + "\nSAFE TO LOAD CONFIGURATION: " + \
                ("YES" if not mismatches else "NO")
        self.assertTrue(audit.endswith("YES"), audit[-400:])

    def test_the_mock_is_not_vacuous(self):
        # Each enforcement fires on a violation, so a green replay means
        # something: field before list, index before field, duplicates.
        sp = MockSharePoint()
        with self.assertRaises(AssertionError):
            sp.create_field("MF Nope", {"Title": "X"})
        sp.create_list({"Title": "MF T", "BaseTemplate": 100})
        with self.assertRaises(AssertionError):
            sp.merge_index("_api/web/lists/getbytitle('MF T')/fields/"
                           "getbyinternalnameortitle('Later')",
                           {"Indexed": True},
                           {"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})
        sp.create_field("MF T", {"Title": "Later"})
        with self.assertRaises(AssertionError):
            sp.create_field("MF T", {"Title": "Later"})
        self.assertEqual(sharepoint_internal_name("Installation ID"),
                         "Installation_x0020_ID")

    def test_runbooks_carry_the_delete_list_and_the_honesty_lines(self):
        build = open(os.path.join(KIT, "FLOW-BUILD.md"),
                     encoding="utf-8").read()
        for l in self.kit:
            self.assertIn(f"`{l['listTitle']}`", build,
                          "the delete list must name all 17")
        self.assertIn("Concurrency Control", build)
        self.assertIn("Exponential, Count 4", build)
        self.assertIn("delete the MF lists, fix, rerun", build)
        readme = open(os.path.join(KIT, "README.md"),
                      encoding="utf-8").read()
        self.assertIn("NOT TESTABLE LOCALLY", readme)
        self.assertIn("have NOT been executed in Power",
                      readme.replace("\n", " "))
        verify = open(os.path.join(KIT, "FLOW-VERIFY.md"),
                      encoding="utf-8").read()
        self.assertIn("SAFE TO LOAD CONFIGURATION", verify)
        self.assertIn("Delete both flows", verify)

    def test_kit_is_email_safe(self):
        for base, _d, files in os.walk(KIT):
            for f in files:
                self.assertFalse(
                    f.endswith((".sh", ".ps1", ".py", ".exe", ".msapp",
                                ".msapr")),
                    f"script/binary type in the kit: {f}")
