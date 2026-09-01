#!/usr/bin/env bash
# Build dist/MissionFeedingOperations_1.0.0_operator-bundle.zip -- the
# EMAIL-SAFE operator bundle.
#
# This is deliberately NOT the self-contained Path A bundle
# (build_bundle.sh). Mail filters reject archives containing script types,
# so this one carries no .sh, .ps1, .py, .exe, or .msapp -- the operator
# runs nothing from it except through Power Automate and Studio. Path A's
# assembler stays in the repository and runs on a CLI workstation from a
# clone; README_OPERATOR.md inside says so.
#
# FAIL-CLOSED ON: the inner Artifact 1 hash differing from the pinned
# release hash, any forbidden file type surviving into the stage, any
# forbidden string in any staged file, any residue inside the inner ZIP.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_ZIP="$ROOT/dist/MissionFeedingOperations_1.0.0_operator-bundle.zip"
STAGE="$(mktemp -d)/MissionFeedingOperations_1.0.0_operator-bundle"
trap 'rm -rf "$(dirname "$STAGE")"' EXIT
mkdir -p "$STAGE"

PINNED="1762f78cb629043d25e65808b3a0f33c72278fd9faed67acf6b84a9aa9513024"
INNER="$ROOT/dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip"

[ -f "$INNER" ] || { echo "build Artifact 1 first (scripts/build_release.sh)"; exit 1; }
ACTUAL="$(sha256sum "$INNER" | cut -d' ' -f1)"
if [ "$ACTUAL" != "$PINNED" ]; then
    echo "STOP: Artifact 1 hashes $ACTUAL, pinned release hash is $PINNED."
    echo "Do not ship a different hash with a note. Find out why it moved."
    exit 1
fi

# --- contents, exactly per the operator-bundle spec -------------------------
cp "$INNER" "$STAGE/"

mkdir -p "$STAGE/configuration"
cp "$ROOT"/configuration/*.csv "$STAGE/configuration/"

mkdir -p "$STAGE/provisioning"
cp "$ROOT/provisioning/sharepoint-schema.json" \
   "$ROOT/provisioning/whatif-report.md" \
   "$ROOT/provisioning/PROVISION-WITHOUT-POWERSHELL.md" \
   "$ROOT/provisioning/manual-column-sheet.csv" \
   "$STAGE/provisioning/"

mkdir -p "$STAGE/canvas-app"
cp -r "$ROOT/canvas-app/src"      "$STAGE/canvas-app/src"
cp -r "$ROOT/canvas-app/formulas" "$STAGE/canvas-app/formulas"

mkdir -p "$STAGE/deployment"
cp "$ROOT/deployment/site-bindings.md" \
   "$ROOT/deployment/deployment-settings.example.json" \
   "$STAGE/deployment/"

cp "$ROOT/CANVAS_APP_ASSEMBLY.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/IMPORT_CHECKLIST.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/POST_IMPORT_CHECKLIST.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/KNOWN_LIMITATIONS.md" \
   "$ROOT/dist/MissionFeedingOperations_1.0.0/SECURITY_README.md" \
   "$STAGE/"

cat > "$STAGE/README_OPERATOR.md" <<'EOF'
# Mission Feeding Operations — operator bundle (email-safe: no scripts, no binaries)
1. This bundle imports and configures the backend and carries the canvas source for reference; you run nothing from it except through Power Automate and Studio.
2. On arrival: `sha256sum MissionFeedingOperations_1.0.0.zip` must read `1762f78cb629043d25e65808b3a0f33c72278fd9faed67acf6b84a9aa9513024`, then verify the rest against `SHA256SUMS.txt`.
3. Provision the 17 SharePoint lists from `provisioning/` (`PROVISION-WITHOUT-POWERSHELL.md`; payloads in `sharepoint-schema.json`).
4. VERIFY every index exists before loading any data — `IMPORT_CHECKLIST.md` explains why this comes first.
5. Seed the configuration CSVs (`configuration/`), then create your real security-mapping rows (the shipped CSV is a sample; every Site_URL ships blank).
6. Import `MissionFeedingOperations_1.0.0.zip` in the DoD maker portal → Solutions → Import.
7. Bind the 3 connection references (service account) and the 24 environment variables (`deployment/site-bindings.md` is the worksheet; `deployment-settings.example.json` the template).
8. Canvas app: Path A (recommended) needs the repository clone and its assembler on a CLI workstation — `CANVAS_APP_ASSEMBLY.md` governs; Path C (paste, no CLI) uses `canvas-app/` here.
9. EOM-02b: copy the imported flow ×3 so all four portfolios are covered, per `POST_IMPORT_CHECKLIST.md`.
10. Enable **EOM-01 only**, run it **twice**, expect **737 rows both times** — then continue the checklist; notifications stay last.
EOF

# --- forbidden file types: none survive ------------------------------------
BAD_TYPES="$(find "$STAGE" -type f \( -name '*.sh' -o -name '*.ps1' -o -name '*.py' \
             -o -name '*.exe' -o -name '*.msapp' -o -name '*.msapr' \) | sed "s|$STAGE/||")"
if [ -n "$BAD_TYPES" ]; then
    echo "STOP: script/binary types in an email-safe bundle:"; echo "$BAD_TYPES"; exit 1
fi

# --- residue sweep: every staged file, plus every entry of the inner ZIP ----
python3 - "$STAGE" "$ROOT" <<'PY'
import os, sys
stage, root = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, "scripts"))
from build_msapp import FORBIDDEN, sweep_archive
bad = []
for base, _dirs, files in os.walk(stage):
    for f in files:
        p = os.path.join(base, f)
        if p.endswith(".zip"):
            bad += [(os.path.relpath(p, stage) + "!" + e, s)
                    for e, s in sweep_archive(p)]
            continue
        text = open(p, encoding="utf-8", errors="ignore").read()
        for line in text.splitlines():
            if "prerelease: allow" in line:
                continue  # governed inline exception, same rule as the scanner
            for s in FORBIDDEN:
                if s in line:
                    bad.append((os.path.relpath(p, stage), s))
if bad:
    print("STOP: residue in the staged bundle:")
    for where, s in bad:
        print(f"  {where}: {s}")
    raise SystemExit(1)
print("residue sweep: clean over the stage and the inner ZIP")
PY

# --- manifest last, then pack ----------------------------------------------
( cd "$STAGE" && find . -type f ! -name SHA256SUMS.txt -print0 \
    | sort -z | xargs -0 sha256sum | sed 's|\./||' > SHA256SUMS.txt )

rm -f "$OUT_ZIP"
( cd "$(dirname "$STAGE")" && zip -qrX "$OUT_ZIP" "$(basename "$STAGE")" )

echo "built $OUT_ZIP"
sha256sum "$OUT_ZIP"
( cd "$STAGE" && find . -type f | sed 's|^\./||' | sort )
