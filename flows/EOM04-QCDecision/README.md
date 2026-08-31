# EOM-04 — QC decision and notifications

Called by `scrReview`. Accepts or returns a submission, then re-evaluates the
item through the status engine.

## QC decisions are inputs, not statuses

A reviewer accepts or returns. The engine decides what the item then looks
like. Nobody picks `ACCEPTED` and nobody picks a colour — the flow writes
back the four fields one evaluation returned.

| Decision | Submission | Item becomes |
|---|---|---|
| `ACCEPTED` | `QC_Status = ACCEPTED` | `ACCEPTED` / Green, action owner `None` |
| `RETURNED` | `QC_Status = RETURNED`, `QC_Comment`, `New_Suspense_Date` | `RETURNED` / Amber, action owner `Facility`, and the item's `Suspense_Date` moves to the new date |

## A return is blocked without a comment and a new suspense date

```
if decision = RETURNED and (comment is blank or newSuspenseDate is blank):
    respond { ok: false, code: "RETURN_INCOMPLETE" } and write nothing
```

Both are checked in the app, which disables the button, and again here, which
is the control. A returned document with no deadline is how items disappear:
nobody owns it, nothing goes red, and it surfaces at an inspection.

The new suspense date is written to the submission **and** back onto
`MF_EOM_Item.Suspense_Date`, because the engine's step 8 reads the item.

## Resubmission

A return does not create a new version. The facility resubmits through
`scrUpload`, `EOM-05` creates v2, demotes v1, and the item's status follows
the new current version. **v1 keeps its row, its file and its QC comment** —
the audit question is "what did they send and what did the reviewer say", for
every attempt.

## Notifications — flag-gated, ships off

`EnableNotifications` ships `False`, and capability gate 7 (Office 365
Outlook) must be GREEN before it may be turned on.

**Read the log for a full cycle before enabling.** Every notification the flow
*would* have sent is written to `MF_App_Event_Log` as a `FlowRun` row with
the recipient and reason, so the volume and the targeting can be inspected
against a real month before anyone's inbox is involved. A notification system
switched on untested is how a programme teaches several hundred people to
filter its mail to a folder.

When enabled it sends on:

* a return, to the facility manager — one mail, with the comment and the new
  suspense date, and no digest;
* an item crossing its suspense date unsubmitted, **only when the requirement
  is `VERIFIED`**. A provisional requirement does not generate a nag: the
  action sits with the programme, not the facility, and mailing a facility
  about an obligation nobody has confirmed exists is exactly the behaviour
  the Gray state prevents on screen.
