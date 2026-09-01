#!/usr/bin/env python3
"""Figma -> Canvas design-parity gate.

The Figma package (reference/figma-build) is the VISUAL source of truth; the
canvas source (canvas-app/src) is the FUNCTIONAL source of truth; the parity
contract between them is configuration/figma-canvas-map.json, narrated in
docs/FIGMA_CANVAS_PARITY.md.

This gate verifies, from the actual files:

  1. TOKENS   every clr* token in App.Formulas.fx matches the approved value
              recorded in the map, byte for byte, and every mapped token is
              actually defined. Amber and yellow are never merged.
  2. LITERALS no ColorValue()/RGBA() colour literal anywhere in Screens/ or
              Components/ -- colour is declared once, in App.Formulas.fx.
  3. DEFAULTS every screen sets Fill from a token: a screen that falls back
              to default Power Apps styling fails the gate (FUNCTIONAL
              DESIGN DRIFT, per the fidelity directive).
  4. NAV      the tabs a base user sees are exactly the approved BASE_TABS
              (Home / My Package / Calendar); Submit, request-access and
              unmatched-classification are never tabs; every nav screen
              exists.
  5. CHIP     cmpStatusBadge structurally matches the StatusChip spec:
              1px status border, radius 2, colour via MF_StatusColor /
              MF_StatusBackground (label + icon, never colour alone).
  6. MAP      the map covers every canvas screen and every Figma screen
              file, uses only real identifiers, and carries no FAIL row.
  7. RUNTIME  no external runtime fetch (CDN / fonts / blob) in canvas
              source -- asset fidelity means no network dependency.

Exit 0 only when every check passes. This script never talks to the network
and never modifies anything. Do not weaken it to make a build pass: fix the
source or, for an approved deviation, record it in the map WITH a rationale.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "canvas-app" / "src"
FORMULAS = ROOT / "canvas-app" / "formulas"
MAP_PATH = ROOT / "configuration" / "figma-canvas-map.json"
FIGMA_SCREENS = ROOT / "reference" / "figma-build" / "src" / "screens"

VALID_PARITY = {"PASS", "MINOR DRIFT", "PLATFORM SUBSTITUTION", "FAIL"}

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


# ---------------------------------------------------------------- tokens
def check_tokens(mapping: dict) -> None:
    text = (FORMULAS / "App.Formulas.fx").read_text(encoding="utf-8")
    defined: dict[str, str] = {}
    for m in re.finditer(
        r'^(clr[A-Z][A-Za-z0-9_]*)\s*=\s*ColorValue\("(#[0-9A-Fa-f]{6})"\);',
        text, re.M,
    ):
        defined[m.group(1)] = m.group(2).upper()

    approved = mapping["tokens"]["map"]
    for name, spec in approved.items():
        want = spec["canvas"].upper()
        got = defined.get(name)
        if got is None:
            fail(f"token {name}: in the map but not defined in App.Formulas.fx")
        elif got != want:
            fail(f"token {name}: App.Formulas.fx has {got}, map approves {want}")

    for name in defined:
        if name not in approved:
            fail(f"token {name}: defined in App.Formulas.fx but missing from the map "
                 f"-- every colour token must be in the parity contract")

    # The six-state guarantee: amber and yellow are distinct inks and fills.
    if defined.get("clrStatusAmber") == defined.get("clrStatusYellow"):
        fail("clrStatusAmber == clrStatusYellow: the amber/yellow separation is the "
             "whole point of six states and may never be merged")
    if defined.get("clrStatusAmberBg") == defined.get("clrStatusYellowBg"):
        fail("clrStatusAmberBg == clrStatusYellowBg: never merge the fills either")


# ------------------------------------------------------------- literals
def check_no_colour_literals() -> None:
    for f in sorted(list((SRC / "Screens").glob("*.pa.yaml"))
                    + list((SRC / "Components").glob("*.pa.yaml"))):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0] if line.lstrip().startswith("#") else line
            if "ColorValue(" in code or "RGBA(" in code:
                fail(f"{f.relative_to(ROOT)}:{i}: colour literal outside "
                     f"App.Formulas.fx -- use a clr* token")


# ------------------------------------------------------------- defaults
def check_screen_fills() -> None:
    for f in sorted((SRC / "Screens").glob("*.pa.yaml")):
        text = f.read_text(encoding="utf-8")
        if not re.search(r"^\s+Fill:\s*=clr[A-Z]", text, re.M):
            fail(f"{f.name}: screen does not set Fill from a token -- default "
                 f"Power Apps styling is FUNCTIONAL DESIGN DRIFT")


# ------------------------------------------------------------------ nav
NAV_ENTRY = re.compile(
    r'\{\s*key:\s*"([^"]+)",\s*label:\s*"([^"]+)",\s*screen:\s*"([^"]+)",'
    r'\s*flag:\s*"([^"]*)",\s*need:\s*"([^"]+)"\s*\}'
)


def check_nav(mapping: dict, screen_names: set[str]) -> None:
    text = (FORMULAS / "App.Formulas.fx").read_text(encoding="utf-8")
    entries = NAV_ENTRY.findall(text)
    if not entries:
        fail("colNavigation: no entries parsed from App.Formulas.fx")
        return

    base_labels = [label for _, label, _, _, need in entries if need == "all"]
    want_base = mapping["navigation"]["base_tabs"]
    if base_labels != want_base:
        fail(f"base nav is {base_labels}, approved BASE_TABS is {want_base} "
             f"(Submit is a primary action, never a tab)")

    labels = {label for _, label, _, _, _ in entries}
    for banned in ("Submit", "Upload", "Request access", "Request Access",
                   "Unmatched", "Classify"):
        if banned in labels:
            fail(f"nav contains '{banned}': reached by action/row in the approved "
                 f"design, never a tab")

    for key, label, screen, _flag, _need in entries:
        if screen not in screen_names:
            fail(f"nav '{key}' targets {screen}, which is not a screen file")

    afsvc_visible = {label for _, label, _, _, need in entries
                     if need in ("all", "qc", "admin")}
    for tab in mapping["navigation"]["afsvc_tabs"]:
        if tab not in afsvc_visible:
            fail(f"approved AFSVC tab '{tab}' is not reachable in colNavigation")


# ----------------------------------------------------------------- chip
def check_status_chip() -> None:
    f = SRC / "Components" / "cmpStatusBadge.pa.yaml"
    text = f.read_text(encoding="utf-8")
    checks = [
        (r"BorderThickness:\s*=1\b", "1px status border"),
        (r"RadiusTopLeft:\s*=2\b", "radius 2 (StatusChip spec)"),
        (r"BorderColor:\s*=MF_StatusColor\(", "border colour from MF_StatusColor"),
        (r"MF_StatusBackground\(", "fill from MF_StatusBackground"),
    ]
    for pattern, what in checks:
        if not re.search(pattern, text):
            fail(f"cmpStatusBadge: missing {what}")


# ------------------------------------------------------------------ map
def check_map(mapping: dict, screen_names: set[str], comp_names: set[str]) -> None:
    mapped_canvas: set[str] = set()
    for row in mapping["screens"]:
        parity = row["parity"]
        if parity not in VALID_PARITY:
            fail(f"map screens[{row['figma']}]: parity '{parity}' is not one of "
                 f"{sorted(VALID_PARITY)}")
        if parity == "FAIL":
            fail(f"map screens[{row['figma']}]: parity FAIL blocks release")
        if parity in ("MINOR DRIFT", "PLATFORM SUBSTITUTION") and not row.get("note"):
            fail(f"map screens[{row['figma']}]: {parity} requires a rationale note")
        tsx = FIGMA_SCREENS / row["figma"]
        if not tsx.is_file():
            fail(f"map screens[{row['figma']}]: no such Figma screen file")
        cv = row["canvas"]
        if cv is None:
            continue
        if cv == "App":
            mapped_canvas.add("App")
        elif cv in screen_names or cv in comp_names:
            mapped_canvas.add(cv)
        else:
            fail(f"map screens[{row['figma']}]: canvas '{cv}' does not exist")

    for row in mapping.get("canvas_only_screens", []):
        cv = row["canvas"]
        if cv not in screen_names:
            fail(f"map canvas_only_screens: '{cv}' does not exist")
        if not row.get("origin"):
            fail(f"map canvas_only_screens '{cv}': needs an origin -- a screen "
                 f"with no design source is an invented requirement")
        mapped_canvas.add(cv)

    for name in sorted(screen_names - mapped_canvas):
        fail(f"canvas screen {name} is not in the parity map")

    mapped_figma = {row["figma"] for row in mapping["screens"]}
    for tsx in sorted(FIGMA_SCREENS.glob("*.tsx")):
        if tsx.name not in mapped_figma:
            fail(f"Figma screen {tsx.name} is not in the parity map")

    mapped_comps = set()
    for row in mapping["components"]:
        if row["parity"] not in VALID_PARITY:
            fail(f"map components[{row['figma']}]: invalid parity")
        if row["parity"] == "FAIL":
            fail(f"map components[{row['figma']}]: parity FAIL blocks release")
        if row["canvas"] not in comp_names:
            fail(f"map components[{row['figma']}]: canvas '{row['canvas']}' "
                 f"does not exist")
        mapped_comps.add(row["canvas"])
    for name in sorted(comp_names - mapped_comps):
        fail(f"canvas component {name} is not in the parity map")


# -------------------------------------------------------------- runtime
RUNTIME_FETCH = re.compile(
    r"https?://|cdn\.|fonts\.googleapis|figma\.com|\.blob\.", re.I)


def check_no_runtime_fetches() -> None:
    for f in sorted(SRC.rglob("*.pa.yaml")) + sorted(FORMULAS.glob("*.fx")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith(("#", "//")):
                continue  # commentary may cite docs URLs; formulas may not
            if RUNTIME_FETCH.search(line):
                fail(f"{f.relative_to(ROOT)}:{i}: external runtime reference -- "
                     f"the app must render with zero network fetches beyond "
                     f"its data sources")


def main() -> int:
    mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    screen_names = {f.stem.removesuffix(".pa")
                    for f in (SRC / "Screens").glob("*.pa.yaml")}
    comp_names = {f.stem.removesuffix(".pa")
                  for f in (SRC / "Components").glob("*.pa.yaml")}

    if len(screen_names) != 16:
        fail(f"expected 16 screens, found {len(screen_names)}")
    if len(comp_names) != 6:
        fail(f"expected 6 components, found {len(comp_names)}")

    check_tokens(mapping)
    check_no_colour_literals()
    check_screen_fills()
    check_nav(mapping, screen_names)
    check_status_chip()
    check_map(mapping, screen_names, comp_names)
    check_no_runtime_fetches()

    if failures:
        print("DESIGN PARITY: FAIL")
        for f in failures:
            print(f"  {f}")
        return 1

    print("DESIGN PARITY: PASS")
    print(f"  {len(screen_names)} screens, {len(comp_names)} components, "
          f"{len(mapping['tokens']['map'])} tokens verified against "
          f"configuration/figma-canvas-map.json")
    print("  NOT TESTABLE LOCALLY: how Studio actually renders these screens. "
          "The Studio-open visual gate in CANVAS_APP_ASSEMBLY.md covers that; "
          "this gate proves the source can only draw from approved tokens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
