# The donor app

`AlmTestApp-asManyEntitiesAsPossible.msapp` is a genuine Power Apps
Studio-built canvas app (MSAppStructureVersion 2.4.0), vendored verbatim from
Microsoft's open-source repository:

    https://github.com/microsoft/PowerApps-Language-Tooling
    src/Persistence.Tests/_TestData/AlmApps/  (MIT license)

    SHA-256 recorded in scripts/build_msapp.py and verified on every build.

## Why it exists

`pac canvas pack --layout SourceCode` cannot originate an app: it requires a
`.msapr` reference archive that only a real Studio-built app can yield. This
app is unpacked to obtain that archive — the format scaffolding Studio minted:
`Header.json`, themes, control templates, publish info.

**What is taken:** structure and scaffolding only.
**What is stripped, and why — see `scripts/build_msapp.py`:** every entry
carrying the donor app's own content (its control trees, its component, its
Dataverse data-source metadata, which references a commercial-cloud dev
instance) is removed or emptied. The build fails if any commercial-cloud
string survives into the output.

The app's screens, components and formulas come exclusively from
`canvas-app/msapp-src/`, generated from `canvas-app/src/`.
