# MissionFeedingOperations 1.0.0 — release folder

> ## PARTIAL — flows and configuration, no canvas app
>
> `MissionFeedingOperations_1.0.0.zip` is a real unmanaged solution containing
> **five cloud flows, three connection references and eighteen environment
> variables**. Import it.
>
> **It contains no canvas app and no placeholder for one.** The `.msapp` format
> is owned by Studio and mid-transition; a hand-authored file it rejects on
> open would fail the import with an error naming an internal file and
> explaining nothing.
>
> Create the app **inside this solution after importing it** — it inherits the
> connection references and environment variables the moment it exists. See
> `CANVAS_APP_ASSEMBLY.md`.
>
> **The flows are wired but their bodies are not implemented.** Each carries its
> real trigger, its connection bindings, its environment variables and the
> schema guard, and each names the specification it must be built from. All five
> import disabled, which the deployment procedure requires anyway.

## What this folder is for

Everything a deployment needs to read **before** anyone touches a tenant, plus a
checksummed, tag-traceable snapshot of the solution envelope at 1.0.0.

| File | What it is |
|---|---|
| `MissionFeedingOperations_1.0.0.zip` | The solution, packed from tag `v1.0.0` |
| `CANVAS_APP_ASSEMBLY.md` | How to build the app inside the imported solution |
| `PREFLIGHT.md` | The four decisions and the read-only discovery script to run first |
| `PROVISION-WITHOUT-POWERSHELL.md` | The Power Automate route, for when module installs are blocked |
| `SHA256SUMS.txt` | Checksum. The version, the commit and this checksum describe one build |
| `RELEASE_NOTES.md` | What is in the release and what ships switched off |
| `KNOWN_LIMITATIONS.md` | What does not work yet, stated plainly |
| `IMPORT_CHECKLIST.md` | What must be true before the import |
| `POST_IMPORT_CHECKLIST.md` | What must be done after it, in order |
| `DEPENDENCY_MANIFEST.md` | 66 destination-side resources. **16 MUST ALREADY EXIST** |
| `SECURITY_README.md` | The security verification, and the one open issue |

**Deployment documentation sits beside the ZIP, not inside it.** The ZIP
contains only what Power Platform import expects.

## Order of work

1. **`PREFLIGHT.md`** — four decisions, and one read-only discovery script whose
   output fills in the four site bindings.
2. **Provision the lists.** `provisioning/Provision-MFOpsLists.ps1`, or
   `PROVISION-WITHOUT-POWERSHELL.md` if module installs are blocked, which is
   normal on `.mil`. **This is not part of the import and never will be.**
3. **Import this ZIP.** Flows arrive disabled; leave them.
4. **Build the app** — `CANVAS_APP_ASSEMBLY.md`. It inherits the solution's
   connection references and environment variables.
5. **Build the flow bodies** from `flows/*/definition.md`, enabling them one at
   a time in the order in `POST_IMPORT_CHECKLIST.md`.
6. **Export unmanaged**, `pac canvas unpack` the `.msapp`, and compare against
   `canvas-app/src`. **If they disagree the committed YAML wins** and the app is
   corrected, not the source.
7. Re-tag and rebuild this folder from the new tag.

## Traceability

```
version  1.0.0
tag      v1.0.0
commit   see SHA256SUMS.txt
```

The version, the commit hash and the checksum describe the same build, or the
artifact cannot be traced once it crosses to the `.mil` side.
