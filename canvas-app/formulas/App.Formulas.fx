// =============================================================================
// App.Formulas.fx — named formulas.
//
// Microsoft's current guidance: prefer named formulas over a bloated
// App.OnStart. They evaluate lazily, recalculate when their inputs change, and
// do not delay app start. Anything derived belongs here; OnStart keeps only
// what genuinely cannot be expressed as a formula.
//
// Named formulas cannot ClearCollect. That is a feature here — it forces
// server-side filtering instead of pulling lists into memory.
//
// Carried forward from V3 with the status functions removed: they now live in
// StatusEngine.fx as ONE evaluation rather than three parallel switches.
// =============================================================================


// --- identity ------------------------------------------------------------
// No sign-in. On the network CAC identifies the user before the app loads.
// There is no login screen and no "welcome back" state; the app resolves
// identity, scope and permissions from MF_Security_Mapping on open.
gblCurrentUser = User();


// --- configuration -------------------------------------------------------
// No URL, site GUID or list name is hard-coded anywhere. Every value below is
// read from MF_App_Config, which mirrors the environment variables so that
// neither path is load-bearing alone.
MF_ConfigRows = Filter('MF App Config', Active_Flag = true);

MF_Config(Key: Text, Fallback: Text): Text =
    With( { row: LookUp(MF_ConfigRows, Config_Key = Key) },
          If(IsBlank(row.Config_Value), Fallback, row.Config_Value) );

MF_ConfigNumber(Key: Text, Fallback: Number): Number =
    With( { v: MF_Config(Key, "") },
          If(IsBlank(v) || !IsNumeric(v), Fallback, Value(v)) );

MF_ConfigBool(Key: Text, Fallback: Boolean): Boolean =
    Switch( Lower(MF_Config(Key, "")), "true", true, "false", false, Fallback );

gblAppVersion     = MF_Config("AppVersion", "0.0.0-unconfigured");
gblSchemaVersion  = MF_Config("SchemaVersion", "unknown");
gblTenantCloud    = MF_Config("TenantCloud", "UNKNOWN");
gblOpenPeriod     = MF_Config("OpenReportingPeriod", Text(DateAdd(Today(), -1, Months), "yyyy-mm"));
gblFiscalYear     = MF_Config("CurrentFiscalYear", "");
gblSupportMessage = MF_Config("SupportMessage", "Mission Feeding Operations is briefly unavailable for maintenance.");
gblSupportContact = MF_Config("SupportContact", "");
gblPowerBIURL     = MF_Config("PowerBIReportURL", "");
gblEOMRootPath    = MF_Config("EOM_Root_Path", "/EOM");

// The kill switch. Both default FALSE: a configuration outage must not lock
// every user out, and must not silently unlock writes either — the flows check
// ReadOnlyMode independently, so FALSE here is safe.
gblMaintenanceMode = MF_ConfigBool("MaintenanceMode", false);
gblReadOnlyMode    = MF_ConfigBool("ReadOnlyMode", false);
gblRequireQC       = MF_ConfigBool("RequireQC", true);

MF_MaxUploadBytes  = MF_ConfigNumber("MaxUploadSizeMB", 50) * 1024 * 1024;
MF_DelegationWarnAt = MF_ConfigNumber("DelegationWarningThreshold", 2000);


// --- scope ---------------------------------------------------------------
// Delegable: filters on UPN, an indexed column, server-side.
gblMyScope =
    Filter('MF Security Mapping',
           UPN = gblCurrentUser.Email,
           Active_Flag = true);

gblHasAccess = CountRows(gblMyScope) > 0;

// Widest scope wins, ranked rather than alphabetical.
gblScopeType =
    With( { s: gblMyScope },
        If( "Enterprise"   in s.Scope_Type, "Enterprise",
            "Portfolio"    in s.Scope_Type, "Portfolio",
            "Installation" in s.Scope_Type, "Installation",
            "Facility"     in s.Scope_Type, "Facility",
            "None" ) );

gblRole = First(gblMyScope).Role;

gblCanQC       = CountRows(Filter(gblMyScope, Can_QC = true)) > 0;
gblCanOnBehalf = CountRows(Filter(gblMyScope, Can_Submit_On_Behalf = true)) > 0;
gblCanEditReqs = CountRows(Filter(gblMyScope, Can_Edit_Requirements = true)) > 0;

// Never granted by a role. Only by an explicit flag on the mapping row.
gblIsDeveloper = CountRows(Filter(gblMyScope, Developer_Flag = true)) > 0;
gblIsTester    = CountRows(Filter(gblMyScope, Tester_Flag = true))    > 0;

gblMyPortfolio    = First(gblMyScope).Portfolio_ID;
gblMyInstallation = First(gblMyScope).Installation_ID;
gblMyFacility     = First(gblMyScope).Facility_ID;

// Write access: read-only mode locks everyone except developers, and
// maintenance mode locks everyone except developers and admins.
gblCanWrite     = !gblReadOnlyMode || gblIsDeveloper;
gblCanEnterApp  = !gblMaintenanceMode || gblIsDeveloper || gblCanEditReqs;

MF_WriteMode    = If(gblCanWrite, DisplayMode.Edit, DisplayMode.Disabled);

MF_ReadOnlyBanner =
    If( gblReadOnlyMode,
        "The app is read-only while we finish maintenance. You can view status but not submit.",
        "" );

// The gate, evaluated before any screen renders. Unmapped users get a clear
// route to fix it, not an empty app.
MF_StartScreen =
    If( !gblHasAccess,      scrNoAccess,
        !gblCanEnterApp,    scrMaintenance,
        scrHome );


// --- feature flags -------------------------------------------------------
// One published app carries released and unreleased screens at once. This is
// what makes a single-environment tenant survivable. Do not copy the common
// workaround of hand-renaming old and new screens.
MF_FlagRows = 'MF Feature Flags';

MF_IsFeatureOn(Key: Text): Boolean =
    With( { f: LookUp(MF_FlagRows, Feature_Key = Key) },
        If( IsBlank(f.Feature_Key), false,          // unknown flag is OFF
            f.Enabled_Prod, true,
            f.Enabled_Testers && (gblIsTester || gblIsDeveloper), true,
            false ) );


// --- scope-resolved reference data ---------------------------------------
// Small tables, safe to hold. Everything transactional stays server-filtered.
MF_MyInstallations =
    Switch( gblScopeType,
        "Enterprise", Filter('MF Installation', Active_Flag = true),
        "Portfolio",  Filter('MF Installation', Active_Flag = true, Portfolio_ID = gblMyPortfolio),
        Filter('MF Installation', Active_Flag = true, Installation_ID = gblMyInstallation) );

MF_MyFacilities =
    Switch( gblScopeType,
        "Facility",     Filter('MF Facility', Active_Flag = true, Facility_ID = gblMyFacility),
        "Installation", Filter('MF Facility', Active_Flag = true, Installation_ID = gblMyInstallation),
        "Portfolio",    Filter('MF Facility', Active_Flag = true,
                               Installation_ID in MF_MyInstallations.Installation_ID),
        Filter('MF Facility', Active_Flag = true) );

// A DFAC manager with one facility row sees no dropdowns at all, just an
// upload box. Everything else is the exception path.
MF_ShowDropdowns = CountRows(MF_MyFacilities) > 1 || gblCanOnBehalf;

// Last 13 periods, newest first. Reporting_Period is YYYY-MM throughout.
MF_SelectablePeriods =
    ForAll( Sequence(13, 0, 1) As n,
        { Period: Text(DateAdd(Today(), -1 - n.Value, Months), "yyyy-mm") } );


// --- navigation ----------------------------------------------------------
// Role-shaped: three destinations for a facility user, six for an admin.
// A feature flag removes the destination, not merely the button.
colNavigation =
    Filter(
        Table(
            { key: "home",     label: "Home",           screen: "scrHome",              flag: "",                need: "all"    },
            { key: "package",  label: "My package",     screen: "scrInstallation",      flag: "",                need: "all"    },
            { key: "upload",   label: "Submit",         screen: "scrUpload",            flag: "EOM_UPLOAD",      need: "write"  },
            { key: "review",   label: "Review",         screen: "scrReview",            flag: "EOM_QC",          need: "qc"     },
            { key: "unmatch",  label: "Needs classification", screen: "scrUnmatched",   flag: "EOM_UNMATCHED",   need: "qc"     },
            { key: "activity", label: "Activity",       screen: "scrActivity",          flag: "",                need: "all"    },
            { key: "admin",    label: "Requirements",   screen: "scrAdminRequirements", flag: "EOM_ADMIN_REQS",  need: "admin"  },
            { key: "diag",     label: "Diagnostics",    screen: "scrDiagnostics",       flag: "EOM_DIAGNOSTICS", need: "dev"    }
        ),
        (IsBlank(flag) || MF_IsFeatureOn(flag))
        && Switch( need,
               "all",   true,
               "write", gblCanWrite,
               "qc",    gblCanQC,
               "admin", gblCanEditReqs,
               "dev",   gblIsDeveloper,
               false )
    );


// --- colour tokens -------------------------------------------------------
// Declared once. No screen may use a colour literal. Ratios verified in
// docs/accessibility.md.
clrStatusBlue    = ColorValue("#0F548C");   clrStatusBlueBg  = ColorValue("#EFF6FC");
clrStatusAmber   = ColorValue("#8A5300");   clrStatusAmberBg = ColorValue("#FFF9F0");
clrStatusRed     = ColorValue("#A4262C");   clrStatusRedBg   = ColorValue("#FDF3F4");
clrStatusGreen   = ColorValue("#0E700E");   clrStatusGreenBg = ColorValue("#F1FAF1");
clrStatusGray    = ColorValue("#424242");   clrStatusGrayBg  = ColorValue("#F5F5F5");
clrText          = ColorValue("#242424");
clrTextSecondary = ColorValue("#616161");
clrSurface       = ColorValue("#FFFFFF");
clrSurfaceAlt    = ColorValue("#FAF9F8");
clrBorder        = ColorValue("#D1D1D1");
clrFocus         = ColorValue("#0F6CBD");


// --- telemetry -----------------------------------------------------------
// Business events, not click tracking. Every row answers a question somebody
// will ask about the programme.
gblSessionId = GUID();

MF_EventRow(EventType: Text, Result: Text, RecordId: Text, ErrorCode: Text, ErrorMessage: Text) =
    {
        Event_ID:        "EVT-" & Text(Now(), "yyyymmddhhmmss") & "-" & Text(gblSessionId),
        Event_DateTime:  Now(),
        User_UPN:        gblCurrentUser.Email,
        Role:            gblRole,
        Portfolio_ID:    gblMyPortfolio,
        Installation_ID: gblMyInstallation,
        Facility_ID:     gblMyFacility,
        Event_Type:      EventType,
        Record_ID:       RecordId,
        Result:          Result,
        Error_Code:      ErrorCode,
        Error_Message:   ErrorMessage,
        App_Version:     gblAppVersion
    };
