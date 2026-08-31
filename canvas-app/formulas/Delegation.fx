// =============================================================================
// Delegation.fx  —  patterns, anti-patterns, and the queries this app is
//                   allowed to run.
//
// THE FAILURE THAT DOES NOT ANNOUNCE ITSELF
//
// A non-delegable query returns the first 500 rows — 2,000 at the maximum
// data row limit — and reports success. No error, no warning at runtime, no
// entry in the log. A Portfolio Manager sees "3 overdue" when there are
// eleven, and nobody finds out until an inspection.
//
// MF_EOM_Item at 89 installations x facilities x requirements x 12 months x
// the first year of versions passes that ceiling comfortably in the first
// quarter. MF_EOM_Status passes it in the first month.
//
// So: every production query filters server-side on indexed columns, and
// Reporting_Period_ID comes first. The indexes are created by
// provisioning/Provision-MFOpsLists.ps1 BEFORE any list crosses 5,000 items,
// because SharePoint will not add one afterward.
// =============================================================================


// -----------------------------------------------------------------------------
// WHAT DELEGATES TO SHAREPOINT
//
//   =  <>  <  <=  >  >=          on Text, Number, DateTime, Boolean
//   And / Or / Not               (&&  ||  !)
//   StartsWith                   on Text
//   Filter, LookUp, Search
//   SortByColumns                on a single indexed column
//   CountRows                    ONLY on an already-filtered delegable table,
//                                and only under the row limit
//   in                           ONLY as a membership test against a literal
//                                or small in-memory table on the RIGHT
//
// WHAT DOES NOT
//
//   Search() across several columns
//   IsBlank()   on a list column          <- the trap, see below
//   Len(), Left(), Right(), Mid(), Upper(), Lower(), Trim()
//   Sum / Average / Max / Min / StdevP    on a SharePoint source
//   GroupBy, AddColumns, ShowColumns, DropColumns, Distinct  (all client-side)
//   ForAll over a data source
//   Choice column compared with = to a text literal
//     (SharePoint choice is a record: use .Value)
//   Any expression that references a control property inside the Filter
//     predicate in a way the compiler cannot resolve to a constant
//   CountRows() on an unfiltered list
//   Sort() (as distinct from SortByColumns)
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
// THE IsBlank TRAP  —  and why Facility_ID is null, not empty string.
//
// Installation- and Contract-scope rows carry a NULL Facility_ID. It has to be
// null rather than "" because those two look identical in a gallery and behave
// differently in every Filter():
//
//   IsBlank(Facility_ID)               NOT DELEGABLE. Silently truncates.
//   Facility_ID = ""                   does not match a true null in SharePoint.
//
// The delegable way to ask "is this a facility-scope row" is to ask the
// question the data actually models — the scope — on an indexed choice column:
//
//   Filter(MF_EOM_Item, Requirement_Scope.Value = "Facility")     DELEGABLE
//
// That is why Requirement_Scope is denormalized onto the item at generation
// time, and why the schema forbids an empty string in Facility_ID.
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
// ANTI-PATTERNS — every one of these has shipped somewhere and lied quietly.
// -----------------------------------------------------------------------------
//
// BAD   Filter(MF_EOM_Item, Status_Code.Value = "OVERDUE")
//       Unbounded across every period ever generated. Truncates at 500.
// GOOD  Filter(MF_EOM_Item,
//              Reporting_Period_ID = MF_CurrentPeriod.Period_ID,
//              Status_Code.Value = "OVERDUE")
//
// BAD   Filter(MF_EOM_Item, IsBlank(Facility_ID))
//       Not delegable, and does not mean what it looks like.
// GOOD  Filter(MF_EOM_Item, Requirement_Scope.Value = "Installation")
//
// BAD   CountRows(Filter(MF_EOM_Item, Status_Code.Value <> "ACCEPTED"))
//       Counts a truncated set and reports it as a total. This is the
//       "3 overdue when there are eleven" failure exactly.
// GOOD  Count the fact instead — MF_EOM_Status carries Is_Complete and
//       Is_In_Denominator precomputed by EOM-03 — or count within one
//       period and one facility, which is bounded by construction.
//
// BAD   Filter(MF_EOM_Item, Facility_ID in MF_MyFacilityIDs)
//       'in' with a table on the right does not delegate. It pulls the list
//       down and filters locally.
// GOOD  Filter(MF_EOM_Item,
//              Reporting_Period_ID = period,
//              Facility_ID = gblCurrentFacility.Facility_ID)
//       One facility at a time. For a multi-facility view, ForAll over the
//       user's facility LIST (small, in memory) issuing one delegable query
//       each — never ForAll over the data source.
//
// BAD   SortByColumns(Filter(...), "Requirement_Name")
//       Requirement_Name is not indexed. Sorting on it is client-side over a
//       truncated set.
// GOOD  Sort on Suspense_Date (indexed), or sort the small result client-side
//       after a delegable filter has already bounded it.
//
// BAD   Search(MF_EOM_Item, txtSearch.Text, "Facility_Name", "Requirement_Name")
//       Multi-column Search does not delegate.
// GOOD  StartsWith on one indexed column, inside a period filter.
//
// BAD   Filter(MF_EOM_Submission, EOM_Item_ID = ThisItem.EOM_Item_ID)
//         used as a gallery Items on a 200-row parent gallery
//       200 gallery rows issue 200 queries. The screen appears to hang.
// GOOD  One query for the period's submissions, then relate in memory, or
//       read Current_Submission_ID and Current_Version_Number off the item —
//       which is why the item denormalizes them.
//
// BAD   ClearCollect(colAll, MF_EOM_Item)
//       The whole list. 500 rows of 250,000, with no indication.
// GOOD  Never collect a large source. Bind the gallery to the delegable
//       Filter directly and let virtualisation page it.
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
// THE APPROVED QUERIES.
//
// These are the only shapes that touch MF_EOM_Item, MF_EOM_Submission or
// MF_EOM_Status in production. Each filters on indexed columns with
// Reporting_Period_ID first. Adding a new one means adding it here.
// -----------------------------------------------------------------------------

// My work: one facility, one period. Bounded by construction — at most the
// requirement count, currently twelve.
MF_ItemsForFacility(FacilityId: Text, PeriodId: Text): Table =
    SortByColumns(
        Filter(
            MF_EOM_Item,
            Reporting_Period_ID = PeriodId,          // indexed, first
            Facility_ID = FacilityId                 // indexed
        ),
        "Suspense_Date", SortOrder.Ascending          // indexed
    );

// Installation view. Bounded by facilities x requirements for one period.
// Includes the installation-scope rows, whose Facility_ID is null — reached
// through Installation_ID, never through IsBlank().
MF_ItemsForInstallation(InstallationId: Text, PeriodId: Text): Table =
    SortByColumns(
        Filter(
            MF_EOM_Item,
            Reporting_Period_ID = PeriodId,
            Installation_ID = InstallationId
        ),
        "Suspense_Date", SortOrder.Ascending
    );

// Portfolio view. This is the one that would truncate if Portfolio_ID were not
// denormalized onto the item — a join to MF_Facility would be client-side.
// Still bounded per period, and the COP should prefer MF_EOM_Status.
MF_ItemsForPortfolio(PortfolioId: Text, PeriodId: Text): Table =
    Filter(
        MF_EOM_Item,
        Reporting_Period_ID = PeriodId,
        Portfolio_ID = PortfolioId
    );

// Action list. Action_Required is stored and indexed precisely so this
// delegates instead of being computed over a truncated set.
MF_ActionItemsForFacility(FacilityId: Text, PeriodId: Text): Table =
    Filter(
        MF_EOM_Item,
        Reporting_Period_ID = PeriodId,
        Facility_ID = FacilityId,
        Action_Required = true
    );

// Review queue. QC_Status and Is_Current_Version are both indexed.
MF_ReviewQueue(PeriodId: Text): Table =
    SortByColumns(
        Filter(
            MF_EOM_Submission,
            Is_Current_Version = true,
            Classification_Status.Value = "CLASSIFIED",
            QC_Status.Value in ["PENDING", "IN_REVIEW"]
        ),
        "Submitted_On", SortOrder.Ascending
    );

// Needs Classification. Reached by Classification_Status, never by asking
// whether EOM_Item_ID is blank.
MF_UnmatchedQueue(): Table =
    SortByColumns(
        Filter(
            MF_EOM_Submission,
            Classification_Status.Value = "NEEDS_CLASSIFICATION"
        ),
        "Submitted_On", SortOrder.Ascending
    );

// One item by id. Delegable on the indexed EOM_Item_ID and bounded to a
// single row, so it is safe to call from a gallery row's OnSelect. It is here
// rather than inline on a screen because EVERY query against a high-volume
// list lives in this file - that is what makes the set reviewable.
MF_ItemById(ItemId: Text): Record =
    LookUp(MF_EOM_Item, EOM_Item_ID = ItemId);

// Version history for one item. Bounded by the version count.
MF_VersionsForItem(ItemId: Text): Table =
    SortByColumns(
        Filter(MF_EOM_Submission, EOM_Item_ID = ItemId),
        "Version_Number", SortOrder.Descending
    );


// -----------------------------------------------------------------------------
// COUNTS AND ROLLUPS
//
// Counting is where truncation hides. Two rules:
//
//   1. Only count a table that a delegable Filter has already bounded to one
//      period and one scope.
//   2. Anything wider than that comes from MF_EOM_Status, where EOM-03 has
//      already resolved Is_Complete and Is_In_Denominator server-side.
//
// And the count is displayed next to the row count so a truncation is visible:
// if the gallery says 500 and the count says 500, suspect truncation. See
// docs/accessibility.md — the visible count also serves the screen reader.
// -----------------------------------------------------------------------------

MF_FacilityRollup(FacilityId: Text, PeriodId: Text) =
    With(
        { items: MF_ItemsForFacility(FacilityId, PeriodId) },
        {
            total:      CountRows(items),
            complete:   CountRows(Filter(items, Status_Code.Value = "ACCEPTED")),
            denominator:CountRows(Filter(items, !(Status_Code.Value in ["NOT_DUE", "WAIVED", "NOT_APPLICABLE", "SUPERSEDED"]))),
            action:     CountRows(Filter(items, Action_Required = true)),
            truncated:  CountRows(items) >= MF_DelegationWarnAt
        }
    );

// A facility user must not receive an installation figure derived from their
// neighbours. The rollup is computed over the rows the viewer may actually
// see, and it says so when the scope has been narrowed.
MF_ScopeQualifier(RequestedScope: Text): Text =
    If( MF_IsGlobalScope || RequestedScope in MF_MyInstallationIDs || RequestedScope in MF_MyPortfolioIDs,
        "",
        "Covers your assigned facilities only, not the whole " & RequestedScope & "."
    );
