# Known limitations — 1.0.0

Everything here is stated because it is true, not because it is comfortable.
Nothing in this list is a surprise waiting for an inspection.

---

## OPEN — installation-scope data-layer security

**Power Apps `Visible` and `Filter` are not a security boundary.** They shape
what a screen renders. They do not stop a determined user reading rows the app
chose not to show, because the connector fetches with the *user's* permissions
and the filtering happens client-side.

Every query in this build filters by `Installation_ID` / `Portfolio_ID` from
`MF Security Mapping`, and that is the right thing to do — but it is a
presentation control, not an authorisation one. **The data layer must enforce
installation scope independently**, through SharePoint item-level permissions,
a security-trimmed view, or an equivalent the SharePoint administrator owns.

`docs/security-open-issue.md` carries the detail. `security-manifest.yaml`
records `data_layer_permissions_verified: false` and will keep recording it
until someone verifies it.

**This does not block a single-site pilot. It blocks widening one.** An ISSM
will find it, and finding it in a review is much better than finding it after.

---

## UNKNOWN — production month-folder naming

EOM-02 **finds** folders and never creates them. That is deliberate: creating a
folder on a production site because a match failed is how a document ends up
somewhere nobody looks.

The consequence is that the month-folder naming on each of the four production
sites must be read off the site and recorded. It differs per site and cannot be
guessed — `08 Aug`, `Aug`, `August`, `2026-08` and `08` are all in use
somewhere.

**Until it is recorded, the four production destinations stay inactive.** They
ship `Active_Flag FALSE` with `Site_URL`, `Verified_By` and `Verified_Date`
blank, and EOM-02 fails closed on them with `CONFIGURATION_REQUIRED`, which is
correct.

If it is skipped, nothing errors. Submissions fall back to the configured root
with `Needs_Filing TRUE` and pile up one level above where anyone looks. The
Exceptions screen exists to make that visible.

`deployment/site-bindings.md` section 4 is the worksheet.

---

## NOT IN THE BOX — the canvas app

Artifact 1 contains **no canvas app**, and the reason is architectural rather
than a judgement call: `pac canvas pack` cannot originate an app from YAML.
Both of its layouts require a seed artifact that only Studio or an
authenticated environment can mint. `CANVAS_APP_ASSEMBLY.md` carries the CLI
output that establishes this.

The source is complete — 16 screens, 6 components, 4 formula files, 1,829
formulas, all of which parse under Microsoft's own Power Fx engine. What is
missing is one Studio session, and after it the exported ZIP carries the app
permanently.

---

## NOT TESTABLE LOCALLY

Every one of these is a real gap in the evidence, not a formality.

| | Why it cannot be tested here |
|---|---|
| Whether the solution ZIP imports | No Power Platform environment. The package matches a structure taken from documentation; if that reading is wrong, 67 structural tests pass and the import still fails naming an internal file. |
| Whether the flows run | 118 actions across five flows, all verified structurally, none executed. The status expression is the exception: it is evaluated against the engine's fixtures and that found two real defects. |
| Whether a SharePoint write lands | No tenant. Folder resolution is tested against constructed listings, not against a site. |
| Whether the canvas app opens in Studio | No Studio. The formulas parse; the control tree has never been rendered. |
| Whether tenant security holds | The open issue above. |
| Whether provisioning created every index | `scripts/verify_provisioning.py` compares a tenant export against the schema, and is proven against fixtures. The tenant export has to come from the tenant. |
| Whether a query delegates past 5,000 items | Two predicates sit on unindexed columns inside an `OR` behind indexed leading predicates. SharePoint can usually resolve those through the leading index, and *usually* is not good enough. `scripts/canvas_delegation_check.py` reports them rather than rounding up. |

---

## Recommendation

**DEV or PILOT only.** Not production.

It becomes a production candidate when, on the real tenant: EOM-01 has run
twice for the same period and produced 737 rows both times, one pilot document
has landed in the folder it was supposed to land in, and the data-layer scope
question above has an answer.
