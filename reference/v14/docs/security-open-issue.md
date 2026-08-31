# Open issue — the data layer does not enforce installation scope

**Status:** unresolved. `security-manifest.yaml` carries
`data_layer_permissions_verified: false` until it is.

## The gap

Power Apps `Visible` and `Filter()` are not access control. Microsoft states
plainly that permissions implemented in an app interface do not remove the
user's permission to the underlying data source.

The confirmed structure is one Teams site (DAF Mission Feeding), four portfolio
channels, a monthly docs folder, then a month folder. Access is granted at the
channel level.

So every base user with access to a portfolio channel can reach every other
installation's documents in that channel — through Teams, through SharePoint
directly, through Explorer sync, through any client that speaks to the library.
The app will show a Lackland DFAC manager only Lackland. SharePoint will still
serve them Creech's 1119 if they browse to it.

**The app's scope claim is presentational until this is closed.** An ISSM will
find it.

## Three ways to close it

**1. Item-level permissions on the evidence library.** Break inheritance per
installation folder, drive membership from Entra security groups. Works with the
current structure and requires no reorganisation. Needs SharePoint admin support,
and the unique-permission-scope count per library should be reviewed against
SharePoint's practical limits before committing — 43 Legacy installations is
comfortably fine; the full 103 with several folders each deserves a check.

**2. One library per portfolio, one folder per installation, one group per
installation.** Cleaner permission story, more provisioning work, and it changes
where people are used to dropping files.

**3. Accept portfolio-level visibility as the boundary.** Legitimate if the
information is not protected and the AO agrees. But it becomes a documented risk
decision with a signature, not an unexamined default.

## Recommendation

Option 1 for R1. It preserves the folder structure people already use, it maps
cleanly onto the installation-grain access model already in
`MF_Security_Mapping`, and it can be applied to the 43 Legacy installations in
scope without touching the other 60.

Whichever is chosen, the app-layer filtering stays exactly as designed. Defence
in depth means both layers, not either.

## What this is not

This is not a reason to delay the app build. Every control in the app is
correct and necessary regardless of which option is chosen. It is a deployment
dependency to raise with the SharePoint administrator now, so it is resolved
before the pilot rather than during the ISSM review.
