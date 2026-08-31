# Solution packaging

> **The contents of `src/` are the solution ENVELOPE, not a complete solution.**
> There is no `.msapp` and no flow `definition.json` here, because the Power
> Platform build has not started. A ZIP packed from this folder declares
> components it does not contain and **will not import**. See
> `dist/MissionFeedingOperations_1.0.0/README.md`.

`MissionFeedingOperations`, unmanaged source. The unpacked XML here is the
source of truth for the solution *envelope* — its components, version and
connection references. The app itself lives in `canvas-app/src` as `.pa.yaml`
and the flows are specified in `flows/*/definition.md`.

**No Pipelines.** Releases are a ZIP plus a git tag, and rollback is importing
the previous ZIP from `dist/`. See `docs/government-environment-mode.md`.

## Build

```bash
# validate first — the export is not the place to discover a schema drift
bash tests/run_tests.sh

# pack (requires PAC CLI; see the fallback below if it is not authorized)
pac solution pack --zipfile dist/MissionFeedingOperations_1.0.0.zip \
    --folder solution/src --packagetype Managed
```

### If PAC CLI is not authorized in this tenant

Nothing in the design depends on it.

1. Author in the maker portal.
2. Export the solution — **managed** for production, **unmanaged** as the
   source of truth.
3. Unpack the `.msapp` to YAML with `pac canvas unpack` on any workstation:
   unpacking is an offline operation on the exported file and does not touch
   the tenant.
4. Commit the YAML. Commit the managed ZIP to `dist/`.

If the YAML and the artifact ever disagree, **the YAML wins** and the artifact
is rebuilt.

## Connection references

The one unavoidable environment-specific value in this repository. Each
connection reference carries an id that differs per environment, so they are
parameterised in `Customizations.xml` and supplied at import time by a
deployment settings file:

```bash
pac solution import --path dist/MissionFeedingOperations_1.0.0.zip \
    --settings-file solution/deployment-settings.json
```

`deployment-settings.json` is **not committed**: it holds the environment's
connection ids and the site URL. A template is below; fill it in per
environment and keep it out of source control.

The full set is in `configuration/connection-references.json` and
`configuration/environment-variables.json`. Fill in a settings file per
environment and keep it out of source control.

`mfops_office365` (Outlook) is referenced only by EOM-04's notification branch,
which ships disabled. If the Outlook connector is unavailable, leave its
connection id empty: EOM-04 records what it would have sent to `MF_EOM_Audit`
instead, which is what you read for a full cycle before enabling it anyway.

## Versioning

`Solution.xml` carries `<Version>`, currently `1.0.0`. Bump it with the
release, matching `MF_App_Config.AppVersion` and the git tag. The release
ladder is in `docs/government-environment-mode.md`.

| Part | Meaning |
|---|---|
| MAJOR | a schema change requiring a provisioning run |
| MINOR | a screen, flow or requirement change |
| PATCH | a fix with no schema or contract change |

## What is NOT a solution component

**The SharePoint lists.** They are provisioned by
`provisioning/Provision-MFOpsLists.ps1` from `scripts/eom_schema.py`, which is
the single source of truth. Carrying list definitions in two places is how they
drift, and the drift is invisible until a column is silently missing in one
environment.
