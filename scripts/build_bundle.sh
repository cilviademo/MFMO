#!/usr/bin/env bash
# Assemble dist/MissionFeedingOperations_1.1.0/ -- the operator hand-off bundle.
#
# SELF-CONTAINMENT IS THE CONTRACT. The V1 review unzipped the "complete"
# delivery on a clean workstation and found the assembler's inputs and the
# validators' Python modules missing -- the engineering was ready, the
# delivery was not. Everything the bundle's own scripts and checklists
# reference must ship INSIDE it, in the repo-mirroring layout the scripts
# expect (they compute ROOT as scripts/..). tests/test_operator_bundle_
# selfcontained.py is the enforcing gate: it copies this directory to a temp
# location and proves the closure with no repository in sight.
#
# After the Studio cycle the operator drops the two platform re-exports in
# beside these and appends their hashes to SHA256SUMS.txt; until then the
# bundle's status is READY FOR PATH A ASSEMBLY, not a validated final release.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/MissionFeedingOperations_1.1.0"

[ -f "$ROOT/dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip" ] \
    || { echo "build Artifact 1 first (scripts/build_release.sh)"; exit 1; }
[ -f "$ROOT/dist/canvas/MissionFeedingOperations_REFERENCE_ONLY.msapp" ] \
    || { echo "build the reference msapp first (scripts/build_msapp.py)"; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT/Artifact1" "$OUT/Canvas" "$OUT/scripts" "$OUT/configuration" \
         "$OUT/deployment" "$OUT/provisioning" "$OUT/docs" "$OUT/flows"

cp "$ROOT/dist/MissionFeedingOperations_1.0.0/MissionFeedingOperations_1.0.0.zip" "$OUT/Artifact1/"
cp "$ROOT/dist/canvas/MissionFeedingOperations_REFERENCE_ONLY.msapp" "$OUT/Canvas/"

# --- scripts: the transitive closure of what the two entry points need -----
# assemble_full_solution.sh -> validate_solution.py, build_msapp.py (sweep),
# gen_msapp_source.py (the repo-fix instruction it prints);
# validate_final_export.sh -> eom_schema.py, build_msapp.py;
# validate_solution.py -> eom_schema, status_engine, and the canvas tree;
# gen_msapp_source.py -> validate_msapp_source.py -> the two schemas;
# provisioning docs -> gen_rest_payloads.py, verify_provisioning.py.
# The self-containment test recomputes the import closure from the shipped
# files, so a new import that is not shipped fails the suite.
cp "$ROOT/scripts/assemble_full_solution.sh" \
   "$ROOT/scripts/validate_final_export.sh" \
   "$ROOT/scripts/validate_solution.py" \
   "$ROOT/scripts/build_msapp.py" \
   "$ROOT/scripts/eom_schema.py" \
   "$ROOT/scripts/status_engine.py" \
   "$ROOT/scripts/flow_status_expression.py" \
   "$ROOT/scripts/gen_msapp_source.py" \
   "$ROOT/scripts/validate_msapp_source.py" \
   "$ROOT/scripts/gen_rest_payloads.py" \
   "$ROOT/scripts/verify_provisioning.py" \
   "$ROOT/scripts/gen_deployment_settings.py" \
   "$ROOT/scripts/folder_resolver.py" \
   "$ROOT/scripts/generate_expected_items.py" \
   "$ROOT/scripts/routing_dryrun.py" \
   "$ROOT/scripts/canvas_delegation_check.py" \
   "$ROOT/scripts/canvas_reference_check.py" \
   "$ROOT/scripts/neutralise_donor.py" \
   "$ROOT/scripts/canvas_formulas.py" \
   "$ROOT/scripts/vocabulary_guard.py" \
   "$ROOT/scripts/prerelease_scan.py" \
   "$ROOT/scripts/check_design_parity.py" \
   "$ROOT/scripts/build_release.sh" \
   "$ROOT/scripts/build_canvas.sh" \
   "$OUT/scripts/"

# --- canvas source: what the assembler injects and the fix-loop edits ------
mkdir -p "$OUT/canvas-app"
cp -r "$ROOT/canvas-app/msapp-src"  "$OUT/canvas-app/msapp-src"
cp -r "$ROOT/canvas-app/src"        "$OUT/canvas-app/src"
cp -r "$ROOT/canvas-app/formulas"   "$OUT/canvas-app/formulas"
cp -r "$ROOT/canvas-app/donor"      "$OUT/canvas-app/donor"
cp "$ROOT/canvas-app/pa.schema.yaml" \
   "$ROOT/canvas-app/ControlTypeId-1P-controls-enum.schema.yaml" \
   "$OUT/canvas-app/"

# --- provisioning: step 1 of the import checklist ---------------------------
cp "$ROOT"/provisioning/*.ps1 "$ROOT"/provisioning/*.md \
   "$ROOT"/provisioning/*.json "$ROOT"/provisioning/*.csv \
   "$OUT/provisioning/" 2>/dev/null || true

# --- flow definitions: validate_solution.py checks them ---------------------
for d in "$ROOT"/flows/*/; do
    name="$(basename "$d")"
    mkdir -p "$OUT/flows/$name"
    cp "$d/definition.md" "$OUT/flows/$name/" 2>/dev/null || true
done
cp "$ROOT/flows/README.md" "$OUT/flows/" 2>/dev/null || true

cp "$ROOT"/configuration/*.csv "$ROOT"/configuration/*.json "$OUT/configuration/" 2>/dev/null || true

# --- deployment worksheets + the sanitised settings example -----------------
python3 "$ROOT/scripts/gen_deployment_settings.py"
cp "$ROOT/deployment/PREFLIGHT.md" \
   "$ROOT/deployment/DEPENDENCY_MANIFEST.md" \
   "$ROOT/deployment/site-bindings.md" \
   "$ROOT/deployment/LISTS_EXPLAINED.md" \
   "$ROOT/deployment/deployment-settings.example.json" \
   "$OUT/deployment/"

# --- the docs the checklists and validators cite ----------------------------
cp "$ROOT/docs/SHAREPOINT_SCHEMA_MANIFEST.md" \
   "$ROOT/docs/DEPLOYMENT.md" \
   "$ROOT/docs/data-model.md" \
   "$ROOT/docs/MF_EOM_Data_Dictionary.csv" \
   "$ROOT/docs/security-open-issue.md" \
   "$ROOT/docs/accessibility.md" \
   "$ROOT/docs/TEST_MATRIX.md" \
   "$ROOT/docs/government-environment-mode.md" \
   "$ROOT/docs/status-calculation.md" \
   "$ROOT/docs/FIGMA_CANVAS_PARITY.md" \
   "$ROOT/docs/mf-operations-prototype.html" \
   "$OUT/docs/"
mkdir -p "$OUT/docs/handoffs"
cp "$ROOT/docs/handoffs/RECONCILIATION.md" "$OUT/docs/handoffs/" 2>/dev/null || true

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
  Studio (zero errors, delegation review, Accessibility Checker, Live Monitor
  smoke run) → publish → re-export → scripts/validate_final_export.sh
  <re-export>.zip → pac solution check against the DoD checker endpoint.

This bundle is SELF-CONTAINED: the assembler's canvas source, every Python
module its validators import, the full provisioning package, and the docs the
checklists cite all travel inside it. SHA256SUMS.txt is the integrity
manifest for every file here -- verify it before anything else:

  cd into this directory && sha256sum -c SHA256SUMS.txt

After the Studio cycle, place beside this file and append hashes:
  MissionFeedingOperations_1.1.0_UNMANAGED.zip
  MissionFeedingOperations_1.1.0_MANAGED.zip

The Canvas/*.msapp here is REFERENCE / BUILD VALIDATION ONLY -- it carries no
platform-minted identity and is not a deployment artifact.
EOF

# --- integrity manifest, last, covering everything --------------------------
( cd "$OUT" && find . -type f ! -name SHA256SUMS.txt -print0 \
    | sort -z | xargs -0 sha256sum | sed 's|\./||' > SHA256SUMS.txt )

echo "bundle: $OUT"
find "$OUT" -type f | wc -l
