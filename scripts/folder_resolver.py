#!/usr/bin/env python3
"""Destination folder resolution for EOM-02 — find, never create.

The reference implementation. `flows/EOM02-Submission/definition.md` describes
this in prose and `canvas-app`/Power Automate transliterate it; the tests hold
all of them to what is here.

WHY MATCHING RATHER THAN CONSTRUCTING
-------------------------------------
The four portfolios are four separate SharePoint site collections, and their
root folders are named four different ways:

    Legacy_Portfolio 1/H. Monthly Data Call
    Legacy_Portfolio 2/5. Monthly Data Call
    Legacy_Portfolio 3/Monthly Data Call
    Legacy_Portfolio 4/Monthly Data Call

`H.` and `5.` are sort-order prefixes somebody typed years ago. If four sites
name their ROOT folders four ways, there is no reason to believe they name their
MONTH folders one way. So the FY and month folders are matched against what is
actually on the site, never rendered from a template and created.

A flow that creates folders will eventually produce `Aug 26` beside someone's
`August 2026`. Both look right, half the submissions go to each, and nobody
notices for a month — by which point there is no way to tell which folder a
given base was told to use. `Create_Missing_Folders` is FALSE permanently.

When a folder cannot be matched, FIND_OR_ROOT puts the file at the Monthly Data
Call root with Needs_Filing set and a note saying what was looked for. A
submission that lands somewhere findable beats one that fails: the base did
their part, and the mess is ours to clean up where it can be counted.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December")

# The federal fiscal year runs October through September: October 2025 is FY26.
FY_START_MONTH = 10

# SharePoint rejects these in a file or folder name outright.
_ILLEGAL = '"*:<>?/\\|'

SEP = "/"


def fiscal_year(period: str) -> int:
    """'2026-08' -> 2026.  '2025-10' -> 2026, because October starts the FY."""
    year, month = _split_period(period)
    return year + 1 if month >= FY_START_MONTH else year


def _split_period(period: str):
    m = re.fullmatch(r"(\d{4})-(\d{2})", period.strip())
    if not m:
        raise ValueError(f"reporting period must be YYYY-MM, got {period!r}")
    year, month = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        raise ValueError(f"month out of range in {period!r}")
    return year, month


def _fold(name: str) -> str:
    """Case-fold and strip accents so matching is not defeated by typography."""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    return n.casefold()


def match_fiscal_year_folder(children, period: str):
    """Return the child folder that names this fiscal year, or None.

    Accepts FY26, FY 26, FY-26, FY2026 and FY 2026. Matched as a whole token so
    'FY26 ARCHIVE' matches and 'DRAFT_FY261' does not.
    """
    fy = fiscal_year(period)
    short, long_ = f"{fy % 100:02d}", str(fy)
    pattern = re.compile(rf"\bfy[\s_-]*({re.escape(long_)}|{re.escape(short)})\b")
    for child in children:
        if pattern.search(_fold(child)):
            return child
    return None


def match_month_folder(children, period: str):
    """Return the child folder that names this month, or None.

    Three forms are tried IN ORDER, and the order is the point:

      1. the full month name       August, august, AUGUST
      2. the three-letter form     Aug, AUG
      3. the two-digit number      08

    Strongest signal first. A folder called '08. August' carries both the name
    and the number, so trying them in any other order would be a coin flip; and
    where a site holds both 'August 2026' and a stray '08', the named one is
    what a person meant. The bare number is last because it is the weakest
    evidence a folder can offer that it is about August.

    A year, when the folder carries one, must be the right year. 'August 2025'
    never matches the 2026-08 period, and a folder with no year is accepted as
    written — plenty of sites keep the year only on the FY folder above.
    """
    year, month = _split_period(period)
    name = MONTH_NAMES[month - 1]
    forms = (
        re.compile(rf"\b{name.casefold()}\b"),
        re.compile(rf"\b{name[:3].casefold()}\b"),
        re.compile(rf"(?<!\d){month:02d}(?!\d)"),
    )
    for form in forms:
        for child in children:
            folded = _fold(child)
            if not form.search(folded):
                continue
            if _names_a_different_year(folded, year):
                continue
            return child
    return None


def _names_a_different_year(folded_name: str, year: int) -> bool:
    """True when the folder states a year and it is not the one we want.

    Both the four-digit year and a two-digit one are considered, so 'Aug 25'
    is rejected for a 2026 period rather than matching on the month alone. A
    folder naming no year at all is not rejected — it is simply not evidence.
    """
    four = {int(y) for y in re.findall(r"(?<!\d)(20\d{2})(?!\d)", folded_name)}
    if four:
        return year not in four
    # Two-digit years only count when they are not the month we just matched.
    two = {int(y) for y in re.findall(r"(?<!\d)(\d{2})(?!\d)", folded_name)}
    two.discard(int(folded_name[:2]) if folded_name[:2].isdigit() else -1)
    candidates = {y for y in two if 20 <= y <= 99}
    if candidates:
        return (year % 100) not in candidates
    return False


def sanitize_segment(segment: str) -> str:
    """Make one path segment safe for SharePoint without changing its meaning."""
    cleaned = "".join(" " if ch in _ILLEGAL else ch for ch in segment)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned[:255]


def join_path(*segments) -> str:
    """Join path parts, sanitising each one individually.

    An argument may itself be several segments — `Root_Folder` is
    `Legacy_Portfolio 2/5. Monthly Data Call`, one configured value spanning two
    folders — so split on the separator BEFORE sanitising. Sanitising first
    would eat the separator that is meant to be there and silently flatten two
    folders into one.
    """
    parts = []
    for segment in segments:
        if not segment:
            continue
        for piece in str(segment).split(SEP):
            cleaned = sanitize_segment(piece)
            if cleaned:
                parts.append(cleaned)
    return SEP.join(parts)


@dataclass(frozen=True)
class Resolution:
    """Where a file goes, and whether a human has to touch it afterwards."""
    path: str
    needs_filing: bool
    note: str
    fiscal_year_folder: str | None = None
    month_folder: str | None = None


class DestinationNotUsable(Exception):
    """Raised instead of writing somewhere convenient. Carries the error code
    EOM-02 returns to the app, which never shows the user a path or a URL."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code if not detail else f"{code}: {detail}")
        self.code = code
        self.detail = detail


def check_destination(destination) -> None:
    """Three independent gates, all defaulting to 'no'.

    A destination nobody has walked cannot receive a file by accident. This is
    the difference between fail-closed and fail-into-whatever-row-was-seeded.
    """
    if destination is None:
        raise DestinationNotUsable("DESTINATION_NOT_CONFIGURED",
                                   "no row for this portfolio and domain")
    if not destination.get("Active_Flag"):
        raise DestinationNotUsable("DESTINATION_NOT_CONFIGURED",
                                   "row is inactive")
    if not str(destination.get("Verified_By") or "").strip():
        raise DestinationNotUsable("DESTINATION_NOT_VERIFIED",
                                   "nobody has walked this site")
    if not str(destination.get("Site_URL") or "").strip():
        raise DestinationNotUsable("CONFIGURATION_REQUIRED",
                                   "Site_URL is not bound")


def resolve_destination_folder(destination, period, list_children):
    """Resolve the folder for one submission.

    `destination` is the MF_Document_Destination row. `list_children(path)`
    returns the folder names directly under `path` — the flow's SharePoint
    call, injected so this is testable without a tenant.

    Never creates anything. Never returns a path outside the configured root.
    """
    check_destination(destination)

    root = join_path(destination["Library_Name"], destination["Root_Folder"])
    fallback = destination.get("Fallback_Policy", "FIND_OR_ROOT")

    fy_name = match_fiscal_year_folder(list_children(root), period)
    if fy_name is None:
        return _fall_back(
            fallback, root,
            f"no child of the Monthly Data Call root matched FY{fiscal_year(period) % 100:02d}")

    fy_path = join_path(root, fy_name)
    month_name = match_month_folder(list_children(fy_path), period)
    if month_name is None:
        year, month = _split_period(period)
        return _fall_back(
            fallback, root,
            f"no child of {fy_name} matched {MONTH_NAMES[month - 1]} {year}",
            fiscal_year_folder=fy_name)

    return Resolution(
        path=join_path(fy_path, month_name),
        needs_filing=False,
        note="",
        fiscal_year_folder=fy_name,
        month_folder=month_name,
    )


def _fall_back(policy, root, note, fiscal_year_folder=None):
    """THE FALLBACK CEILING.

    The fallback writes to the approved Monthly Data Call root and **never
    above it** — not to the site root, not to the library root, not to another
    portfolio. A file that lands above the approved root looks like it worked:
    it is in SharePoint, the upload returned success, and it is somewhere
    nobody will ever look. That is strictly worse than a failed upload, because
    a failed upload gets retried.

    `root` is built from the destination row's own Library_Name and
    Root_Folder, so it cannot be anything else — but the assertion is here
    anyway, because "it cannot happen" is what every silent failure in this
    programme has had in common.
    """
    if policy == "FIND_OR_FAIL":
        raise DestinationNotUsable("DESTINATION_FOLDER_NOT_FOUND", note)
    if not root or len(root.split(SEP)) < 2:
        raise DestinationNotUsable(
            "DESTINATION_NOT_CONFIGURED",
            f"refusing to fall back to {root!r}: that is at or above the "
            "library root, not the approved Monthly Data Call root")
    return Resolution(path=root, needs_filing=True, note=note,
                      fiscal_year_folder=fiscal_year_folder)


def next_version_name(file_name: str, existing) -> str:
    """Preserve the uploaded name; disambiguate a collision, never overwrite.

    Filenames are never authoritative — MF_EOM_Submission is the record and it
    carries Version_No. This only stops SharePoint from silently replacing a
    file that happens to share a name.
    """
    existing = set(existing or ())
    if file_name not in existing:
        return file_name
    stem, dot, ext = file_name.rpartition(".")
    if not dot:
        stem, ext = file_name, ""
    n = 2
    while True:
        candidate = f"{stem} (v{n}){'.' + ext if ext else ''}"
        if candidate not in existing:
            return candidate
        n += 1
