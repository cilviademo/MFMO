// Delegation patterns.
//
// The rule that matters: a non-delegable query silently returns only the first
// 500 rows (2,000 maximum). It does not warn the user and it does not fail. It
// returns a WRONG answer. A Portfolio Manager sees "3 overdue" when there are
// eleven, and nobody finds out until an IG does.
//
// Every list query below filters on indexed columns, server-side, most
// selective first.

// --- my work queue -------------------------------------------------------
// Reporting_Period first: the most selective indexed column.
// Status_Code is indexed and stored (never computed) precisely so this
// filter delegates.
galMyWork.Items =
    SortByColumns(
        Filter( 'MF EOM Item',
            Reporting_Period = locSelectedPeriod,
            Status_Code < 3,
            Portfolio_ID = gblMyPortfolio
        ),
        "Due_Date", Ascending
    )

// A facility-scoped user narrows further, still server-side.
galMyWorkFacility.Items =
    SortByColumns(
        Filter( 'MF EOM Item',
            Reporting_Period = locSelectedPeriod,
            Facility_ID = gblMyFacility,
            Status_Code < 3
        ),
        "Due_Date", Ascending
    )

// --- requirement grid ----------------------------------------------------
galRequirements.Items =
    Filter( 'MF EOM Item',
        Reporting_Period = locSelectedPeriod,
        Facility_ID = cmbFacility.Selected.Facility_ID )

// --- version history -----------------------------------------------------
// EOM_Item_ID is indexed; this stays small and delegable.
galVersions.Items =
    SortByColumns(
        Filter( 'MF EOM Submission', EOM_Item_ID = locSelectedItem.EOM_Item_ID ),
        "Version_No", Descending )

// ========================================================================
// ANTI-PATTERNS — do not write these
// ========================================================================
//
// ClearCollect( colAllItems, 'MF EOM Item' )
//     Silently truncates. Every count downstream is wrong.
//
// Filter( 'MF EOM Item', Status_Code = MFItemStatusCode(...) )
//     Computed comparison, non-delegable. This is why Status_Code is STORED.
//
// Filter( 'MF EOM Item', StartsWith(EOM_Item_Key, "LACKLAND") )
//     StartsWith does not delegate on SharePoint. Filter on Installation_ID.
//
// ForAll( colFacilities, ForAll( colRequirements, Patch(...) ) )
//     Nested ForAll. Microsoft warns explicitly; this belongs in EOM-01.
//
// Filter( 'MF EOM Item', Installation_ID = galParent.Selected.Installation_ID )
//     Cross-screen control reference. Use a variable.
//
// Reference to 'MF App Event Log' in a gallery
//     Append-only and unbounded. Query by Record_ID only.
