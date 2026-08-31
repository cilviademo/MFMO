#!/usr/bin/env python3
"""
MissionFeedingOperations — the status engine.

The Power App and Power BI must never disagree about what colour a base is.
This module is the reference implementation; `canvas-app/formulas/StatusEngine.fx`,
`flows/EOM03-Reconciliation` and the prototype are mechanical translations of
it, held in agreement by `tests/test_status_engine.py`.

Nothing about status is ever set by a human. There is no colour picker.

  * ``Final_Status`` is the SEMANTIC string.
  * ``Status_Code`` is the NUMERIC visual code, 0-5.
  * Both are stored. One evaluation writes both. Neither is derived from the
    other, and no second function derives the label independently of the code.

SIX visual states, and the amber/yellow split is the point. Colour carries
OWNERSHIP and time risk, not severity:

    Blue   4  not due, window open           nobody yet
    Amber  5  past first suspense            the base, with runway
    Red    1  past final call, or returned   the base, out of runway
    Yellow 2  received, awaiting review      AFSVC
    Green  3  accepted                       nobody
    Gray   0  not applicable                 nobody

Amber means TIME RISK. Yellow means SOMEBODY ELSE HAS IT. Collapsing them
tells a DFAC manager that a document they filed on time and a document they
never sent are the same kind of problem.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

# --- the six visual codes -------------------------------------------------
GRAY = 0
RED = 1
YELLOW = 2
GREEN = 3
BLUE = 4
AMBER = 5

CODE_COLOUR = {GRAY: "Gray", RED: "Red", YELLOW: "Yellow",
               GREEN: "Green", BLUE: "Blue", AMBER: "Amber"}

# --- action owners --------------------------------------------------------
FACILITY = "Facility"
REVIEWER = "Reviewer"
ADMIN = "Admin"
NONE = "None"

# --- the nine semantic statuses -------------------------------------------
# (Status_Code, label, Action_Owner, Action_Required)
STATUSES = {
    "NOT_APPLICABLE":      (GRAY,   "Not applicable",     NONE,     False),
    "NOT_DUE":             (BLUE,   "Not due",            FACILITY, False),
    "PENDING_VALIDATION":  (BLUE,   "Informational",      ADMIN,    False),
    "LATE":                (AMBER,  "Late",               FACILITY, True),
    "OVERDUE":             (RED,    "Overdue",            FACILITY, True),
    "RETURNED":            (RED,    "Returned",           FACILITY, True),
    "NOT_SATISFIED":       (RED,    "Not satisfied",      FACILITY, True),
    "RECEIVED_PENDING_QC": (YELLOW, "Awaiting review",    REVIEWER, True),
    "ACCEPTED":            (GREEN,  "Accepted",           NONE,     False),
}

# The four verdicts that mean "it came back". The engine collapses them into
# one RETURNED state; the submitter reads the specific reason off the
# submission's QC_Status. The engine does not need four states to say it came
# back, and the submitter needs four reasons to know what to fix.
QC_RETURNING = ("Correction Required", "Incomplete",
                "Wrong Reporting Period", "Wrong Facility")

# --- package rollup states ------------------------------------------------
PACKAGE_STATES = {
    "ACTION_REQUIRED": (RED,    "Action required"),
    "IN_REVIEW":       (YELLOW, "In review"),
    "COMPLETE":        (GREEN,  "Complete"),
    "IN_PROGRESS":     (BLUE,   "In progress"),
    "NOT_APPLICABLE":  (GRAY,   "Nothing due"),
}

# Any of these means the base owes something now.
ADVERSE = ("OVERDUE", "RETURNED", "NOT_SATISFIED", "LATE")


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


# ==========================================================================
# Dates — nominal and effective
# ==========================================================================

def nominal_date(period: str, day, offset_months: int = 1):
    """The policy date. 'The 5th' stays the 5th.

    Both values come from the requirement row, never from a flow. Changing the
    5th to the 7th is a list edit.
    """
    if day in (None, "", 0):
        return None
    year, month = (int(x) for x in period.split("-")[:2])
    month += int(offset_months or 0)
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = int(day)
    last = (_dt.date(year + (month == 12), (month % 12) + 1, 1)
            - _dt.timedelta(days=1)).day
    return _dt.date(year, month, min(day, last))


def is_non_duty_day(day, non_duty_days=(), scope_ids=()) -> bool:
    """A weekend, or a date in MF_Non_Duty_Day in scope for this row.

    ``non_duty_days`` is a sequence of dicts with Date, Scope_Type, Scope_ID
    and Active_Flag — the list itself, not a pre-filtered view, so the scope
    test lives in one place.
    """
    day = _day(day)
    if day is None:
        return False
    if day.weekday() >= 5:                       # Saturday, Sunday
        return True
    for row in non_duty_days:
        if not row.get("Active_Flag", True):
            continue
        if _day(row.get("Date")) != day:
            continue
        scope_type = row.get("Scope_Type", "Enterprise")
        if scope_type == "Enterprise":
            return True
        if row.get("Scope_ID") in scope_ids:
            return True
    return False


def effective_date(nominal, policy="NEXT_DUTY_DAY", non_duty_days=(), scope_ids=()):
    """Resolve a nominal date to the date a person is actually held to.

    A nominal suspense that lands on a Saturday cannot be the date someone is
    held to, and burying that adjustment in a formula produces a monthly
    argument. Status evaluation uses this; reporting uses the nominal date, so
    'the 5th' stays the 5th in a leadership brief.
    """
    day = _day(nominal)
    if day is None or policy == "NO_ADJUSTMENT":
        return day
    step = 1 if policy == "NEXT_DUTY_DAY" else -1
    # Bounded: a run of non-duty days longer than a fortnight is a data error,
    # not a holiday, and looping forever would hide it.
    for _ in range(14):
        if not is_non_duty_day(day, non_duty_days, scope_ids):
            return day
        day += _dt.timedelta(days=step)
    raise ValueError(
        f"more than 14 consecutive non-duty days from {nominal!r}; "
        "check MF_Non_Duty_Day for a bad bulk import")


def resolve_dates(period, requirement, non_duty_days=(), scope_ids=()) -> dict:
    """The four dates every item carries, plus whether they differ."""
    policy = requirement.get("NonDutyDay_Policy") or "NEXT_DUTY_DAY"
    offset = requirement.get("Due_Offset_Months")
    offset = 1 if offset in (None, "") else int(offset)

    nominal_due = nominal_date(period, requirement.get("Due_Day"), offset)
    nominal_final = nominal_date(period, requirement.get("Final_Due_Day"), offset)

    effective_due = effective_date(nominal_due, policy, non_duty_days, scope_ids)
    effective_final = effective_date(nominal_final, policy, non_duty_days, scope_ids)

    return {
        "Nominal_Due_Date": nominal_due,
        "Effective_Due_Date": effective_due,
        "Nominal_Final_Call_Date": nominal_final,
        "Effective_Final_Call_Date": effective_final,
        "Due_Date_Adjusted": bool(
            (nominal_due and effective_due and nominal_due != effective_due)
            or (nominal_final and effective_final and nominal_final != effective_final)
        ),
    }


# ==========================================================================
# The evaluation
# ==========================================================================

def item_status(
    *,
    today,
    effective_due_date,
    effective_final_call_date=None,
    required_flag=True,
    waived_flag=False,
    authority_status="UNVERIFIED",
    received_flag=False,
    qc_status=None,
) -> StatusResult:
    """Evaluate one checklist row. Ordered, total, first match wins.

    ``qc_status`` is the QC verdict on the CURRENT-VERSION submission, or None
    when nothing has been received. A superseded version never influences the
    item — that is what ``Is_Current`` is for.

    **Evaluation always uses the EFFECTIVE dates.** Reporting uses the nominal
    ones. The order is behaviour and the tests assert it.
    """
    today = _day(today)
    due = _day(effective_due_date)
    # A requirement with no final call is held to its first suspense.
    final = _day(effective_final_call_date) or due

    # 1. The obligation does not exist for this row this period.
    if waived_flag or not required_flag:
        return _mk("NOT_APPLICABLE")

    # 2. A provisional requirement is informational, never adverse. The base
    #    has nothing to do and nothing is wrong; the action is the programme's.
    #    With eleven of thirteen requirements now VERIFIED against the AFSVC
    #    procedures deck, this applies to almost nothing — a missed 1119 turns
    #    red as it should.
    if authority_status in ("UNVERIFIED", "PROPOSED") and not received_flag:
        return _mk("PENDING_VALIDATION")

    # 3-8. A current submission exists; its verdict decides.
    if qc_status == "Accepted":
        return _mk("ACCEPTED")
    if qc_status == "Not Applicable":
        return _mk("NOT_APPLICABLE")
    if qc_status == "Recalled":
        # A recall is the submitter withdrawing before review, not a rejection.
        # The item reverts to its date-based state and the withdrawn version
        # stays in history as superseded.
        return _date_state(today, due, final)
    if qc_status in QC_RETURNING:
        # Four verdicts, one status. The reason lives on the submission.
        return _mk("RETURNED")
    if qc_status == "Wrong Document":
        # A wrong document does not stay Red forever by fiat: the requirement
        # is still UNMET, and whether that is urgent depends on the suspense
        # date rather than the reviewer's verdict.
        return _mk("OVERDUE") if (final and today > final) else _mk("NOT_SATISFIED")

    # 9. Received and waiting on a reviewer. Yellow: AFSVC owns it.
    if received_flag:
        return _mk("RECEIVED_PENDING_QC")

    # 10-12. Nothing received. Time decides, and the two suspenses split it.
    return _date_state(today, due, final)


def _date_state(today, due, final) -> StatusResult:
    """Rules 10-12. The only week in the cycle where a reminder still changes
    the outcome is the one between the two dates, so it gets its own state."""
    if due is None or today <= due:
        return _mk("NOT_DUE")
    if final is None or today <= final:
        return _mk("LATE")
    return _mk("OVERDUE")


# ==========================================================================
# On-time is two questions, not one
# ==========================================================================

def on_time_facts(*, initial_submitted, acceptable_evidence,
                  effective_due_date, effective_final_call_date=None) -> dict:
    """Uploaded 4 Sep, returned 9 Sep, corrected and accepted 12 Sep: the base
    submitted on time and AFSVC did not have usable evidence on time. Both are
    true, and they are told to different audiences."""
    due = _day(effective_due_date)
    final = _day(effective_final_call_date) or due
    submitted = _day(initial_submitted)
    accepted = _day(acceptable_evidence)
    return {
        "Initial_Submission_On_Time":
            None if submitted is None else (due is None or submitted <= due),
        "Final_Evidence_On_Time":
            None if accepted is None else (final is None or accepted <= final),
    }


def describe_on_time(facts: dict, initial_submitted=None, acceptable_evidence=None) -> str:
    """Never show the two flags as bare booleans. Translate."""
    parts = []
    if initial_submitted is not None:
        when = _day(initial_submitted).strftime("%-d %b")
        parts.append(f"Submitted {when} — "
                     + ("on time" if facts["Initial_Submission_On_Time"] else "after suspense"))
    if acceptable_evidence is not None:
        when = _day(acceptable_evidence).strftime("%-d %b")
        parts.append(f"Accepted {when} — "
                     + ("final evidence on time" if facts["Final_Evidence_On_Time"]
                        else "final evidence after suspense"))
    return "\n".join(parts)


def days_late(effective_final_call_date, today=None, acceptable_evidence=None):
    """Magnitude against the final call. Amber and Red share an owner; this
    carries the difference in degree. Positive means late."""
    final = _day(effective_final_call_date)
    if final is None:
        return None
    ref = _day(acceptable_evidence) if acceptable_evidence else _day(today or _dt.date.today())
    return max(0, (ref - final).days)


# ==========================================================================
# Package rollup — over semantic statuses, never over colour codes
# ==========================================================================

def package_state(statuses, visible_predicate=None) -> dict:
    """Roll up a sequence of StatusResult (or Final_Status strings).

    The naive colour rollup sees no 1 and no 2 in ``[3, 4, 4]`` and marks the
    package Complete. It is IN_PROGRESS: two requirements have not been filed.

    ``visible_predicate`` is applied first. A user must not receive a figure
    derived from packages they may not see — that leaks across a security
    boundary even when no names appear on screen, because the numbers
    themselves are the disclosure.
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
    elif has(*ADVERSE):
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


if __name__ == "__main__":
    today = _dt.date(2026, 9, 8)
    req = {"Due_Day": 5, "Final_Due_Day": 10, "NonDutyDay_Policy": "NEXT_DUTY_DAY"}
    dates = resolve_dates("2026-08", req)
    print("2026-08 nominal due", dates["Nominal_Due_Date"],
          "-> effective", dates["Effective_Due_Date"],
          "adjusted" if dates["Due_Date_Adjusted"] else "")
    for label, kw in [
        ("nothing filed, before first suspense",
         dict(today=_dt.date(2026, 9, 3))),
        ("nothing filed, between the two",
         dict(today=_dt.date(2026, 9, 9))),
        ("nothing filed, past final call",
         dict(today=_dt.date(2026, 9, 12))),
        ("filed, awaiting review",
         dict(today=_dt.date(2026, 9, 12), received_flag=True, qc_status="Pending Review")),
        ("returned as Wrong Facility",
         dict(today=_dt.date(2026, 9, 12), received_flag=True, qc_status="Wrong Facility")),
        ("recalled before review",
         dict(today=_dt.date(2026, 9, 9), received_flag=True, qc_status="Recalled")),
    ]:
        kw.setdefault("authority_status", "VERIFIED")
        r = item_status(effective_due_date=dates["Effective_Due_Date"],
                        effective_final_call_date=dates["Effective_Final_Call_Date"], **kw)
        print(f"  {label:<40}{r.status:<20}{r.code}  {r.colour}")
    print()
    print("[ACCEPTED, NOT_DUE, NOT_DUE] ->",
          package_state(["ACCEPTED", "NOT_DUE", "NOT_DUE"])["state"])
