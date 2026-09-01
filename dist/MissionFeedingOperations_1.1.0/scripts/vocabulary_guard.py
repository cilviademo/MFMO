#!/usr/bin/env python3
"""A filter that matches nothing must say so. It must never return zero quietly.

WHY THIS EXISTS
---------------
Twice, a generator filtered on a vocabulary that did not exist in the data and
produced zero rows without an error:

  1. `Applicable_Model` filtered on `Legacy/APF`. The registry says `Legacy`.
     Every facility-scope requirement matched nothing.
  2. `Applicable_Facility_Types` filtered on types the QRG does not carry at
     all. Every type-scoped requirement excluded every facility.

Both looked like success. A run that creates no expected items reports "created
0" and exits 0, and a base with no expected rows is indistinguishable from a
base with nothing due — which is to say, it reads as compliant.

THE RULE
--------
Any generator that filters on a vocabulary must assert that the filter's terms
exist in the data, and fail loudly when they do not.

There are two different zeroes and only one of them is a bug:

  * The filter names a value that exists NOWHERE in the source data. That is a
    configuration error — a typo, a renamed vocabulary, a stale seed — and it
    raises `VocabularyMismatch`.

  * The filter names a real value that no CURRENTLY SELECTED row happens to
    carry. That is a legitimate empty result: a Food 2.0 requirement when no
    Food 2.0 base has been onboarded yet. It is reported, never raised.

Distinguishing them is the whole job. Failing on the second would make
onboarding one base at a time impossible; passing the first is what cost a
month.

AND THE COROLLARY
-----------------
**An empty filter column means "no constraint", never "no match".** A
requirement that names no facility types applies to every facility, including
one whose type is unknown. Under-generating is worse than over-generating: an
extra row is visible and a reviewer can waive it; a missing row is invisible and
nobody finds out until an inspection.
"""

from __future__ import annotations


class VocabularyMismatch(Exception):
    """A filter names a value that appears nowhere in the source data."""


def split_terms(raw, separator=";"):
    """Parse a filter cell into terms. Blank yields no terms — no constraint."""
    if raw is None:
        return []
    return [t.strip() for t in str(raw).split(separator) if t.strip()]


def observed_values(rows, column):
    """Every non-blank value of `column` across `rows`, as written."""
    return {str(r.get(column) or "").strip()
            for r in rows if str(r.get(column) or "").strip()}


def check_vocabulary(filter_name, terms, observed, *, wildcards=("All",),
                     source="the registry", hint=""):
    """Raise when a filter term exists nowhere in the observed data.

    `terms` are what the configuration asks for; `observed` is what the data
    actually contains. A wildcard term constrains nothing and is always valid.

    Returns the terms that will actually match something, so a caller can tell
    the difference between "filtered to nothing" and "nothing was selected".
    """
    live = [t for t in terms if t not in wildcards]
    if not live:
        return list(terms)

    unknown = [t for t in live if t not in observed]
    if unknown:
        known = ", ".join(sorted(observed)[:12]) or "(none)"
        raise VocabularyMismatch(
            f"{filter_name} filters on {unknown!r}, which {source} never "
            f"contains. It would have matched nothing and reported success.\n"
            f"  asks for: {sorted(live)}\n"
            f"  {source} has: {known}\n"
            + (f"  {hint}\n" if hint else "")
            + "  Normalise the vocabulary at import, or correct the filter. Do "
              "not widen the filter to make this pass."
        )
    return live


def check_requirement_filters(requirements, facilities):
    """The EOM-01 guard. Called before any row is generated.

    Every vocabulary a requirement can filter on is checked against what the
    facility registry actually holds. This runs against ALL facilities, not the
    onboarded subset, so onboarding one base at a time never trips it.
    """
    models = observed_values(facilities, "Operating_Model")
    types = observed_values(facilities, "Facility_Type")

    for req in requirements:
        rid = req.get("Requirement_ID", "?")

        check_vocabulary(
            f"{rid}.Applicable_Model",
            split_terms(req.get("Applicable_Model")),
            models,
            source="the facility registry",
            hint=("Operating models are normalised by "
                  "scripts/eom_schema.normalize_operating_model — the QRG says "
                  "'Legacy', the requirement catalogue says 'Legacy/APF'."),
        )

        # Facility_Type is the corollary case. The QRG carries no type at all,
        # so `types` is empty and there is nothing to check against — but a
        # requirement naming types must still not be treated as matching
        # nothing. facility_type_applies() returns True for an unknown type for
        # exactly that reason, so an empty registry vocabulary is not an error.
        if types:
            check_vocabulary(
                f"{rid}.Applicable_Facility_Types",
                split_terms(req.get("Applicable_Facility_Types")),
                types,
                source="the facility registry",
                hint=("A facility whose type is unknown MATCHES. An empty "
                      "filter column means no constraint, never no match."),
            )
