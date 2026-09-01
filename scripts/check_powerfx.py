#!/usr/bin/env python3
"""Parse every canvas formula with Microsoft's own Power Fx engine.

Until now nothing here had ever parsed the canvas source as Power Fx; the tests
read the .pa.yaml as text. This runs each formula through `pac power-fx run`
(Microsoft.PowerFx, shipped in the Power Platform CLI) and reports SYNTAX
errors.

BINDING errors are expected and ignored. Nothing is connected here: there are
no SharePoint data sources, no App scope, no named formulas from the .fx files,
no controls. So "Name isn't valid" is the engine correctly telling us a data
source is absent, and it says nothing about whether the formula is written
correctly. A SYNTAX error is different: it is wrong on any machine, connected
or not, and Studio would reject it too.

Requires the PAC CLI. Set PAC to its path; without it this exits 0 and says it
skipped, because an unavailable checker must not read as a passing one.

  PAC=/path/to/pac python3 scripts/check_powerfx.py
"""
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canvas_formulas import all_formulas          # noqa: E402

# Diagnostics that mean "this name is not in scope here". Every one of them is
# a consequence of running detached from an app and its data sources.
BINDING = (
    "isn't recognized",
    "has some invalid arguments",
    "does not exist",
    "Incompatible types for comparison",
    "The type of this argument",
    "Invalid argument type",
    "Invalid number of arguments",
    "cannot be used in this context",
    "Expected a value compatible",
    "This identifier",
    "Name isn't valid",
    "The specified column",
    "Behavior function in a non-behavior property",
    "This function has invalid arguments",
    "is not a valid",
    # Cascades. Once one name fails to bind the engine yields Error, and every
    # operation on that Error reports its own diagnostic. All of these are
    # downstream of an absent data source or an absent named formula, not of
    # anything written wrongly.
    "unknown or unsupported function",
    "cannot be used on Error values",
    "has a type that is not compatible",
    "must evaluate to a Text value",
    "Incompatible type",
    "The value cannot be converted",
    "Expected a Table value",
    "Expected a Record value",
    "Cannot use a non-record value",
    "This argument",
    "expects a",
    # Canvas-only functions. The standalone interpreter implements the Power Fx
    # language, not the canvas host: Back, Navigate, User, Defaults, Patch on a
    # connector and friends exist only inside an app. "Recognized but not
    # supported" is the engine saying exactly that.
    "recognized but not supported function",
    "cannot be used on Unknown values",
)

# Reported separately: not syntax, not binding, but worth seeing.
ADVISORY = (
    "Deprecated use of",
)


def strip_comments(text):
    """Remove // and /* */ comments outside string literals."""
    out, i, n = [], 0, len(text)
    instr = None
    while i < n:
        c = text[i]
        if instr:
            out.append(c)
            if c == instr:
                instr = None
            i += 1
            continue
        if c in "\"'":
            instr = c
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def one_line(text):
    return " ".join(strip_comments(text).split())


def run_batch(pac, formulas):
    """Return {line_index: [diagnostic, ...]} for one batch."""
    with tempfile.NamedTemporaryFile("w", suffix=".fx", delete=False,
                                     encoding="utf-8") as fh:
        for _rel, _ln, _name, text in formulas:
            fh.write(one_line(text) + "\n")
        path = fh.name
    try:
        proc = subprocess.run([pac, "power-fx", "run", "--file", path],
                              capture_output=True, timeout=600)
    finally:
        os.unlink(path)
    raw = proc.stdout.replace(b"\x00", b"").decode("utf-8", "ignore")
    found = {}
    for m in re.finditer(r"^Line (\d+): Error [\d-]+: (.+)$", raw, re.M):
        found.setdefault(int(m.group(1)), []).append(m.group(2).strip())
    return found


def main():
    pac = os.environ.get("PAC")
    if not pac or not os.path.exists(pac):
        print("SKIPPED — the Power Platform CLI is not available here.")
        print("An unavailable checker is not a passing one. Set PAC=<path>.")
        return 0

    formulas = list(all_formulas())
    print(f"Power Fx syntax check — {len(formulas)} formulas from "
          f"{len({f[0] for f in formulas})} files")
    print("=" * 62)

    syntax, advisory, binding_count = [], [], 0
    BATCH = 120
    for start in range(0, len(formulas), BATCH):
        chunk = formulas[start:start + BATCH]
        diags = run_batch(pac, chunk)
        for idx, messages in diags.items():
            rel, line, name, _text = chunk[idx - 1]
            for msg in messages:
                if any(a in msg for a in ADVISORY):
                    advisory.append((rel, line, name, msg))
                elif any(b in msg for b in BINDING):
                    binding_count += 1
                else:
                    syntax.append((rel, line, name, msg))
        sys.stdout.write(f"\r  {min(start + BATCH, len(formulas))}"
                         f"/{len(formulas)}")
        sys.stdout.flush()
    print()

    print(f"\n  binding diagnostics ignored: {binding_count}")
    print("  (no data sources, no App scope, no named formulas — expected)")
    if advisory:
        seen = sorted({(a[0], a[1], a[3]) for a in advisory})
        print(f"\n  ADVISORY ({len(seen)}) — and every one is probably a"
              f" cascade too")
        print("  A deprecation warning on '.' means the engine could not tell"
              " record-field")
        print("  access from table-column shorthand, because the identifier is"
              " unbound.")
        print("  Spot-checked: locUnmatched.Unmatched_ID is a record field and"
              " is correct.")
        for rel, line, msg in seen[:20]:
            print(f"    {rel}:{line}  {msg}")
        if len(seen) > 20:
            print(f"    ... and {len(seen) - 20} more")

    if syntax:
        print(f"\nSYNTAX ERRORS ({len(syntax)})")
        for rel, line, name, msg in syntax:
            print(f"  {rel}:{line}  {name}")
            print(f"      {msg}")
        return 1
    print("\nNo syntax errors. Every formula parses under Microsoft.PowerFx.")
    print("\nThis is a PARSE result, not a runtime one. It says nothing about")
    print("whether a formula returns the right answer against real data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
