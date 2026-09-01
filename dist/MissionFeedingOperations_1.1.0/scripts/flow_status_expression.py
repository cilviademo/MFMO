#!/usr/bin/env python3
"""The status engine as a Power Automate (Logic Apps) expression.

    python3 scripts/flow_status_expression.py          # print it

WHY THIS FILE EXISTS
--------------------
`scripts/status_engine.py` is THE engine. `canvas-app/formulas/StatusEngine.fx`
is its Power Fx transliteration. This is its **Logic Apps** transliteration, for
the flows — a third language saying the same thing, which is exactly the shape
of drift that has bitten this programme in every snapshot delivered to it.

So it is not written by hand. It is generated from the same ordered rule table,
and `tests/test_flow_expression.py` EVALUATES it — a small interpreter for the
subset of the Logic Apps expression language used here — against the same 30
fixture cases that hold the Python and the Power Fx together. Three
implementations, one rule table, one set of cases.

WHY ONE EXPRESSION RATHER THAN AN ACTION GRAPH
----------------------------------------------
Twelve rules as twelve `If` actions is roughly forty actions once each branch
is closed, and the ordering lives in `runAfter` clauses that no reviewer can
read. As one nested `if()` the order is the nesting, which is the thing that
must not be got wrong.
"""

from __future__ import annotations

import os
import sys

# THE CATALOGUE IS IMPORTED, NOT COPIED.
#
# A hand-kept copy here would be a fourth place the six states are written
# down, and the first to go stale -- NOT_SATISFIED is Red, not Amber, which a
# copy made from memory gets wrong because the name sounds softer than the
# state is. scripts/status_engine.STATUSES is the catalogue; this reshapes it.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from status_engine import ADVERSE, QC_RETURNING, STATUSES  # noqa: E402,F401

CATALOG = {
    name: (code, owner, action)
    for name, (code, _label, owner, action) in STATUSES.items()
}

# The inputs, named once. Each is a Compose the flow sets before calling this.
V = {
    "today":    "variables('Today')",
    "due":      "variables('EffectiveDueDate')",
    # A REQUIREMENT WITH NO FINAL CALL IS HELD TO ITS FIRST SUSPENSE. Without
    # this coalesce a requirement carrying no final call sits amber forever
    # instead of going red, which is the wrong answer in the safe-looking
    # direction. `scripts/status_engine.item_status` does the same thing on its
    # first three lines; this is the same rule, not a second one.
    "final":    ("if(empty(variables('EffectiveFinalCallDate')), "
                 "variables('EffectiveDueDate'), "
                 "variables('EffectiveFinalCallDate'))"),
    "required": "variables('RequiredFlag')",
    "waived":   "variables('WaivedFlag')",
    "auth":     "variables('AuthorityStatus')",
    "received": "variables('ReceivedFlag')",
    "qc":       "variables('QCStatus')",
}


def _s(status):
    """A status literal as an object, so one evaluation returns all four."""
    code, owner, action = CATALOG[status]
    return (f"json('{{\"status\":\"{status}\",\"code\":{code},"
            f"\"actionOwner\":\"{owner}\","
            f"\"actionRequired\":{str(action).lower()}}}')")


# LOGIC APPS or() AND and() ARE NOT SHORT-CIRCUITING. Both arguments are
# evaluated before the operator runs, so `or(empty(d), ticks(d) > ...)` throws
# on a null date rather than taking the first branch -- at run time, in a
# tenant, on the one item whose requirement has no final call.
#
# if() IS lazy. Every null guard below is therefore a nested if(), not an or().
# The interpreter in tests/test_flow_expression.py models the same eagerness,
# which is how this was caught here instead of six weeks from now.

def _past(date_var):
    """today > date, with a null date meaning 'no such deadline'."""
    return (f"if(empty({date_var}), false, "
            f"greater(ticks({V['today']}), ticks({date_var})))")


def _not_yet(date_var):
    """today <= date, with a null date meaning 'no such deadline'."""
    return (f"if(empty({date_var}), true, "
            f"lessOrEquals(ticks({V['today']}), ticks({date_var})))")


def _date_state():
    """Rules 10-12. The only week where a reminder still changes the outcome is
    the one between the two dates, so it gets its own state."""
    return (
        f"if({_not_yet(V['due'])}, {_s('NOT_DUE')}, "
        f"if({_not_yet(V['final'])}, {_s('LATE')}, {_s('OVERDUE')}))"
    )


def _nest(rules, otherwise):
    """Build if(c1, r1, if(c2, r2, ... otherwise)) from an ordered list.

    Built structurally rather than by concatenating strings and counting
    brackets at the end. Hand-balanced parentheses in a 2,400-character
    expression is a defect waiting for the one reviewer who does not count.
    """
    out = otherwise
    for cond, result in reversed(rules):
        out = f"if({cond}, {result}, {out})"
    return out


def expression():
    """The twelve rules, in order. The nesting IS the order."""
    returning = ", ".join(f"'{v}'" for v in QC_RETURNING)
    rules = [
        # 1. The obligation does not exist for this row this period.
        (f"or({V['waived']}, not({V['required']}))", _s("NOT_APPLICABLE")),
        # 2. A provisional requirement is informational, never adverse. The
        #    base has nothing to do and nothing is wrong; the action is the
        #    programme's.
        (f"and(contains(createArray('UNVERIFIED','PROPOSED'), {V['auth']}), "
         f"not({V['received']}))", _s("PENDING_VALIDATION")),
        # 3-8. A current submission exists; its verdict decides.
        (f"equals({V['qc']}, 'Accepted')", _s("ACCEPTED")),
        (f"equals({V['qc']}, 'Not Applicable')", _s("NOT_APPLICABLE")),
        # A recall is the submitter withdrawing before review, not a
        # rejection: the item reverts to its date-based state and the
        # withdrawn version stays in history as superseded.
        (f"equals({V['qc']}, 'Recalled')", _date_state()),
        # Four verdicts, one status. The reason lives on the submission.
        (f"contains(createArray({returning}), {V['qc']})", _s("RETURNED")),
        # A wrong document does not stay Red forever by fiat: the requirement
        # is still unmet, and whether that is urgent depends on the suspense
        # rather than the reviewer's verdict.
        (f"equals({V['qc']}, 'Wrong Document')",
         f"if({_past(V['final'])}, {_s('OVERDUE')}, {_s('NOT_SATISFIED')})"),
        # 9. Received and waiting on a reviewer. Yellow: AFSVC owns it.
        (V["received"], _s("RECEIVED_PENDING_QC")),
    ]
    # 10-12. Nothing received. Time decides, and the two suspenses split it.
    return _nest(rules, _date_state())


if __name__ == "__main__":
    sys.stdout.write("@{" + expression() + "}\n")
