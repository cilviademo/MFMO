// =============================================================================
// StatusEngine.fx  —  the one status engine, transliterated.
//
// Reference implementation: scripts/status_engine.py.
// Server-side twin:        flows/EOM03-StatusFact.
// Held in agreement by:    tests/test_status_engine.py.
//
// One evaluation. It returns { status, code, label, actionOwner, actionRequired }.
// NEVER write a second function that derives the label independently of the
// code. If you need a label, call MF_StatusPresentation(code). If you need a
// colour, call MF_StatusPresentation(code).status. Nothing else.
//
// Status is calculated, never chosen. There is no colour picker anywhere in
// this app, and no control writes Final_Status except by copying what this
// returned.
//
// Paste this file into App.Formulas alongside App.Formulas.fx. It is kept
// separate here so the engine is reviewable on its own.
// =============================================================================

// The result type. Every caller receives the whole record; nobody
// reconstructs part of it.
MF_StatusResult := Type({
    code:           Text,
    status:         Text,     // Final_Status — one of five visual states
    label:          Text,     // Status_Semantic
    actionOwner:    Text,
    actionRequired: Boolean
});

// -----------------------------------------------------------------------------
// The catalogue. Eleven codes, five visual states. This table IS the mapping;
// it is not duplicated in a Switch() anywhere else in the app.
//
// Order here is presentation order (worst first for the My Work sort). The
// EVALUATION order is in MF_EvaluateStatus below and is a different thing.
// -----------------------------------------------------------------------------
MF_StatusCatalog =
    Table(
        { code: "OVERDUE",             status: "Red",   label: "Overdue",                                actionOwner: "Facility", actionRequired: true,  rank: 1, icon: "Warning"    },
        { code: "RETURNED",            status: "Amber", label: "Returned for correction",                actionOwner: "Facility", actionRequired: true,  rank: 2, icon: "Undo"       },
        { code: "PROVISIONAL_OVERDUE", status: "Gray",  label: "Past suspense - requirement unverified", actionOwner: "Program",  actionRequired: true,  rank: 3, icon: "Info"       },
        { code: "DUE_SOON",            status: "Amber", label: "Due soon",                               actionOwner: "Facility", actionRequired: true,  rank: 4, icon: "Clock"      },
        { code: "SUBMITTED",           status: "Amber", label: "Submitted - awaiting review",            actionOwner: "Reviewer", actionRequired: true,  rank: 5, icon: "Upload"     },
        { code: "IN_REVIEW",           status: "Amber", label: "In review",                              actionOwner: "Reviewer", actionRequired: true,  rank: 6, icon: "View"       },
        { code: "NOT_DUE",             status: "Blue",  label: "Not due yet",                            actionOwner: "Facility", actionRequired: false, rank: 7, icon: "Clock"      },
        { code: "ACCEPTED",            status: "Green", label: "Accepted",                               actionOwner: "None",     actionRequired: false, rank: 8, icon: "CheckMark"  },
        { code: "WAIVED",              status: "Gray",  label: "Waived",                                 actionOwner: "None",     actionRequired: false, rank: 9, icon: "Info"       },
        { code: "NOT_APPLICABLE",      status: "Gray",  label: "Not applicable",                         actionOwner: "None",     actionRequired: false, rank: 10, icon: "Info"      },
        { code: "SUPERSEDED",          status: "Gray",  label: "Superseded",                             actionOwner: "None",     actionRequired: false, rank: 11, icon: "Info"      }
    );

// Presentation from a stored code. This is what every gallery, badge and
// detail pane calls. It is a lookup, not a recomputation: the row already
// carries the code, written by the engine in EOM-01 / EOM-05 / the QC flow.
MF_StatusPresentation(StatusCode: Text): MF_StatusResult =
    With(
        { m: LookUp(MF_StatusCatalog, code = StatusCode) },
        If(
            IsBlank(m.code),
            // An unknown code is a bug, not a state. Show it, do not hide it.
            { code: StatusCode, status: "Gray", label: "Unknown status", actionOwner: "Program", actionRequired: true },
            { code: m.code, status: m.status, label: m.label, actionOwner: m.actionOwner, actionRequired: m.actionRequired }
        )
    );

// -----------------------------------------------------------------------------
// The evaluation. Ordered, total, first match wins.
//
// Mirrors scripts/status_engine.py evaluate() line for line. Used in the app
// only for preview — "if you submit this now, the item becomes ..." — and by
// scrDiagnostics. The authoritative write is server-side, so the app and the
// flow can never disagree about a row that exists.
//
// Reordering these branches changes behaviour. The order is asserted by the
// tests. Do not reorder to make a screen read better.
// -----------------------------------------------------------------------------
MF_EvaluateStatus(
    AsOf: Date,
    SuspenseDate: Date,
    VerificationStatus: Text,
    RequirementIsActive: Boolean,
    AppliesToFacility: Boolean,
    QCStatus: Text,
    HasCurrentSubmission: Boolean,
    Waived: Boolean,
    Superseded: Boolean,
    DueSoonWindowDays: Number
): MF_StatusResult =
    MF_StatusPresentation(
        // 1. The obligation does not exist for this row.
        If( !AppliesToFacility || !RequirementIsActive || VerificationStatus = "RETIRED",
            "NOT_APPLICABLE",

        // 2. The obligation existed and was released.
        Waived,
            "WAIVED",

        // 3. The obligation was replaced.
        Superseded,
            "SUPERSEDED",

        // 4-7. A CURRENT-VERSION submission exists; its QC state is the item's
        //      state. A rejected v1 under an accepted v2 is invisible here,
        //      which is what Is_Current_Version is for.
        HasCurrentSubmission && QCStatus = "ACCEPTED",
            "ACCEPTED",
        HasCurrentSubmission && QCStatus = "RETURNED",
            "RETURNED",
        HasCurrentSubmission && QCStatus = "IN_REVIEW",
            "IN_REVIEW",
        HasCurrentSubmission && QCStatus = "PENDING",
            "SUBMITTED",

        // 8. Nothing submitted. Time decides; verification decides the colour.
        IsBlank(SuspenseDate),
            "NOT_DUE",

        // 8a / 8b. An UNVERIFIED requirement NEVER drives Red. It goes Gray and
        //          the action lands on the Program, not on the facility: the
        //          action required is "verify the requirement", not "submit the
        //          document". All twelve seeded requirements are provisional
        //          today, so this is the default path, not an edge case.
        AsOf > SuspenseDate,
            If( VerificationStatus = "VERIFIED", "OVERDUE", "PROVISIONAL_OVERDUE" ),

        // 8c.
        DateDiff(AsOf, SuspenseDate, Days) <= DueSoonWindowDays,
            "DUE_SOON",

        // 8d.
            "NOT_DUE"
        )
    );

// -----------------------------------------------------------------------------
// Rollup semantics. Over semantic status, never over colour.
//
// A colour rollup calls [ACCEPTED, NOT_DUE, NOT_DUE] one green out of three
// and reports 33%. It is 100%: two of those are not due yet and belong in
// neither the numerator nor the denominator.
// -----------------------------------------------------------------------------
MF_IsComplete(StatusCode: Text): Boolean =
    StatusCode = "ACCEPTED";

MF_IsInDenominator(StatusCode: Text): Boolean =
    !(StatusCode in ["NOT_DUE", "WAIVED", "NOT_APPLICABLE", "SUPERSEDED"]);

// Display-only. Never stored, never written to a list, and blank rather than
// zero when nothing is due — "0% of nothing" is a lie a manager will act on.
MF_CompleteRatio(Items: Table): Number =
    With(
        {
            den: CountRows(Filter(Items, MF_IsInDenominator(Status_Code))),
            num: CountRows(Filter(Items, Status_Code = "ACCEPTED"))
        },
        If(den = 0, Blank(), num / den)
    );

MF_CompleteRatioLabel(Items: Table): Text =
    With(
        { r: MF_CompleteRatio(Items) },
        If(IsBlank(r), "Nothing due", Text(r, "0%") & " complete")
    );

// The accessible sentence. This is the badge's AccessibleLabel, and it is the
// only place the sentence is built. See docs/accessibility.md gate A4.
MF_StatusAccessibleLabel(StatusCode: Text, SuspenseDate: Date): Text =
    With(
        { p: MF_StatusPresentation(StatusCode) },
        "Status: " & p.label & ". " &
        If(p.actionOwner = "None", "No action required. ", "Action owner: " & p.actionOwner & ". ") &
        If(IsBlank(SuspenseDate), "", "Suspense date " & Text(SuspenseDate, "d mmmm yyyy") & ".")
    );
