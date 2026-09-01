# The scaffolding

`scaffolding.msapr` is the format scaffolding a canvas app needs beyond its
YAML source — header, themes, control templates, publish info — taken from a
genuine Power Apps Studio-built app and **neutralised before it was ever
tracked**. Its hash is pinned in `scaffolding.sha256` and verified on every
build; the archive-aware pre-release scanner sweeps its every entry on every
run.

## Where it comes from, and why the raw donor is NOT here

The raw donor is Microsoft's MIT-licensed ALM test app:

    https://github.com/microsoft/PowerApps-Language-Tooling
    src/Persistence.Tests/_TestData/AlmApps/AlmTestApp-asManyEntitiesAsPossible.msapp
    sha256 08a80c3d2686ddbd9acd18774cc66a35ae3059d89e80d22444aef94a5598baf9

An earlier build vendored it raw and neutralised at build time — and the
blocklist was too narrow: the shipped `.msapp` still carried signed Azure Blob
URLs (`sig=` SAS fragments, an `sktid=` tenant identifier), three donor
images, the donor's app name, and donor feature flags (runtime copilot,
experimental CDS/SQL connectors). Found by user inspection, not by the sweep
that claimed "clean".

The structural fix: the repository now tracks only the CLEAN scaffolding.
`scripts/neutralise_donor.py` documents the disposition of every donor entry,
verifies the output against the same blocklist the builder and the final
validator enforce, and is how you regenerate this file — fetch the raw donor
from the URL above (hash must match) and run the script. The raw file never
gets tracked. (It exists in git history at the earlier commit; the current
tree is what ships and what the scanner guards.)

## What consumes it

Only `scripts/build_msapp.py`, which produces the **REFERENCE-ONLY** `.msapp`
(build validation, never a deployment artifact). Path A —
`scripts/assemble_full_solution.sh` — never touches the donor at all: its
scaffolding comes from the operator's own exported wrapper, which is the
point.
