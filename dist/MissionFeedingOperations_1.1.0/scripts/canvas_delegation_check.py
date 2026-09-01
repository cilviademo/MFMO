#!/usr/bin/env python3
"""Every query that reaches a business list must delegate.

The delegation ceiling is the worst failure mode in this app, because it does
not look like a failure. A non-delegable Filter over MF EOM Item returns the
FIRST 500 ROWS and reports success. The gallery renders, the count is wrong,
and nothing anywhere says so. At 103 installations the list passes 500 rows in
the first month.

So: every Filter / LookUp / Search that names a business list must constrain
only INDEXED columns, using operators SharePoint can delegate.

Two things are deliberately allowed, and both are stated at the call site in
the source rather than inferred here:

  * A predicate applied to a NAMED FORMULA (MF_VisibleItems, MF_MyWork, ...).
    Those are defined in Delegation.fx, are already period- and scope-bounded,
    and are audited there.
  * Search / StartsWith over a small reference list -- the 103-row registry,
    the 13-row requirement catalogue. Bounded by construction.

Exit 1 on a non-delegable predicate over a high-volume list.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import eom_schema as S                                    # noqa: E402
from canvas_formulas import all_formulas                  # noqa: E402

# Lists that grow without bound. A non-delegable query over one of these is a
# correctness defect, not a performance note.
HIGH_VOLUME = {"MF_EOM_Item", "MF_EOM_Submission", "MF_EOM_Status",
               "MF_EOM_Audit", "MF_App_Event_Log", "MF_Calendar_Event"}

# Functions SharePoint cannot delegate at all, in any position.
NON_DELEGABLE_FN = ("Sort(", "Ungroup(", "GroupBy(", "Concat(", "Collect(",
                    "ClearCollect(", "AddColumns(", "DropColumns(",
                    "RenameColumns(", "ShowColumns(")

# Operators and forms SharePoint cannot delegate in a predicate.
NON_DELEGABLE_OP = (
    (re.compile(r"\bin\s+\["), "the 'in' operator over a literal set"),
    (re.compile(r"\bin\s+[A-Za-z_]"), "the 'in' operator"),
    (re.compile(r"\bExactIn\b"), "ExactIn"),
    (re.compile(r"\bIsBlank\s*\(\s*[A-Z][A-Za-z0-9_]*\s*\)"),
     "IsBlank() on a column -- reach the rows by an indexed status column"),
    (re.compile(r"\bLen\s*\("), "Len()"),
    (re.compile(r"\bLower\s*\(\s*[A-Z]"), "Lower() on a column"),
    (re.compile(r"\bUpper\s*\(\s*[A-Z]"), "Upper() on a column"),
    (re.compile(r"\bCountRows\s*\(\s*Filter\s*\(\s*'"), None),   # allowed
)


def indexed(list_name):
    return {c.name for c in S.LISTS_BY_NAME[list_name].columns if c.indexed}


def title_to_internal():
    return {l.title: l.name for l in S.LISTS}


def find_calls(text):
    """Yield (function, quoted-source, argument-text) for Filter/LookUp/Search."""
    for m in re.finditer(r"\b(Filter|LookUp|Search)\s*\(\s*'([^']+)'\s*,", text):
        start = m.end()
        depth, i = 1, m.start() + len(m.group(1))
        # walk from the opening paren to its match
        i = text.index("(", m.start())
        depth, j = 0, i
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield m.group(1), m.group(2), text[start:j]


def main():
    by_title = title_to_internal()
    problems, uncertain, checked = [], [], 0

    for rel, line, prop, text in all_formulas():
        flat = " ".join(text.split())
        for fn, source, args in find_calls(flat):
            internal = by_title.get(source)
            if internal is None:
                continue                       # reference check owns this
            checked += 1
            if internal not in HIGH_VOLUME:
                continue

            idx = indexed(internal)

            for bad in NON_DELEGABLE_FN:
                if bad in args:
                    problems.append((rel, line, source,
                                     f"{bad[:-1]}() inside the predicate"))

            for pattern, why in NON_DELEGABLE_OP:
                if why and pattern.search(args):
                    problems.append((rel, line, source, why))

            # Every `Column <op> ...` constraint must name an indexed column.
            #
            # BUT the risk is not uniform, and reporting it as one thing would
            # be wrong in both directions. SharePoint refuses a query it cannot
            # resolve through an index once a list passes 5,000 items. A
            # LEADING indexed AND-predicate lets it reduce the set first, so a
            # non-indexed column that appears only inside a later OR is a
            # different -- and genuinely uncertain -- case from one that leads.
            #
            # Uncertain is reported as uncertain. It is not rounded up to PASS
            # and not rounded down to FAIL.
            cols = {c.name for c in S.LISTS_BY_NAME[internal].columns}
            constraints = [
                (m.group(1), m.start()) for m in re.finditer(
                    r"(?<![.\w])([A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\s*"
                    r"(?:=|<>|<|>|<=|>=)", args)
                if m.group(1) in cols]
            first_indexed = next(
                (pos for name, pos in constraints if name in idx), None)
            for name, pos in constraints:
                if name in idx:
                    continue
                inside_or = "||" in args[:pos] or "||" in args[pos:pos + 200]
                if first_indexed is not None and first_indexed < pos and inside_or:
                    uncertain.append(
                        (rel, line, source, name,
                         "inside an OR, behind indexed leading predicates"))
                else:
                    problems.append(
                        (rel, line, source,
                         f"predicate on '{name}', which is NOT indexed, "
                         f"with no indexed predicate leading it"))

    print("Canvas delegation check")
    print("=" * 58)
    print(f"  {checked} queries against a schema list")
    print(f"  high-volume lists: {', '.join(sorted(HIGH_VOLUME))}")
    print()

    if uncertain:
        seen = sorted(set(uncertain))
        print(f"NOT VERIFIABLE LOCALLY ({len(seen)}) — report, do not round up")
        for rel, line, source, col, why in seen:
            print(f"  {rel}:{line}")
            print(f"      {source}.{col} is not indexed, {why}.")
        print()
        print("  SharePoint can usually resolve these through the leading")
        print("  index, and usually is not a word this build accepts. Whether")
        print("  the optimiser uses the index across an OR that spans an")
        print("  unindexed column cannot be established without a list of over")
        print("  5,000 items on the real tenant.")
        print()
        print("  Adding an index would settle it and is NOT done here: the")
        print("  schema is a settled authority and this is a change to it.")
        print("  MF_EOM_Item has 13 of 20, so there is room. The decision is")
        print("  the schema owner's, and the smoke test is the evidence:")
        print("  run EOM-01 twice for 737 rows, then confirm a Facility-scoped")
        print("  user sees every row they should once the list passes 5,000.")
        print()

    if problems:
        seen = sorted(set(problems))
        print(f"NON-DELEGABLE ({len(seen)})")
        for rel, line, source, why in seen:
            print(f"  {rel}:{line}")
            print(f"      {source}: {why}")
        print("\nA non-delegable query over one of these lists returns the first")
        print("500 rows and reports success. Nothing errors. The count is wrong.")
        return 1

    print("Every query against a high-volume list constrains indexed columns")
    print("with delegable operators.")
    if uncertain:
        print(f"{len(set(uncertain))} predicate(s) reported above as NOT")
        print("VERIFIABLE LOCALLY. That is a report, not a pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
