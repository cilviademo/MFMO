# Components — build once, reuse across every future module

`Requirement | Scope | Due | Status | Action` works for EOM documents today and
FMAT corrective actions, training certifications, equipment work orders and
Five-Year requirements later. That reuse is the reason this is a Power App and
not six Teams tabs.

| Component | Properties | Notes |
|---|---|---|
| `cmpStatusChip` | `StatusCode`, `Label`, `Size` | Colour from `MFStatusColor`. Only place a colour is chosen. |
| `cmpHeader` | `Title`, `Subtitle`, `ShowBack` | Consistent nav |
| `cmpInstallationCard` | `Installation`, `PackageCode`, `OnSelect` | Home grid tile |
| `cmpRequirementRow` | `Label`, `Scope`, `DueDate`, `StatusCode`, `IsUnverified`, `OnSelect` | The workhorse |
| `cmpWorkQueueItem` | `Installation`, `Facility`, `Requirement`, `StatusCode`, `DueDate`, `OnSelect` | My Work |
| `cmpEmptyState` | `Icon`, `Message`, `ActionLabel`, `OnAction` | "Nothing due" is a good outcome — say so |
| `cmpConfirmationDialog` | `Title`, `Body`, `OnConfirm`, `OnCancel` | QC and waivers |
| `cmpCascadePicker` | `ShowInstallation`, `ShowFacility`, `ShowRequirement`, `AllowOnBehalf` | Hides itself when the user has one choice |

`cmpStatusChip` is the only component that maps a code to a colour. Nothing else
in the app references a hex value, so changing the palette is one edit.

`cmpRequirementRow` renders unverified requirements dimmed with a tooltip
carrying `Authority_Reference`. A user should be able to see that SF 1080 is
provisional rather than wonder why it never turns red.
