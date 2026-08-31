#!/usr/bin/env python3
"""
MissionFeedingOperations — the status engine.

The Power App and Power BI must never disagree about what colour a base is.
This module is the reference implementation; `canvas-app/formulas/StatusEngine.fx`,
`flows/EOM03-Reconciliation` and the prototype are mechanical translations of
it, held in agreement by `tests/test_status_engine.py`.

Ported from the V3 prototype's `itemStatus()` and `packageState()`, which are
the most current and correct V3 artifacts. V3's Power Fx and its
`App.Formulas.fx` are NOT the reference — they had already drifted from the
decision table in the same document, in three ways recorded as C1-C3 in
`docs/handoffs/RECONCILIATION.md`.

Nothing about status is ever set by a human. There is no "make this yellow"
control anywhere in the app.

  * ``Final_Status`` is the SEMANTIC string.
  * ``Status_Code`` is the NUMERIC visual code, 0-4.
  * Both are stored. One evaluation writes both. Neither is derived from the
    other, and no second function derives the label independently of the code —
    that is how a status engine starts lying.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

# --- the five visual codes -------------------------------------------------
# Four states were not enough. Collapsing "not applicable" and "not due yet"
# into Gray made an installation whose requirements simply had not come due
# display as Not applicable, which is false. Blue separates "in progress,
# nothing wrong" from "does not apply".
NA = 0       # Gray
ACTION = 1   # Red
PENDING = 2  # Amber
DONE = 3     # Green
INFO = 4     # Blue

CODE_COLOUR = {NA: "Gray", ACTION: "Red", PENDING: "Amber", DONE: "Green", INFO: "Blue"}

# --- action owners ---------------------------------------------------------
FACILITY = "Facility"
REVIEWER = "Reviewer"
ADMIN = "Admin"
NONE = "None"

# --- the eight semantic statuses ------------------------------------------
# (Status_Code, label, Action_Owner, Action_Required)
STATUSES = {
    "NOT_APPLICABLE":      (NA,      "Not applicable",    NONE,     False),
    "NOT_DUE":             (INFO,    "Not due",           FACILITY, False),
    "PENDING_VALIDATION":  (INFO,    "Informational",     ADMIN,    False),
    "OVERDUE":             (ACTION,  "Overdue",           FACILITY, True),
    "NOT_SATISFIED":       (PENDING, "Not satisfied",     FACILITY, True),
    "CORRECTION_REQUIRED": (PENDING, "Correction needed", FACILITY, True),
    "RECEIVED_PENDING_QC": (PENDING, "Awaiting review",   REVIEWER, True),
    "ACCEPTED":            (DONE,    "Accepted",          NONE,     False),
}

# --- package rollup states -------------------------------------------------
PACKAGE_STATES = {
    "ACTION_REQUIRED": (ACTION,  "Action required"),
    "IN_REVIEW":       (PENDING, "In review"),
    "COMPLETE":        (DONE,    "Complete"),
    "IN_PROGRESS":     (INFO,    "In progress"),
    "NOT_APPLICABLE":  (NA,      "Nothing due"),
}


@dataclass(frozen=True)
class StatusResult:
    """The single return value of the single evaluation."""

    status: str          # Final_Status — the semantic string
    code: int            # Status_Code — the numeric visual code
    label: str           # display text
    actionOwner: str
    actionRequired: bool

    @property
    def colour(self) -> str:
        return CODE_COLOUR[self.code]

    def as_item_fields(self) -> dict:
        """The four columns MF_EOM_Item stores, written together."""
        return {
            "Final_Status": self.status,
            "Status_Code": self.code,
            "Action_Owner": self.actionOwner,
            "Action_Required": self.actionRequired,
        }


def _mk(status: str) -> StatusResult:
    code, label, owner, required = STATUSES[status]
    return StatusResult(status=status, code=code, label=label,
                        actionOwner=owner, actionRequired=required)


def _day(value):
    """Reporting_Period is YYYY-MM, dates are YYYY-MM-DD, datetimes carry a
    time part. Parse to a date before comparing so a timestamp never leaks
    into a day comparison."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    return _dt.date.fromisoformat(str(value)[:10])


def item_status(
    *,
    today,
    due_date,
    required_flag=True,
    waived_flag=False,
    authority_status="UNVERIFIED",
    received_flag=False,
    qc_status=None,
) -> StatusResult:
    """Evaluate one checklist row. Ordered, total, first match wins.

    ``qc_status`` is the QC state of the CURRENT-VERSION submission, or None
    when nothing has been received. A rejected v1 under an accepted v2 never
    influences the item — that is what ``Is_Current`` is for.

    The order is behaviour. Reordering it to make a screen read better is a
    behaviour change, and the tests assert it.
    """
    today = _day(today)
    due_date = _day(due_date)

    # 1. The obligation does not exist for this row.
    if waived_flag or not required_flag:
        return _mk("NOT_APPLICABLE")

    # 2. A provisional requirement is informational, never adverse.
    #    All twelve seeded requirements are UNVERIFIED, so this is the default
    #    path today, not an edge case. Until the authority is confirmed, an
    #    unfiled document is not a finding and the action sits with the Admin
    #    (verify the requirement), not with the facility (file the document).
    if authority_status == "UNVERIFIED" and not received_flag:
        return _mk("PENDING_VALIDATION")

    # 3-7. A current submission exists; its QC verdict decides.
    if qc_status == "Accepted":
        return _mk("ACCEPTED")
    if qc_status == "Not Applicable":
        return _mk("NOT_APPLICABLE")
    if qc_status == "Correction Required":
        return _mk("CORRECTION_REQUIRED")
    if qc_status == "Wrong Document":
        # A wrong document does not stay Red forever. It means the requirement
        # is still UNMET; whether that is urgent depends on the suspense date,
        # not on the reviewer's verdict. A submission-level QC result must
        # never become the parent item's status directly.
        return _mk("OVERDUE") if (due_date and today > due_date) else _mk("NOT_SATISFIED")

    # 8. Received and waiting on a reviewer.
    if received_flag:
        return _mk("RECEIVED_PENDING_QC")

    # 9-10. Nothing received. Time decides.
    if due_date is None or today <= due_date:
        return _mk("NOT_DUE")
    return _mk("OVERDUE")


def package_state(statuses, visible_predicate=None) -> dict:
    """Roll up a sequence of StatusResult (or Final_Status strings).

    Over SEMANTIC statuses, never over colour codes. The naive colour rollup
    sees ``[3, 4, 4]`` with no 1 and no 2 and marks the package Complete. It is
    IN_PROGRESS: two requirements have not been filed yet.

    ``visible_predicate`` is applied first. A user scoped to one DFAC must not
    receive an installation figure derived from their neighbours' packages —
    that leaks across a security boundary even when no names appear on screen.
    """
    rows = []
    for s in statuses:
        if isinstance(s, str):
            s = _mk(s)
        if visible_predicate is not None and not visible_predicate(s):
            continue
        rows.append(s)

    def has(*names):
        return any(r.status in names for r in rows)

    applicable = [r for r in rows if r.status != "NOT_APPLICABLE"]

    if not applicable:
        state = "NOT_APPLICABLE"
    elif has("OVERDUE", "CORRECTION_REQUIRED", "NOT_SATISFIED"):
        state = "ACTION_REQUIRED"
    elif has("RECEIVED_PENDING_QC"):
        state = "IN_REVIEW"
    else:
        # A provisional requirement neither completes a package nor blocks it.
        real = [r for r in applicable if r.status != "PENDING_VALIDATION"]
        if real and all(r.status == "ACCEPTED" for r in real):
            state = "COMPLETE"
        else:
            state = "IN_PROGRESS"

    code, label = PACKAGE_STATES[state]
    by_status, by_code = {}, {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_code[r.code] = by_code.get(r.code, 0) + 1

    return {
        "state": state,
        "code": code,
        "label": label,
        "total": len(rows),
        "applicable": len(applicable),
        "accepted": sum(1 for r in rows if r.status == "ACCEPTED"),
        "action_required": sum(1 for r in rows if r.actionRequired),
        "by_status": by_status,
        "by_code": by_code,
    }


def due_date_for(period: str, due_day, due_offset_months=1):
    """Due_Date = date(period + Due_Offset_Months, Due_Day).

    Both values come from the requirement row, never from the flow. Changing
    the 10th to the 15th is a list edit, not a deployment.
    """
    year, month = (int(x) for x in period.split("-"))
    month += int(due_offset_months or 0)
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = int(due_day or 1)
    # Clamp rather than roll over: a Due_Day of 31 in a 30-day month is the
    # last day of that month, not the 1st of the next.
    last = (_dt.date(year + (month == 12), (month % 12) + 1, 1)
            - _dt.timedelta(days=1)).day
    return _dt.date(year, month, min(day, last))


def days_late(due_date, received_datetime, today=None):
    """Set by EOM-03 rather than computed in DAX. Positive means late."""
    due = _day(due_date)
    if due is None:
        return None
    ref = _day(received_datetime) if received_datetime else _day(today or _dt.date.today())
    return (ref - due).days


if __name__ == "__main__":
    today = _dt.date(2026, 9, 12)
    demo = [
        ("provisional requirement, nothing filed",
         dict(today=today, due_date=_dt.date(2026, 9, 10))),
        ("verified requirement, nothing filed, past suspense",
         dict(today=today, due_date=_dt.date(2026, 9, 10), authority_status="Verified")),
        ("verified, filed, awaiting review",
         dict(today=today, due_date=_dt.date(2026, 9, 10), authority_status="Verified",
              received_flag=True, qc_status="Pending Review")),
        ("wrong document before suspense",
         dict(today=today, due_date=_dt.date(2026, 9, 20), authority_status="Verified",
              received_flag=True, qc_status="Wrong Document")),
        ("wrong document after suspense",
         dict(today=today, due_date=_dt.date(2026, 9, 10), authority_status="Verified",
              received_flag=True, qc_status="Wrong Document")),
    ]
    for label, kw in demo:
        r = item_status(**kw)
        print(f"{label:<44}{r.status:<20}{r.code}  {r.colour:<6}{r.actionOwner}")
    print()
    print("[ACCEPTED, NOT_DUE, NOT_DUE] ->",
          package_state(["ACCEPTED", "NOT_DUE", "NOT_DUE"])["state"])
