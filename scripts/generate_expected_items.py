#!/usr/bin/env python3
"""
EOM-01 — Expected Package Generator. Reference implementation.

`flows/EOM01-ExpectedPackage/definition.md` is the implementation spec; this
module is the executable version of it, and `tests/test_eom01.py` runs both
against the same seeds.

For a reporting period, expand the active requirement catalogue across the
active installations, facilities and contracts and upsert one `MF_EOM_Item`
per obligation.

Three properties matter more than anything else, and each is tested:

1. **Idempotent.** Identity is the deterministic `EOM_Item_ID`. Re-running for
   a period that already has items must not change the row count. The
   checklist row is persistent; only submissions are versioned.

2. **`Facility_ID` is null, not empty string,** for Installation and Contract
   scope. The Power BI relationship and the app's LookUp both depend on it,
   and the two look identical in a gallery while behaving differently in every
   `Filter()`.

3. **Requirements follow the facility.** `Operating_Model` lives at facility
   grain: Lackland runs a legacy DFAC and a Food 2.0 cafe, and they generate
   different requirement sets. An installation has no operating model, and a
   contract may span facilities running different ones, so the model filter is
   applied at facility scope only.

Never invent a requirement. This module only expands the catalogue; it has no
path that creates a row from an uploaded file.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from status_engine import item_status, due_date_for  # noqa: E402

# Frequency decides whether a requirement expands in this period. Nothing is
# inferred from the period's name.
#   Monthly     always
#   Quarterly   period month in {12, 3, 6, 9}   (federal fiscal quarters)
#   Semiannual  {3, 9}
#   Annual      {9}                             (fiscal year end)
#   Conditional never auto-generated
QUARTER_MONTHS = {12, 3, 6, 9}
SEMIANNUAL_MONTHS = {3, 9}
ANNUAL_MONTHS = {9}


def _bool(v):
    return str(v).strip().upper() in ("TRUE", "1", "YES", "Y")


def _null_if_blank(v):
    """Null, never empty string. The distinction is load-bearing."""
    v = (v or "").strip()
    return v or None


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def frequency_applies(frequency: str, period: str) -> bool:
    month = int(period.split("-")[1])
    if frequency == "Monthly":
        return True
    if frequency == "Quarterly":
        return month in QUARTER_MONTHS
    if frequency == "Semiannual":
        return month in SEMIANNUAL_MONTHS
    if frequency == "Annual":
        return month in ANNUAL_MONTHS
    if frequency == "Conditional":
        return False
    raise ValueError(f"unknown Frequency {frequency!r}")


def model_applies(requirement, operating_model: str) -> bool:
    """'All' applies regardless of the facility's model."""
    applicable = (requirement.get("Applicable_Model") or "").strip()
    return applicable == "All" or applicable == operating_model


def facility_type_applies(requirement, facility_type: str) -> bool:
    """Blank means every type. Kiosks rarely file a 1119."""
    raw = (requirement.get("Applicable_Facility_Types") or "").strip()
    if not raw:
        return True
    return facility_type in {t.strip() for t in raw.split(";") if t.strip()}


def item_id_for(period, scope_id, requirement_id) -> str:
    """The deterministic key that makes generation idempotent.

    period|<facility or contract or installation>|requirement
    """
    return f"{period}|{scope_id}|{requirement_id}"


def item_key_for(installation_code, scope_label, period, document_code) -> str:
    """Human-readable compound key: LACKLAND|BLDG1234|2026-10|1119."""
    return f"{installation_code}|{scope_label}|{period}|{document_code}"


def _short(identifier: str) -> str:
    """Trailing segment of an ID, for the human-readable key."""
    return (identifier or "").split("-")[-1].upper()


def _targets(requirement, installations, facilities):
    """Yield one tuple per obligation the requirement creates this period.

    (scope_id, facility_id, installation_id, contract_id, facility_row)
    """
    scope = requirement["Requirement_Scope"]
    active_facilities = [f for f in facilities if _bool(f["Active_Flag"])]
    active_installations = [i for i in installations if _bool(i["Active_Flag"])]
    installation_ids = {i["Installation_ID"] for i in active_installations}

    if scope == "Facility":
        for f in active_facilities:
            if f["Installation_ID"] not in installation_ids:
                continue
            if not model_applies(requirement, f["Operating_Model"]):
                continue
            if not facility_type_applies(requirement, f["Facility_Type"]):
                continue
            yield (f["Facility_ID"], f["Facility_ID"], f["Installation_ID"],
                   _null_if_blank(f.get("Contract_ID")), f)

    elif scope == "Installation":
        # Installations having AT LEAST ONE active facility whose model
        # matches. A base with no Food 2.0 operation does not owe a Food 2.0
        # installation return.
        for i in active_installations:
            mine = [f for f in active_facilities
                    if f["Installation_ID"] == i["Installation_ID"]
                    and model_applies(requirement, f["Operating_Model"])]
            if not mine:
                continue
            yield (i["Installation_ID"], None, i["Installation_ID"], None, None)

    elif scope == "Contract":
        # One item per contract. A contractor invoice may cover several
        # facilities under one CLIN, which is why the obligation attaches to
        # the contract and Facility_ID is null.
        seen = {}
        for f in active_facilities:
            cid = _null_if_blank(f.get("Contract_ID"))
            if not cid or f["Installation_ID"] not in installation_ids:
                continue
            if not model_applies(requirement, f["Operating_Model"]):
                continue
            seen.setdefault(cid, f)          # installation of the first facility
        for cid, f in seen.items():
            yield (cid, None, f["Installation_ID"], cid, None)

    else:
        raise ValueError(f"unknown Requirement_Scope {scope!r}")


def generate(
    requirements,
    installations,
    facilities,
    period,
    *,
    existing=None,
    today=None,
    run_id=None,
):
    """Return (rows_by_item_id, stats).

    ``existing`` is the current contents of MF_EOM_Item keyed by EOM_Item_ID.
    A row already present is left alone: a generation run never resets a
    submission, a QC decision, a waiver or a moved correction suspense.
    """
    today = today or _dt.date.today()
    existing = existing or {}
    installations_by_id = {i["Installation_ID"]: i for i in installations}
    facilities_by_id = {f["Facility_ID"]: f for f in facilities}

    rows = {}
    stats = {"created": 0, "retained": 0, "skipped_inactive": 0,
             "skipped_frequency": 0, "period": period,
             "facilities_with_no_requirements": []}

    covered_facilities = set()

    for req in requirements:
        if not _bool(req["Active_Flag"]):
            stats["skipped_inactive"] += 1
            continue
        if not frequency_applies(req["Frequency"], period):
            stats["skipped_frequency"] += 1
            continue

        due = due_date_for(period, req.get("Due_Day") or 1,
                           req.get("Due_Offset_Months") or 1)

        for scope_id, facility_id, installation_id, contract_id, facility in \
                _targets(req, installations, facilities):

            item_id = item_id_for(period, scope_id, req["Requirement_ID"])
            if facility_id:
                covered_facilities.add(facility_id)

            if item_id in existing:
                stats["retained"] += 1
                rows[item_id] = dict(existing[item_id])
                continue

            installation = installations_by_id.get(installation_id, {})
            scope_label = (_short(facility_id) if facility_id
                           else _short(contract_id) if contract_id
                           else "INSTALLATION")

            status = item_status(
                today=today,
                due_date=due,
                required_flag=_bool(req["Required_Flag"]),
                waived_flag=False,
                authority_status=req["Authority_Status"],
                received_flag=False,
                qc_status=None,
            )

            row = {
                "EOM_Item_ID": item_id,
                "EOM_Item_Key": item_key_for(
                    _short(installation_id), scope_label, period, req["Document_Code"]),
                "Portfolio_ID": installation.get("Portfolio_ID"),
                "Installation_ID": installation_id,
                # Null, never empty string, for Installation and Contract scope.
                "Facility_ID": facility_id,
                "Contract_ID": contract_id,
                "Reporting_Period": period,
                "Requirement_ID": req["Requirement_ID"],
                "Requirement_Scope": req["Requirement_Scope"],
                # Denormalized: the status engine's rule 2 reads it and a
                # lookup would not delegate.
                "Authority_Status": req["Authority_Status"],
                "Required_Flag": _bool(req["Required_Flag"]),
                "Due_Date": due.isoformat(),
                "Current_Submission_ID": None,
                "Received_Flag": False,
                "Received_DateTime": None,
                "Days_Late": None,
                "On_Time_Flag": None,
                "Last_Reconciled_DateTime": None,
                "Exception_Flag": False,
                "Correction_Due": None,
                "Waived_Flag": False,
                "Waiver_Reason": None,
            }
            row.update(status.as_item_fields())
            rows[item_id] = row
            stats["created"] += 1

    # A facility with no applicable requirement set is a configuration gap, not
    # a facility with nothing to do. Surface it rather than letting it sit
    # silently green.
    for f in facilities:
        if _bool(f["Active_Flag"]) and f["Facility_ID"] not in covered_facilities:
            stats["facilities_with_no_requirements"].append(f["Facility_ID"])

    return rows, stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config-dir", default="configuration")
    p.add_argument("--period", default=None, help="YYYY-MM; defaults to last month")
    p.add_argument("--today", default=None, help="ISO date; defaults to today")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    today = _dt.date.fromisoformat(args.today) if args.today else _dt.date.today()
    if args.period:
        period = args.period
    else:
        first = today.replace(day=1)
        period = (first - _dt.timedelta(days=1)).strftime("%Y-%m")

    d = args.config_dir
    rows, stats = generate(
        load_csv(os.path.join(d, "requirements.csv")),
        load_csv(os.path.join(d, "installations.sample.csv")),
        load_csv(os.path.join(d, "facilities.sample.csv")),
        period,
        today=today,
    )

    if args.json:
        print(json.dumps(list(rows.values()), indent=2, default=str))
        return 0

    print(f"period {period}  (as of {today})")
    print(f"created {stats['created']}, retained {stats['retained']}")
    by_scope, by_status = {}, {}
    for r in rows.values():
        by_scope[r["Requirement_Scope"]] = by_scope.get(r["Requirement_Scope"], 0) + 1
        by_status[r["Final_Status"]] = by_status.get(r["Final_Status"], 0) + 1
    for k in sorted(by_scope):
        print(f"  {k:<14}{by_scope[k]:>4}")
    print(f"  {'null Facility_ID':<14}{sum(1 for r in rows.values() if r['Facility_ID'] is None):>4}")
    for k in sorted(by_status):
        print(f"  {k:<22}{by_status[k]:>4}")
    if stats["facilities_with_no_requirements"]:
        print("  facilities with NO applicable requirements: "
              + ", ".join(stats["facilities_with_no_requirements"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
