#!/usr/bin/env bash
# Assemble MissionFeedingOperations_1.1.0.zip -- the FULL solution, canvas app
# inside -- from the operator's own exported solution.
#
#   scripts/assemble_full_solution.sh <their-exported-solution.zip> [out.zip]
#
# WHY THE OPERATOR'S EXPORT IS THE WRAPPER
#
# A canvas app rides in a solution as an .msapp plus component metadata that
# the PLATFORM mints at export time. Nothing offline can mint it truthfully.
# So the wrapper is theirs: they import Artifact 1, create ONE BLANK canvas
# app named "Mission Feeding Operations" inside the solution -- ideally adding
# the data sources listed in CANVAS_APP_ASSEMBLY.md step 2 while they are
# there, so the environment mints REAL SharePoint data-source metadata -- save,
# and export. That export contains a genuine, platform-authored CanvasApp
# component whose app is blank.
#
# This script replaces the blank app's CONTENT with this repository's, keeping
# THEIR identity and THEIR environment's scaffolding:
#
#   1. unpack their .msapp with pac (SourceCode layout) -> their .msapr, which
#      carries their identity, their templates, and -- if they added sources --
#      their environment's real data-source metadata
#   2. replace the Src/ yaml with canvas-app/msapp-src (generated, validated
#      against Microsoft's published schema, Power-Fx-parsed)
#   3. pack with pac against THEIR msapr
#   4. put the packed .msapp back at the same path inside their export
#   5. validate the result with validate_solution.py --export, then hash it
#
# Nothing in the output is fabricated: identity and wrapper are the platform's,
# scaffolding is Studio's, content is this repository's, assembly is pac's.
#
# THEN: import the ZIP, open the app for edit once -- Microsoft's packer states
# a SourceCode-packed app is validated by that open -- publish, re-export.
set -euo pipefail

IN="${1:?usage: assemble_full_solution.sh <exported-solution.zip> [out.zip]}"
OUT="${2:-MissionFeedingOperations_1.1.0.zip}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

command -v pac >/dev/null || { echo "pac is not on PATH." >&2; exit 1; }
[ -d "$ROOT/canvas-app/msapp-src/Src" ] || {
    echo "canvas-app/msapp-src missing; run scripts/gen_msapp_source.py" >&2
    exit 1
}

echo "1/6  unzipping the export"
unzip -q "$IN" -d "$WORK/solution"
MSAPP_REL="$(cd "$WORK/solution" && ls CanvasApps/*.msapp 2>/dev/null | head -1)"
[ -n "$MSAPP_REL" ] || {
    echo "No CanvasApps/*.msapp in the export. Create the blank canvas app" >&2
    echo "INSIDE the solution before exporting -- see CANVAS_APP_ASSEMBLY.md." >&2
    exit 1
}
echo "     found $MSAPP_REL"

echo "2/6  unpacking their app (their identity + their scaffolding)"
pac canvas unpack --msapp "$WORK/solution/$MSAPP_REL" \
    --sources "$WORK/src" --layout SourceCode >/dev/null

echo "3/6  replacing the content with this repository's"
rm -rf "$WORK/src/Src"
cp -r "$ROOT/canvas-app/msapp-src/Src" "$WORK/src/Src"

echo "4/6  packing with Microsoft's packer against THEIR reference archive"
pac canvas pack --sources "$WORK/src" \
    --msapp "$WORK/solution/$MSAPP_REL" --layout SourceCode --overwrite \
    | grep -E "succeeded|Error" || true

echo "5/6  re-zipping"
rm -f "$OUT"
( cd "$WORK/solution" && zip -qrX "$OUT" . )

echo "6/6  validating the assembled export"
python3 "$ROOT/scripts/validate_solution.py" --export "$OUT" || {
    echo "VALIDATION FAILED -- do not import this. See the findings above." >&2
    exit 1
}
echo
sha256sum "$OUT"
echo
echo "Import this, open the app for edit once (that open IS the validation"
echo "step Microsoft's packer requires), add any data source still missing,"
echo "save, publish, and re-export -- the re-export is the final artifact."
