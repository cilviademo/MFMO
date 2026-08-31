// App.Formulas — named formulas.
// Microsoft's current guidance: prefer named formulas over a bloated App.OnStart.
// They evaluate lazily, recalculate when their inputs change, and do not delay
// app start. Anything derived belongs here; OnStart keeps only what genuinely
// cannot be expressed as a formula.
//
// NOTE: named formulas cannot ClearCollect. That is a feature here — it forces
// server-side filtering instead of pulling lists into memory.

// --- identity and configuration -----------------------------------------
gblCurrentUser = User();

gblAppVersion = LookUp('MF App Config', Config_Key = "AppVersion").Config_Value;

gblOpenPeriod = LookUp('MF App Config', Config_Key = "OpenReportingPeriod").Config_Value;

gblFiscalYear = LookUp('MF App Config', Config_Key = "CurrentFiscalYear").Config_Value;

gblMaintenanceMode =
    LookUp('MF App Config', Config_Key = "MaintenanceMode").Config_Value = "True";

gblReadOnlyMode =
    LookUp('MF App Config', Config_Key = "ReadOnlyMode").Config_Value = "True";

gblSupportMessage = LookUp('MF App Config', Config_Key = "SupportMessage").Config_Value;

// --- scope ---------------------------------------------------------------
// Delegable: filters on UPN, an indexed column, server-side.
gblMyScope =
    Filter( 'MF Security Mapping',
            UPN = gblCurrentUser.Email And Active_Flag = true );

gblScopeType =
    First( Sort( gblMyScope,
        Switch( Scope_Type, "Enterprise",1, "Portfolio",2, "Installation",3, "Facility",4 )
    )).Scope_Type;

gblIsDeveloper = CountRows( Filter(gblMyScope, Developer_Flag = true) ) > 0;
gblIsTester    = CountRows( Filter(gblMyScope, Tester_Flag = true) ) > 0;
gblCanQC       = CountRows( Filter(gblMyScope, Can_QC = true) ) > 0;
gblCanOnBehalf = CountRows( Filter(gblMyScope, Can_Submit_On_Behalf = true) ) > 0;
gblCanEditReqs = CountRows( Filter(gblMyScope, Can_Edit_Requirements = true) ) > 0;

gblMyPortfolio    = First(gblMyScope).Portfolio_ID;
gblMyInstallation = First(gblMyScope).Installation_ID;
gblMyFacility     = First(gblMyScope).Facility_ID;

// Write access: read-only mode locks everyone except developers, and
// maintenance mode locks everyone except developers and admins.
gblCanWrite =
    Not(gblReadOnlyMode) Or gblIsDeveloper;

gblCanEnterApp =
    Not(gblMaintenanceMode) Or gblIsDeveloper Or gblCanEditReqs;

// --- feature flags -------------------------------------------------------
// One published app can carry released and unreleased screens at once. This is
// what makes a single-environment tenant survivable.
IsFeatureOn( key: Text ): Boolean =
    With( { f: LookUp('MF Feature Flags', Feature_Key = key) },
        If( IsBlank(f), false,
            f.Enabled_Prod, true,
            f.Enabled_Testers And (gblIsTester Or gblIsDeveloper), true,
            false )
    );

// --- status --------------------------------------------------------------
// Presentation only. The authoritative calculation lives in EOM-03; the app
// reads the stored Status_Code. This exists so a just-patched row renders
// correctly before the nightly run.
StatusLabel( code: Number ): Text =
    Switch( code, 3,"Accepted", 2,"Needs attention", 1,"Action required", "Not applicable" );

StatusColor( code: Number ): Color =
    Switch( code, 3, ColorValue("#3F7D4F"), 2, ColorValue("#9A7318"),
                  1, ColorValue("#A83A30"), ColorValue("#6B7681") );

// Never colour alone — Section 508. Every chip carries this text.
StatusSemantic( code: Number ): Text =
    Switch( code, 3,"ACCEPTED", 2,"PENDING", 1,"OVERDUE", "NOT_APPLICABLE" );
