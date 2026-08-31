# MissionFeedingOperations 1.0.0 — release folder

> ## THIS ZIP IS NOT YET AN IMPORTABLE SOLUTION
>
> `MissionFeedingOperations_1.0.0.zip` contains the solution **envelope** —
> `Solution.xml` and `Customizations.xml` — and nothing else. There is no
> `.msapp` and no flow `definition.json`, because **the Power Platform build
> has not started**.
>
> The envelope declares a canvas app and five flows it does not contain, so
> importing it will fail on the missing components. That is not a defect in the
> package; it is the state of the programme, and calling it anything else would
> be the exact failure this release was consolidated to prevent.

## What this folder is for

Everything a deployment needs to read **before** anyone touches a tenant, plus a
checksummed, tag-traceable snapshot of the solution envelope at 1.0.0.

| File | What it is |
|---|---|
| `MissionFeedingOperations_1.0.0.zip` | The solution envelope, packed from tag `v1.0.0` |
| `SHA256SUMS.txt` | Checksum. The version, the commit and this checksum describe one build |
| `RELEASE_NOTES.md` | What is in the release and what ships switched off |
| `KNOWN_LIMITATIONS.md` | What does not work yet, stated plainly |
| `IMPORT_CHECKLIST.md` | What must be true before the import |
| `POST_IMPORT_CHECKLIST.md` | What must be done after it, in order |
| `DEPENDENCY_MANIFEST.md` | 66 destination-side resources. **16 MUST ALREADY EXIST** |
| `SECURITY_README.md` | The security verification, and the one open issue |

**Deployment documentation sits beside the ZIP, not inside it.** The ZIP
contains only what Power Platform import expects.

## How this becomes an importable solution

1. Provision the lists — `provisioning/Provision-MFOpsLists.ps1`. **This is not
   part of the import and never will be.**
2. Author the canvas app in the maker portal from `canvas-app/src/*.pa.yaml`.
3. Build the five flows from `flows/*/definition.md`. They are specifications,
   deliberately not fabricated JSON.
4. Export the solution, unmanaged, and `pac canvas unpack` the `.msapp`.
5. **If the exported YAML disagrees with `canvas-app/src`, the committed YAML
   wins** and the app is corrected, not the source.
6. Re-tag and rebuild this folder from the new tag.

## Traceability

```
version  1.0.0
tag      v1.0.0
commit   see SHA256SUMS.txt
```

The version, the commit hash and the checksum describe the same build, or the
artifact cannot be traced once it crosses to the `.mil` side.
