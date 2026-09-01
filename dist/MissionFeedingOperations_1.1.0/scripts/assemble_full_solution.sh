#!/usr/bin/env bash
# Assemble the MissionFeedingOperations full-solution CANDIDATE from the
# operator's own exported wrapper solution.
#
#   scripts/assemble_full_solution.sh <their-exported-solution.zip> [out.zip]
#
# The wrapper is the operator's because a Canvas solution component needs
# platform-minted identity and environment data-source metadata; nothing
# offline can mint those truthfully. This script replaces ONLY the blank
# app's Src/ content, keeping their identity, their scaffolding, and their
# environment's data-source bindings.
#
# EVERY GATE FAILS CLOSED. The first version piped pac through `grep || true`,
# which could mask a failed pack and re-ship the blank app; that class of
# defect is why each step below checks its own exit code and its own output.
#
# Gates, in order:
#   G1  pac present and the TESTED version (2.11.2); PAC_ALLOW_VERSION_DRIFT=1
#       overrides only after the canvas round-trip suite passes on the drift
#   G2  exactly ONE CanvasApps/*.msapp (or MF_EXPECTED_APP names the one)
#   G3  the wrapper app carries ALL 19 required data sources -- named check,
#       stops with exactly what is missing; Path A's point is an already-bound
#       app, not "add it in Studio later"
#   G4  the environment-minted flow reference matches what the source calls
#       (EOM02_Submission); a mismatch stops with instructions to update the
#       REPOSITORY source -- the generated app is never silently patched
#   G5  unpack must succeed
#   G6  pack must succeed AND the .msapp bytes must actually change
#   G7  the internal Solution.xml version must equal the release version
#       (default 1.1.0; override with MF_RELEASE_VERSION) -- bump the solution
#       version in Power Apps BEFORE the wrapper export
#   G8  structural validation (validate_solution.py --export)
#   G9  archive leak sweep over every entry of the output
set -euo pipefail

IN="${1:?usage: assemble_full_solution.sh <exported-solution.zip> [out.zip]}"
RELEASE_VERSION="${MF_RELEASE_VERSION:-1.1.0}"
OUT="${2:-MissionFeedingOperations_${RELEASE_VERSION}.zip}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PAC_TESTED="2.11.2"

fail() { echo "FAIL: $*" >&2; exit 1; }

command -v pac >/dev/null || fail "pac is not on PATH"
[ -d "$ROOT/canvas-app/msapp-src/Src" ] \
    || fail "canvas-app/msapp-src missing; run scripts/gen_msapp_source.py"

# --- G1: pinned toolchain --------------------------------------------------
PAC_VER="$(pac help 2>/dev/null | sed -n 's/^Version: \([0-9.]*\).*/\1/p' | head -1)"
if [ "$PAC_VER" != "$PAC_TESTED" ]; then
    echo "PAC CLI $PAC_VER detected; this pipeline was proven on $PAC_TESTED." >&2
    if [ "${PAC_ALLOW_VERSION_DRIFT:-0}" != "1" ]; then
        fail "canvas pack/unpack is a preview surface; a different CLI silently
decides the release output. Set PAC_ALLOW_VERSION_DRIFT=1 only after the full
canvas round-trip test suite has passed on $PAC_VER."
    fi
    echo "PAC_ALLOW_VERSION_DRIFT=1 -- continuing under protest." >&2
fi

echo "1/9  unzipping the export"
unzip -q "$IN" -d "$WORK/solution"

# --- G2: exactly one canvas app -------------------------------------------
mapfile -t APPS < <(cd "$WORK/solution" && ls CanvasApps/*.msapp 2>/dev/null || true)
if [ "${#APPS[@]}" -eq 0 ]; then
    fail "no CanvasApps/*.msapp in the export. Create the blank canvas app
INSIDE the solution before exporting -- CANVAS_APP_ASSEMBLY.md Path A step 2."
elif [ "${#APPS[@]}" -eq 1 ]; then
    MSAPP_REL="${APPS[0]}"
elif [ -n "${MF_EXPECTED_APP:-}" ]; then
    MSAPP_REL=""
    for a in "${APPS[@]}"; do
        case "$a" in *"$MF_EXPECTED_APP"*) MSAPP_REL="$a" ;; esac
    done
    [ -n "$MSAPP_REL" ] || fail "MF_EXPECTED_APP='$MF_EXPECTED_APP' matches none of: ${APPS[*]}"
else
    fail "${#APPS[@]} canvas apps in the export: ${APPS[*]}
Refusing to guess which is Mission Feeding Operations. Re-export a solution
with only the one app, or set MF_EXPECTED_APP=<distinctive filename part>."
fi
echo "     target: $MSAPP_REL"

# --- G7 (checked early, before any work is wasted): solution version -------
SOL_VER="$(python3 - "$WORK/solution/Other/Solution.xml" "$WORK/solution/solution.xml" <<'PY'
import sys, re, os
for p in sys.argv[1:]:
    if os.path.exists(p):
        m = re.search(r"<Version>([^<]+)</Version>", open(p).read())
        if m:
            print(m.group(1)); break
PY
)"
[ -n "$SOL_VER" ] || fail "could not read <Version> from the export's Solution.xml"
if [ "$SOL_VER" != "$RELEASE_VERSION" ]; then
    fail "internal solution version is $SOL_VER but this release is
$RELEASE_VERSION. Bump the solution version to $RELEASE_VERSION in Power Apps
(solution → settings) BEFORE the wrapper export, then re-export. The filename
and the platform metadata must agree; this script never rewrites platform
identity metadata."
fi
echo "     solution version: $SOL_VER (matches release)"

# --- G3 + G4: data sources and the flow reference, read from THEIR app -----
python3 - "$WORK/solution/$MSAPP_REL" "$ROOT" <<'PY'
import io, json, re, sys, zipfile
msapp, root = sys.argv[1], sys.argv[2]
REQUIRED_LISTS = [
    "MF Installation", "MF Facility", "MF EOM Requirement", "MF EOM Item",
    "MF EOM Submission", "MF Unmatched File", "MF Security Mapping",
    "MF EOM Audit", "MF App Config", "MF Feature Flags", "MF App Event Log",
    "MF EOM Status", "MF Non Duty Day", "MF Calendar Event",
    "MF Access Request", "MF Notification Rule", "MF Document Destination"]
z = zipfile.ZipFile(msapp)
entry = next((n for n in z.namelist()
              if n.replace("\\", "/") == "References/DataSources.json"), None)
if entry is None:
    sys.exit("FAIL: the wrapper app has no References/DataSources.json -- it "
             "was exported before any data source was added.")
names = [d.get("Name", "")
         for d in json.loads(z.read(entry)).get("DataSources", [])]
missing = [r for r in REQUIRED_LISTS if r not in names]
squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
if not any(squash(n) == "office365users" for n in names):
    missing.append("Office365Users")
flowish = [n for n in names if "eom02" in squash(n)]
if not flowish:
    missing.append("EOM-02 Submission (the Power Automate flow)")
if missing:
    print("FAIL: the wrapper app is missing required data sources:",
          file=sys.stderr)
    for m in missing:
        print(f"  - {m}", file=sys.stderr)
    print("Add them in Studio, save, re-export, and run this again. Path A's\n"
          "point is an already-bound app; 'add it later' is not a step.",
          file=sys.stderr)
    sys.exit(1)
# G4: the exact identifier the environment minted vs what the source calls.
source_name = "EOM02_Submission"
minted = flowish[0]
if squash(minted) != squash(source_name):
    sys.exit(f"FAIL: the environment minted flow reference '{minted}' but the "
             f"source calls {source_name}.Run(...). Do NOT patch the built "
             f"app: update canvas-app/src/Screens/scrUpload.pa.yaml to the "
             f"minted name in a deliberate commit, regenerate "
             f"(gen_msapp_source.py), re-run the suite, then re-run this.")
print(f"     data sources: all 19 present; flow reference '{minted}' matches "
      f"the source")
PY

echo "2/9  hashing their app before replacement"
BEFORE_SHA="$(sha256sum "$WORK/solution/$MSAPP_REL" | cut -d' ' -f1)"

echo "3/9  unpacking their app (their identity + their scaffolding)"
UNPACK_LOG="$WORK/unpack.log"
if ! pac canvas unpack --msapp "$WORK/solution/$MSAPP_REL" \
        --sources "$WORK/src" --layout SourceCode >"$UNPACK_LOG" 2>&1; then
    cat "$UNPACK_LOG"
    fail "canvas unpack failed"
fi
grep -q "Unpacking succeeded" "$UNPACK_LOG" || { cat "$UNPACK_LOG"; fail "unpack did not report success"; }

echo "4/9  replacing the content with this repository's"
rm -rf "$WORK/src/Src"
cp -r "$ROOT/canvas-app/msapp-src/Src" "$WORK/src/Src"

echo "5/9  packing with Microsoft's packer against THEIR reference archive"
PACK_LOG="$WORK/pack.log"
if ! pac canvas pack --sources "$WORK/src" \
        --msapp "$WORK/solution/$MSAPP_REL" --layout SourceCode --overwrite \
        >"$PACK_LOG" 2>&1; then
    cat "$PACK_LOG"
    fail "canvas pack FAILED -- release blocked; nothing was assembled."
fi
grep -q "Packing succeeded" "$PACK_LOG" || { cat "$PACK_LOG"; fail "pack did not report success"; }
cat "$PACK_LOG" | grep -E "succeeded" || true

echo "6/9  verifying the app actually changed"
AFTER_SHA="$(sha256sum "$WORK/solution/$MSAPP_REL" | cut -d' ' -f1)"
[ "$BEFORE_SHA" != "$AFTER_SHA" ] || fail "the .msapp is byte-identical after
packing -- the replacement did not take, and shipping the blank app as the
candidate is exactly the failure this gate exists for."

echo "7/9  re-zipping"
rm -f "$OUT"
( cd "$WORK/solution" && zip -qrX "$OUT" . )

echo "8/9  structural validation"
python3 "$ROOT/scripts/validate_solution.py" --export "$OUT" \
    || fail "structural validation failed -- do not import this."

echo "9/9  archive leak sweep"
python3 - "$OUT" "$ROOT" <<'PY'
import sys, zipfile, os
sys.path.insert(0, os.path.join(sys.argv[2], "scripts"))
from build_msapp import sweep_archive
leaks = sweep_archive(sys.argv[1])
if leaks:
    for entry, bad in leaks:
        print(f"LEAK: '{bad}' in {entry}", file=sys.stderr)
    sys.exit(1)
print("     clean")
PY

echo
sha256sum "$OUT"
echo
echo "This is the release CANDIDATE. The permanent artifact is the solution"
echo "Power Platform re-exports AFTER: import, open the app for edit once"
echo "(that open IS the validation Microsoft's packer requires), resolve zero"
echo "errors, run the Accessibility Checker, save, publish, re-export. Then:"
echo "  scripts/validate_final_export.sh <re-exported>.zip"
