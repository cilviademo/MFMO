# Open issue — the data layer does not enforce installation scope

**Status:** narrowed, not closed. `security-manifest.yaml` carries
`data_layer_permissions_verified: false` until it is.

## The gap

Power Apps `Visible` and `Filter()` are not access control. Microsoft states
plainly that permissions implemented in an app interface do not remove the
user's permission to the underlying data source.

Every base user with access to a portfolio's documents can reach every other
installation's documents in that portfolio — through Teams, through SharePoint
directly, through Explorer sync, through any client that speaks to the library.
The app will show a Lackland DFAC manager only Lackland. SharePoint will still
serve them Creech's 1119 if they browse to it.

**The app's scope claim is presentational until this is closed.** An ISSM will
find it.

## What the routing finding changed — half of it is already enforced

This issue was written against the structure everyone believed in at the time:
**one** Teams site with four portfolio channels, access granted at the channel.
That was wrong. The four portfolios are **four separate site collections**, each
with its own permissions and its own administrator.

So the portfolio boundary is now a **site** boundary, which SharePoint enforces
natively and which nobody has to build. A Portfolio 2 user was never going to
reach Portfolio 3's library by browsing; they would have to be granted access to
a different site collection first.

That halves the problem without a line of code, and it changes the shape of the
remaining one. What is still open is **installation scope within a single
portfolio site** — a Lackland user reaching Creech, both of them Portfolio 2.
Smaller, but the same class of gap, and still the one an ISSM will ask about.

It also multiplies the *administrative* work: four site collections means four
sets of permissions and, per option 1 below, four libraries to break inheritance
in, each with its own admin to persuade. `deployment/site-bindings.md` asks who
administers each site for exactly this reason.

## The same gap, on the audit list

`MF_EOM_Audit.Actor_UPN` and `MF_EOM_Submission.Uploaded_By` are written by the
app as `User().Email`. Inside the app that is the authenticated identity and a
user cannot forge it — Power Apps derives it from the signed-in session, not
from anything the user controls.

**It is not enforced at the data layer.** A user with direct write access to
`MF_EOM_Audit` could create a row attributing an action to somebody else. That
is the same exposure as installation scope, on the same lists, and it closes
the same way: deny end-user write on `MF_EOM_Audit` and `MF_EOM_Submission`,
and let the flows write those rows under the application connection.

Doing that also removes the last reason for a base user to hold write
permission on anything but the item list, which makes option 1 below a smaller
change than it first appears.

`security-manifest.yaml` records this as
`audit_author_enforced_at_data_layer: false`. It previously carried only
`user_may_edit_audit_author: false`, which claimed a control the deployment
does not yet have.

## Three ways to close it

**1. Item-level permissions inside each portfolio's library.** Break inheritance
per installation folder, drive membership from Entra security groups. Works with
the structure that is already there and requires no reorganisation. Needs
support from each of the four site administrators, and the unique-permission-
scope count per library should be reviewed against SharePoint's practical limits
before committing — the largest portfolio's share of 43 Legacy installations is
comfortably fine; the full 103 with several folders each deserves a check.

Note that the folders it would break inheritance on are the **hand-curated FY
and month folders**, which is why `Create_Missing_Folders` being FALSE matters
here too: a flow that invented folders would be creating permission scopes
nobody configured.

**2. One library per portfolio, one folder per installation, one group per
installation.** Cleaner permission story, more provisioning work, and it changes
where people are used to dropping files — in four different places, each with
its own established habits.

**3. Accept portfolio-level visibility as the boundary.** Now a materially more
defensible position than it was, because the portfolio boundary is a real,
natively enforced site boundary rather than a folder in a shared library.
Legitimate if the information is not protected and the AO agrees. It still
becomes a documented risk decision with a signature, not an unexamined default.

## Recommendation

Option 1 for R1. It preserves the folder structure people already use, it maps
cleanly onto the installation-grain access model already in
`MF_Security_Mapping`, and it can be applied to the 43 Legacy installations in
scope without touching the other 60.

Option 3 is now worth putting to the AO explicitly rather than dismissing. With
the portfolio boundary enforced by SharePoint, the residual exposure is one
installation seeing another *within the same portfolio* — a narrower question,
and one the AO may reasonably accept for unclassified EOM evidence. Ask; do not
assume the answer either way.

Whichever is chosen, the app-layer filtering stays exactly as designed. Defence
in depth means both layers, not either.

## What this is not

This is not a reason to delay the app build. Every control in the app is
correct and necessary regardless of which option is chosen. It is a deployment
dependency to raise with the SharePoint administrator now, so it is resolved
before the pilot rather than during the ISSM review.
