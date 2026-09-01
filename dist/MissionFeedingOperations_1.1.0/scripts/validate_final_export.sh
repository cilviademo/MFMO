#!/usr/bin/env bash
# Validate the solution Power Platform re-exported after the Studio cycle.
#
#   scripts/validate_final_export.sh <re-exported-solution.zip> [expected-version]
#
# This runs against the TRUE release artifact -- the platform's own re-export
# after import, Studio open, publish. The locally assembled candidate is never
# stronger evidence than this export; this validator is what promotes it.
#
# Every row prints PASS or FAIL, or NOT TESTABLE LOCALLY where only a tenant
# can answer. NOT TESTABLE LOCALLY is never converted into PASS.
set -euo pipefail
IN="${1:?usage: validate_final_export.sh <solution.zip> [expected-version]}"
EXPECTED_VERSION="${2:-1.1.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$IN" "$EXPECTED_VERSION" "$ROOT" <<'PY'
import io, json, re, sys, zipfile, os
zip_path, expected_version, root = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(root, "scripts"))
import eom_schema as S
from build_msapp import sweep_archive, FORBIDDEN

FAILS = []
def row(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    if not ok:
        FAILS.append(label)
    print(f"  {mark:4} {label:44} {detail}")
def ntl(label, detail):
    print(f"  NTL  {label:44} {detail}")

z = zipfile.ZipFile(zip_path)
names = [n.replace("\\", "/") for n in z.namelist()]
cust = next((z.read(n) for n in z.namelist()
             if n.replace("\\", "/").endswith("Customizations.xml")), b"").decode("utf-8", "ignore")
solxml = next((z.read(n) for n in z.namelist()
               if n.replace("\\", "/").endswith("Solution.xml")), b"").decode("utf-8", "ignore")

print(f"Final export validation - {os.path.basename(zip_path)}")
print("=" * 62)

msapps = [n for n in names if n.lower().endswith(".msapp")]
row("Canvas App present", len(msapps) >= 1, msapps[:1])
row("Expected Canvas App count = 1", len(msapps) == 1, f"{len(msapps)} found")

app_names, app_sources, app_text = set(), [], ""
if len(msapps) == 1:
    inner = zipfile.ZipFile(io.BytesIO(z.read(
        [n for n in z.namelist() if n.replace("\\", "/") == msapps[0]][0])))
    for n in inner.namelist():
        norm = n.replace("\\", "/")
        blob = inner.read(n)
        app_text += blob.decode("utf-8", "ignore")
        m = re.search(r"(scr[A-Za-z]+)", os.path.basename(norm))
        if m and norm.startswith(("Src/", "Src\\")):
            app_names.add(m.group(1))
        if norm == "References/DataSources.json":
            app_sources = [d.get("Name", "") for d in
                           json.loads(blob).get("DataSources", [])]
    comps = {re.search(r"(cmp[A-Za-z]+)", os.path.basename(n)).group(1)
             for n in inner.namelist()
             if re.search(r"cmp[A-Za-z]+", os.path.basename(n))}
    row("16 screens", len(app_names) == 16, f"{len(app_names)} found")
    row("6 components", len(comps) == 6, f"{len(comps)} found")
    # The wrapper app is created with a default blank screen. Path A replaces
    # Src/ wholesale; if a default screen survives, the replacement was not
    # complete and the app opens on an unstyled blank page instead of the
    # design (FIGMA_CANVAS_PARITY.md - visual source must survive assembly).
    default_screens = [os.path.basename(n) for n in inner.namelist()
                       if re.match(r"^Screen\d+\.pa\.yaml$",
                                   os.path.basename(n.replace("\\", "/")))]
    row("No default Screen1 survives", not default_screens,
        default_screens or "Src/ fully replaced")

    required = [l.title for l in S.LISTS]
    missing = [r for r in required if r not in app_sources]
    sq = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    if not any(sq(n) == "office365users" for n in app_sources):
        missing.append("Office365Users")
    flow = [n for n in app_sources if "eom02" in sq(n)]
    if not flow:
        missing.append("EOM-02 flow")
    row("19 expected data sources", not missing, missing or "all bound")
    row("EOM-02 flow reference resolved",
        bool(flow) and sq(flow[0]) == "eom02submission",
        flow[0] if flow else "absent")

wf = re.findall(r"<Workflow WorkflowId=", cust)
row("5 workflows", len(wf) == 5, f"{len(wf)} found")
states = re.findall(r"<StateCode>(\d)</StateCode>", cust)
row("All workflows import disabled", bool(states) and set(states) == {"0"},
    f"StateCodes {sorted(set(states))}")
ev = re.findall(r"<environmentvariabledefinition[^>]*schemaname=", cust)
row("24 environment variables", len(ev) == 24, f"{len(ev)} found")
defaults = re.findall(r"<defaultvalue>([^<]*)</defaultvalue>", cust)
row("All environment defaults blank", all(not d.strip() for d in defaults),
    f"{sum(1 for d in defaults if d.strip())} populated")
cr = re.findall(r"<connectionreference[^>]*connectionreferencelogicalname=", cust)
row("3 connection references", len(cr) == 3, f"{len(cr)} found")

vm = re.search(r"<Version>([^<]+)</Version>", solxml)
row("Solution version matches release",
    bool(vm) and vm.group(1) == expected_version,
    vm.group(1) if vm else "unreadable")

leaks = sweep_archive(zip_path)
row("No donor/commercial/SAS/.mil residue", not leaks,
    [f"{e}:{b}" for e, b in leaks[:3]] or f"{len(FORBIDDEN)} strings checked")
row("No donor AppName", "almtestapp" not in app_text.lower()
    and "asmanyentities" not in app_text.lower())
row("No donor image resources", "stickeromg" not in app_text.lower())
rc = re.findall(r'<RootComponent type="(\d+)"', solxml)
row("RootComponents present", len(rc) > 0,
    {t: rc.count(t) for t in sorted(set(rc))})
row("Canvas RootComponent (type 300) present", "300" in rc,
    "platform-minted" if "300" in rc else "MISSING - not a canvas export")
row("Schema totals 17/286/90",
    (len(S.LISTS), sum(len(l.columns) for l in S.LISTS),
     sum(1 for l in S.LISTS for c in l.columns if c.indexed)) == (17, 286, 90))

ntl("App opens and renders", "only Studio/tenant can answer")
ntl("Flows execute against SharePoint", "only the tenant can answer")
ntl("Data-layer security enforcement", "docs/security-open-issue.md is OPEN")

print()
if FAILS:
    print(f"FAILED {len(FAILS)} check(s): " + "; ".join(FAILS))
    sys.exit(1)
print("Structural validation PASS. NOT TESTABLE LOCALLY rows remain exactly")
print("that. This export is now the canonical Canvas-inclusive artifact;")
print("record its SHA-256 in the release report.")
PY
echo
sha256sum "$IN"
