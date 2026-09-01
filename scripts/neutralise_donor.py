#!/usr/bin/env python3
"""Produce canvas-app/donor/scaffolding.msapr -- the CLEAN, tracked scaffolding.

    python3 scripts/neutralise_donor.py <raw-donor.msapp>

WHY THIS EXISTS. The first build vendored Microsoft's raw ALM test app and
neutralised it at build time. The blocklist was too narrow and the shipped
.msapp still carried donor residue the user found by inspection:
signed Azure Blob URLs (`blob.core.windows.net/...sig=...`), a donor tenant
identifier (`sktid=`), three donor images, the donor's AppName, and donor
feature flags (runtime copilot, experimental CDS/SQL connectors). The claim
"leak sweep: clean" was FALSE.

The fix is structural, not just a longer list: the tracked artifact is now the
NEUTRALISED scaffolding itself, so the repository never carries the residue at
all, and every consumer starts clean. The raw donor is not tracked; to
regenerate, fetch it from Microsoft's repository and re-run this script:

    raw source  https://raw.githubusercontent.com/microsoft/
                PowerApps-Language-Tooling/master/src/Persistence.Tests/
                _TestData/AlmApps/AlmTestApp-asManyEntitiesAsPossible.msapp
    raw sha256  08a80c3d2686ddbd9acd18774cc66a35ae3059d89e80d22444aef94a5598baf9

DISPOSITION of every donor entry:

  keep verbatim   Header.json; References/{Themes,ModernThemes,Templates,
                  QualifiedValues}.json  (format + control-template scaffolding)
  edit            Properties.json  (identity; leak fields emptied; donor
                  feature flags forced OFF; ControlCount emptied)
                  Resources/PublishInfo.json  (donor AppName out; neutral
                  background; logo blank)
  empty           References/Resources.json  (all four entries are donor image
                  resources; the Mission Feeding source references NO image
                  resource -- asserted below)
                  References/DataSources.json
  strip           Controls/*, Components/*, ComponentsMetadata.json,
                  AppCheckerResult.sarif, Assets/**, .gitignore

The output is deterministic (fixed timestamps) and is verified residue-free
against the same blocklist scripts/build_msapp.py enforces, before writing.
"""
import hashlib
import json
import os
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "canvas-app", "donor", "scaffolding.msapr")
RAW_SHA = "08a80c3d2686ddbd9acd18774cc66a35ae3059d89e80d22444aef94a5598baf9"

KEEP_VERBATIM = {
    "Header.json",
    "References/Themes.json",
    "References/ModernThemes.json",
    "References/Templates.json",
    "References/QualifiedValues.json",
}

# Donor flags forced OFF. Explicit False beats deletion: a deleted key falls
# back to whatever the platform's default is that year; False is an answer.
FLAGS_OFF = (
    "enablecanvasappruntimecopilot", "enablecopilotanswercontrol",
    "enablecopilotcontrol", "nativecdsexperimental",
    "useexperimentalcdsconnector", "useexperimentalsqlconnector",
    "aibuilderserviceenrollment",
)

FORBIDDEN = None  # imported from build_msapp so there is exactly one list


def neutral_properties(raw):
    import base64
    import uuid
    p = json.loads(raw)
    ns = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    p["Name"] = base64.b64encode(b"MissionFeedingOperations").decode().rstrip("=") + ".msapp"
    p["AppDescription"] = ("Mission Feeding Operations - EOM/EOY document "
                           "requirement tracking. DEV/PILOT.")
    p["FileID"] = str(uuid.uuid5(ns, "MissionFeedingOperations/FileID"))
    p["Id"] = str(uuid.uuid5(ns, "MissionFeedingOperations/Id"))
    p["LocalDatabaseReferences"] = ""
    p["ConnectionString"] = ""
    p["LocalConnectionReferences"] = "{}" if isinstance(
        p.get("LocalConnectionReferences"), str) else {}
    p["ControlCount"] = {}
    flags = p.get("AppPreviewFlagsMap", {})
    for f in FLAGS_OFF:
        if f in flags:
            flags[f] = False
    return json.dumps(p, indent=2).encode()


def neutral_publishinfo(raw):
    p = json.loads(raw)
    p["AppName"] = "MissionFeedingOperations"
    p["BackgroundColor"] = "RGBA(250,249,248,1)"      # clrSurfaceAlt
    p["LogoFileName"] = ""
    return json.dumps(p, indent=2).encode()


def source_references_no_image_resource(donor):
    """The whole basis for emptying Resources.json, proven not assumed."""
    r = json.loads(donor.read("References\\Resources.json"))
    names = [res.get("Name", "") for res in r.get("Resources", [])]
    src = os.path.join(ROOT, "canvas-app", "msapp-src", "Src")
    blob = ""
    for base, _d, files in os.walk(src):
        for f in files:
            blob += open(os.path.join(base, f), encoding="utf-8").read()
    used = [n for n in names if n and n in blob]
    if used:
        raise SystemExit(f"the source references donor resources {used}; "
                         f"they cannot be stripped blindly")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    raw = argv[1]
    h = hashlib.sha256(open(raw, "rb").read()).hexdigest()
    if h != RAW_SHA:
        print(f"raw donor hash {h}\ndoes not match the pinned {RAW_SHA}; stop.")
        return 1

    from build_msapp import FORBIDDEN as forbidden      # one list, one place

    donor = zipfile.ZipFile(raw)
    source_references_no_image_resource(donor)

    entries = {}
    entries["msapr-header.json"] = json.dumps({
        "MsaprStructureVersion": "1.0",
        "UnpackedConfiguration": {"ContentTypes": ["PaYamlSourceCode"]},
    }).encode()
    for e in donor.namelist():
        norm = e.replace("\\", "/")
        if norm in KEEP_VERBATIM:
            entries["msapp/" + norm] = donor.read(e)
    entries["msapp/Properties.json"] = neutral_properties(
        donor.read("Properties.json"))
    entries["msapp/Resources/PublishInfo.json"] = neutral_publishinfo(
        donor.read("Resources\\PublishInfo.json"))
    entries["msapp/References/Resources.json"] = json.dumps(
        {"Resources": []}).encode()
    entries["msapp/References/DataSources.json"] = json.dumps(
        {"DataSources": []}).encode()

    # Residue-free before a byte is written.
    leaks = []
    for name, data in entries.items():
        text = data.decode("utf-8", "ignore").lower()
        for bad in forbidden:
            if bad.lower() in text:
                leaks.append((name, bad))
    if leaks:
        for name, bad in leaks:
            print(f"RESIDUE: '{bad}' in {name}")
        return 1

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(entries):
            zi = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, entries[name])

    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print(f"  {len(entries)} entries, residue-free against "
          f"{len(forbidden)} blocked strings")
    print(f"  sha256 {hashlib.sha256(open(OUT, 'rb').read()).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv))
