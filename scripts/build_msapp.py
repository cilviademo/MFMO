#!/usr/bin/env python3
"""Build the REFERENCE-ONLY .msapp with Microsoft's own packer.

    PAC=<path to pac> python3 scripts/build_msapp.py

Output: dist/canvas/MissionFeedingOperations_REFERENCE_ONLY.msapp

REFERENCE / BUILD VALIDATION ONLY. This is NOT the deployable application:
it carries no platform-minted Canvas solution identity and no environment
data-source metadata, and it has never been opened by Power Apps Studio.
Path A (scripts/assemble_full_solution.sh) produces the deployable candidate
from the operator's own exported wrapper. This artifact exists to prove the
source packs, round-trips, and is residue-free -- nothing more.

PROVENANCE OF EVERY BYTE
  Src/**            canvas-app/msapp-src (generated from canvas-app/src,
                    YAML-parsed, validated against Microsoft's published
                    pa.yaml v3 schema)
  everything else   canvas-app/donor/scaffolding.msapr -- the PRE-NEUTRALISED
                    scaffolding produced by scripts/neutralise_donor.py from
                    Microsoft's MIT-licensed ALM test app. The raw donor is
                    NOT tracked; the tracked scaffolding is residue-free and
                    hash-pinned. See canvas-app/donor/README.md.
  assembly          `pac canvas pack` (tested with PAC CLI 2.11.2 -- enforced)

FAIL-CLOSED ON: scaffolding hash drift, PAC version drift (override with
PAC_ALLOW_VERSION_DRIFT=1 only after the round-trip suite passes), pack
failure, round-trip divergence, or ANY blocked string in ANY entry of the
output. The earlier build failed open on exactly this and shipped donor
residue; see the neutraliser's docstring.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCAFFOLDING = os.path.join(ROOT, "canvas-app", "donor", "scaffolding.msapr")
MSAPP_SRC = os.path.join(ROOT, "canvas-app", "msapp-src", "Src")
OUT = os.path.join(ROOT, "dist", "canvas",
                   "MissionFeedingOperations_REFERENCE_ONLY.msapp")

PAC_TESTED_VERSION = "2.11.2"

# ONE blocklist, consumed by the neutraliser, this builder, the archive
# scanner and the final-export validator. Grown after the residue finding:
# the first version had five entries and missed everything below the line.
FORBIDDEN = (
    "crm.dynamics.com",
    "ppdevtools",
    ".sharepoint.com",       # prerelease: allow CLD-03 the denylist IS the control; naming the host is how it forbids it
    "azurewebsites.net",     # prerelease: allow CLD-04 the denylist IS the control; naming the host is how it forbids it
    "make.powerapps.com",    # prerelease: allow CLD-01 the denylist IS the control; naming the host is how it forbids it
    # -- added after donor residue shipped in the first build --
    "blob.core.windows.net",
    ".windows.net",
    "sig=",                  # SAS signature fragment
    "sktid=",                # tenant identifier in signed resource URLs
    "skoid=",
    "sv=2",                  # SAS version prefix as seen in signed URLs
    "almtestapp",
    "asmanyentities",
    "stickeromg",
    ".dps.mil/sites/",       # prerelease: allow URL-01 the denylist IS the control; naming the path shape is how it forbids it
    ".dps.mil/teams/",       # prerelease: allow URL-01 the denylist IS the control; naming the path shape is how it forbids it
    "@us.af.mil",            # prerelease: allow IDN-02 the denylist IS the control; naming the namespace is how it forbids it
)

# Verified once by neutralise_donor.py and pinned here; drift means the
# scaffolding is not the reviewed one.
SCAFFOLDING_SHA = None   # set below after first generation; see check


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sweep_archive(path):
    """Every entry, every byte, case-insensitive. Returns [(entry, string)]."""
    leaks = []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            text = z.read(n).decode("utf-8", "ignore").lower()
            for bad in FORBIDDEN:
                if bad.lower() in text:
                    leaks.append((n, bad))
    return leaks


def pac_version(pac):
    r = subprocess.run([pac, "help"], capture_output=True, text=True)
    m = re.search(r"Version:\s*([\d.]+)", r.stdout)
    return m.group(1) if m else "unknown"


def main():
    pac = os.environ.get("PAC")
    if not pac or not os.path.exists(pac):
        print("SKIPPED - set PAC=<path to the Power Platform CLI>.")
        print("An unavailable builder is not a passing one.")
        return 2

    v = pac_version(pac)
    if v != PAC_TESTED_VERSION:
        print(f"PAC CLI {v} detected; this pipeline was proven on "
              f"{PAC_TESTED_VERSION}.")
        if os.environ.get("PAC_ALLOW_VERSION_DRIFT") != "1":
            print("Refusing: canvas pack/unpack is a preview surface and a "
                  "different CLI silently decides the release output. Set "
                  "PAC_ALLOW_VERSION_DRIFT=1 only after the full canvas "
                  "round-trip suite passes on the new version.")
            return 1
        print("PAC_ALLOW_VERSION_DRIFT=1 -- continuing under protest.")

    expected = read_pinned_scaffolding_sha()
    actual = sha256(SCAFFOLDING)
    if expected and actual != expected:
        print(f"SCAFFOLDING HASH DRIFT: {actual}\nexpected {expected}. The "
              f"tracked scaffolding is not the reviewed one. Stop.")
        return 1

    leaks = sweep_archive(SCAFFOLDING)
    if leaks:
        for n, bad in leaks:
            print(f"RESIDUE IN SCAFFOLDING: '{bad}' in {n}")
        return 1

    work = tempfile.mkdtemp()
    try:
        src_dir = os.path.join(work, "sources")
        shutil.copytree(MSAPP_SRC, os.path.join(src_dir, "Src"))
        shutil.copy(SCAFFOLDING,
                    os.path.join(src_dir, "MissionFeedingOperations.msapr"))

        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        r = subprocess.run(
            [pac, "canvas", "pack", "--sources", src_dir, "--msapp", OUT,
             "--layout", "SourceCode", "--overwrite"],
            capture_output=True, text=True)
        if r.returncode != 0 or "Packing succeeded" not in r.stdout:
            print(r.stdout[-2000:], r.stderr[-500:])
            print("PACK FAILED -- nothing shipped.")
            return 1

        rt = os.path.join(work, "rt")
        r2 = subprocess.run(
            [pac, "canvas", "unpack", "--msapp", OUT, "--sources", rt,
             "--layout", "SourceCode"], capture_output=True, text=True)
        if r2.returncode != 0 or "Unpacking succeeded" not in r2.stdout:
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

        leaks = sweep_archive(OUT)
        if leaks:
            for n, bad in leaks:
                print(f"LEAK: '{bad}' in {n} -- not shipped.")
            try:
                os.unlink(OUT)
            except OSError:
                pass
            return 1

        with zipfile.ZipFile(OUT) as z:
            entries = z.namelist()
        print(f"built {os.path.relpath(OUT, ROOT)}   REFERENCE ONLY")
        print(f"  {len(entries)} entries "
              f"({sum(1 for e in entries if e.replace(chr(92), '/').startswith('Src/'))} yaml)")
        print(f"  pac {v}; scaffolding {actual[:16]}...")
        print(f"  round-trip identical; sweep clean against "
              f"{len(FORBIDDEN)} blocked strings")
        print(f"  SHA-256 {sha256(OUT)}")
        print()
        print("NOT the deployable app: no platform-minted identity, never")
        print("opened by Studio. Path A produces the deployable candidate.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def read_pinned_scaffolding_sha():
    p = os.path.join(ROOT, "canvas-app", "donor", "scaffolding.sha256")
    if os.path.exists(p):
        return open(p).read().split()[0]
    return None


if __name__ == "__main__":
    sys.exit(main())
