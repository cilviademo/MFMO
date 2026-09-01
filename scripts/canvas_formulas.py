#!/usr/bin/env python3
"""Extract every Power Fx formula from the canvas source.

The .pa.yaml files are the app's source of truth, and until now nothing in this
repository has parsed them as Power Fx -- the tests read them as text. This
pulls out each formula so a real Power Fx engine can be pointed at it.

Two shapes appear in the YAML:

    Key: =expression                      inline
    Key: |                                block
      =expression continuing
      over several lines

and the .fx files are whole-file named formulas (Name = expression ;).
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "canvas-app", "src")
FORMULAS = os.path.join(ROOT, "canvas-app", "formulas")


def _dedent_block(lines, indent):
    out = []
    for ln in lines:
        out.append(ln[indent:] if len(ln) >= indent and ln[:indent].isspace()
                   else ln.lstrip())
    return out


def from_yaml(path):
    """Yield (line_number, property_name, formula_text)."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*:\s*\|\s*$", line)
        if m:
            indent = len(raw) - len(raw.lstrip())
            body, j = [], i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                body.append(nxt)
                j += 1
            text = "\n".join(_dedent_block(body, indent + 2)).strip()
            if text.startswith("="):
                yield i + 1, m.group(1), text[1:].strip()
            i = j
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*:\s*=(.+)$", line)
        if m:
            yield i + 1, m.group(1), m.group(2).strip()
        i += 1


def from_fx(path):
    """A .fx file is a sequence of `Name = expression;` named formulas."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # Strip // comments outside strings, conservatively: only whole-line ones.
    kept = []
    for n, ln in enumerate(text.split("\n"), 1):
        kept.append("" if ln.lstrip().startswith("//") else ln)
    text = "\n".join(kept)
    # Three shapes appear in the .fx files, and an earlier version of this
    # regex matched only the first two -- so Delegation.fx, the file that
    # decides whether every query delegates, contributed ZERO formulas and was
    # never parsed. The count still looked healthy because the other files made
    # it up. Hence test_every_expected_file_contributes below: a named list,
    # not a total.
    #
    #     Name = expr;                       plain
    #     Name(a: Text) = expr;              parameters
    #     Name(a: Text): Table = expr;       parameters and a return type
    for m in re.finditer(
            r"^([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?\s*(:\s*[A-Za-z_][A-Za-z0-9_]*)?\s*=\s*",
            text, re.M):
        start = m.end()
        depth, j, instr = 0, start, None
        while j < len(text):
            c = text[j]
            if instr:
                if c == instr:
                    instr = None
            elif c in "\"'":
                instr = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == ";" and depth == 0:
                break
            j += 1
        line = text[:m.start()].count("\n") + 1
        yield line, m.group(1), text[start:j].strip()


def all_formulas():
    for base, _dirs, files in os.walk(SRC):
        for f in sorted(files):
            if f.endswith(".pa.yaml"):
                p = os.path.join(base, f)
                for item in from_yaml(p):
                    yield (os.path.relpath(p, ROOT),) + item
    for f in sorted(os.listdir(FORMULAS)):
        if f.endswith(".fx"):
            p = os.path.join(FORMULAS, f)
            for item in from_fx(p):
                yield (os.path.relpath(p, ROOT),) + item


if __name__ == "__main__":
    items = list(all_formulas())
    print(f"{len(items)} formulas")
    if "-v" in sys.argv:
        for rel, line, name, text in items:
            one = " ".join(text.split())
            print(f"  {rel}:{line} {name} = {one[:90]}")
