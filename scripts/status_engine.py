#!/usr/bin/env python3
"""
MissionFeedingOperations — the status engine.

One engine, one evaluation. It returns
``{status, code, label, actionOwner, actionRequired}`` plus the two rollup
flags the Power BI fact carries. Nothing anywhere else in this solution may
derive a label, a colour or a completeness flag independently of the code.

This module is the reference implementation. ``canvas-app/formulas/StatusEngine.fx``
is a line-for-line transliteration of ``evaluate()`` into Power Fx and
``flows/EOM03-StatusFact`` applies the same ordering server-side. The three
are held in agreement by ``tests/test_status_engine.py``, which runs the same
fixtures through this module and asserts the Power Fx and flow definitions
still contain the same ordered branches.

Rules that are not negotiable:

  * Status is calculated, never chosen. No colour picker exists anywhere.
  * Status is never colour-only. Every code carries a label.
  * An UNVERIFIED requirement never drives Red. It goes Gray.
  * Blue means "not due yet". Gray means "not applicable, waived,
    superseded, or provisional". Those are different facts about the world
    and a four-state model conflates them.
  * No percentage is ever stored. Rollups are computed from the two
    boolean flags at read time.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

# --- the five visual states ------------------------------------------------
BLUE = "Blue"
AMBER = "Amber"
RED = "Red"
GREEN = "Green"
GRAY = "Gray"

# --- action owners ---------------------------------------------------------
FACILITY = "Facility"
REVIEWER = "Reviewer"
PROGRAM = "Program"
NONE = "None"

# --- the eleven codes, in evaluation order --------------------------------
# Each entry is (Final_Status, Status_Semantic, Action_Owner_Role, Action_Required).
CODES = {
    "NOT_APPLICABLE":      (GRAY,  "Not applicable",                 NONE,     False),
    "WAIVED":              (GRAY,  "Waived",                         NONE,     False),
    "SUPERSEDED":          (GRAY,  "Superseded",                     NONE,     False),
    "ACCEPTED":            (GREEN, "Accepted",                       NONE,     False),
    "RETURNED":            (AMBER, "Returned for correction",        FACILITY, True),
    "IN_REVIEW":           (AMBER, "In review",                      REVIEWER, True),
    "SUBMITTED":           (AMBER, "Submitted - awaiting review",    REVIEWER, True),
    "OVERDUE":             (RED,   "Overdue",                        FACILITY, True),
    "PROVISIONAL_OVERDUE": (GRAY,  "Past suspense - requirement unverified", PROGRAM, True),
    "DUE_SOON":            (AMBER, "Due soon",                       FACILITY, True),
    "NOT_DUE":             (BLUE,  "Not due yet",                    FACILITY, False),
}

# Rollup semantics. A colour rollup calls [ACCEPTED, NOT_DUE, NOT_DUE]
# Complete; a semantic rollup does not. Only ACCEPTED counts toward the
# numerator, and the four codes that describe an obligation nobody owes are
# excluded from the denominator entirely rather than counted as done.
COMPLETE_CODES = frozenset({"ACCEPTED"})
OUT_OF_DENOMINATOR_CODES = frozenset(
    {"NOT_DUE", "WAIVED", "NOT_APPLICABLE", "SUPERSEDED"}
)

DEFAULT_DUE_SOON_WINDOW_DAYS = 7


@dataclass(frozen=True)
class StatusResult:
    """The single return value of the single evaluation."""

    code: str
    status: str            # Final_Status, one of the five visual states
    label: str             # Status_Semantic
    actionOwner: str
    actionRequired: bool

    @property
    def is_complete(self) -> bool:
        return self.code in COMPLETE_CODES

    @property
    def is_in_denominator(self) -> bool:
        return self.code not in OUT_OF_DENOMINATOR_CODES

    def as_item_fields(self) -> dict:
        """The four columns MF_EOM_Item stores, and nothing else."""
        return {
            "Status_Code": self.code,
            "Status_Semantic": self.label,
            "Final_Status": self.status,
            "Action_Owner_Role": self.actionOwner,
            "Action_Required": self.actionRequired,
        }

    def as_fact_fields(self) -> dict:
        d = self.as_item_fields()
        d["Is_Complete"] = self.is_complete
        d["Is_In_Denominator"] = self.is_in_denominator
        return d


def _result(code: str) -> StatusResult:
    status, label, owner, required = CODES[code]
    return StatusResult(code=code, status=status, label=label,
                        actionOwner=owner, actionRequired=required)


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    return _dt.date.fromisoformat(str(value)[:10])


def evaluate(
    *,
    as_of,
    suspense_date,
    requirement_verification_status="UNVERIFIED",
    requirement_is_active=True,
    qc_status=None,
    has_current_submission=False,
    waived=False,
    superseded=False,
    applies_to_facility=True,
    due_soon_window_days=DEFAULT_DUE_SOON_WINDOW_DAYS,
) -> StatusResult:
    """Evaluate one checklist row. Ordered, total, and side-effect free.

    ``qc_status`` is the QC state of the *current version* submission, or
    None when no submission exists. Superseded versions never influence the
    item's status; that is what ``Is_Current_Version`` is for.
    """
    as_of = _as_date(as_of)
    suspense_date = _as_date(suspense_date)

    # 1. The obligation does not exist for this row.
    if not applies_to_facility or not requirement_is_active or \
            requirement_verification_status == "RETIRED":
        return _result("NOT_APPLICABLE")

    # 2. The obligation existed and was released.
    if waived:
        return _result("WAIVED")

    # 3. The obligation was replaced by another row.
    if superseded:
        return _result("SUPERSEDED")

    # 4-7. A current submission exists. Its QC state is the item's state.
    if has_current_submission and qc_status:
        if qc_status == "ACCEPTED":
            return _result("ACCEPTED")
        if qc_status == "RETURNED":
            return _result("RETURNED")
        if qc_status == "IN_REVIEW":
            return _result("IN_REVIEW")
        if qc_status == "PENDING":
            return _result("SUBMITTED")
        raise ValueError(f"unknown qc_status {qc_status!r}")

    # 8. Nothing submitted. Time decides, and verification decides the colour.
    if suspense_date is None:
        return _result("NOT_DUE")

    if as_of > suspense_date:
        # An UNVERIFIED requirement never drives Red. All twelve seeded
        # requirements are provisional today, so this is the default path.
        if requirement_verification_status == "VERIFIED":
            return _result("OVERDUE")
        return _result("PROVISIONAL_OVERDUE")

    if (suspense_date - as_of).days <= due_soon_window_days:
        return _result("DUE_SOON")

    return _result("NOT_DUE")


# --------------------------------------------------------------------------
# Rollups. Computed, never stored.
# --------------------------------------------------------------------------

def rollup(results, visible_predicate=None) -> dict:
    """Roll up a sequence of StatusResult (or Status_Code strings).

    ``visible_predicate`` is applied first. A facility user must not receive
    an installation figure derived from their neighbours' rows, so the
    caller passes the same visibility filter the app and RLS apply, and the
    rollup is computed over what the viewer may actually see.

    Returns counts and a complete/denominator pair. The percentage is
    computed by the caller for display and is never persisted.
    """
    rows = []
    for r in results:
        if isinstance(r, str):
            r = _result(r)
        if visible_predicate is not None and not visible_predicate(r):
            continue
        rows.append(r)

    denominator = [r for r in rows if r.is_in_denominator]
    complete = [r for r in denominator if r.is_complete]

    by_code = {}
    by_status = {}
    for r in rows:
        by_code[r.code] = by_code.get(r.code, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1

    return {
        "total": len(rows),
        "in_denominator": len(denominator),
        "complete": len(complete),
        "action_required": sum(1 for r in rows if r.actionRequired),
        "by_code": by_code,
        "by_status": by_status,
        # Present for display only. Not a column, not stored, and undefined
        # rather than zero when nothing is due.
        "complete_ratio": (len(complete) / len(denominator)) if denominator else None,
    }


def due_and_suspense(period_end, due_offset_days, suspense_offset_days):
    """Both dates are offsets from the period end. Nothing is inferred."""
    period_end = _as_date(period_end)
    due = period_end + _dt.timedelta(days=int(due_offset_days))
    suspense = period_end + _dt.timedelta(days=int(suspense_offset_days))
    if suspense < due:
        raise ValueError("Suspense_Offset_Days must be >= Due_Offset_Days")
    return due, suspense


if __name__ == "__main__":
    import json
    today = _dt.date(2026, 11, 10)
    demo = [
        ("verified, past suspense, nothing submitted",
         dict(as_of=today, suspense_date=_dt.date(2026, 11, 5),
              requirement_verification_status="VERIFIED")),
        ("provisional, past suspense, nothing submitted",
         dict(as_of=today, suspense_date=_dt.date(2026, 11, 5),
              requirement_verification_status="UNVERIFIED")),
        ("submitted, awaiting QC",
         dict(as_of=today, suspense_date=_dt.date(2026, 11, 15),
              has_current_submission=True, qc_status="PENDING")),
        ("returned for correction",
         dict(as_of=today, suspense_date=_dt.date(2026, 11, 20),
              has_current_submission=True, qc_status="RETURNED")),
    ]
    for label, kw in demo:
        r = evaluate(**kw)
        print(f"{label:<44} {r.code:<20} {r.status:<6} {r.actionOwner}")
    print()
    print(json.dumps(rollup(["ACCEPTED", "NOT_DUE", "NOT_DUE"]), indent=2))
