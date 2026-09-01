#!/usr/bin/env bash
# Build the canvas app from this repository's .pa.yaml source.
#
# WHY THIS NEEDS A SEED
#
# `pac canvas pack` cannot originate an app from YAML. Verified against
# Microsoft's own CLI 2.11.2:
#
#   --layout SourceCode    requires exactly one .msapr file in the sources
#                          directory. The .pa.yaml files are an EDIT LAYER over
#                          that archive, not a substitute for it.
#   --layout Experimental  requires the full PAModel tree -- CanvasManifest.json,
#                          Controls/*.json, Entropy/, Checksum.json -- where the
#                          control tree lives in JSON, not in the YAML.
#
# Either way the seed comes from an app that already exists in an environment.
# That is why this repository ships source and this script, and not an .msapp:
# the missing piece is not effort, it is an artifact only Studio or an
# authenticated environment can mint.
#
# WHAT THIS DOES
#
#   1. downloads the seed app you created in the target environment
#   2. unpacks it
#   3. overlays this repository's .pa.yaml over the unpacked Src/
#   4. packs it back to an .msapp
#   5. leaves the .msapp ready to add to the solution
#
# After step 5, import the .msapp into the solution in the maker portal, or
# `pac solution add-reference`, and export the solution as one ZIP.
#
# Usage:
#   pac auth create --environment <url> --cloud UsGovDod
#   pac canvas list                                  # find the seed app id
#   scripts/build_canvas.sh <app-id> [out.msapp]
set -euo pipefail

APP_ID="${1:?usage: build_canvas.sh <seed-app-id> [out.msapp]}"
OUT="${2:-MissionFeedingOperations.msapp}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

command -v pac >/dev/null || {
    echo "pac not on PATH. Install the Power Platform CLI first." >&2
    exit 1
}

echo "1/5  downloading the seed app"
pac canvas download --name "$APP_ID" --file-name "$WORK/seed.msapp"

echo "2/5  unpacking"
pac canvas unpack --msapp "$WORK/seed.msapp" --sources "$WORK/src" \
    --layout SourceCode

echo "3/5  overlaying this repository's source"
# The seed contributes the archive and the control identities; this repository
# contributes every formula, screen and component. Where they disagree, this
# repository wins -- the .pa.yaml is the code.
mkdir -p "$WORK/src/Src"
cp "$ROOT/canvas-app/src/App.pa.yaml"                "$WORK/src/Src/"
cp "$ROOT"/canvas-app/src/Screens/*.pa.yaml          "$WORK/src/Src/"
mkdir -p "$WORK/src/Src/Components"
cp "$ROOT"/canvas-app/src/Components/*.pa.yaml       "$WORK/src/Src/Components/"

echo "4/5  packing"
pac canvas pack --sources "$WORK/src" --msapp "$OUT" \
    --layout SourceCode --overwrite

echo "5/5  done -> $OUT"
echo
echo "Microsoft's packer prints a warning that a SourceCode-packed app must be"
echo "opened for edit in Studio before it is considered validated. Do that"
echo "before adding it to the solution. If Studio reports an error, fix the"
echo ".pa.yaml in this repository and re-run -- never hand-edit the .msapp."
