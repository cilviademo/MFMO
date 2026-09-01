#!/usr/bin/env python3
"""Every name a screen uses must resolve to something that exists.

A canvas app fails SILENTLY on a wrong data-source or column name.
`LookUp('MF EOM Itm', ...)` does not error: it returns blank, the gallery
renders empty, and the screen reads as "nothing due". That is the failure this
programme exists to prevent, arriving through a typo.

Checked from the sources of truth, never from a list kept by hand:

  data sources  a quoted 'MF ...' name must be a display name in eom_schema.py
  screens       a bare Navigate() target must be a screen file
  components    ComponentName must be a component file
  flows         a .Run() target must match a workflow in solution/src/Workflows
                once both sides are reduced to alphanumerics -- Studio decides
                the exact identifier it generates from a display name, and this
                cannot verify which it chose
  formulas      MF_* / gbl* / colX names must be defined in canvas-app/formulas

String literals are excluded: a message that NAMES a list in prose is not a
reference to it.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import eom_schema as S                                    # noqa: E402
from canvas_formulas import all_formulas                  # noqa: E402

SRC = os.path.join(ROOT, "canvas-app", "src")
FX = os.path.join(ROOT, "canvas-app", "formulas")

DEF = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?"
    r"(:\s*[A-Za-z_][A-Za-z0-9_]*)?\s*=", re.M)
# Ours: MF_Anything, gblAnything, colAnything -- col must be followed by an
# upper-case letter, or the word "collects" in a comment reads as a reference.
OURS = re.compile(r"\b(MF_[A-Za-z0-9_]*|gbl[A-Z][A-Za-z0-9_]*|col[A-Z][A-Za-z0-9_]*)")


def strip_strings(text):
    """Blank out string literals, keeping length so offsets still line up.

    An interpolated $"..." can contain {expr}, and those ARE references, so
    the braces' contents are kept.
    """
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            quote, j = c, i + 1
            while j < n and text[j] != quote:
                if text[j] == "{":                     # interpolation, keep it
                    depth = 1
                    j += 1
                    while j < n and depth:
                        depth += (text[j] == "{") - (text[j] == "}")
                        j += 1
                    continue
                out[j] = " "
                j += 1
            out[i] = " "
            if j < n:
                out[j] = " "
            i = j + 1
            continue
        i += 1
    return "".join(out)


def _names(path):
    with open(path, encoding="utf-8") as fh:
        return {m.group(1) for m in DEF.finditer(fh.read())}


def defined_formulas():
    names = set()
    for f in sorted(os.listdir(FX)):
        if f.endswith(".fx"):
            names |= _names(os.path.join(FX, f))
    return names


def _files(sub):
    return {f[: -len(".pa.yaml")]
            for f in os.listdir(os.path.join(SRC, sub))
            if f.endswith(".pa.yaml")}


def workflows():
    d = os.path.join(ROOT, "solution", "src", "Workflows")
    return {f.split("-")[0] for f in os.listdir(d) if f.endswith(".json")}


def squash(name):
    return re.sub(r"[^A-Za-z0-9]", "", name).lower()


def main():
    display_names = {l.title for l in S.LISTS}
    known_formulas = defined_formulas()
    known_screens = _files("Screens")
    known_components = _files("Components")
    known_flows = {squash(w) for w in workflows()}

    problems = []
    for rel, line, _prop, raw in all_formulas():
        text = strip_strings(raw)

        for m in re.finditer(r"'((?:MF|Mission)[^']*)'", raw):
            if m.group(1) not in display_names:
                problems.append((rel, line, "data source", m.group(1)))

        # Only a BARE identifier is checked. Navigate(If(...)) and
        # Navigate(MF_StartScreen) are both legitimate.
        for m in re.finditer(r"Navigate\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*[,)]", text):
            n = m.group(1)
            if n not in known_screens and n not in known_formulas:
                problems.append((rel, line, "screen", n))

        for m in re.finditer(r"([A-Za-z0-9_]+)\.Run\(", text):
            if squash(m.group(1)) not in known_flows:
                problems.append((rel, line, "flow", m.group(1)))

        for m in OURS.finditer(text):
            if m.group(1) not in known_formulas:
                problems.append((rel, line, "formula", m.group(1)))

    for base, _d, files in os.walk(SRC):
        for f in sorted(files):
            if not f.endswith(".pa.yaml"):
                continue
            p = os.path.join(base, f)
            rel = os.path.relpath(p, ROOT)
            for i, ln in enumerate(open(p, encoding="utf-8"), 1):
                m = re.search(r"ComponentName:\s*([A-Za-z_][A-Za-z0-9_]*)", ln)
                if m and m.group(1) not in known_components:
                    problems.append((rel, i, "component", m.group(1)))

    print("Canvas reference check")
    print("=" * 58)
    print(f"  {len(display_names)} list display names")
    print(f"  {len(known_screens)} screens, {len(known_components)} components")
    print(f"  {len(known_flows)} flows, {len(known_formulas)} named formulas")
    print()

    if problems:
        seen = sorted(set(problems))
        print(f"UNRESOLVED ({len(seen)})")
        for rel, line, kind, name in seen:
            print(f"  {rel}:{line}  {kind} '{name}' does not exist")
        print("\nA wrong data-source or column name does not error in a canvas")
        print("app. It returns blank and the screen reads as nothing due.")
        return 1

    print("Every data source, screen, component, flow and formula resolves.")
    print()
    print("NOT VERIFIABLE HERE: the exact identifier Studio generates for a")
    print("flow display name. This matches on alphanumerics, so EOM02_Submission")
    print("and EOM02Submission both resolve. Studio shows an error on the")
    print("formula if it disagrees -- unlike a wrong list name, that failure is")
    print("visible. CANVAS_APP_ASSEMBLY.md carries the check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
