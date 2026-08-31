"""The Logic Apps status expression, evaluated and held to the Python engine.

A third language saying the same thing is exactly the shape of drift that has
bitten this programme in every snapshot delivered to it: v3 shipped three
parallel status functions already diverged from its own table, v11 a four-state
Power Fx block under a twelve-rule decision order.

So the expression is not merely inspected. A small interpreter for the subset of
the Logic Apps expression language it uses evaluates it, and the result is
compared against `scripts/status_engine.item_status` on the same 30 fixture
cases that hold the Python and the Power Fx together.

The interpreter is deliberately small and strict: an unknown function raises
rather than returning None, so a typo in the expression fails here rather than
in a tenant six weeks from now.
"""

import datetime as dt
import json
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from flow_status_expression import CATALOG, QC_RETURNING, expression  # noqa: E402
from status_engine import item_status  # noqa: E402


# --- a tiny Logic Apps expression interpreter -----------------------------

class ExpressionError(Exception):
    pass


def tokenize(src):
    spec = [
        ("STR", r"'(?:[^']|'')*'"),
        ("NUM", r"-?\d+(?:\.\d+)?"),
        ("NAME", r"[A-Za-z_][A-Za-z0-9_]*"),
        ("PUNC", r"[(),]"),
        ("WS", r"\s+"),
    ]
    rx = re.compile("|".join(f"(?P<{n}>{p})" for n, p in spec))
    pos, out = 0, []
    while pos < len(src):
        m = rx.match(src, pos)
        if not m:
            raise ExpressionError(f"cannot tokenize at {src[pos:pos+40]!r}")
        pos = m.end()
        if m.lastgroup != "WS":
            out.append((m.lastgroup, m.group()))
    return out


class Parser:
    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, value=None):
        kind, tok = self.peek()
        if value is not None and tok != value:
            raise ExpressionError(f"expected {value!r}, got {tok!r}")
        self.i += 1
        return kind, tok

    def parse(self):
        node = self.expr()
        if self.i != len(self.t):
            raise ExpressionError(f"trailing tokens at {self.t[self.i:][:3]}")
        return node

    def expr(self):
        kind, tok = self.take()
        if kind == "STR":
            return ("lit", tok[1:-1].replace("''", "'"))
        if kind == "NUM":
            return ("lit", float(tok) if "." in tok else int(tok))
        if kind == "NAME":
            # Logic Apps boolean literals.
            if tok in ("true", "false") and self.peek()[1] != "(":
                return ("lit", tok == "true")
            if tok in ("null",) and self.peek()[1] != "(":
                return ("lit", None)
            if self.peek()[1] != "(":
                raise ExpressionError(f"bare name {tok!r}")
            self.take("(")
            args = []
            if self.peek()[1] != ")":
                args.append(self.expr())
                while self.peek()[1] == ",":
                    self.take(",")
                    args.append(self.expr())
            self.take(")")
            return ("call", tok, args)
        raise ExpressionError(f"unexpected {tok!r}")


def _ticks(v):
    """Logic Apps ticks(). Only ordering matters here."""
    if v in (None, ""):
        raise ExpressionError("ticks() on an empty value")
    d = dt.date.fromisoformat(str(v)[:10])
    return d.toordinal()


def evaluate(node, env):
    kind = node[0]
    if kind == "lit":
        return node[1]
    _, fn, args = node

    # Lazily evaluated: if() must not evaluate the branch it does not take, or
    # ticks() on a null date raises in a branch that was never reached.
    if fn == "if":
        if len(args) != 3:
            raise ExpressionError("if() takes three arguments")
        return evaluate(args[1] if _truthy(evaluate(args[0], env)) else args[2],
                        env)

    a = [evaluate(x, env) for x in args]

    if fn == "variables":
        if a[0] not in env:
            raise ExpressionError(f"undefined variable {a[0]!r}")
        return env[a[0]]
    if fn == "or":
        return any(_truthy(x) for x in a)
    if fn == "and":
        return all(_truthy(x) for x in a)
    if fn == "not":
        return not _truthy(a[0])
    if fn == "equals":
        return a[0] == a[1]
    if fn == "empty":
        return a[0] in (None, "", [], {})
    if fn == "contains":
        return a[1] in a[0]
    if fn == "createArray":
        return list(a)
    if fn == "greater":
        return a[0] > a[1]
    if fn == "lessOrEquals":
        return a[0] <= a[1]
    if fn == "ticks":
        return _ticks(a[0])
    if fn == "json":
        return json.loads(a[0])
    raise ExpressionError(f"unknown function {fn!r} -- typo, or the "
                          "interpreter needs extending deliberately")


def _truthy(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    raise ExpressionError(f"non-boolean in a boolean position: {v!r}")


def run_expression(**env):
    return evaluate(Parser(tokenize(expression())).parse(), env)


# --- the tests ------------------------------------------------------------

with open(os.path.join(ROOT, "tests", "fixtures", "status_cases.json"),
          encoding="utf-8") as _fh:
    FIXTURES = json.load(_fh)


def _dates(case):
    d = case.get("dates", {})
    return (d.get("effective_due_date", FIXTURES["effective_due_date"]),
            d.get("effective_final_call_date",
                  FIXTURES["effective_final_call_date"]))


def to_env(case):
    """Fixture case -> the flow's variables.

    A null date arrives as the empty string, which is what a SharePoint date
    column reads as when unset -- and is exactly the value the eager-or()
    problem showed up on.
    """
    due, final = _dates(case)
    inp = case["input"]
    return {
        "Today": case["today"],
        "EffectiveDueDate": due or "",
        "EffectiveFinalCallDate": final or "",
        "RequiredFlag": bool(inp.get("required_flag", True)),
        "WaivedFlag": bool(inp.get("waived_flag", False)),
        "AuthorityStatus": inp.get("authority_status") or "",
        "ReceivedFlag": bool(inp.get("received_flag", False)),
        "QCStatus": inp.get("qc_status") or "",
    }


def to_python(case):
    due, final = _dates(case)
    return item_status(today=case["today"], effective_due_date=due,
                       effective_final_call_date=final, **case["input"])


class TheInterpreterIsStrict(unittest.TestCase):
    """A lenient interpreter proves nothing."""

    def test_an_unknown_function_raises(self):
        with self.assertRaises(ExpressionError):
            evaluate(Parser(tokenize("nosuchfn('x')")).parse(), {})

    def test_an_undefined_variable_raises(self):
        with self.assertRaises(ExpressionError):
            evaluate(Parser(tokenize("variables('Nope')")).parse(), {})

    def test_a_non_boolean_condition_raises(self):
        with self.assertRaises(ExpressionError):
            evaluate(Parser(tokenize("if('x', 1, 2)")).parse(), {})

    def test_unbalanced_parentheses_raise(self):
        with self.assertRaises(ExpressionError):
            Parser(tokenize("if(equals('a','a'), 1, 2")).parse()

    def test_if_does_not_evaluate_the_untaken_branch(self):
        # ticks('') raises. If the false branch were evaluated eagerly this
        # would fail, and the real expression depends on that laziness for a
        # null final-call date.
        node = Parser(tokenize("if(equals('a','a'), 1, ticks(''))")).parse()
        self.assertEqual(evaluate(node, {}), 1)


class TheExpressionIsWellFormed(unittest.TestCase):
    def test_it_parses(self):
        Parser(tokenize(expression())).parse()

    def test_parentheses_balance(self):
        e = expression()
        self.assertEqual(e.count("("), e.count(")"))

    def test_every_status_in_the_catalogue_can_be_produced(self):
        e = expression()
        for status in CATALOG:
            self.assertIn(f'"status":"{status}"', e, status)

    def test_all_four_returning_verdicts_are_named(self):
        e = expression()
        for verdict in QC_RETURNING:
            self.assertIn(f"'{verdict}'", e, verdict)

    def test_the_code_beside_each_status_matches_the_catalogue(self):
        e = expression()
        for status, (code, owner, action) in CATALOG.items():
            self.assertIn(
                f'{{"status":"{status}","code":{code},"actionOwner":"{owner}",'
                f'"actionRequired":{str(action).lower()}}}', e, status)


class TheExpressionAgreesWithTheEngine(unittest.TestCase):
    """The whole point. Same rule table, same cases, three languages."""

    def setUp(self):
        self.cases = FIXTURES["cases"]

    def test_there_are_cases_to_check(self):
        self.assertGreaterEqual(len(self.cases), 25)

    def test_every_fixture_case_agrees(self):
        for case in self.cases:
            with self.subTest(case=case.get("name", case)):
                want = to_python(case)
                got = run_expression(**to_env(case))
                self.assertEqual(got["status"], want.status, case)
                self.assertEqual(got["code"], want.code, case)
                self.assertEqual(got["actionOwner"], want.actionOwner, case)
                self.assertEqual(got["actionRequired"], want.actionRequired,
                                 case)
                # And against what the fixture itself declares, so a change to
                # BOTH implementations still has to face the recorded case.
                for key, expected in case["expect"].items():
                    self.assertEqual(got[key], expected,
                                     f"{case['name']}: {key}")

    def test_the_six_visual_codes_all_appear_across_the_cases(self):
        seen = {run_expression(**to_env(c))["code"] for c in self.cases}
        self.assertEqual(seen, {0, 1, 2, 3, 4, 5},
                         "the fixtures no longer exercise every state")


if __name__ == "__main__":
    unittest.main()
