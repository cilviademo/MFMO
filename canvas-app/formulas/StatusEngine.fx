// =============================================================================
// StatusEngine.fx — the one status engine.
//
// Reference implementation:  scripts/status_engine.py
// Server-side twin:          flows/EOM03-Reconciliation
// Executable specification:  docs/mf-operations-prototype.html  itemStatus()
// Held in agreement by:      tests/test_status_engine.py
//
// ONE evaluation returns the whole state object. Label, colour and action
// ownership never diverge because they are never derived separately.
//
// This replaces the V3 App.Formulas.fx, which had StatusLabel(), StatusColor()
// and StatusSemantic() as three parallel Switch statements over the numeric
// code — and those three had already drifted from V3's own decision table.
// See docs/handoffs/RECONCILIATION.md corrections C1-C3.
//
// Nothing about status is ever set by a human. There is no colour picker.
// =============================================================================

// Final_Status is the SEMANTIC string. Status_Code is the NUMERIC visual code.
// Both are stored on MF_EOM_Item, written together, and neither is derived
// from the other.
MF_StatusResult := Type({
    status:         Text,       // Final_Status
    code:           Number,     // Status_Code, 0-4
    label:          Text,
    actionOwner:    Text,
    actionRequired: Boolean
});

// -----------------------------------------------------------------------------
// The five visual codes.
//
// Four were not enough. Collapsing "not applicable" and "not due yet" into Gray
// made an installation whose requirements had simply not come due display as
// Not applicable. Blue separates "in progress, nothing wrong" from "does not
// apply".
// -----------------------------------------------------------------------------
MF_CodeNA      = 0;    // Gray
MF_CodeAction  = 1;    // Red
MF_CodePending = 2;    // Amber
MF_CodeDone    = 3;    // Green
MF_CodeInfo    = 4;    // Blue

// The eight semantic statuses. This table IS the mapping; it is not repeated
// in a Switch() anywhere else in the app.
MF_StatusCatalog =
    Table(
        { status: "NOT_APPLICABLE",      code: 0, label: "Not applicable",    actionOwner: "None",     actionRequired: false, rank: 8 },
        { status: "NOT_DUE",             code: 4, label: "Not due",           actionOwner: "Facility", actionRequired: false, rank: 6 },
        { status: "PENDING_VALIDATION",  code: 4, label: "Informational",     actionOwner: "Admin",    actionRequired: false, rank: 7 },
        { status: "OVERDUE",             code: 1, label: "Overdue",           actionOwner: "Facility", actionRequired: true,  rank: 1 },
        { status: "NOT_SATISFIED",       code: 2, label: "Not satisfied",     actionOwner: "Facility", actionRequired: true,  rank: 3 },
        { status: "CORRECTION_REQUIRED", code: 2, label: "Correction needed", actionOwner: "Facility", actionRequired: true,  rank: 2 },
        { status: "RECEIVED_PENDING_QC", code: 2, label: "Awaiting review",   actionOwner: "Reviewer", actionRequired: true,  rank: 4 },
        { status: "ACCEPTED",            code: 3, label: "Accepted",          actionOwner: "None",     actionRequired: false, rank: 5 }
    );

// Presentation from a stored Final_Status. This is what every gallery, badge and
// detail pane calls. It is a LOOKUP, not a recomputation: the row already
// carries the status, written by EOM-03 or by the app's own QC action.
MF_Status(FinalStatus: Text): MF_StatusResult =
    With(
        { m: LookUp(MF_StatusCatalog, status = FinalStatus) },
        If(
            IsBlank(m.status),
            // An unknown status is a bug, not a state. Show it; do not hide it.
            { status: FinalStatus, code: 0, label: "Unknown status",
              actionOwner: "Admin", actionRequired: true },
            { status: m.status, code: m.code, label: m.label,
              actionOwner: m.actionOwner, actionRequired: m.actionRequired }
        )
    );

// -----------------------------------------------------------------------------
// The evaluation. Ordered, total, first match wins.
//
// Mirrors scripts/status_engine.py item_status() and the prototype's
// itemStatus() branch for branch. Used in the app so a just-patched row renders
// correctly before the nightly run; the authoritative write is EOM-03, so the
// app and the flow can never disagree about a row that already exists.
//
// Reordering these branches changes behaviour. The tests assert the order.
// -----------------------------------------------------------------------------
MF_EvaluateStatus(
    Today: Date,
    DueDate: Date,
    RequiredFlag: Boolean,
    WaivedFlag: Boolean,
    AuthorityStatus: Text,
    ReceivedFlag: Boolean,
    QCStatus: Text
): MF_StatusResult =
    MF_Status(
        // 1. The obligation does not exist for this row.
        If( WaivedFlag || !RequiredFlag,
            "NOT_APPLICABLE",

        // 2. A provisional requirement is informational, never adverse. All
        //    twelve seeded requirements are UNVERIFIED, so this is the default
        //    path today. The action sits with the Admin — verify the
        //    requirement — not with the facility.
        AuthorityStatus = "UNVERIFIED" && !ReceivedFlag,
            "PENDING_VALIDATION",

        // 3-7. A current-version submission exists; its QC verdict decides.
        QCStatus = "Accepted",
            "ACCEPTED",
        QCStatus = "Not Applicable",
            "NOT_APPLICABLE",
        QCStatus = "Correction Required",
            "CORRECTION_REQUIRED",

        // A wrong document does not stay Red forever. It means the requirement
        // is still UNMET, and whether that is urgent depends on the suspense
        // date rather than on the reviewer's verdict.
        QCStatus = "Wrong Document",
            If( Today > DueDate, "OVERDUE", "NOT_SATISFIED" ),

        // 8. Received and waiting on a reviewer.
        ReceivedFlag,
            "RECEIVED_PENDING_QC",

        // 9-10. Nothing received. Time decides.
        IsBlank(DueDate) || Today <= DueDate,
            "NOT_DUE",

            "OVERDUE"
        )
    );

// -----------------------------------------------------------------------------
// Package rollup — over SEMANTIC statuses, never over colour codes.
//
// The naive colour rollup sees [3, 4, 4], finds no 1 and no 2, and marks the
// package Complete. It is IN PROGRESS: two requirements have not been filed.
//
// This replaces V3's MFRollup(), which was that naive colour rollup — on the
// page below V3's own prose calling it wrong.
// -----------------------------------------------------------------------------
MF_PackageCatalog =
    Table(
        { state: "ACTION_REQUIRED", code: 1, label: "Action required" },
        { state: "IN_REVIEW",       code: 2, label: "In review" },
        { state: "COMPLETE",        code: 3, label: "Complete" },
        { state: "IN_PROGRESS",     code: 4, label: "In progress" },
        { state: "NOT_APPLICABLE",  code: 0, label: "Nothing due" }
    );

// Items must already be filtered to what the viewer may see. A user scoped to
// one DFAC must not receive an installation figure derived from their
// neighbours' packages — see Delegation.fx MF_VisibleItems.
MF_PackageState(Items: Table): Text =
    With(
        {
            applicable: Filter(Items, Final_Status <> "NOT_APPLICABLE"),
            adverse:    Filter(Items, Final_Status in ["OVERDUE", "CORRECTION_REQUIRED", "NOT_SATISFIED"]),
            inReview:   Filter(Items, Final_Status = "RECEIVED_PENDING_QC")
        },
        If( CountRows(applicable) = 0,           "NOT_APPLICABLE",
            CountRows(adverse) > 0,              "ACTION_REQUIRED",
            CountRows(inReview) > 0,             "IN_REVIEW",
            // A provisional requirement neither completes a package nor blocks it.
            With( { real: Filter(applicable, Final_Status <> "PENDING_VALIDATION") },
                If( CountRows(real) > 0
                        && CountRows(Filter(real, Final_Status <> "ACCEPTED")) = 0,
                    "COMPLETE",
                    "IN_PROGRESS" )
            )
        )
    );

MF_PackageLabel(Items: Table): Text =
    LookUp(MF_PackageCatalog, state = MF_PackageState(Items)).label;

MF_PackageCode(Items: Table): Number =
    LookUp(MF_PackageCatalog, state = MF_PackageState(Items)).code;

// -----------------------------------------------------------------------------
// Colour. Derived from the code and from nothing else.
// Contrast ratios verified in docs/accessibility.md.
// -----------------------------------------------------------------------------
MF_StatusColor(Code: Number): Color =
    Switch( Code,
        MF_CodeDone,    clrStatusGreen,
        MF_CodePending, clrStatusAmber,
        MF_CodeAction,  clrStatusRed,
        MF_CodeInfo,    clrStatusBlue,
        clrStatusGray
    );

MF_StatusBackground(Code: Number): Color =
    Switch( Code,
        MF_CodeDone,    clrStatusGreenBg,
        MF_CodePending, clrStatusAmberBg,
        MF_CodeAction,  clrStatusRedBg,
        MF_CodeInfo,    clrStatusBlueBg,
        clrStatusGrayBg
    );

// The accessible sentence, built in one place. Status is never colour-only:
// every chip carries its label, and a screen reader gets the whole sentence.
MF_StatusAccessibleLabel(FinalStatus: Text, DueDate: Date): Text =
    With(
        { p: MF_Status(FinalStatus) },
        "Status: " & p.label & ". " &
        If( p.actionOwner = "None",
            "No action required. ",
            "Action owner: " & p.actionOwner & ". " ) &
        If( IsBlank(DueDate), "", "Due " & Text(DueDate, "d mmmm yyyy") & "." )
    );

// "Is this mine, or am I waiting on someone else?" Status_Code alone cannot
// answer it — Amber covers both correction needed (the facility's action) and
// awaiting review (AFSVC's). Home filters on ownership, not on colour.
MF_IsMyAction(FinalStatus: Text): Boolean =
    With(
        { p: MF_Status(FinalStatus) },
        p.actionRequired &&
        Switch( p.actionOwner,
            "Facility", gblScopeType = "Facility" || gblScopeType = "Installation",
            "Reviewer", gblCanQC,
            "Admin",    gblCanEditReqs,
            false )
    );
