"""assemble_full_solution.sh must fail closed at every gate.

The first version piped pac through `grep || true`, which masked a failed pack
and could re-ship the operator's blank app as the release candidate. Each test
here simulates one failure and asserts the script STOPS, says why, and
produces no output ZIP.

Everything is hermetic: a pac shim answers the version probe (and, where a
test needs it, fails the pack), so no real CLI is required. The full dry run
against the real packer lives in the release process, not here.
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "assemble_full_solution.sh")

REQUIRED = [
    "MF Installation", "MF Facility", "MF EOM Requirement", "MF EOM Item",
    "MF EOM Submission", "MF Unmatched File", "MF Security Mapping",
    "MF EOM Audit", "MF App Config", "MF Feature Flags", "MF App Event Log",
    "MF EOM Status", "MF Non Duty Day", "MF Calendar Event",
    "MF Access Request", "MF Notification Rule", "MF Document Destination"]


def make_msapp(datasource_names):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Header.json", json.dumps(
            {"DocVersion": "1.348", "MinVersionToLoad": "1.348",
             "MSAppStructureVersion": "2.4.0"}))
        z.writestr("References/DataSources.json", json.dumps(
            {"DataSources": [{"Name": n} for n in datasource_names]}))
        z.writestr("Src/App.pa.yaml", "App:\n  Properties:\n")
    return buf.getvalue()


def make_export(path, apps, version="1.1.0"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Other/Solution.xml",
                   f"<ImportExportXml><SolutionManifest>"
                   f"<Version>{version}</Version>"
                   f"</SolutionManifest></ImportExportXml>")
        z.writestr("Other/Customizations.xml", "<ImportExportXml/>")
        for name, blob in apps.items():
            z.writestr(f"CanvasApps/{name}", blob)


class AssemblerFailsClosed(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        # pac shim: reports the tested version; pack/unpack fail unless a
        # test installs different behaviour.
        self.bin = os.path.join(self.td, "bin")
        os.makedirs(self.bin)
        self._shim("""#!/bin/bash
if [ "$1" = help ]; then echo "Version: 2.11.2"; exit 0; fi
echo "shim: unexpected pac invocation: $*" >&2
exit 1
""")
        self.out = os.path.join(self.td, "out.zip")

    def _shim(self, body):
        p = os.path.join(self.bin, "pac")
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, 0o755)

    def _run(self, export, env=None):
        e = dict(os.environ)
        e["PATH"] = self.bin + os.pathsep + e["PATH"]
        e.update(env or {})
        return subprocess.run(
            ["bash", SCRIPT, export, self.out],
            capture_output=True, text=True, cwd=self.td, env=e)

    def _good_sources(self):
        return REQUIRED + ["Office365Users", "EOM02_Submission"]

    def test_zero_canvas_apps_fails(self):
        exp = os.path.join(self.td, "e.zip")
        make_export(exp, {})
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no CanvasApps", r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_two_canvas_apps_fail_without_a_selector(self):
        exp = os.path.join(self.td, "e.zip")
        blob = make_msapp(self._good_sources())
        make_export(exp, {"a_first.msapp": blob, "b_second.msapp": blob})
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Refusing to guess", r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_two_canvas_apps_pass_the_gate_with_an_explicit_selector(self):
        exp = os.path.join(self.td, "e.zip")
        blob = make_msapp(self._good_sources())
        make_export(exp, {"a_first.msapp": blob, "b_target.msapp": blob})
        r = self._run(exp, {"MF_EXPECTED_APP": "b_target"})
        # It proceeds past selection and dies later at the unpack shim --
        # proving selection chose, not guessed.
        self.assertIn("target: CanvasApps/b_target.msapp", r.stdout)

    def test_a_missing_data_source_names_itself_and_stops(self):
        exp = os.path.join(self.td, "e.zip")
        srcs = [s for s in self._good_sources() if s != "MF EOM Status"]
        make_export(exp, {"app.msapp": make_msapp(srcs)})
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("MF EOM Status", r.stderr)
        self.assertIn("missing required data sources", r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_a_minted_flow_name_mismatch_stops_with_instructions(self):
        exp = os.path.join(self.td, "e.zip")
        srcs = REQUIRED + ["Office365Users", "EOM02Submission_1"]
        make_export(exp, {"app.msapp": make_msapp(srcs)})
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("EOM02Submission_1", r.stderr + r.stdout)
        self.assertIn("deliberate commit", r.stderr + r.stdout)
        self.assertFalse(os.path.exists(self.out))

    def test_a_version_mismatch_stops(self):
        exp = os.path.join(self.td, "e.zip")
        make_export(exp, {"app.msapp": make_msapp(self._good_sources())},
                    version="1.0.0")
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("1.0.0", r.stderr)
        self.assertIn("Bump the solution version", r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_a_failed_pack_produces_no_output(self):
        exp = os.path.join(self.td, "e.zip")
        make_export(exp, {"app.msapp": make_msapp(self._good_sources())})
        self._shim("""#!/bin/bash
case "$1 $2" in
  "help ") echo "Version: 2.11.2";;
  "canvas unpack") mkdir -p "$6"; echo "Unpacking succeeded";;
  "canvas pack") echo "boom: simulated pack failure"; exit 1;;
  *) exit 1;;
esac
""")
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("pack FAILED", r.stderr)
        self.assertIn("simulated pack failure", r.stdout + r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_an_unchanged_msapp_after_pack_is_refused(self):
        # pack "succeeds" but writes nothing -- the blank app must never ship.
        exp = os.path.join(self.td, "e.zip")
        make_export(exp, {"app.msapp": make_msapp(self._good_sources())})
        self._shim("""#!/bin/bash
case "$1 $2" in
  "help ") echo "Version: 2.11.2";;
  "canvas unpack") mkdir -p "$6"; echo "Unpacking succeeded";;
  "canvas pack") echo "Packing succeeded";;
  *) exit 1;;
esac
""")
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("byte-identical", r.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_a_wrong_pac_version_is_refused_without_the_override(self):
        self._shim('#!/bin/bash\necho "Version: 9.9.9"\n')
        exp = os.path.join(self.td, "e.zip")
        make_export(exp, {"app.msapp": make_msapp(self._good_sources())})
        r = self._run(exp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("2.11.2", r.stderr)
        self.assertFalse(os.path.exists(self.out))


class FinalExportValidatorWorks(unittest.TestCase):
    """validate_final_export.sh promotes the platform re-export -- or refuses.

    Its fixtures are built from the real REFERENCE msapp and the real
    Artifact 1, so the checks run against genuine structure rather than
    hand-drawn JSON.
    """

    LISTS = REQUIRED

    @classmethod
    def setUpClass(cls):
        cls.ref = os.path.join(
            ROOT, "dist", "canvas",
            "MissionFeedingOperations_REFERENCE_ONLY.msapp")
        cls.art1 = os.path.join(
            ROOT, "dist", "MissionFeedingOperations_1.0.0",
            "MissionFeedingOperations_1.0.0.zip")
        if not (os.path.exists(cls.ref) and os.path.exists(cls.art1)):
            raise unittest.SkipTest("built artifacts not present")

    def _fixture(self, version=b"1.1.0", sources_extra=("Office365Users",
                 "EOM02_Submission"), plant=None, root300=True):
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        ref = zipfile.ZipFile(self.ref)
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as w:
            for n in ref.namelist():
                norm = n.replace("\\", "/")
                if norm == "References/DataSources.json":
                    w.writestr(n, json.dumps({"DataSources": [
                        {"Name": x} for x in list(self.LISTS) + list(sources_extra)]}))
                elif plant and norm == "Properties.json":
                    w.writestr(n, ref.read(n) + plant)
                else:
                    w.writestr(n, ref.read(n))
        base = zipfile.ZipFile(self.art1)
        out = os.path.join(td, "export.zip")
        with zipfile.ZipFile(out, "w") as w:
            for n in base.namelist():
                data = base.read(n)
                if n.endswith("Solution.xml"):
                    data = data.replace(b"<Version>1.0.0</Version>",
                                        b"<Version>" + version + b"</Version>")
                    if root300:
                        data = data.replace(
                            b"</RootComponents>",
                            b'<RootComponent type="300" schemaName="x" />'
                            b"</RootComponents>")
                w.writestr(n, data)
            w.writestr("CanvasApps/app_DocumentUri.msapp", inner.getvalue())
        return out

    def _run(self, path):
        return subprocess.run(
            ["bash", os.path.join(ROOT, "scripts",
                                  "validate_final_export.sh"), path],
            capture_output=True, text=True, cwd=ROOT)

    def test_a_good_export_passes_every_structural_row(self):
        r = self._run(self._fixture())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("FAIL", r.stdout.replace("FAILED 0", ""))
        self.assertIn("NTL", r.stdout)

    def test_planted_sas_residue_fails(self):
        r = self._run(self._fixture(
            plant=b'{"u":"https://x.blob.core.windows.net/a?sig=zz&sktid=t"}'))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("residue", r.stdout)

    def test_a_version_mismatch_fails(self):
        r = self._run(self._fixture(version=b"1.0.0"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Solution version", r.stdout)

    def test_a_missing_canvas_rootcomponent_fails(self):
        r = self._run(self._fixture(root300=False))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("type 300", r.stdout)

    def test_ntl_rows_are_never_pass(self):
        r = self._run(self._fixture())
        for line in r.stdout.splitlines():
            if "only the tenant" in line or "only Studio" in line \
                    or "security-open-issue" in line:
                self.assertTrue(line.strip().startswith("NTL"), line)


class PathAOnlyReplacesContent(unittest.TestCase):
    """Donor metadata must never contaminate the operator's wrapper.

    Path A's contract: the wrapper's environment/Studio-minted metadata WINS;
    only Src/ (the application content) is replaced. These are static proofs
    over the script itself -- the dynamic proof is the dry run's hash checks.
    """

    def setUp(self):
        with open(SCRIPT, encoding="utf-8") as fh:
            self.text = fh.read()

    def test_the_only_deletion_is_the_src_tree(self):
        import re
        rms = [ln.strip() for ln in self.text.splitlines()
               if re.match(r"\s*rm\s", ln) and "rm -rf \"$WORK\"" not in ln]
        self.assertEqual(
            [r for r in rms if "src/Src" in r or "$OUT" in r], rms,
            f"the assembler deletes something beyond Src/ and its own "
            f"output: {rms}")

    def test_the_only_copy_target_is_the_src_tree(self):
        cps = [ln.strip() for ln in self.text.splitlines()
               if ln.strip().startswith("cp ")]
        for c in cps:
            self.assertIn("msapp-src/Src", c, c)

    def test_it_never_references_the_donor(self):
        for token in ("donor", "scaffolding.msapr", "AlmTestApp"):
            self.assertNotIn(token, self.text,
                             f"Path A must not touch the donor ({token})")
