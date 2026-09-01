// =============================================================================
// Delegation.fx — patterns, anti-patterns, and every query this app is
//                 allowed to run against a high-volume list.
//
// THE FAILURE THAT DOES NOT ANNOUNCE ITSELF
//
// A non-delegable query silently returns only the first 500 rows (2,000
// maximum). It does not warn the user and it does not fail. It returns a WRONG
// answer. A Portfolio Manager sees "3 overdue" when there are eleven, and
// nobody finds out until an IG does.
//
// At 89 installations x facilities x requirements x 12 months, MF EOM Item
// passes that ceiling inside the first year. MF EOM Audit and MF App Event Log
// pass it sooner.
//
// So: every query below filters server-side on indexed columns, most selective
// first, with Reporting_Period leading. The indexes are created by
// provisioning/Provision-MFOpsLists.ps1 BEFORE any list crosses 5,000 items,
// because SharePoint will not add one afterward.
// =============================================================================


// -----------------------------------------------------------------------------
// WHAT DELEGATES TO SHAREPOINT
//
//   =  <>  <  <=  >  >=        on Text, Number, DateTime, Boolean
//   And / Or / Not             (&&  ||  !)
//   StartsWith                 on Text
//   Filter, LookUp, Search
//   SortByColumns              on a single indexed column
//   CountRows                  only on an already-filtered delegable table
//
// WHAT DOES NOT
//
//   IsBlank() on a list column                <- the trap, see below
//   Len / Left / Right / Mid / Upper / Lower / Trim
//   Sum / Average / Max / Min / StdevP        on a SharePoint source
//   GroupBy, AddColumns, Distinct, ShowColumns   (all client-side)
//   ForAll over a data source
//   Sort() (as distinct from SortByColumns)
//   multi-column Search()
//   a Choice column compared with = to a text literal without .Value
//   any predicate the compiler cannot resolve to a constant
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
// THE IsBlank TRAP — and why Facility_ID is null, not empty string.
//
// Installation- and Contract-scope rows carry a NULL Facility_ID. It has to be
// null rather than "" because the two look identical in a gallery and behave
// differently in every Filter():
//
//   IsBlank(Facility_ID)        NOT DELEGABLE. Silently truncates.
//   Facility_ID = ""            does not match a true null in SharePoint.
//
// The delegable way to ask "is this a facility row" is to ask the question the
// data actually models — the scope — on an indexed column:
//
//   Filter('MF EOM Item', Requirement_Scope = "Facility")     DELEGABLE
//
// That is why Requirement_Scope is denormalized onto the item at generation.
// The same reasoning put Authority_Status there: rule 2 of the status engine
// reads it, and a lookup to MF EOM Requirement would not delegate either.
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
// ANTI-PATTERNS — every one of these has shipped somewhere and lied quietly.
// -----------------------------------------------------------------------------
//
// BAD   ClearCollect( colAllItems, 'MF EOM Item' )
//       The whole list. 500 rows of 250,000, with no indication. Every count
//       downstream is wrong.
//
// BAD   Filter( 'MF EOM Item', Status_Code < 3 )
//       Unbounded across every period ever generated. Add the period.
// GOOD  Filter( 'MF EOM Item', Reporting_Period = locPeriod, Status_Code < 3 )
//
// BAD   Filter( 'MF EOM Item', IsBlank(Facility_ID) )
//       Not delegable, and does not mean what it looks like.
// GOOD  Filter( 'MF EOM Item', Requirement_Scope = "Installation" )
//
// BAD   Filter( 'MF EOM Item', Status_Code = MFItemStatusCode(...) )
//       Computed comparison, non-delegable. This is why Status_Code is STORED.
//
// BAD   Filter( 'MF EOM Item', StartsWith(EOM_Item_Key, "LACKLAND") )
//       StartsWith does not delegate on SharePoint. Filter on Installation_ID.
//
// BAD   CountRows(Filter('MF EOM Item', Final_Status <> "ACCEPTED"))
//       Counts a truncated set and reports it as a total. This is the
//       "3 overdue when there are eleven" failure exactly.
//
// BAD   ForAll( colFacilities, ForAll( colRequirements, Patch(...) ) )
//       Nested ForAll. Microsoft warns explicitly; this belongs in EOM-01.
//
// BAD   Filter( 'MF EOM Item', Installation_ID = galParent.Selected.Installation_ID )
//       Cross-screen control reference. Use a variable.
//
// BAD   a gallery bound to 'MF App Event Log' or 'MF EOM Audit'
//       Append-only and unbounded. Query by Record_ID or Entity_ID only.
// -----------------------------------------------------------------------------


// -----------------------------------------------------------------------------
// SECURITY BEFORE ROLLUP
//
// A facility-scoped user previously received an installation package rollup
// computed from every facility at that base. That leaks across a security
// boundary even when no names appear on screen — the numbers themselves are
// the disclosure.
//
// Scope is applied server-side, in the query, before anything is counted. A
// contract-scope item is visible only when the contract actually covers a
// facility in the viewer's scope.
// -----------------------------------------------------------------------------

// Items for one facility and period. Bounded by construction — at most the
// requirement count. Reporting_Period first, then the indexed facility.
// SORTED BY THE EFFECTIVE DATE, not the nominal one. The nominal date is what
// leadership is briefed on -- "the 5th" stays the 5th -- but the order a base
// works its list in is the order the dates actually fall, and a suspense rolled
// off a weekend falls later than one that did not. Sorting by nominal would put
// two items with the same printed date in an order that contradicts when they
// are really owed.
//
// `Due_Date` was the column here until the four-date split. It no longer
// exists, and SortByColumns against a missing column does not error loudly.
MF_ItemsForFacility(FacilityId: Text, Period: Text): Table =
    SortByColumns(
        Filter( 'MF EOM Item',
                Reporting_Period = Period,
                Facility_ID = FacilityId ),
        "Effective_Due_Date", SortOrder.Ascending );

// Everything at one installation for a period, including the Installation- and
// Contract-scope rows whose Facility_ID is null. Reached through
// Installation_ID, never through IsBlank().
MF_ItemsForInstallation(InstallationId: Text, Period: Text): Table =
    SortByColumns(
        Filter( 'MF EOM Item',
                Reporting_Period = Period,
                Installation_ID = InstallationId ),
        "Effective_Due_Date", SortOrder.Ascending );

// Portfolio view. This is the query that would truncate if Portfolio_ID were
// not denormalized onto the item — a join to MF Facility would be client-side.
MF_ItemsForPortfolio(PortfolioId: Text, Period: Text): Table =
    Filter( 'MF EOM Item',
            Reporting_Period = Period,
            Portfolio_ID = PortfolioId );

// The scope-correct item set for the current viewer. Every rollup starts here.
// A Facility-scoped user gets their facility's rows plus the installation- and
// contract-scope rows that genuinely belong to them.
MF_VisibleItems(Period: Text): Table =
    Switch( gblScopeType,
        "Facility",
            Filter( 'MF EOM Item',
                    Reporting_Period = Period,
                    Installation_ID = gblMyInstallation,
                    // Their own facility rows, plus the shared obligations of
                    // the installation. NOT their neighbours' facility rows.
                    ( Facility_ID = gblMyFacility
                      || Requirement_Scope = "Installation"
                      || Requirement_Scope = "Contract" ) ),
        "Installation",
            Filter( 'MF EOM Item',
                    Reporting_Period = Period,
                    Installation_ID = gblMyInstallation ),
        "Portfolio",
            Filter( 'MF EOM Item',
                    Reporting_Period = Period,
                    Portfolio_ID = gblMyPortfolio ),
        Filter( 'MF EOM Item', Reporting_Period = Period ) );

// A contract row is only theirs if the contract covers one of their facilities.
// Applied in memory over the already-scoped set above, which is bounded.
MF_ContractItemIsMine(ContractId: Text): Boolean =
    IsBlank(ContractId)
    || CountRows(Filter(MF_MyFacilities, Contract_ID = ContractId)) > 0;

// Health check: does this facility have any expected items at all for the
// period? A facility with no requirement set is a configuration gap, not a
// facility with nothing to do, and it sits silently green until something
// looks for it.
MF_HasItems(FacilityId: Text, Period: Text): Boolean =
    CountRows(MF_ItemsForFacility(FacilityId, Period)) > 0;

// My work: what I owe, not what someone else owes. Action_Owner and
// Action_Required are stored and indexed precisely so this delegates.
MF_MyWork(Period: Text): Table =
    SortByColumns(
        Filter( MF_VisibleItems(Period), Action_Required = true ),
        "Effective_Due_Date", SortOrder.Ascending );

// Waiting on someone else. A submitter's "needs your attention" list must not
// contain documents sitting in AFSVC's review queue.
MF_WaitingOnOthers(Period: Text): Table =
    Filter( MF_VisibleItems(Period),
            Action_Required = true,
            Action_Owner = "Reviewer" );

// The review queue. QC_Status and Is_Current are both indexed.
MF_ReviewQueue(): Table =
    SortByColumns(
        Filter( 'MF EOM Submission',
                Is_Current = true,
                QC_Status = "Pending Review" ),
        "Uploaded_DateTime", SortOrder.Ascending );

// Needs Classification. Reached by Resolution_Status, never by asking whether
// a foreign key is blank.
MF_UnmatchedQueue(): Table =
    SortByColumns(
        Filter( 'MF Unmatched File', Resolution_Status = "Needs Classification" ),
        "Discovered_DateTime", SortOrder.Ascending );

// Version history for one item. EOM_Item_ID is indexed and this stays small.
MF_VersionsForItem(ItemId: Text): Table =
    SortByColumns(
        Filter( 'MF EOM Submission', EOM_Item_ID = ItemId ),
        "Version_No", SortOrder.Descending );

// One item by id, for a gallery row's OnSelect. Delegable and single-row.
MF_ItemById(ItemId: Text): Record =
    LookUp('MF EOM Item', EOM_Item_ID = ItemId);

// Activity for one record. Never an unfiltered read of the audit list.
MF_ActivityForRecord(EntityId: Text): Table =
    SortByColumns(
        Filter('MF EOM Audit', Entity_ID = EntityId),
        "Action_DateTime", SortOrder.Descending );


// -----------------------------------------------------------------------------
// COUNTS
//
// Counting is where truncation hides. Only count a table a delegable Filter has
// already bounded to one period and one scope, and display the row count beside
// the figure so a truncation is visible rather than silent: if the gallery says
// 500 and the count says 500, suspect truncation.
// -----------------------------------------------------------------------------

MF_TruncationSuspected(Items: Table): Boolean =
    CountRows(Items) >= MF_DelegationWarnAt;

// A figure whose scope is narrower than its label says so, in text. It is never
// silently narrowed and presented as the installation total.
MF_ScopeQualifier(): Text =
    If( gblScopeType = "Facility",
        "Covers your facility and this installation's shared obligations, not the whole base.",
        "" );

// =============================================================================
// Helpers added for the approved screen set: scrMyPackage, scrOverview,
// scrInstallations, scrExceptions.
//
// Every one of these starts from a query that delegates on indexed columns.
// Where a predicate cannot delegate it is applied IN MEMORY over an
// already-bounded result, and that is stated at the helper rather than left for
// a reader to work out. The bound is always Reporting_Period plus scope, which
// MF_VisibleItems has already applied server-side.
// =============================================================================

// One period's package for one installation, which is what scrMyPackage shows.
// Delegates on Reporting_Period and Installation_ID, both indexed.
MF_PackageForPeriod(Period: Text): Table =
    SortByColumns(
        MF_VisibleItems(Period),
        "Effective_Due_Date", SortOrder.Ascending );

// Counts for the scrOverview metric strip. Final_Status is indexed, so each of
// these delegates; CountRows over a delegable Filter does not pull rows.
//
// The four metrics are SEMANTIC, never colour. Amber covers both "the base owes
// a correction" and "AFSVC owes a review", so counting by colour would put two
// different people's work in one number.
MF_CountAccepted(Period: Text): Number =
    CountRows(Filter(MF_VisibleItems(Period), Final_Status = "ACCEPTED"));

MF_CountAwaitingReview(Period: Text): Number =
    CountRows(Filter(MF_VisibleItems(Period), Final_Status = "RECEIVED_PENDING_QC"));

MF_CountCorrections(Period: Text): Number =
    CountRows(Filter(MF_VisibleItems(Period), Final_Status = "RETURNED"));

MF_CountOverdue(Period: Text): Number =
    CountRows(Filter(MF_VisibleItems(Period),
                     Final_Status = "OVERDUE" || Final_Status = "NOT_SATISFIED"));

// The installations this viewer may see, with their package rollup.
// MF_MyInstallations is already scope-filtered in App.Formulas; the rollup runs
// over that set, which is at most the 103-row registry and usually one row.
MF_InstallationsInScope(Period: Text): Table =
    SortByColumns(
        AddColumns(
            MF_MyInstallations,
            "Pkg_Total",    CountRows(MF_ItemsForInstallation(Installation_ID, Period)),
            "Pkg_Accepted", CountRows(Filter(MF_ItemsForInstallation(Installation_ID, Period),
                                             Final_Status = "ACCEPTED")),
            "Pkg_Open",     CountRows(Filter(MF_ItemsForInstallation(Installation_ID, Period),
                                             Action_Required = true))
        ),
        "Installation_Name", SortOrder.Ascending );

// EXCEPTIONS, three kinds. They are three different problems and must not read
// as one number.

// 1. Files the app did not write and nobody has classified.
//    Resolution_Status is indexed. This is MF_UnmatchedQueue, reused.

// 2. Submissions that landed at the configured root because no month folder
//    matched. Is_Current and Needs_Filing are both indexed, so this delegates.
//    Nothing errored when these were written -- that is exactly why they need
//    a screen.
MF_NeedsFilingQueue(): Table =
    SortByColumns(
        Filter( 'MF EOM Submission',
                Is_Current = true,
                Needs_Filing = true ),
        "Uploaded_DateTime", SortOrder.Ascending );

// 3. Correction tickets past their suspense.
//    DELEGATION NOTE: Correction_Due is NOT an indexed column, so the date
//    comparison cannot delegate. The Filter that reaches SharePoint is
//    MF_VisibleItems (Reporting_Period + scope, all indexed) narrowed by
//    Final_Status (indexed); the date test then runs in memory over that
//    bounded result. Adding an index for Correction_Due would be a schema
//    change and is not made here.
MF_CorrectionsPastDue(Period: Text): Table =
    Filter(
        Filter( MF_VisibleItems(Period), Final_Status = "RETURNED" ),
        !IsBlank(Correction_Due) && Correction_Due < Today() );

MF_CorrectionsOpen(Period: Text): Table =
    Filter( MF_VisibleItems(Period), Final_Status = "RETURNED" );

// Total exceptions across all three kinds, for the tab labels. Each part is
// counted from its own delegable query.
MF_ExceptionCount(Period: Text): Number =
    CountRows(MF_UnmatchedQueue())
    + CountRows(MF_NeedsFilingQueue())
    + CountRows(MF_CorrectionsPastDue(Period));
