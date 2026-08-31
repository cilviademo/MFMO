# Rollback

**Rollback is importing the previous ZIP from `dist/`.** It is tested as part
of each release, not assumed. There is no Pipelines dependency and no automatic
down-migration.

This matters more here than in most builds: the tenant grants **one
environment**, so publishing is deploying and there is no staging tier to catch
a bad release. The kill switch, not the rollback, is the first response.

---

## The order of response

Work down this list. Most incidents stop at step 1 or 2.

### 1. `ReadOnlyMode` — something is wrong but not broken

```
MF_App_Config.ReadOnlyMode = True
```

Status stays readable; writes stop. **Prefer this to pulling the app.** When a
base cannot tell whether their 1119 arrived, taking the app away is worse than
leaving it read-only — and the flows enforce the same key, so the disabled
control is a courtesy and the flow check is the control.

Takes effect on the next named-formula re-evaluation. No deployment.

### 2. `MaintenanceMode` — the app itself is the problem

```
MF_App_Config.MaintenanceMode = True
MF_App_Config.SupportMessage  = what people should do instead
```

Everyone except developers and admins lands on `scrMaintenance` before any
business data source is opened. Use this when the app is wrong in a way that
would mislead someone, not merely inconvenient.

### 3. Turn off one feature

```
MF_Feature_Flags.<Feature_Key>.Enabled_Prod = FALSE
```

If a single screen is at fault, remove that screen rather than the release.
This is why the flags exist: **the rollback is a checkbox.** Do not hand-rename
old and new screens.

### 4. Disable a flow

Turn off the offending flow in the maker portal. EOM-01, EOM-03 and EOM-04 are
each independently disableable, and none of them is load-bearing for reading
status:

| Flow off | Consequence |
|---|---|
| EOM-01 | No new expected items next period. Existing ones unaffected. |
| EOM-02 | Folder drops stop being discovered. **They are not lost** — re-running later picks them up, because intake is idempotent on `SharePoint_File_ID`. |
| EOM-03 | Status stops being recalculated overnight. The app still recalculates on every QC action, so the data does not rot; it goes stale. |
| EOM-04 | Notifications stop. Nothing else. |

### 5. Import the previous ZIP

```bash
pac solution import --path dist/MissionFeedingOperations_v<previous>.zip \
    --settings-file <environment settings> --force-overwrite
```

Then verify against the checklist below.

---

## What a solution rollback does NOT undo

This is the part that gets missed.

| Changed by the release | Reverted by the import? |
|---|---|
| App screens, formulas, components | **Yes** |
| Flow definitions | **Yes** |
| Connection references, environment variables | Yes, from the settings file |
| **SharePoint list columns** | **NO** |
| **Data written since the release** | **NO** |
| **`MF_App_Config` and `MF_Feature_Flags` rows** | **NO** — they are data |
| **Status values EOM-03 already wrote** | **NO** |

The lists are provisioned from `scripts/eom_schema.py`, deliberately **not**
carried as solution components — carrying list definitions in two places is how
they drift. The consequence is that a schema change is not rolled back by a
solution import and has to be handled separately.

### Rolling back across a schema change

Schema changes are **additive within a version line**. A retired column is
marked unused and documented, never deleted, because deleting a SharePoint
column destroys its data irreversibly and no import restores it.

So the rollback procedure is:

1. Import the previous solution ZIP.
2. **Leave the new columns in place.** The older app ignores columns it does
   not know about; deleting them to "clean up" is the one irreversible act in
   this whole document.
3. If the newer release wrote values the older app cannot read — a
   `Final_Status` of `LATE` into an app that predates the six-state model, for
   example — run the previous release's EOM-03 over the affected periods to
   rewrite them.
4. Record the variance in `CHANGELOG.md` against the release you rolled back
   to, not the one you rolled back from.

Step 3 is the reason the status engine writes all four status fields together
from one evaluation: a partial rewrite is recoverable, a mixed set is not.

---

## Verification after a rollback

Do not declare it done on import success. **Import success is not
authorisation to operate**, and it is not proof of a working rollback either.

- [ ] `MF_App_Config.AppVersion` reads the version you rolled back to
- [ ] `scrDiagnostics` shows the expected app and schema versions, and no
      schema-mismatch warning
- [ ] A base user can open the app, see their package, and upload
- [ ] A reviewer can accept and return, and a return still demands a comment
      and a correction date
- [ ] EOM-01 re-run for the open period creates **zero** rows
- [ ] `MF_EOM_Status` and the app agree, via
      `python3 scripts/validate_solution.py --reconcile-fact`
- [ ] Telemetry rows carry the rolled-back `App_Version`, so the event log
      shows exactly when the change took effect

That last one is why `App_Version` is stamped on every event: in a
single-environment tenant it is the only reliable record of which build
produced which data.

---

## Release history

Every release produces `dist/MissionFeedingOperations_vX.Y.Z.zip`, a
`CHANGELOG.md` entry and the deployment settings for that environment.
Canonical source lives in this repository, not inside Power Apps: even where
the tenant forces an import-as-new-app pattern, any release can be recreated
exactly from the tagged commit.

**`dist/` currently holds no ZIP.** No tenant has been touched, so there is
nothing to roll back to yet, and a hand-assembled artifact that had never been
imported would be worse than none.

---

## What R1 adds to this

**The four site bindings are not in the ZIP.** Rolling the solution back does
not unbind them and does not rebind them — `Site_URL`, `Verified_By` and
`Active_Flag` live in `MF_Document_Destination`, which is data. If a
destination was wrongly activated, set `Active_Flag = FALSE` on that row: EOM-02
fails closed immediately and no import is needed.

**A schema rollback is not a solution rollback.** Importing the previous ZIP
gives you the previous app and flows against the *current* SharePoint schema.
That is safe in one direction only:

| | |
|---|---|
| Older app, newer schema | **Safe.** The app reads columns it knows and ignores the rest. The schema gate refuses writes on a version mismatch, which is the intended behaviour, not a fault |
| Newer app, older schema | **Not safe, and now blocked.** The app patches columns that do not exist, which writes nothing rather than erroring. `gblSchemaMatches` disables writes for everyone, developers included |

So a rollback of the app alone is fine. A rollback that also means reverting
`scripts/eom_schema.py` is not a rollback — it is a migration, and columns are
never deleted, only marked unused.

**`Submission_Request_ID` is required.** A rolled-back app that does not send it
cannot write a submission at all. That is deliberate: an app that skips the
idempotency key would create duplicates on every retry. If you must run an
older app against this schema, do it read-only.
