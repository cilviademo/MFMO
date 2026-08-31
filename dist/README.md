# Release artifacts

`MissionFeedingOperations_v<version>.zip` — the exported **managed** solution
for each release. Committed deliberately: rollback is importing the previous
ZIP from here, and a rollback that depends on rebuilding from source is not a
rollback.

The YAML in `canvas-app/src` is the code. These are build artifacts. If they
disagree, the YAML wins and the artifact is rebuilt.

## Producing one

See `docs/DEPLOYMENT.md` step 12 and `solution/README.md`. In short: validate,
export managed from the maker portal (or `pac solution pack`), drop it here
named for the version, update `CHANGELOG.md`, tag.

## Current state

**No ZIP has been produced yet.** The solution has not been built in a tenant:
`TenantCloud` and `PacCliAuthorized` both read `UNKNOWN`, and both must be
answered before step 1 of the build order. Nothing in this repository can
produce a genuine `.msapp` or solution ZIP without a Power Platform
environment to export from, and a hand-assembled ZIP that had never been
imported would be worse than none.
