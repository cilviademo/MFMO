# EOM-02 — File intake (folder drops)

**The app is the front door, and folder drops keep working.** This flow is the
second path, not the fallback for a failure of the first: people will keep
copying files into folders, and a system that loses them is worse than one
that queues them.

## Library-level trigger, not folder-level

The SharePoint trigger binds to the **library**, with the folder path left
empty.

A folder-level trigger silently misses everything dropped into a folder
created after the flow was authored — and Portfolio FY folders are created
every year, per installation, by people who do not know a flow exists. The
failure is invisible: no error, no run, just files that never arrive.

So: one trigger on the library, and the folder path becomes evidence the flow
reads rather than a binding it depends on.

## What it does

```
on file created in <EvidenceLibraryPath>:

  if the file was written by EOM-05 (it carries the item key prefix and the
     submission row already exists for this SharePoint_File_ID):
        do nothing — this is the front door's own write coming back round

  else:
     parse the folder path for a TIER 1 hint:
        <PortfolioRootPath>/<Portfolio>/FY<year>/<Installation>/<Facility>/<Period>
     look up an expected item matching the hint

     create MF_EOM_Submission with
        EOM_Item_ID           = NULL
        Classification_Status = NEEDS_CLASSIFICATION
        Classification_Method = FOLDER_HINT (or UNCLASSIFIED with no hint)
        Suggested_Facility_ID, Suggested_Requirement_ID from the hint
```

**The hint is never applied.** It is displayed on `scrUnmatched` as a
suggestion beside the pickers, and a human chooses. A folder path is a
convention, and conventions drift; a declared upload is a fact.

**Never invent a requirement.** There is no branch in this flow that creates
an `MF_EOM_Item`. A file with no matching expected item stays in the queue
until somebody decides what it is — or decides the requirement should exist,
which is a deliberate act on `scrAdminRequirements`, not a side effect of a
file appearing.

**Filenames are never read for meaning.** Not for the facility, not for the
period, not for the document type. `File_Name` is stored as evidence.

## The classification ladder

| Tier | Method | Status |
|---|---|---|
| 0 | `DECLARED` — installation, facility, document type and period declared at upload | production baseline, ~95% of volume |
| 1 | `FOLDER_HINT` — folder context, uploader | **suggestion only, never applied** |
| 2 | `CONTENT` — document content | behind `EnableDocumentContentAI`, ships `False`, no code path in R1 |
| 3 | `AI_BUILDER` | behind `EnableAIBuilder`, ships `False`, no code path in R1 |
| 4 | `MANUAL` — the queue | `scrUnmatched` |

Tiers 2 and 3 exist as vocabulary and as flags. **Do not build a classifier
the architecture no longer needs.** The system declares at upload, so it
mostly does not have to infer — and AI Builder must never become a dependency
whose availability could block the app.

## The companion: EOM02-ClassifyUnmatched

`scrUnmatched` calls `EOM02_ClassifyUnmatched.Run(...)` to resolve a queued
row against an **existing** expected item. It:

1. re-checks `ReadOnlyMode` and the caller's scope,
2. verifies the target `MF_EOM_Item` exists (refusing if not),
3. computes the next version number the same way `EOM-05` does,
4. demotes the previous current version,
5. patches the queued row: `EOM_Item_ID` set, `Classification_Status =
   CLASSIFIED`, `Classification_Method = MANUAL`, `QC_Status = PENDING`,
6. patches the item's status through the engine.

It never creates an item and never deletes the queued row — a resolved stray
keeps its history, including the fact that it arrived unclassified.

## Duplicate suppression

A file whose `SharePoint_File_ID` already exists on a submission row is
recorded as `REJECTED_DUPLICATE` rather than queued again. Re-running the
flow over a library, which happens after any outage, is therefore safe.
