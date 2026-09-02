#!/usr/bin/env bash
# Regenerate and package the blank-slate provisioning kit:
#   dist/MFOps_blankslate-provisioning_1.0/     (tracked, generated)
#   dist/MFOps_blankslate-provisioning_1.0.zip  (tracked, email-safe)
# FAIL-CLOSED ON: script/binary types in the kit, FORBIDDEN strings,
# the 17/286/90 totals (the generator asserts them itself).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIT="$ROOT/dist/MFOps_blankslate-provisioning_1.0"

python3 "$ROOT/scripts/gen_blankslate_kit.py"

BAD="$(find "$KIT" -type f \( -name '*.sh' -o -name '*.ps1' -o -name '*.py' \
       -o -name '*.exe' -o -name '*.msapp' -o -name '*.msapr' \) | sed "s|$KIT/||")"
[ -z "$BAD" ] || { echo "STOP: script/binary types:"; echo "$BAD"; exit 1; }

python3 - "$KIT" "$ROOT" <<'PY'
import os, sys
kit, root = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, "scripts"))
from build_msapp import FORBIDDEN
bad = []
for base, _d, files in os.walk(kit):
    for f in files:
        for line in open(os.path.join(base, f), encoding="utf-8",
                         errors="ignore").read().splitlines():
            if "prerelease: allow" in line:
                continue
            for s in FORBIDDEN:
                if s in line:
                    bad.append((f, s))
if bad:
    print("STOP: residue:", bad)
    raise SystemExit(1)
print("residue sweep: clean over the blank-slate kit")
PY

( cd "$KIT" && find . -type f ! -name SHA256SUMS.txt -print0 \
    | sort -z | xargs -0 sha256sum | sed 's|\./||' > SHA256SUMS.txt )

rm -f "$ROOT/dist/MFOps_blankslate-provisioning_1.0.zip"
( cd "$ROOT/dist" && zip -qrX "$ROOT/dist/MFOps_blankslate-provisioning_1.0.zip" \
    MFOps_blankslate-provisioning_1.0 )
sha256sum "$ROOT/dist/MFOps_blankslate-provisioning_1.0.zip"
