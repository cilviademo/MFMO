#!/usr/bin/env python3
"""
EOM-01 — expected item generation. Reference implementation.

``flows/EOM01-GenerateExpectedItems`` is a transliteration of this module.
The tests run both against the same fixtures.

What it does: for every OPEN reporting period, expand the active requirement
catalogue across the active installations, facilities and contracts, and
produce the persistent checklist rows of ``MF_EOM_Item``.

Three properties matter more than anything else here, and each is tested:

1. **Idempotency.** Running it twice produces no duplicate rows. The
   identity of a row is its ``EOM_Item_Key``, and generation is an upsert
   keyed on that string. A checklist row is persistent; only submissions are
   versioned.
2. **Null, not empty string.** Installation- and Contract-scope rows carry
   ``Facility_ID = None``. An empty string looks the same in a gallery and
   behaves differently in every ``Filter()``, so the distinction is asserted.
3. **Requirements follow the facility, not the installation.** One base can
   run a legacy DFAC and a Food 2.0 cafe. The operating-model filter is
   evaluated per facility, so those two facilities on the same installation
   generate different requirement sets.

Never invent a requirement. This module only ever expands the catalogue; it
has no path that creates a row from an uploaded file.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from status_engine import evaluate, due_and_suspense, DEFAULT_DUE_SOON_WINDOW_DAYS

# Frequency on the requirement selects the reporting period type it expands
# against. Nothing is inferred from the period name.
FREQUENCY_TO_PERIOD_TYPE = {
    "Monthly": "Month",
    "Quarterly": "Quarter",
    "SemiAnnual": "Quarter",
    "Annual": "FiscalYear",
}


def _bool(v):
    return str(v).strip().upper() in ("TRUE", "1", "YES", "Y")


def _date(v):
    v = (v or "").strip()
    return _dt.date.fromisoformat(v[:10]) if v else None


def _null_if_blank(v):
    """Facility_ID is null, not empty string, for installation and contract scope."""
    v = (v or "").strip()
    return v if v else None


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def applies_to_operating_model(requirement, operating_model) -> bool:
    """Empty Applies_To_Operating_Model means every model."""
    raw = (requirement.get("Applies_To_Operating_Model") or "").strip()
    if not raw:
        return True
    allowed = {x.strip() for x in raw.split(";") if x.strip()}
    return operating_model in allowed


def requirement_effective_for_period(requirement, period) -> bool:
    start = _date(requirement.get("Effective_Start_Date"))
    end = _date(requirement.get("Effective_End_Date"))
    period_end = _date(period["Period_End"])
    if start and period_end < start:
        return False
    if end and period_end > end:
        return False
    return True


def item_key(scope, scope_id, requirement_code, period_id) -> str:
    """The compound human-readable key. Also the idempotency key."""
    return f"{scope}|{scope_id}|{requirement_code}|{period_id}"


def _targets(requirement, installations, facilities, contracts):
    """Yield (scope_id, facility_id, installation_id, contract_id, portfolio_id,
    facility_name, installation_name) for one requirement.

    The operating-model filter is evaluated per facility and only for
    Facility-scope requirements: an installation has no operating model and a
    contract may span facilities running different ones.
    """
    scope = requirement["Requirement_Scope"]

    if scope == "Facility":
        for f in facilities:
            if not _bool(f["Is_Active"]):
                continue
            if not applies_to_operating_model(requirement, f["Operating_Model"]):
                continue
            yield (
                f["Facility_ID"], f["Facility_ID"], f["Installation_ID"],
                _null_if_blank(f.get("Contract_ID")), f["Portfolio_ID"],
                f["Title"], f["Installation_Name"],
            )

    elif scope == "Installation":
        for i in installations:
            if not _bool(i["Is_Active"]):
                continue
            yield (
                i["Installation_ID"], None, i["Installation_ID"],
                None, i["Portfolio_ID"], None, i["Title"],
            )

    elif scope == "Contract":
        for c in contracts:
            if not _bool(c["Is_Active"]):
                continue
            yield (
                c["Contract_ID"], None, c["Installation_ID"],
                c["Contract_ID"], c["Portfolio_ID"], None, None,
            )

    else:
        raise ValueError(f"unknown Requirement_Scope {scope!r}")


def generate(
    requirements,
    installations,
    facilities,
    contracts,
    periods,
    *,
    existing=None,
    as_of=None,
    run_id=None,
    period_states=("OPEN",),
    due_soon_window_days=DEFAULT_DUE_SOON_WINDOW_DAYS,
):
    """Return (rows, stats).

    ``existing`` is the current contents of MF_EOM_Item keyed by
    EOM_Item_Key. Rows already present are left alone apart from a status
    re-evaluation: the checklist row is persistent and is never duplicated
    on resubmission, and its EOM_Item_ID never changes.
    """
    as_of = as_of or _dt.date.today()
    run_id = run_id or str(uuid.uuid4())
    existing = existing or {}

    installations_by_id = {i["Installation_ID"]: i for i in installations}
    rows = {}
    stats = {"created": 0, "retained": 0, "skipped_inactive_requirement": 0,
             "skipped_not_effective": 0, "periods": []}

    open_periods = [p for p in periods if p["Period_State"] in period_states]

    for period in open_periods:
        stats["periods"].append(period["Period_ID"])
        for req in requirements:
            if not _bool(req["Is_Active"]):
                stats["skipped_inactive_requirement"] += 1
                continue
            if FREQUENCY_TO_PERIOD_TYPE.get(req["Frequency"]) != period["Period_Type"]:
                continue
            if not requirement_effective_for_period(req, period):
                stats["skipped_not_effective"] += 1
                continue

            due, suspense = due_and_suspense(
                period["Period_End"],
                req["Due_Offset_Days"],
                req["Suspense_Offset_Days"],
            )

            for (scope_id, facility_id, installation_id, contract_id,
                 portfolio_id, facility_name, installation_name) in _targets(
                    req, installations, facilities, contracts):

                key = item_key(req["Requirement_Scope"], scope_id,
                               req["Requirement_Code"], period["Period_ID"])

                prior = existing.get(key)
                if prior:
                    stats["retained"] += 1
                    row = dict(prior)
                    # A generation run never resets a submission or a QC
                    # decision. It only re-evaluates the status of what is
                    # already there.
                    status = evaluate(
                        as_of=as_of,
                        suspense_date=row.get("Suspense_Date") or suspense,
                        requirement_verification_status=req["Verification_Status"],
                        requirement_is_active=True,
                        qc_status=row.get("_qc_status"),
                        has_current_submission=bool(row.get("Current_Submission_ID")),
                        due_soon_window_days=due_soon_window_days,
                    )
                    row.update(status.as_item_fields())
                    rows[key] = row
                    continue

                status = evaluate(
                    as_of=as_of,
                    suspense_date=suspense,
                    requirement_verification_status=req["Verification_Status"],
                    requirement_is_active=True,
                    has_current_submission=False,
                    due_soon_window_days=due_soon_window_days,
                )

                if installation_name is None:
                    inst = installations_by_id.get(installation_id)
                    installation_name = inst["Title"] if inst else None

                row = {
                    "Title": key,
                    "EOM_Item_ID": str(uuid.uuid4()),
                    "Requirement_ID": req["Requirement_ID"],
                    "Requirement_Name": req["Title"],
                    "Requirement_Scope": req["Requirement_Scope"],
                    "Requirement_Verification_Status": req["Verification_Status"],
                    # Null, never empty string, on Installation and Contract scope.
                    "Facility_ID": facility_id,
                    "Facility_Name": facility_name,
                    "Installation_ID": installation_id,
                    "Installation_Name": installation_name,
                    "Contract_ID": contract_id,
                    "Portfolio_ID": portfolio_id,
                    "Reporting_Period_ID": period["Period_ID"],
                    "Fiscal_Year": int(period["Fiscal_Year"]),
                    "Due_Date": due.isoformat(),
                    "Suspense_Date": suspense.isoformat(),
                    "Current_Submission_ID": None,
                    "Current_Version_Number": 0,
                    "Generation_Run_ID": run_id,
                }
                row.update(status.as_item_fields())
                rows[key] = row
                stats["created"] += 1

    return rows, stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config-dir", default="configuration")
    p.add_argument("--as-of", default=None, help="ISO date; defaults to today")
    p.add_argument("--period-state", action="append", default=None,
                   help="repeatable; defaults to OPEN")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    d = args.config_dir
    rows, stats = generate(
        load_csv(os.path.join(d, "requirements.csv")),
        load_csv(os.path.join(d, "installations.sample.csv")),
        load_csv(os.path.join(d, "facilities.sample.csv")),
        load_csv(os.path.join(d, "contracts.sample.csv")),
        load_csv(os.path.join(d, "reporting_periods.sample.csv")),
        as_of=_dt.date.fromisoformat(args.as_of) if args.as_of else None,
        period_states=tuple(args.period_state or ("OPEN",)),
    )

    if args.json:
        print(json.dumps(list(rows.values()), indent=2, default=str))
        return 0

    print(f"periods: {', '.join(stats['periods']) or '(none open)'}")
    print(f"created: {stats['created']}  retained: {stats['retained']}")
    by_scope = {}
    for r in rows.values():
        by_scope[r["Requirement_Scope"]] = by_scope.get(r["Requirement_Scope"], 0) + 1
    for k in sorted(by_scope):
        print(f"  {k:<13} {by_scope[k]:>4}")
    nulls = sum(1 for r in rows.values() if r["Facility_ID"] is None)
    print(f"  rows with null Facility_ID: {nulls}")
    by_status = {}
    for r in rows.values():
        by_status[r["Status_Code"]] = by_status.get(r["Status_Code"], 0) + 1
    for k in sorted(by_status):
        print(f"  {k:<22} {by_status[k]:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
