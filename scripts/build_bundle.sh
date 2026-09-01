#!/usr/bin/env bash
# Assemble dist/MissionFeedingOperations_1.1.0/ -- the operator hand-off bundle.
#
# Contains everything Path A needs on the .mil side. After the Studio cycle
# the operator drops the two platform re-exports and SHA256SUMS.txt in beside
# these; until then the bundle's status is READY FOR PATH A ASSEMBLY, not a
# validated final release.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/MissionFeedingOperations_1.1.0"

[ -f "$ROOT/dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip" ] \
    || { echo "build Artifact 1 first (scripts/build_release.sh)"; exit 1; }
[ -f "$ROOT/dist/canvas/MissionFeedingOperations_REFERENCE_ONLY.msapp" ] \
    || { echo "build the reference msapp first (scripts/build_msapp.py)"; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT/Artifact1" "$OUT/Canvas" "$OUT/scripts" "$OUT/configuration"

cp "$ROOT/dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip" "$OUT/Artifact1/"
cp "$ROOT/dist/canvas/MissionFeedingOperations_REFERENCE_ONLY.msapp" "$OUT/Canvas/"
cp "$ROOT/scripts/assemble_full_solution.sh" \
   "$ROOT/scripts/validate_final_export.sh" "$OUT/scripts/"
cp "$ROOT"/configuration/*.csv "$ROOT"/configuration/*.json "$OUT/configuration/" 2>/dev/null || true
cp "$ROOT/CANVAS_APP_ASSEMBLY.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/IMPORT_CHECKLIST.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/POST_IMPORT_CHECKLIST.md" \
   "$ROOT/RELEASE_NOTES.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/SECURITY_README.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/KNOWN_LIMITATIONS.md" \
   "$ROOT/FINAL_RELEASE_REPORT.md" \
   "$ROOT/requirements-dev.txt" "$OUT/"

cat > "$OUT/STATUS.md" <<'EOF'
# READY FOR PATH A ASSEMBLY

Not yet a validated final release. It becomes DEV/PILOT RELEASE CANDIDATE only
after the platform cycle completes on the .mil side:

  import Artifact1 → blank wrapper app + 19 sources → bump version to 1.1.0 →
  export → scripts/assemble_full_solution.sh → import candidate → open once in
  Studio (zero errors, Accessibility Checker) → publish → re-export →
  scripts/validate_final_export.sh <re-export>.zip

Then place beside this file:
  MissionFeedingOperations_1.1.0_UNMANAGED.zip
  MissionFeedingOperations_1.1.0_MANAGED.zip
  SHA256SUMS.txt   (sha256sum of both, plus Artifact1)

The Canvas/*.msapp here is REFERENCE / BUILD VALIDATION ONLY -- it carries no
platform-minted identity and is not a deployment artifact.
EOF
echo "bundle: $OUT"
find "$OUT" -type f | wc -l
