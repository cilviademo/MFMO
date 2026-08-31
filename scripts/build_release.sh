#!/usr/bin/env bash
# Build the release folder from a tag. Reproducible: the same tag always
# produces the same ZIP and the same checksum.
#
# Not from the working tree. The artifact must trace to one commit, or the
# version, the checksum and the code stop describing the same thing once it
# crosses to the .mil side.
set -euo pipefail

TAG="${1:?usage: build_release.sh <tag>}"
VER="${TAG#v}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/MissionFeedingOperations_$VER"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

git -C "$ROOT" rev-parse "$TAG^{commit}" >/dev/null
git -C "$ROOT" archive "$TAG" | tar -x -C "$STAGE"

# Fixed timestamps. git archive stamps files from the commit date, so without
# this the checksum changes every time the commit changes even when not one
# byte of content does -- and a checksum that moves on its own is not evidence
# of anything.
find "$STAGE/solution/src" -exec touch -t 200001010000.00 {} +

mkdir -p "$OUT"
rm -f "$OUT/MissionFeedingOperations_$VER.zip"
( cd "$STAGE/solution" && zip -qrX "$OUT/MissionFeedingOperations_$VER.zip" src )

cp "$STAGE/RELEASE_NOTES.md" "$OUT/"
cp "$STAGE/deployment/DEPENDENCY_MANIFEST.md" "$OUT/"
cp "$STAGE/docs/SECURITY_VERIFICATION.md" "$OUT/SECURITY_README.md"

COMMIT="$(git -C "$ROOT" rev-parse "$TAG^{commit}")"
{
    echo "# Build provenance"
    echo
    echo "version  $VER"
    echo "tag      $TAG"
    echo "commit   $COMMIT"
    echo "built    reproducibly from the tagged commit; timestamps normalised"
    echo
    ( cd "$OUT" && sha256sum ./*.zip ./*.md | sed 's|\./||' )
} > "$OUT/SHA256SUMS.txt"

echo "built $OUT"
sed -n '1,7p' "$OUT/SHA256SUMS.txt"
