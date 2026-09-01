#!/usr/bin/env bash
# Package dist/MissionFeedingOperations_1.1.0/ as MAIN_DOWNLOAD.zip at the
# repository root -- the tracked, easy-access copy of the operator bundle on
# main. Run this LAST in a release round, after every document is final, so
# the zip's contents are byte-identical to the tree that commits it (the
# archive scanner dedupes tree-identical entries; a stale copy re-fires the
# residue rules on the report's quoted specimens, by design).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/dist/MissionFeedingOperations_1.1.0"
[ -d "$SRC" ] || { echo "build the bundle first (scripts/build_bundle.sh)"; exit 1; }
[ -f "$SRC/Canvas/MissionFeedingOperations_REFERENCE_ONLY.msapp" ] \
    || { echo "bundle has no msapp; rebuild it before packaging the download"; exit 1; }
rm -f "$ROOT/MAIN_DOWNLOAD.zip"
( cd "$ROOT/dist" && zip -qrX "$ROOT/MAIN_DOWNLOAD.zip" MissionFeedingOperations_1.1.0 )
sha256sum "$ROOT/MAIN_DOWNLOAD.zip"
