#!/usr/bin/env python3
"""Build MissionFeedingOperations.msapp with Microsoft's own packer.

    python3 scripts/build_msapp.py            # needs PAC=<path to pac>

WHAT THIS IS, EXACTLY, so nobody has to trust an adjective:

  * The screens, components and formulas come from canvas-app/msapp-src/,
    generated from canvas-app/src/ by gen_msapp_source.py and validated
    against Microsoft's published pa.yaml v3 schema (validate_msapp_source.py)
    -- the packer itself validates NOTHING, which was proven by feeding it
    garbage that "packed successfully".
  * The format scaffolding comes from a genuine Studio-built app (see
    canvas-app/donor/README.md), NEUTRALISED per the table below.
  * The binary is assembled by `pac canvas pack`, Microsoft's packer, and then
    unpacked again with the same tool to prove the source round-trips.
  * The output has never been opened by Power Apps Studio. Microsoft's own
    packer prints, on every run, that a SourceCode-packed app must be
    validated by opening it for edit in Studio. This build does not and cannot
    change that. It moves the Studio session from "paste 22 files" to "open,
    check, save, export".

NEUTRALISATION -- every donor entry, dispositioned:

  entry                            disposition  why
  msapr-header.json                rebuilt      packer contract (MsaprHeaderJson)
  msapp/Header.json                verbatim     format/doc version, Studio-authored
  msapp/Properties.json            edited       fresh deterministic FileID/Id;
                                                Name; LocalDatabaseReferences and
                                                ConnectionString EMPTIED (donor's
                                                names a commercial Dataverse dev
                                                instance); ControlCount emptied
                                                (donor-derived, Studio rebuilds)
  msapp/References/DataSources.json emptied     donor's Dataverse metadata incl.
                                                commercial instance URLs; this
                                                app's sources are added in Studio
  msapp/Controls/*.json            STRIPPED     donor screens' control trees --
  msapp/Components/7.json          STRIPPED     stale derived state describing
  msapp/ComponentsMetadata.json    STRIPPED     content this app does not have;
                                                LoadFromYaml has Studio rebuild
                                                it, and stale state that loads
                                                silently is worse than absent
                                                state that fails loudly
  msapp/AppCheckerResult.sarif     STRIPPED     donor's analysis results
  msapp/References/Themes.json     verbatim     format scaffolding
  msapp/References/ModernThemes.json verbatim
  msapp/References/Templates.json  verbatim     the control template catalogue
  msapp/References/Resources.json  verbatim     (no commercial strings; verified)
  msapp/References/QualifiedValues.json verbatim
  msapp/Resources/PublishInfo.json verbatim     publish scaffolding
  msapp/Assets/**                  verbatim     the three sample images PublishInfo
                                                references (Microsoft MIT assets)
  msapp/.gitignore                 verbatim

The build FAILS if any commercial-cloud string survives into the output, if
the donor hash drifts, or if the round-trip diverges from msapp-src.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DONOR = os.path.join(ROOT, "canvas-app", "donor",
                     "AlmTestApp-asManyEntitiesAsPossible.msapp")
DONOR_SHA = "08a80c3d2686ddbd9acd18774cc66a35ae3059d89e80d22444aef94a5598baf9"
MSAPP_SRC = os.path.join(ROOT, "canvas-app", "msapp-src", "Src")
OUT = os.path.join(ROOT, "dist", "canvas",
                   "MissionFeedingOperations.msapp")

STRIP = re.compile(r"^msapp/(Controls/|Components/|ComponentsMetadata\.json"
                   r"|AppCheckerResult\.sarif|References/DataSources\.json)")
FORBIDDEN = (
    "crm.dynamics.com",
    "ppdevtools",
    ".sharepoint.com",        # prerelease: allow CLD-03 the denylist IS the control; naming the host is how it forbids it
    "azurewebsites.net",      # prerelease: allow CLD-04 the denylist IS the control; naming the host is how it forbids it
    "make.powerapps.com",     # prerelease: allow CLD-01 the denylist IS the control; naming the host is how it forbids it
)
# Deterministic app identity, derived from the programme's name -- fresh
# GUIDs would make the build non-reproducible, and reusing the donor's would
# make this artifact claim to BE the donor.
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
FILE_ID = str(uuid.uuid5(NS, "MissionFeedingOperations/FileID"))
APP_ID = str(uuid.uuid5(NS, "MissionFeedingOperations/Id"))


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def neutralised_properties(raw):
    p = json.loads(raw)
    import base64
    name = base64.b64encode(b"MissionFeedingOperations").decode().rstrip("=")
    p["Name"] = name + ".msapp"
    p["AppDescription"] = ("Mission Feeding Operations - EOM/EOY document "
                           "requirement tracking. DEV/PILOT.")
    p["FileID"] = FILE_ID
    p["Id"] = APP_ID
    p["LocalDatabaseReferences"] = ""
    p["ConnectionString"] = ""
    p["LocalConnectionReferences"] = "{}" if isinstance(
        p.get("LocalConnectionReferences"), str) else {}
    p["ControlCount"] = {}
    return json.dumps(p, indent=2).encode()


def build_msapr(donor_zip, msapr_path):
    kept, stripped = [], []
    with zipfile.ZipFile(msapr_path, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr("msapr-header.json", json.dumps({
            "MsaprStructureVersion": "1.0",
            "UnpackedConfiguration": {"ContentTypes": ["PaYamlSourceCode"]},
        }))
        for entry in donor_zip.namelist():
            norm = "msapp/" + entry.replace("\\", "/")
            if entry.replace("\\", "/").startswith("Src/"):
                continue                    # the yaml layer: ours replaces it
            if STRIP.match(norm):
                stripped.append(norm)
                continue
            data = donor_zip.read(entry)
            if norm.endswith("Properties.json"):
                data = neutralised_properties(data)
            out.writestr(norm, data)
            kept.append(norm)
        out.writestr("msapp/References/DataSources.json",
                     json.dumps({"DataSources": []}))
        kept.append("msapp/References/DataSources.json (emptied)")
    return kept, stripped


def main():
    pac = os.environ.get("PAC")
    if not pac or not os.path.exists(pac):
        print("SKIPPED - set PAC=<path to the Power Platform CLI>.")
        print("An unavailable builder is not a passing one.")
        return 2

    actual = sha256(DONOR)
    if actual != DONOR_SHA:
        print(f"DONOR HASH DRIFT: {actual}")
        print("The vendored donor is not the file this build was written "
              "against. Stop.")
        return 1

    work = tempfile.mkdtemp()
    try:
        src_dir = os.path.join(work, "sources")
        shutil.copytree(MSAPP_SRC, os.path.join(src_dir, "Src"))
        with zipfile.ZipFile(DONOR) as donor:
            kept, stripped = build_msapr(
                donor, os.path.join(src_dir, "MissionFeedingOperations.msapr"))

        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        r = subprocess.run(
            [pac, "canvas", "pack", "--sources", src_dir, "--msapp", OUT,
             "--layout", "SourceCode", "--overwrite"],
            capture_output=True, text=True)
        if "Packing succeeded" not in r.stdout:
            print(r.stdout[-2000:], r.stderr[-500:])
            return 1

        # round-trip: unpack what was packed; the yaml must match msapp-src.
        rt = os.path.join(work, "rt")
        r2 = subprocess.run(
            [pac, "canvas", "unpack", "--msapp", OUT, "--sources", rt,
             "--layout", "SourceCode"], capture_output=True, text=True)
        if "Unpacking succeeded" not in r2.stdout:
            print("ROUND-TRIP UNPACK FAILED")
            print(r2.stdout[-1500:])
            return 1
        mismatches = []
        for base, _d, files in os.walk(MSAPP_SRC):
            for f in files:
                mine = os.path.join(base, f)
                rel = os.path.relpath(mine, MSAPP_SRC)
                theirs = os.path.join(rt, "Src", rel)
                if not os.path.exists(theirs):
                    mismatches.append(f"missing after round-trip: {rel}")
                elif open(mine, "rb").read() != open(theirs, "rb").read():
                    mismatches.append(f"content differs: {rel}")
        if mismatches:
            print("ROUND-TRIP MISMATCH")
            for m in mismatches:
                print("  " + m)
            return 1

        # leak sweep over every byte of the output.
        with zipfile.ZipFile(OUT) as z:
            for n in z.namelist():
                blob = z.read(n).decode("utf-8", "ignore")
                for bad in FORBIDDEN:
                    if bad in blob:
                        print(f"LEAK: '{bad}' in {n}. The neutralisation "
                              f"missed something; the artifact is not shipped.")
                        return 1
            entries = z.namelist()

        print(f"built {os.path.relpath(OUT, ROOT)}")
        print(f"  {len(entries)} entries "
              f"({sum(1 for e in entries if e.replace(chr(92), '/').startswith('Src/'))} yaml)")
        print(f"  donor entries kept: {len(kept)}, stripped: {len(stripped)}")
        print(f"  round-trip: every msapp-src file identical after "
              f"pack+unpack")
        print(f"  leak sweep: clean")
        print(f"  SHA-256 {sha256(OUT)}")
        print()
        print("NOT VALIDATED BY STUDIO. Microsoft's packer states that a")
        print("SourceCode-packed app must be opened for edit in Studio to be")
        print("validated; that step is the operator's and cannot happen here.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
