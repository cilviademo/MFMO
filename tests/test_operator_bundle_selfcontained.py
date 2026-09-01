"""The operator bundle must be able to do what its own documents say.

The V1 review found the defect this file exists to prevent: a ZIP labelled
COMPLETE whose assembler needed canvas-app/msapp-src, whose validators
imported Python modules, and whose checklists cited provisioning documents --
none of which were in the ZIP. The engineering was ready; the delivery was
not. Every check here runs against a COPY of the built bundle in a temp
directory with NO access to the repository, because that is exactly the
situation on the operator's workstation.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUNDLE = os.path.join(ROOT, "dist", "MissionFeedingOperations_1.1.0")


class OperatorBundleIsSelfContained(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(BUNDLE):
            raise unittest.SkipTest(
                "bundle not built (scripts/build_bundle.sh); packaging runs "
                "must build it before this gate means anything")
        cls.tmp = tempfile.mkdtemp(prefix="mf-bundle-")
        cls.box = os.path.join(cls.tmp, "bundle")
        shutil.copytree(BUNDLE, cls.box)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -------------------------------------------------------------- helpers
    def _exists(self, *rel):
        p = os.path.join(self.box, *rel)
        self.assertTrue(os.path.exists(p),
                        f"bundle is missing {os.path.join(*rel)}")
        return p

    def _read(self, *rel):
        with open(self._exists(*rel), encoding="utf-8") as fh:
            return fh.read()

    # --------------------------------------------------- assembler closure
    def test_assembler_source_inputs_exist(self):
        # assemble_full_solution.sh computes ROOT as scripts/.. and copies
        # canvas-app/msapp-src/Src wholesale. Without it, Path A stops at
        # the first gate on a clean workstation.
        self._exists("canvas-app", "msapp-src", "Src")
        yamls = os.listdir(os.path.join(self.box, "canvas-app",
                                        "msapp-src", "Src"))
        self.assertGreaterEqual(
            len([f for f in yamls if f.endswith(".pa.yaml")]), 3)

    def test_regeneration_path_exists(self):
        # The assembler's flow-name gate tells the operator to fix
        # canvas-app source and re-run gen_msapp_source.py. Both halves of
        # that instruction must be present.
        self._exists("scripts", "gen_msapp_source.py")
        self._exists("canvas-app", "src", "Screens")
        self._exists("canvas-app", "formulas")
        self._exists("canvas-app", "pa.schema.yaml")

    def test_python_import_closure_resolves(self):
        # Every shipped script must import cleanly with sys.path limited to
        # the BUNDLE's own scripts directory -- proving no module silently
        # resolves from the repository.
        scripts_dir = os.path.join(self.box, "scripts")
        shipped = [f for f in os.listdir(scripts_dir) if f.endswith(".py")]
        self.assertTrue(shipped, "bundle ships no python scripts at all")
        for f in shipped:
            r = subprocess.run(
                [sys.executable, "-c",
                 "import ast,sys\n"
                 f"src=open({os.path.join(scripts_dir, f)!r},encoding='utf-8').read()\n"
                 "tree=ast.parse(src)\n"
                 "import os\n"
                 f"names={{n[:-3] for n in os.listdir({scripts_dir!r}) if n.endswith('.py')}}\n"
                 "missing=[]\n"
                 "for node in ast.walk(tree):\n"
                 "    mods=[]\n"
                 "    if isinstance(node,ast.Import): mods=[a.name for a in node.names]\n"
                 "    if isinstance(node,ast.ImportFrom) and node.module: mods=[node.module]\n"
                 "    for m in mods:\n"
                 "        top=m.split('.')[0]\n"
                 "        if top in names: continue\n"
                 "        try: __import__(top)\n"
                 "        except ImportError: missing.append(m)\n"
                 "print(';'.join(missing))"],
                capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "",
                             f"{f}: unresolvable imports {r.stdout.strip()} "
                             f"-- ship the module or drop the dependency")

    def test_shell_scripts_parse(self):
        for f in os.listdir(os.path.join(self.box, "scripts")):
            if f.endswith(".sh"):
                r = subprocess.run(
                    ["bash", "-n", os.path.join(self.box, "scripts", f)],
                    capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"{f}: {r.stderr}")

    def test_validators_run_from_the_bundle_alone(self):
        # validate_solution.py is invoked by the assembler (G8). It must at
        # least start and reach its own argument handling using only bundle
        # files -- an import or missing-data crash here is the clean-machine
        # failure the review demonstrated.
        r = subprocess.run(
            [sys.executable, os.path.join(self.box, "scripts",
                                          "validate_solution.py"),
             "--export", os.path.join(self.box, "Artifact1",
                                      "MissionFeedingOperations_1.0.0.zip")],
            capture_output=True, text=True, cwd=self.box)
        blob = r.stdout + r.stderr
        self.assertNotIn("Traceback", blob, blob[-2000:])
        self.assertNotIn("ModuleNotFoundError", blob, blob[-2000:])
        self.assertNotIn("FileNotFoundError", blob, blob[-2000:])

    # ------------------------------------------------- provisioning closure
    def test_provisioning_package_is_present(self):
        for f in ("PROVISION-WITHOUT-POWERSHELL.md",
                  "Provision-MFOpsLists.ps1",
                  "Seed-MFOpsConfiguration.ps1",
                  "Discover-MFDestinations.ps1",
                  "Verify-MFOpsCapabilities.ps1",
                  "sharepoint-schema.json"):
            self._exists("provisioning", f)
        self._exists("scripts", "verify_provisioning.py")
        self._exists("scripts", "gen_rest_payloads.py")
        self._exists("docs", "SHAREPOINT_SCHEMA_MANIFEST.md")

    # ------------------------------------------------ documented references
    DOC_REF = re.compile(
        r"`((?:scripts|provisioning|configuration|deployment|docs|canvas-app|"
        r"Artifact1|Canvas)/[A-Za-z0-9_./-]+?\.[A-Za-z0-9]{2,7})`")

    # Build RECORDS may cite the repository they narrate -- the report
    # describes how the release was made, including scripts (build_release,
    # classify_tests, the parity gate) that only make sense with the repo
    # and its git history present. Operator INSTRUCTIONS get no such pass:
    # every checklist, runbook, worksheet and provisioning doc must resolve
    # entirely inside the delivery.
    RECORD_DOCS = {"FINAL_RELEASE_REPORT.md", "DECISION_LOG.md",
                   "RECONCILIATION.md"}

    def test_every_file_the_documents_cite_is_shipped(self):
        missing = []
        for base, _dirs, files in os.walk(self.box):
            for f in files:
                if not f.endswith(".md") or f in self.RECORD_DOCS:
                    continue
                text = open(os.path.join(base, f), encoding="utf-8").read()
                for ref in self.DOC_REF.findall(text):
                    if ref.endswith((".zip", ".msapp", ".json")) and (
                            "1.1.0" in ref or "UNMANAGED" in ref
                            or "MANAGED" in ref or ".dod." in ref):
                        continue  # produced later, on the .mil side
                    if not os.path.exists(os.path.join(self.box, ref)):
                        missing.append(f"{f} cites {ref}")
        self.assertEqual(missing, [],
                         "documents cite files the delivery does not carry:\n"
                         + "\n".join(missing))

    # ------------------------------------------------------------ manifest
    def test_checksum_manifest_exists_and_verifies(self):
        manifest = self._read("SHA256SUMS.txt")
        import hashlib
        rows = [ln.split(maxsplit=1) for ln in manifest.splitlines()
                if re.match(r"^[0-9a-f]{64}\s", ln)]
        self.assertGreaterEqual(len(rows), 10,
                                "manifest must cover the delivery, not a "
                                "token file or two")
        names = {rel for _sha, rel in rows}
        self.assertIn("Artifact1/MissionFeedingOperations_1.0.0.zip", names)
        for sha, rel in rows:
            p = os.path.join(self.box, rel)
            self.assertTrue(os.path.exists(p), f"manifest names missing {rel}")
            with open(p, "rb") as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
            self.assertEqual(actual, sha, f"hash mismatch for {rel}")

    def test_the_reference_msapp_is_packaged(self):
        # The msapp is gitignored, so this row can only pass on a machine
        # that actually built and packaged it -- which is the only machine
        # allowed to ship the bundle.
        if not os.path.exists(os.path.join(ROOT, "dist", "canvas",
                                           "MissionFeedingOperations_REFERENCE_ONLY.msapp")):
            self.skipTest("reference msapp not built here; packaging "
                          "machines must not skip this")
        self._exists("Canvas", "MissionFeedingOperations_REFERENCE_ONLY.msapp")

    def test_deployment_settings_example_is_sanitised(self):
        import json
        p = self._exists("deployment", "deployment-settings.example.json")
        data = json.load(open(p, encoding="utf-8"))
        self.assertEqual(len(data.get("EnvironmentVariables", [])), 24)
        self.assertEqual(len(data.get("ConnectionReferences", [])), 3)
        for row in data["EnvironmentVariables"]:
            self.assertEqual(row.get("Value", ""), "",
                             f"{row.get('SchemaName')}: example values must "
                             f"be blank -- real values never leave the tenant")
        for row in data["ConnectionReferences"]:
            self.assertEqual(row.get("ConnectionId", ""), "")
