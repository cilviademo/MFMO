# Post-import checklist — the pilot, in order

`IMPORT_CHECKLIST.md` gets the solution in. This gets the pilot running, and it
stops at the first box that does not tick.

**Notifications are LAST and only when approved.** `NotificationsEnabled` is
FALSE by programme decision, and EOM-04 ships disabled. A notification storm
against 103 installations is not recoverable by turning the flag back off.

---

## 1-8 — provisioning and import

Those are `IMPORT_CHECKLIST.md` steps 1 to 8. Do not start here until step 9 of
that file is the next thing left.

Then verify what arrived:

- [ ] `python3 scripts/verify_provisioning.py <tenant-export.json>` returns 0.
      **"The provisioning run said OK" is not evidence.** A run can create a
      list, most of its columns and none of its indexes and report success.
- [ ] The app opens and `gblSchemaVersion` reads `5.0`.

## 8b — sharing and access, before any pilot user touches the app

The four platform steps in `CANVAS_APP_ASSEMBLY.md` → "After publish —
sharing and access". They are repeated here as boxes because forgetting the
second one fails every non-owner's submission at runtime:

- [ ] App shared with the pilot **security group** as **User** (not
      Co-owner, not individuals).
- [ ] **EOM-02 Submission flow shared Run-only** with the same group, with
      connections set to **"Use this connection"** — not "Provided by
      run-only user".
- [ ] All three connection references bound to the **service account**,
      not a person.
- [ ] SharePoint list permissions granted per the security model — app
      sharing grants nothing in SharePoint (`docs/security-open-issue.md`).

## 9 — EOM-01, alone, twice

- [ ] Enable **EOM-01 only**. Every other flow stays off.
- [ ] Run it. **Expect 737 `MF EOM Item` rows** — 268 for `2026-08`, 469 for
      `2026-09`.
- [ ] Run it **again, unchanged**. **Expect 737.**

      A second run that adds rows means the deterministic `EOM_Item_ID` check
      is not working, and every count downstream is wrong from here on.

- [ ] Two views: one filtered `Facility_ID is empty`, one filtered
      `Requirement_Scope is Installation or Contract`. **The counts must agree
      exactly.** A mismatch means empty strings were written where nulls
      belong, and every `Filter()` in the app is wrong.

## 10 — one pilot document, end to end

Enable **EOM-02**. One document, and then check five things — not four.

- [ ] Submit one document from the app for a facility you can see.
- [ ] **Where it landed.** The configured `Root_Folder`, inside the FY26 folder,
      inside the month folder. Not the root. If it is at the root, the month
      folder did not match: `Needs_Filing` will be TRUE and it appears on
      Exceptions.
- [ ] **The file ID.** `SharePoint_Unique_ID` on the submission is populated.
- [ ] **The URL.** `File_URL` resolves, and it was derived from the unique ID
      rather than assembled from a path.
- [ ] **The submission row.** One row. `Is_Current` TRUE, `Version_No` 1,
      `Submission_Request_ID` populated.
- [ ] **The item row.** `Current_Submission_ID` points at it,
      `Received_Flag` TRUE, `Final_Status` moved to `RECEIVED_PENDING_QC`.

- [ ] **Retry the same submission.** Same `Submission_Request_ID`. **Expect one
      submission, not two.** This is the idempotency the whole upload design
      exists for.

## 11 — review, correction, versioning

- [ ] Accept it. `Final_Status` becomes `ACCEPTED`, the item leaves the
      reviewer's queue.
- [ ] Submit a second document for a different requirement, then **Return** it
      with a reason and a correction suspense.
- [ ] Confirm a correction ticket exists with the reason, the comment and the
      due date, and that the item is now the *base's* action, not AFSVC's.
- [ ] Re-submit against the returned item. **Expect `Version_No` 2, the first
      version `Is_Current` FALSE and `Superseded_By` populated.** The first
      version is still there — nothing is deleted.

## 12 — reconciliation

- [ ] Enable **EOM-03**. Run it.
- [ ] Confirm `Final_Status` and `Status_Code` are unchanged for items nobody
      touched. EOM-03 is the only writer of those outside the app's QC action,
      and a reconciliation that moves a status nobody changed is a bug.
- [ ] Confirm `MF EOM Status` was rebuilt and its row count matches
      `MF EOM Item`.

## 13 — legacy intake, one copy at a time

- [ ] Enable **one** EOM-02b copy, for a portfolio whose site you have
      verified.
- [ ] Drop a file into that site's watched folder by hand.
- [ ] Confirm it appears on Exceptions under **Unmatched files**, and that
      **no `MF EOM Item` was created**. Never invent a requirement.
- [ ] Repeat per portfolio, enabling one copy at a time. Four copies pointed at
      the same site looks exactly like working.

## 14 — notifications, LAST, and only when approved

- [ ] Get explicit programme approval. This is not a technical decision.
- [ ] Set `NotificationsEnabled` TRUE.
- [ ] Enable **EOM-04**.
- [ ] Confirm the first run sends a **digest**, not one message per item.

---

## Before anyone calls this production

- [ ] EOM-01 has run twice at 737.
- [ ] One pilot document landed in the right folder on the real tenant.
- [ ] The installation-scope data-layer question in `KNOWN_LIMITATIONS.md` has
      an answer from the SharePoint administrator.

Until all three, the recommendation stays **DEV/PILOT**.
