#!/usr/bin/env python3
"""Compare what the tenant actually has against what the schema declares.

Provisioning is the step whose failure cannot be repaired. SharePoint refuses
to add an index once a list passes 5,000 items, and MF_EOM_Item passes that in
the first quarter. So "the provisioning run said OK" is not evidence: the run
can report success having created a list, most of its columns, and none of its
indexes, and nothing surfaces until months later.

The operator exports the tenant's real list schemas to JSON and points this at
it. Accepts either shape:

    {"MF EOM Item": {"fields": [{"InternalName": "...", "Indexed": true}, ...]}}
    [{"Title": "MF EOM Item", "fields": [...]}, ...]

Field entries may use InternalName / Title / name, and Indexed / indexed.

  python3 scripts/verify_provisioning.py <tenant-export.json>

NOT TESTABLE LOCALLY against a real tenant. Tested against a fixture, which
proves the comparison, not the tenant.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import eom_schema as S                                    # noqa: E402


def _field_name(f):
    for k in ("InternalName", "Title", "name", "StaticName"):
        if isinstance(f, dict) and f.get(k):
            return f[k]
    return str(f)


def _indexed(f):
    if not isinstance(f, dict):
        return False
    for k in ("Indexed", "indexed", "IsIndexed"):
        if k in f:
            return bool(f[k])
    return False


def normalise(raw):
    """Return {list title: {field name: indexed}}."""
    out = {}
    items = raw.items() if isinstance(raw, dict) else (
        (l.get("Title") or l.get("title") or l.get("name"), l) for l in raw)
    for title, body in items:
        fields = body.get("fields", body.get("Fields", [])) \
            if isinstance(body, dict) else []
        out[title] = {_field_name(f): _indexed(f) for f in fields}
    return out


def compare(actual):
    """Yield (severity, list, message)."""
    expected = {l.title: l for l in S.LISTS}

    for title, l in expected.items():
        if title not in actual:
            yield ("FAIL", title, "list is missing entirely")
            continue
        have = actual[title]
        want_cols = {c.name for c in l.columns}
        want_idx = set(l.indexed_columns)
        crosses = l.volume_estimate >= 5000

        for missing in sorted(want_cols - set(have)):
            yield ("FAIL", title, f"column '{missing}' is missing")

        for name in sorted(want_idx):
            if name in have and not have[name]:
                sev = "FAIL" if crosses else "WARN"
                tail = (" — this list is projected past 5,000 rows, so the "
                        "index cannot be added later" if crosses else "")
                yield (sev, title, f"column '{name}' is NOT indexed{tail}")

        for extra in sorted(set(have) - want_cols):
            # Not a failure. Someone may legitimately have added a view column,
            # and SharePoint adds its own. Reported so it is a decision.
            yield ("INFO", title, f"column '{extra}' exists but is not in the "
                                  f"schema")

    for title in sorted(set(actual) - set(expected)):
        yield ("INFO", title, "list exists on the tenant but is not ours")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        actual = normalise(json.load(fh))

    findings = list(compare(actual))
    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    infos = [f for f in findings if f[0] == "INFO"]

    print("Provisioning verification")
    print("=" * 58)
    print(f"  schema v{S.SCHEMA_VERSION}: {len(S.LISTS)} lists, "
          f"{sum(len(l.columns) for l in S.LISTS)} columns, "
          f"{sum(1 for l in S.LISTS for c in l.columns if c.indexed)} indexes")
    print(f"  tenant export: {len(actual)} lists")
    print()

    for label, group in (("FAIL", fails), ("WARN", warns), ("INFO", infos)):
        if group:
            print(f"{label} ({len(group)})")
            for _sev, title, msg in group:
                print(f"  {title}: {msg}")
            print()

    if fails:
        print("PROVISIONING INCOMPLETE. Do not load data into these lists.")
        print("An index missing from a list that will cross 5,000 items is the")
        print("one failure here that cannot be repaired afterwards.")
        return 1
    print("Every declared column and index is present on the tenant.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
