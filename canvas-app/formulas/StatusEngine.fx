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
// The SIX visual codes.
//
// Colour carries OWNERSHIP and time risk, not severity:
//
//   Blue   4  not due, window open           nobody yet
//   Amber  5  past the first suspense        the base, with runway
//   Red    1  past the final call, returned  the base, out of runway
//   Yellow 2  received, awaiting review      AFSVC
//   Green  3  accepted                       nobody
//   Gray   0  not applicable                 nobody
//
// The amber/yellow split is the point. Amber means TIME RISK; yellow means
// SOMEBODY ELSE HAS IT. Collapsing them tells a DFAC manager that a document
// they filed on time and one they never sent are the same kind of problem.
//
// Six is the ceiling. A seventh would stop being scannable.
// -----------------------------------------------------------------------------
MF_CodeNA     = 0;    // Gray
MF_CodeRed    = 1;    // Red
MF_CodeYellow = 2;    // Yellow
MF_CodeGreen  = 3;    // Green
MF_CodeBlue   = 4;    // Blue
MF_CodeAmber  = 5;    // Amber

// The nine semantic statuses. This table IS the mapping; it is not repeated in
// a Switch() anywhere else in the app.
MF_StatusCatalog =
    Table(
        { status: "NOT_APPLICABLE",      code: 0, label: "Not applicable",  actionOwner: "None",     actionRequired: false, rank: 9 },
        { status: "NOT_DUE",             code: 4, label: "Not due",         actionOwner: "Facility", actionRequired: false, rank: 7 },
        { status: "PENDING_VALIDATION",  code: 4, label: "Informational",   actionOwner: "Admin",    actionRequired: false, rank: 8 },
        { status: "LATE",                code: 5, label: "Late",            actionOwner: "Facility", actionRequired: true,  rank: 4 },
        { status: "OVERDUE",             code: 1, label: "Overdue",         actionOwner: "Facility", actionRequired: true,  rank: 1 },
        { status: "RETURNED",            code: 1, label: "Returned",        actionOwner: "Facility", actionRequired: true,  rank: 2 },
        { status: "NOT_SATISFIED",       code: 1, label: "Not satisfied",   actionOwner: "Facility", actionRequired: true,  rank: 3 },
        { status: "RECEIVED_PENDING_QC", code: 2, label: "Awaiting review", actionOwner: "Reviewer", actionRequired: true,  rank: 5 },
        { status: "ACCEPTED",            code: 3, label: "Accepted",        actionOwner: "None",     actionRequired: false, rank: 6 }
    );

// The four verdicts that mean "it came back". The engine collapses them into
// one RETURNED state; the base reads the specific reason off the submission.
MF_ReturningVerdicts =
    ["Correction Required", "Incomplete", "Wrong Reporting Period", "Wrong Facility"];

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
    EffectiveDueDate: Date,
    EffectiveFinalCallDate: Date,
    RequiredFlag: Boolean,
    WaivedFlag: Boolean,
    AuthorityStatus: Text,
    ReceivedFlag: Boolean,
    QCStatus: Text
): MF_StatusResult =
    MF_Status(
        With(
            // A requirement with no final call is held to its first suspense.
            { final: Coalesce(EffectiveFinalCallDate, EffectiveDueDate) },

        // 1. The obligation does not exist for this row this period.
        If( WaivedFlag || !RequiredFlag,
            "NOT_APPLICABLE",

        // 2. A provisional requirement is informational, never adverse: the
        //    base has nothing to do and nothing is wrong. With eleven of
        //    thirteen requirements now VERIFIED against the AFSVC procedures
        //    deck this applies to almost nothing — a missed 1119 turns red as
        //    it should.
        (AuthorityStatus = "UNVERIFIED" || AuthorityStatus = "PROPOSED") && !ReceivedFlag,
            "PENDING_VALIDATION",

        // 3-4. A verdict that ends the obligation.
        QCStatus = "Accepted",
            "ACCEPTED",
        QCStatus = "Not Applicable",
            "NOT_APPLICABLE",

        // 5. A recall is the submitter withdrawing BEFORE review, not a
        //    rejection. The item reverts to its date-based state and the
        //    withdrawn version stays in history as superseded.
        QCStatus = "Recalled",
            MF_DateState(Today, EffectiveDueDate, final),

        // 6. Four verdicts, one status. The reason lives on the submission and
        //    is what the base reads — the engine does not need four states to
        //    say "it came back", and the submitter needs four reasons to know
        //    what to fix.
        QCStatus in MF_ReturningVerdicts,
            "RETURNED",

        // 7-8. A wrong document does not stay Red by fiat: the requirement is
        //      still UNMET, and whether that is urgent depends on the suspense
        //      date rather than on the reviewer's verdict.
        QCStatus = "Wrong Document",
            If( Today > final, "OVERDUE", "NOT_SATISFIED" ),

        // 9. Received and waiting on a reviewer. YELLOW: AFSVC owns it.
        ReceivedFlag,
            "RECEIVED_PENDING_QC",

        // 10-12. Nothing received. Time decides, and the two suspenses split it.
            MF_DateState(Today, EffectiveDueDate, final)
        ))
    );

// Rules 10-12. The week between the two dates is the only one in the cycle
// where a reminder still changes the outcome, so it gets its own state.
//
// ALWAYS evaluated against the EFFECTIVE dates. Reporting uses the nominal
// ones, so "the 5th" stays the 5th in a leadership brief while the base is
// held to a date they can actually meet.
MF_DateState(Today: Date, EffectiveDue: Date, EffectiveFinal: Date): Text =
    If( IsBlank(EffectiveDue) || Today <= EffectiveDue, "NOT_DUE",
        IsBlank(EffectiveFinal) || Today <= EffectiveFinal, "LATE",
        "OVERDUE" );

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
            adverse:    Filter(Items, Final_Status in ["OVERDUE", "RETURNED", "NOT_SATISFIED", "LATE"]),
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
        MF_CodeGreen,  clrStatusGreen,
        MF_CodeYellow, clrStatusYellow,
        MF_CodeAmber,  clrStatusAmber,
        MF_CodeRed,    clrStatusRed,
        MF_CodeBlue,   clrStatusBlue,
        clrStatusGray
    );

MF_StatusBackground(Code: Number): Color =
    Switch( Code,
        MF_CodeGreen,  clrStatusGreenBg,
        MF_CodeYellow, clrStatusYellowBg,
        MF_CodeAmber,  clrStatusAmberBg,
        MF_CodeRed,    clrStatusRedBg,
        MF_CodeBlue,   clrStatusBlueBg,
        clrStatusGrayBg
    );

// The accessible sentence, built in one place. Status is never colour-only:
// every chip carries its label, and a screen reader gets the whole sentence.
MF_StatusAccessibleLabel(FinalStatus: Text, NominalDue: Date, EffectiveDue: Date): Text =
    With(
        { p: MF_Status(FinalStatus) },
        "Status: " & p.label & ". " &
        If( p.actionOwner = "None",
            "No action required. ",
            "Action owner: " & p.actionOwner & ". " ) &
        MF_DueDatePhrase(NominalDue, EffectiveDue)
    );

// "Due 5 Sep (Mon 8 Sep)". Where the two differ the screen shows BOTH — a
// nominal suspense landing on a Saturday cannot be the date someone is held
// to, and burying that adjustment produces a monthly argument.
MF_DueDatePhrase(NominalDue: Date, EffectiveDue: Date): Text =
    If( IsBlank(NominalDue),
        "",
        "Due " & Text(NominalDue, "d mmm") &
        If( IsBlank(EffectiveDue) || NominalDue = EffectiveDue,
            "",
            " (" & Text(EffectiveDue, "ddd d mmm") & ")" ) );

// On-time is two questions and they are told to different audiences. NEVER
// render these as two booleans.
MF_OnTimePhrase(
    InitialSubmitted: DateTime, InitialOnTime: Boolean,
    AcceptableEvidence: DateTime, FinalOnTime: Boolean
): Text =
    Concatenate(
        If( IsBlank(InitialSubmitted), "",
            "Submitted " & Text(InitialSubmitted, "d mmm") & " - " &
            If(InitialOnTime, "on time", "after suspense") ),
        If( IsBlank(AcceptableEvidence), "",
            Char(10) & "Accepted " & Text(AcceptableEvidence, "d mmm") & " - " &
            If(FinalOnTime, "final evidence on time", "final evidence after suspense") )
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
