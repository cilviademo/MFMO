#!/usr/bin/env python3
"""QRG -> canonical registry.

Reads data/QRG__Scrubbed_.csv and emits:
  configuration/installations.csv
  configuration/facilities.csv
  configuration/qrg-data-quality.csv

Normalization rules, all reversible:
  - Exact duplicate rows are excluded and recorded, never silently dropped.
    107 of 261 source rows are byte-identical.
  - "(2.0)" and "(MAF)" suffixes are stripped to yield one physical
    installation. Both source strings are kept in Source_Installation_String.
    The source encodes operating model into the installation name because it
    has nowhere else to put it; MF_Facility.Operating_Model is that place.
  - "CHARLESTON, JB" style names invert to "JB CHARLESTON" for display.
    Search must still match both forms.
  - "N/A" becomes empty. It is an absence, not a value.
  - POS TERMINALS is preserved verbatim as POS_Terminals_Raw. It is free text.
  - Generation_Enabled ships FALSE for every installation. EOM-01 generates
    only where a human has validated the facility list and flipped it.
  - Protected fields (DODAAC, DODAAD, org boxes, contract IDs) are created
    empty and are never populated outside the authorised environment.
"""
import csv, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ONE mapping, in the schema. A second copy here would be the third time this
# programme has had two vocabularies that must agree and nothing making them.
from eom_schema import normalize_operating_model  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "data", "QRG__Scrubbed_.csv")
OUT = os.path.join(ROOT, "configuration")


def nz(v):
    v = (v or "").strip()
    return "" if v.upper() == "N/A" else v


def slug(s):
    return re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")


def physical(name):
    base = re.sub(r"\s*\((2\.0|MAF)\)$", "", name)
    m = re.match(r"^(.*),\s*(JBP?L?)$", base)
    return f"{m.group(2)} {m.group(1)}" if m else base


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    g = lambda r, c: (r[c] or "").strip()
    seen, inst, fac, dq = set(), {}, [], []

    def issue(kind, row, i, f, detail):
        dq.append([f"DQ-{len(dq)+1:04d}", kind, row, i, f, detail])

    for n, r in enumerate(rows, start=2):
        sig = tuple(g(r, k) for k in r)
        if sig in seen:
            issue("Exact duplicate row", n, g(r, "INSTALLATION"),
                  g(r, "FACILITY NAME"),
                  "Byte-identical to an earlier row. Excluded from the registry.")
            continue
        seen.add(sig)

        raw = g(r, "INSTALLATION")
        iid = slug(physical(raw))
        if iid not in inst:
            inst[iid] = dict(
                Installation_ID=iid, Installation_Name=physical(raw),
                Source_Installation_String=raw, Location=g(r, "LOCATION"),
                Portfolio_ID=nz(g(r, "PORTFOLIO")), MAJCOM=g(r, "MAJCOM"),
                Component="Active",
                # Blank: the generator has no site to point at, and a .mil URL
                # in source is a destination leak. An administrator sets it
                # later as a convenience link. It is never used for routing.
                EOM_Folder_URL="",
                Generation_Enabled="FALSE",
                Registry_Validated_By="", Registry_Validated_Date="",
                Source_System="Mission Feeding QRG", Needs_Review_Flag="FALSE",
                DODAAC="", DODAAD="", Org_Box_Email="", Official_POC_UPN="",
                Active_Flag="TRUE")
        elif raw not in inst[iid]["Source_Installation_String"].split(";"):
            inst[iid]["Source_Installation_String"] += ";" + raw

        if not nz(g(r, "PORTFOLIO")):
            inst[iid]["Needs_Review_Flag"] = "TRUE"
            issue("Missing portfolio", n, raw, g(r, "FACILITY NAME"),
                  "Portfolio blank. Left NULL — do not assign.")

        fname = g(r, "FACILITY NAME") or "UNNAMED"
        fid = f"{iid}|{slug(fname)}"
        dupes = sum(1 for x in fac if x["Facility_ID"].split("_")[0] == fid
                    or x["Facility_ID"] == fid)
        if dupes:
            fid = f"{fid}_{dupes+1:02d}"

        # NORMALISED AT IMPORT, with the raw value preserved.
        #
        # The QRG says `Legacy`, `Food 2.0`, `MAFFO`, `Deployed / Field
        # Feeding`. The requirement catalogue filters on `Legacy/APF`,
        # `Food 2.0`, `MAFFO/MAF`, `AOR/CDS`. Emitting the raw value here means
        # every facility-scope requirement matches nothing and EOM-01 reports
        # "created 0" as success -- which is exactly what happened once, and
        # cost a month. scripts/vocabulary_guard.py now raises on it, but a
        # generator that produces data its own consumer rejects is still a bug.
        raw_model = nz(g(r, "FEEDING TYPE"))
        model = normalize_operating_model(raw_model) or ""
        if not raw_model:
            issue("Missing feeding type", n, raw, fname,
                  "Cannot determine EOM applicability. No package generated.")
        elif not model:
            issue("Unmapped feeding type", n, raw, fname,
                  f"QRG says {raw_model!r}, which is not in "
                  "eom_schema.QRG_OPERATING_MODEL_MAP. Add the mapping rather "
                  "than widening the requirement filter.")

        fac.append(dict(
            Facility_ID=fid, Installation_ID=iid, Facility_Name=fname,
            Designation=nz(g(r, "DESIGNATION")), Unit=g(r, "UNIT"),
            # The QRG carries no facility type for any row. The column exists
            # so a base can confirm one during onboarding; until it does,
            # facility_type_applies() treats unknown as MATCHING, so a
            # type-scoped requirement still generates and the facility is
            # reported as needing a type. Under-generating is worse than
            # over-generating: an extra row is visible and can be waived.
            Facility_Type="",
            Operating_Model=model,
            Source_Operating_Model=raw_model,
            Program_Type=nz(g(r, "PROGRAM TYPE")),
            Contract_Type=nz(g(r, "CONTRACT TYPE")),
            Primary_PV=nz(g(r, "PRIMARY PV")),
            POS_Terminals_Raw=nz(g(r, "POS TERMINALS")),
            POC_Display_Name=nz(g(r, "POC")),
            In_R1_Scope="TRUE" if model == "Legacy/APF" else "FALSE",
            Source_Row=n, Source_System="Mission Feeding QRG",
            Facility_DODAAC="", Contract_ID="", Active_Flag="TRUE"))

    for iid, v in inst.items():
        strings = v["Source_Installation_String"].split(";")
        if len(strings) > 1:
            v["Needs_Review_Flag"] = "TRUE"
            issue("Split installation", 0, v["Installation_Name"], "",
                  f"Source carries {len(strings)} installation strings for one "
                  f"base: {strings}. Operating model belongs on the facility.")

    os.makedirs(OUT, exist_ok=True)

    def write(name, data, cols):
        # utf-8 without a BOM. Every reader in the tree opens with utf-8-sig,
        # which accepts either -- but a BOM in a tracked file shows up as a
        # phantom character in the first column name of every diff.
        with open(os.path.join(OUT, name), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)

    write("installations.csv", list(inst.values()),
          list(next(iter(inst.values())).keys()))
    write("facilities.csv", fac, list(fac[0].keys()))
    with open(os.path.join(OUT, "qrg-data-quality.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Issue_ID", "Issue_Type", "Source_Row", "Installation",
                    "Facility", "Detail"])
        w.writerows(dq)

    legacy = [f for f in fac if f["In_R1_Scope"] == "TRUE"]
    print(f"{len(rows)} source rows -> {len(seen)} distinct")
    print(f"installations.csv    {len(inst)}")
    print(f"facilities.csv       {len(fac)}")
    print(f"qrg-data-quality.csv {len(dq)} issues")
    n_inst = len({f["Installation_ID"] for f in legacy})
    print(f"\nR1 Legacy scope: {n_inst} installations, {len(legacy)} facilities")
    print("All Generation_Enabled = FALSE. Validate a base before flipping it.")


if __name__ == "__main__":
    main()
