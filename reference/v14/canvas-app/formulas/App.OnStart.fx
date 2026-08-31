// App.OnStart — deliberately small.
// Everything derivable lives in App.Formulas. OnStart holds only navigation
// and the one telemetry write that must happen at launch.
//
// There is NO ClearCollect of business data here. At 89 installations x
// facilities x requirements x 12 months, MF EOM Item passes the 2,000-row
// non-delegable ceiling inside the first year, and a non-delegable query
// returns WRONG results, not slow ones.

Concurrent(
    // Telemetry: one row per session. Business events, not clicks.
    If( gblCanEnterApp,
        Patch( 'MF App Event Log', Defaults('MF App Event Log'),
            { Event_ID: "EVT-" & Text(Now(), "yyyymmddhhmmss") & "-" & gblCurrentUser.Email,
              Event_DateTime: Now(),
              User_UPN: gblCurrentUser.Email,
              Role: First(gblMyScope).Role,
              Portfolio_ID: gblMyPortfolio,
              Installation_ID: gblMyInstallation,
              Facility_ID: gblMyFacility,
              Event_Type: "AppOpened",
              Result: "Success",
              App_Version: gblAppVersion } ),

        Patch( 'MF App Event Log', Defaults('MF App Event Log'),
            { Event_ID: "EVT-" & Text(Now(), "yyyymmddhhmmss"),
              Event_DateTime: Now(),
              User_UPN: gblCurrentUser.Email,
              Event_Type: "MaintenanceModeBlocked",
              Result: "Warning",
              App_Version: gblAppVersion } )
    ),

    Set( locSelectedPeriod, gblOpenPeriod )
);

// Unmapped users get a clear route, not an empty app.
If( CountRows(gblMyScope) = 0,
    Navigate(scrNoAccess),
    Not(gblCanEnterApp),
    Navigate(scrMaintenance),
    Navigate(scrHome)
);
