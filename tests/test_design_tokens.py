"""Colour tokens, measured rather than asserted by eye.

Amber and yellow shipped 1.16:1 apart in the canvas app and 1.25:1 apart in the
Figma build — two near-identical browns under a model whose entire point is that
colour carries OWNERSHIP. Amber means the base still owes it and still has
runway; yellow means AFSVC has it and the base owes nothing. At 1.2:1 nobody can
tell which of those they are looking at.

Every number here is computed from the tokens actually in the source files. A
comment claiming 4.5:1 is not evidence; this is.
"""

import math
import os
import re
import unittest
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# --- colour maths ---------------------------------------------------------

def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(hexs):
    h = hexs.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def luminance(hexs):
    r, g, b = (_lin(v) for v in _rgb(hexs))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def to_lab(hexs):
    r, g, b = (_lin(v) for v in _rgb(hexs))
    X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    Xn, Yn, Zn = 0.95047, 1.0, 1.08883

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(X / Xn), f(Y / Yn), f(Z / Zn)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def hue_angle(hexs):
    _, a, b = to_lab(hexs)
    return math.degrees(math.atan2(b, a)) % 360


def delta_e2000(h1, h2):
    L1, a1, b1 = to_lab(h1)
    L2, a2, b2 = to_lab(h2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))) if Cb else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dTh = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) if Cbp else 0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dTh)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


CVD = {
    "deuteranopia": [[.625, .375, 0], [.70, .30, 0], [0, .30, .70]],
    "protanopia": [[.567, .433, 0], [.558, .442, 0], [0, .242, .758]],
    "tritanopia": [[.95, .05, 0], [0, .433, .567], [0, .475, .525]],
}


def simulate(hexs, kind):
    m = CVD[kind]
    v = [_lin(c) for c in _rgb(hexs)]
    out = [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]

    def enc(c):
        c = max(0.0, min(1.0, c))
        c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        return int(round(c * 255))

    return "#%02X%02X%02X" % tuple(enc(c) for c in out)


# --- the tokens -----------------------------------------------------------

def canvas_tokens():
    text = read("canvas-app", "formulas", "App.Formulas.fx")
    found = dict(re.findall(
        r'^(clr[A-Za-z]+)\s*=\s*ColorValue\("(#[0-9A-Fa-f]{6})"\)',
        text, re.M))
    # Two tokens share a line, so also sweep inline definitions.
    found.update(dict(re.findall(
        r'(clr[A-Za-z]+)\s*=\s*ColorValue\("(#[0-9A-Fa-f]{6})"\)', text)))
    return found


PAIRS = [("clrStatusBlue", "clrStatusBlueBg"),
         ("clrStatusAmber", "clrStatusAmberBg"),
         ("clrStatusYellow", "clrStatusYellowBg"),
         ("clrStatusRed", "clrStatusRedBg"),
         ("clrStatusGreen", "clrStatusGreenBg"),
         ("clrStatusGray", "clrStatusGrayBg")]


class SixStatesExist(unittest.TestCase):
    def test_all_six_chip_pairs_are_declared(self):
        tokens = canvas_tokens()
        for fg, bg in PAIRS:
            self.assertIn(fg, tokens)
            self.assertIn(bg, tokens)


class EveryChipIsReadable(unittest.TestCase):
    def test_each_chip_clears_four_point_five_to_one(self):
        tokens = canvas_tokens()
        for fg, bg in PAIRS:
            ratio = contrast(tokens[fg], tokens[bg])
            self.assertGreaterEqual(
                ratio, 4.5,
                f"{fg} {tokens[fg]} on {tokens[bg]} is {ratio:.2f}:1")

    def test_body_text_clears_the_gate(self):
        tokens = canvas_tokens()
        self.assertGreaterEqual(contrast(tokens["clrText"], tokens["clrSurface"]), 4.5)
        self.assertGreaterEqual(
            contrast(tokens["clrTextSecondary"], tokens["clrSurface"]), 4.5)


class AmberIsNotYellow(unittest.TestCase):
    """The defect this file exists for."""

    def setUp(self):
        t = canvas_tokens()
        self.amber, self.amber_bg = t["clrStatusAmber"], t["clrStatusAmberBg"]
        self.yellow, self.yellow_bg = t["clrStatusYellow"], t["clrStatusYellowBg"]

    def test_they_are_not_the_old_collision(self):
        # #8A5300 and #6B5300, 1.16:1 apart.
        self.assertNotEqual(self.amber.upper(), "#8A5300")
        self.assertNotEqual(self.yellow.upper(), "#6B5300")

    def test_they_are_perceptually_far_apart(self):
        # dE2000 above ~5 is unambiguous to a casual observer. The old pair was
        # 10.5 and still unreadable at a glance, so the bar here is 20.
        de = delta_e2000(self.amber, self.yellow)
        self.assertGreaterEqual(de, 20.0, f"amber vs yellow dE2000 is only {de:.1f}")

    def test_their_hues_are_far_apart(self):
        # Amber is orange, yellow is gold. Luminance contrast cannot express
        # this -- two colours differing only in hue sit at 1.0:1 -- so hue
        # separation is the measure that answers the actual question.
        dh = abs(hue_angle(self.amber) - hue_angle(self.yellow))
        dh = min(dh, 360 - dh)
        self.assertGreaterEqual(dh, 30.0, f"only {dh:.0f} degrees apart")

    def test_their_backgrounds_differ_too(self):
        de = delta_e2000(self.amber_bg, self.yellow_bg)
        self.assertGreaterEqual(de, 5.0,
                                f"chip fills are {de:.1f} apart; the tint is the "
                                "first thing seen at a glance")

    def test_the_split_survives_colour_vision_deficiency(self):
        for kind in CVD:
            de = delta_e2000(simulate(self.amber, kind), simulate(self.yellow, kind))
            self.assertGreaterEqual(
                de, 8.0, f"under {kind} amber and yellow are only {de:.1f} apart")

    def test_neither_collides_with_red(self):
        # Amber moving toward orange must not arrive at red: red means no
        # runway left, amber means there is still some.
        red = canvas_tokens()["clrStatusRed"]
        self.assertGreaterEqual(delta_e2000(self.amber, red), 15.0)


class TheDocumentedRatiosAreTrue(unittest.TestCase):
    """A table of ratios nobody recomputed is how the old numbers ended up
    understated by three points."""

    def test_accessibility_table_matches_the_tokens(self):
        doc = read("docs", "accessibility.md")
        tokens = canvas_tokens()
        rows = re.findall(
            r"\|\s*`(clr\w+)`\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|\s*([\d.]+):1",
            doc)
        self.assertGreaterEqual(len(rows), 6, "the token table is missing rows")
        for name, fg, bg, claimed in rows:
            self.assertEqual(tokens[name].upper(), fg.upper(),
                             f"{name} in the doc is not the token in the source")
            actual = contrast(fg, bg)
            self.assertAlmostEqual(
                actual, float(claimed), delta=0.1,
                msg=f"{name} claims {claimed}:1, measures {actual:.2f}:1")


class ThePrototypeTeachesSixStates(unittest.TestCase):
    def setUp(self):
        self.html = read("docs", "mf-operations-prototype.html")

    def test_there_is_a_sixth_chip_class(self):
        self.assertRegex(self.html, r"\.c5\{")

    def test_yellow_and_amber_are_separate_variables(self):
        self.assertIn("--yellow:", self.html)
        self.assertIn("--amber:", self.html)

    def test_the_prototype_pair_is_also_far_apart(self):
        def var(name):
            return re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", self.html).group(1)
        de = delta_e2000(var("amber"), var("yellow"))
        self.assertGreaterEqual(de, 20.0, f"prototype pair is {de:.1f} apart")

    def test_the_prototype_chips_are_readable(self):
        def var(name):
            return re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", self.html).group(1)
        for fg, bg in (("amber", "amber-bg"), ("yellow", "yellow-bg")):
            self.assertGreaterEqual(contrast(var(fg), var(bg)), 4.5)


class ThePeriodSelectorIsGenerated(unittest.TestCase):
    """Figma defect 2, as a regression test.

    The Figma build hardcoded four months in the shared TopBar while its own
    Calendar screen called the generator that already existed — so every screen
    but one had a dead dropdown that would go stale in December. The canvas
    source generates the list; this keeps it that way.
    """

    def test_the_app_generates_the_period_list(self):
        fx = read("canvas-app", "formulas", "App.Formulas.fx")
        self.assertIn("MF_SelectablePeriods", fx)
        self.assertRegex(fx, r"MF_SelectablePeriods\s*=")

    def test_the_home_screen_binds_to_the_generator(self):
        home = read("canvas-app", "src", "Screens", "scrHome.pa.yaml")
        self.assertIn("Items: =MF_SelectablePeriods", home)

    def test_no_screen_hardcodes_a_month_name(self):
        # A literal month in a picker is a dropdown that expires.
        months = ("January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December")
        for base, _, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for name in files:
                if not name.endswith(".pa.yaml"):
                    continue
                path = os.path.join(base, name)
                with open(path, encoding="utf-8") as fh:
                    body = fh.read()
                for line in body.splitlines():
                    if line.lstrip().startswith("#") or "Items:" not in line:
                        continue
                    for month in months:
                        self.assertNotIn(
                            month, line,
                            f"{os.path.relpath(path, ROOT)} hardcodes {month} "
                            "in a picker")


class EveryInteractiveControlHasAName(unittest.TestCase):
    """Figma defect 3, as a regression test.

    The Figma build had zero aria-labels across 31 buttons, several of them
    icon-only — the help button and the calendar arrows announce nothing. That
    is a straight 508 gate failure. In Power Apps the equivalent is
    AccessibleLabel, and an icon-only control without one is a control a screen
    reader cannot name.
    """

    def controls(self):
        for base, _, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for name in sorted(files):
                if not name.endswith(".pa.yaml"):
                    continue
                path = os.path.join(base, name)
                with open(path, encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
                for i, line in enumerate(lines):
                    m = re.match(r"^(\s*)- (\w+):\s*$", line)
                    if not m:
                        continue
                    indent = m.group(1)
                    block = []
                    for j in range(i + 1, min(i + 60, len(lines))):
                        if lines[j].strip() and not lines[j].startswith(indent + "  "):
                            break
                        block.append(lines[j])
                    yield (os.path.relpath(path, ROOT), i + 1, m.group(2),
                           "\n".join(block))

    def test_every_icon_and_button_declares_an_accessible_label(self):
        offenders = [
            f"{path}:{line} {name}"
            for path, line, name, block in self.controls()
            if re.search(r"Control:\s*(Icon|Button|Classic/Button)", block)
            and "AccessibleLabel" not in block
        ]
        self.assertEqual(offenders, [], "controls a screen reader cannot name")

    def test_there_are_controls_to_check(self):
        # A test that silently checks nothing is worse than no test.
        found = [c for c in self.controls()
                 if re.search(r"Control:\s*(Icon|Button|Classic/Button)", c[3])]
        self.assertGreater(len(found), 5)


class NothingTheAdminOwnsIsHardcoded(unittest.TestCase):
    """The five values the Figma build baked into components.

    The defaults are fine. What matters is that changing one is a list edit,
    not a code edit — and that two facts which must agree have one source.
    """

    def setUp(self):
        import csv
        with open(os.path.join(ROOT, "configuration", "app-config.csv"),
                  encoding="utf-8-sig") as fh:
            self.cfg = {r["Config_Key"]: r for r in csv.DictReader(fh)}
        with open(os.path.join(ROOT, "configuration", "requirements.csv"),
                  encoding="utf-8-sig") as fh:
            self.reqs = list(csv.DictReader(fh))
        self.fx = read("canvas-app", "formulas", "App.Formulas.fx")

    def test_upload_size_is_configuration(self):
        self.assertIn("MaxUploadSizeMB", self.cfg)
        self.assertIn('MF_ConfigNumber("MaxUploadSizeMB"', self.fx)

    def test_accepted_file_types_live_on_the_requirement(self):
        # Per requirement: a 1119 and a bank statement are not the same file.
        for req in self.reqs:
            self.assertIn("Accepted_File_Types", req)

    def test_the_review_age_threshold_is_configuration(self):
        self.assertIn("ReviewAgeHighlightDays", self.cfg)
        self.assertIn('MF_ConfigNumber("ReviewAgeHighlightDays"', self.fx)

    def test_the_age_bands_are_derived_from_the_threshold(self):
        # Four hardcoded buckets beside a separately hardcoded threshold is two
        # facts that must agree with nothing making them agree.
        self.assertIn("MF_ReviewAgeBands", self.fx)
        block = self.fx.split("MF_ReviewAgeBands")[1].split(";")[0]
        self.assertIn("gblReviewAgeDays", block)
        for literal in ("Low: 2", "High: 3", "Low: 4", "High: 5", "Low: 6"):
            self.assertNotIn(literal, block, "a band is hardcoded")

    def test_the_suspense_days_live_on_the_requirement_row(self):
        # Not a default in the date code. The 5th and the 10th do not have the
        # same standing, and a shared default makes both unchallengeable.
        for req in self.reqs:
            self.assertTrue(req["Due_Day"].strip(), req["Requirement_ID"])
            self.assertTrue(req["Final_Due_Day"].strip(), req["Requirement_ID"])

    def test_the_engine_takes_the_dates_rather_than_defaulting_them(self):
        engine = read("scripts", "status_engine.py")
        signature = engine.split("def item_status(")[1].split(")")[0]
        for name in ("effective_due_date", "effective_final_call_date"):
            self.assertIn(name, signature)
            self.assertNotRegex(signature, rf"{name}\s*=\s*\d")


class ColourIsNeverTheOnlyChannel(unittest.TestCase):
    """The real 508 guarantee. Hue makes six scannable; text makes them
    readable, in greyscale and by a screen reader."""

    def test_every_chip_carries_a_text_label(self):
        badge = read("canvas-app", "src", "Components", "cmpStatusBadge.pa.yaml")
        self.assertIn("Text:", badge)

    def test_the_engine_supplies_an_accessible_label(self):
        fx = read("canvas-app", "formulas", "StatusEngine.fx")
        self.assertIn("MF_StatusAccessibleLabel", fx)

    def test_the_prototype_chips_carry_a_non_colour_glyph(self):
        html = read("docs", "mf-operations-prototype.html")
        self.assertIn(".chip.c5::before", html)


class NoCountIsReportedWithoutItsDenominator(unittest.TestCase):
    """The single most important line to come out of the last build run:
    a not-onboarded installation is not compliant, it has not been asked.

    103 installations ship Generation_Enabled FALSE and contribute no rows to
    the fact table, so a percentage over the rows that exist reports 100% while
    most of the enterprise has never been brought into the system.
    """

    def setUp(self):
        self.bi = read("powerbi", "MF_EOM_Status.md")
        self.native = read("docs", "native-visuals.md")

    def test_the_onboarding_denominator_is_a_measure(self):
        self.assertIn("Installations onboarded", self.bi)
        self.assertIn("Installations not yet onboarded", self.bi)

    def test_the_completion_measure_carries_its_population(self):
        self.assertIn("Completion statement", self.bi)
        block = self.bi.split("Completion statement")[1][:900]
        self.assertIn("[Installations onboarded]", block)
        self.assertIn("not yet onboarded", block)

    def test_every_measure_the_statement_uses_is_defined(self):
        block = self.bi.split("Completion statement")[1][:900]
        for used in re.findall(r"\[([A-Z][A-Za-z ]+)\]", block):
            self.assertRegex(
                self.bi, rf"(?m)^{re.escape(used)}\s*=",
                f"Completion statement uses [{used}], which is never defined")

    def test_both_documents_say_it_in_words(self):
        for doc in (self.bi, self.native):
            self.assertRegex(doc, r"(?i)not[- ]onboarded installation is not compliant")

    def test_the_in_app_bar_separates_amber_from_yellow(self):
        # Merging "the base owes this and has time" with "AFSVC is holding it"
        # gives a DFAC manager a number they cannot act on.
        self.assertIn("Status_Code = 5", self.native)
        self.assertIn("Status_Code = 2", self.native)

    def test_the_chart_controls_stay_prohibited(self):
        # ~50-row cap, no theming, poor screen-reader support. At 103
        # installations a portfolio comparison silently shows part of the data
        # and reports success -- the same failure as a non-delegable Filter().
        self.assertRegex(self.native, r"(?i)do not use the chart controls")
        self.assertIn("FillPortions", self.native)


if __name__ == "__main__":
    unittest.main()


class TheCanvasSourceIsExtractable(unittest.TestCase):
    """The .pa.yaml is the app's source, and the formula extractor is what
    lets a real Power Fx engine see it. If extraction silently returns little,
    `scripts/check_powerfx.py` passes by looking at nothing -- the shape of
    failure this whole build keeps finding."""

    def setUp(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import canvas_formulas
        self.items = list(canvas_formulas.all_formulas())

    def test_every_expected_file_contributes(self):
        """A NAMED list, not a total.

        The first version of this asserted a file COUNT, and the count was
        right while `Delegation.fx` contributed zero formulas -- the regex did
        not handle its `Name(a: Text): Table =` signatures. So the file that
        decides whether every query delegates was never parsed, and the total
        looked healthy because the other twenty made it up. A count cannot
        catch that. A list can.
        """
        found = {i[0] for i in self.items}
        for rel in ("canvas-app/formulas/App.Formulas.fx",
                    "canvas-app/formulas/StatusEngine.fx",
                    "canvas-app/formulas/Delegation.fx",
                    "canvas-app/formulas/Cascade.fx",
                    "canvas-app/src/App.pa.yaml"):
            self.assertIn(rel, found)
        for d, ext in (("Screens", ".pa.yaml"), ("Components", ".pa.yaml")):
            here = os.path.join(ROOT, "canvas-app", "src", d)
            for f in os.listdir(here):
                if f.endswith(ext):
                    rel = f"canvas-app/src/{d}/{f}"
                    self.assertIn(rel, found,
                                  f"{rel} contributed no formulas at all")

    def test_it_finds_a_realistic_number_of_formulas(self):
        # 1,300 at the time of writing. A floor, not an equality: adding a
        # control should not fail this, gutting the extractor should.
        self.assertGreater(len(self.items), 1300)

    def test_block_scalars_are_captured_whole(self):
        # The multi-line `Key: |` form carries the OnStart and every OnSelect.
        # An extractor that only handled `Key: =expr` would miss the behaviour
        # of the entire app and still report a healthy count.
        onstart = [i for i in self.items
                   if i[0].endswith("App.pa.yaml") and i[2] == "OnStart"]
        self.assertEqual(len(onstart), 1)
        self.assertIn("Concurrent", onstart[0][3])
        self.assertGreater(onstart[0][3].count("\n"), 5)

    def test_the_checker_refuses_to_pass_silently_without_pac(self):
        # An unavailable checker must not read as a passing one.
        src = read(os.path.join(ROOT, "scripts", "check_powerfx.py"))
        self.assertIn("SKIPPED", src)
        self.assertIn("An unavailable checker is not a passing one", src)


class CanvasChecksAreWired(unittest.TestCase):
    """The two canvas audits run as part of the suite, and fail it.

    A checker nobody runs is documentation. These two exist because the
    failures they catch are silent in a canvas app: a wrong list name renders
    an empty gallery, and a non-delegable query returns the first 500 rows and
    reports success. Neither surfaces as an error at run time.
    """

    def _run(self, script):
        import subprocess
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", script)],
            capture_output=True, text=True, cwd=ROOT)

    def test_every_reference_resolves(self):
        r = self._run("canvas_reference_check.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_query_delegates(self):
        r = self._run("canvas_delegation_check.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_delegation_check_reports_rather_than_rounding_up(self):
        # Two predicates sit on unindexed columns inside an OR behind indexed
        # leading predicates. That is genuinely uncertain without a >5,000-item
        # list on the real tenant, and the checker must say so rather than
        # print a clean pass.
        r = self._run("canvas_delegation_check.py")
        self.assertIn("NOT VERIFIABLE LOCALLY", r.stdout)
        self.assertIn("That is a report, not a pass", r.stdout)


class TheApprovedScreenSetIsPresent(unittest.TestCase):
    """POLICY. The approved set, named.

    A count would pass while a screen was missing and another duplicated.
    """

    APPROVED = {
        "scrHome", "scrMyPackage", "scrOverview", "scrInstallations",
        "scrExceptions", "scrUpload", "scrReview", "scrInstallation",
        "scrCalendar", "scrActivity", "scrAdminRequirements", "scrUnmatched",
        "scrDiagnostics", "scrMaintenance", "scrNoAccess", "scrAccessRequest",
    }

    def test_the_screen_set_is_exactly_the_approved_set(self):
        here = os.path.join(ROOT, "canvas-app", "src", "Screens")
        found = {f[:-len(".pa.yaml")] for f in os.listdir(here)
                 if f.endswith(".pa.yaml")}
        self.assertEqual(found, self.APPROVED)

    def test_scrupload_keeps_its_name(self):
        # The UX calls it Submit. Renaming a settled source is churn, and the
        # repo name is the one every formula and test already uses.
        self.assertTrue(os.path.exists(os.path.join(
            ROOT, "canvas-app", "src", "Screens", "scrUpload.pa.yaml")))

    def test_the_new_screens_each_read_a_real_source_or_flow(self):
        # Wire, do not decorate. A screen that renders without touching data
        # is a mock-up that passes every structural test.
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import canvas_formulas
        by_file = {}
        for rel, _l, _p, text in canvas_formulas.all_formulas():
            by_file.setdefault(rel, []).append(text)
        for scr in ("scrMyPackage", "scrOverview", "scrInstallations",
                    "scrExceptions"):
            rel = f"canvas-app/src/Screens/{scr}.pa.yaml"
            blob = " ".join(by_file[rel])
            self.assertRegex(blob, r"MF_[A-Za-z]+\(|'MF [A-Za-z ]+'",
                             f"{scr} touches no list and no helper")


class TheSourceIsRealYaml(unittest.TestCase):
    """Every .pa.yaml file must parse with a real YAML parser.

    TEN of the twenty-two source files did not, for the whole life of this
    repository -- inline formulas carrying record literals (`=[{ Period:
    gblOpenPeriod }]`) contain ': ', which a plain YAML scalar cannot. The
    regex-based tests read them happily; Studio's parser would have rejected
    the paste on the spot, an hour into the operator's session. Every checker
    before this one was blind to it because none of them parsed YAML.
    """

    def test_every_source_file_parses(self):
        import yaml
        bad = []
        for base, _d, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for f in sorted(files):
                if f.endswith(".pa.yaml"):
                    p = os.path.join(base, f)
                    try:
                        yaml.safe_load(open(p, encoding="utf-8"))
                    except yaml.YAMLError as exc:
                        bad.append(f"{os.path.relpath(p, ROOT)}: {exc}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_children_are_never_nested_inside_properties(self):
        # scrMaintenance shipped with Children indented under Properties. The
        # regex tests could not see nesting; a YAML parser can.
        import yaml
        for base, _d, files in os.walk(os.path.join(ROOT, "canvas-app", "src")):
            for f in sorted(files):
                if not f.endswith(".pa.yaml"):
                    continue
                doc = yaml.safe_load(open(os.path.join(base, f),
                                          encoding="utf-8"))
                for screens in (doc or {}).get("Screens", {}).values():
                    props = (screens or {}).get("Properties") or {}
                    self.assertNotIn("Children", props, f)


class TheMsappSourceIsFreshAndValid(unittest.TestCase):
    """canvas-app/msapp-src is GENERATED from canvas-app/src and validated
    against Microsoft's published pa.yaml v3 schema.

    The generator exists because `pac canvas pack` validates NOTHING -- fed a
    structurally broken file and a nonexistent control type, it reported
    "Packing succeeded" both times. So schema validation lives here, and the
    calibration standard is Studio's own output: the genuine donor app must
    pass the same validator this enforces.
    """

    def _run(self, script, *args):
        import subprocess
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", script), *args],
            capture_output=True, text=True, cwd=ROOT)

    def test_the_generated_source_is_fresh(self):
        import subprocess, tempfile, filecmp
        live = os.path.join(ROOT, "canvas-app", "msapp-src")
        with tempfile.TemporaryDirectory() as td:
            backup = os.path.join(td, "msapp-src")
            import shutil
            shutil.copytree(live, backup)
            try:
                r = self._run("gen_msapp_source.py")
                self.assertEqual(r.returncode, None if False else 0,
                                 r.stdout + r.stderr)
                diff = filecmp.dircmp(live, backup)
                stale = []
                def walk(dc):
                    stale.extend(dc.diff_files)
                    stale.extend(dc.left_only)
                    stale.extend(dc.right_only)
                    for sub in dc.subdirs.values():
                        walk(sub)
                walk(diff)
                self.assertEqual(stale, [],
                                 "msapp-src is stale; run gen_msapp_source.py")
            finally:
                shutil.rmtree(live)
                shutil.copytree(backup, live)

    def test_it_passes_the_official_schema(self):
        r = self._run("validate_msapp_source.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("No violations", r.stdout)

    def test_the_validator_is_not_vacuous(self):
        # It must fail on the class of defect it exists for.
        import tempfile, shutil
        src = os.path.join(ROOT, "canvas-app", "msapp-src", "Src")
        with tempfile.TemporaryDirectory() as td:
            broken = os.path.join(td, "Src")
            shutil.copytree(src, broken)
            with open(os.path.join(broken, "scrHome.pa.yaml"), "a") as fh:
                fh.write("\nScreens:\n  dup: {Properties: {Children: 1}}\n")
            r = self._run("validate_msapp_source.py",
                          os.path.join(ROOT, "canvas-app", "pa.schema.yaml"),
                          broken)
            self.assertEqual(r.returncode, 1, r.stdout)

    def test_the_donor_is_the_vendored_bytes(self):
        import hashlib
        p = os.path.join(ROOT, "canvas-app", "donor",
                         "AlmTestApp-asManyEntitiesAsPossible.msapp")
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        self.assertEqual(
            h,
            "08a80c3d2686ddbd9acd18774cc66a35ae3059d89e80d22444aef94a5598baf9")
