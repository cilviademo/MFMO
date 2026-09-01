#!/usr/bin/env python3
"""Validate canvas-app/msapp-src against Microsoft's official pa.yaml v3 schema.

This exists because `pac canvas pack` validates NOTHING -- proven by feeding it
structurally broken YAML and a nonexistent control type, both of which "packed
successfully". A pack success is file assembly, not evidence. The schema is
the one Microsoft publishes in PowerApps-Language-Tooling and links from the
banner of every YAML file Studio itself writes.

  python3 scripts/validate_msapp_source.py [schema.yaml]

Exits 1 on any violation.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "canvas-app", "msapp-src", "Src")
# argv[2] may point elsewhere (e.g. a genuine Studio unpack, as the
# calibration standard: whatever Studio itself writes must pass).
DEFAULT_SCHEMA = os.path.join(ROOT, "canvas-app", "pa.schema.yaml")


def main(argv):
    import yaml
    import jsonschema

    schema_path = argv[1] if len(argv) > 1 else DEFAULT_SCHEMA
    with open(schema_path, encoding="utf-8") as fh:
        schema = yaml.safe_load(fh)
    # The schema $refs its sibling 1P-control catalog by relative id; register
    # both documents so references resolve offline.
    from referencing import Registry, Resource
    sibling = os.path.join(os.path.dirname(schema_path),
                           "ControlTypeId-1P-controls-enum.schema.yaml")
    with open(sibling, encoding="utf-8") as fh:
        catalog = yaml.safe_load(fh)
    # $refs resolve relative to the schema's $id base.
    base = schema.get("$id", "").rsplit("/", 1)[0] + "/"
    registry = Registry().with_resources([
        (base + "ControlLibraryVDev/ControlTypeId-1P-controls-enum.schema.yaml",
         Resource.from_contents(catalog, default_specification=
                                jsonschema.Draft7Validator.META_SCHEMA["$schema"])
         if False else Resource.from_contents(catalog)),
        (catalog.get("$id", ""), Resource.from_contents(catalog)),
    ])
    # CALIBRATION: the genuine Studio-built ALM test app fails the published
    # schema's 1P control ENUM twenty times over (Text@0.0.51, Rectangle@2.3.0
    # ...) -- the "VDev" enum lags what Studio actually writes. Studio's own
    # output is the standard, so the control-id check is relaxed to the
    # PATTERN the same schema defines, and everything else stays strict.
    defs = schema.get("definitions", {})
    if "ControlTypeId" in defs:
        defs["ControlTypeId"] = {
            "allOf": [
                {"$ref": "#/definitions/ControlTypeId-pattern"},
                {"not": {"$ref": "#/definitions/ControlTypeId-disallowed-types"}},
            ]
        }
    validator = jsonschema.Draft7Validator(schema, registry=registry)

    target = argv[2] if len(argv) > 2 else OUT
    files = []
    for base, _d, names in os.walk(target):
        for n in sorted(names):
            if n.endswith(".pa.yaml"):
                files.append(os.path.join(base, n))

    problems = 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as fh:
            try:
                doc = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                print(f"YAML PARSE FAILURE {rel}: {exc}")
                problems += 1
                continue
        for err in sorted(validator.iter_errors(doc), key=str):
            loc = "/".join(str(x) for x in err.absolute_path) or "(root)"
            print(f"SCHEMA {rel} :: {loc}\n    {err.message[:160]}")
            problems += 1

    print(f"\n{len(files)} files validated against the official pa.yaml v3 "
          f"schema")
    if problems:
        print(f"{problems} violation(s). The packer would have accepted every "
              f"one of them silently.")
        return 1
    print("No violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
