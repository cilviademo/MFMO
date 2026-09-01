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

// --- schema compatibility ------------------------------------------------
// THE SCHEMA VERSION THIS BUILD WAS COMPILED AGAINST. A literal, deliberately:
// it is a property of the PACKAGE, not of the environment, and reading it from
// the environment would make the check compare a value with itself.
//
// Bump it in the same commit as scripts/eom_schema.py SCHEMA_VERSION.
// tests/test_schema_manifest.py fails if the two drift apart.
MF_ExpectedSchemaVersion = "5.0";

// What is actually deployed, from MF_App_Config. "unknown" when the config
// list did not load -- which is itself a mismatch, not a pass.
gblSchemaVersion  = MF_Config("SchemaVersion", "unknown");

// A NEWER APP MUST NEVER WRITE AGAINST AN OLDER SCHEMA. It would patch columns
// that do not exist yet -- which does not error in Power Apps, it writes
// nothing -- and a document would read as submitted while nothing was
// recorded. Every flow makes the same comparison independently; the app being
// polite is not a control.
gblSchemaMatches  = gblSchemaVersion = MF_ExpectedSchemaVersion;
gblTenantCloud    = MF_Config("TenantCloud", "UNKNOWN");
gblOpenPeriod     = MF_Config("OpenReportingPeriod", Text(DateAdd(Today(), -1, Months), "yyyy-mm"));
gblFiscalYear     = MF_Config("CurrentFiscalYear", "");
gblSupportMessage = MF_Config("SupportMessage", "Mission Feeding Operations is briefly unavailable for maintenance.");
gblSupportContact = MF_Config("SupportContact", "");
gblPowerBIURL     = MF_Config("PowerBIReportURL", "");

// The kill switch. Both default FALSE: a configuration outage must not lock
// every user out, and must not silently unlock writes either — the flows check
// ReadOnlyMode independently, so FALSE here is safe.
gblMaintenanceMode = MF_ConfigBool("MaintenanceMode", false);
gblReadOnlyMode    = MF_ConfigBool("ReadOnlyMode", false);
gblRequireQC       = MF_ConfigBool("RequireQC", true);

MF_MaxUploadBytes  = MF_ConfigNumber("MaxUploadSizeMB", 50) * 1024 * 1024;

// --- review queue ageing -------------------------------------------------
// ONE number an admin can retune. The bands are DERIVED from it, so they can
// never drift out of line with the threshold printed beside them -- which is
// what happens when a developer hardcodes "0-1 / 2-3 / 4-5 / 6+" next to a
// separate "aged 4 days or more" and somebody later changes one of them.
gblReviewAgeDays   = MF_ConfigNumber("ReviewAgeHighlightDays", 4);

MF_ReviewAgeBands =
    With( { n: gblReviewAgeDays },
        Table(
            { Ord: 1, Low: 0,     High: n - 3, Late: false },
            { Ord: 2, Low: n - 2, High: n - 1, Late: false },
            { Ord: 3, Low: n,     High: n + 1, Late: true  },
            { Ord: 4, Low: n + 2, High: Blank(), Late: true } ) );

MF_ReviewAgeLabel(Days: Number): Text =
    With( { b: LookUp(MF_ReviewAgeBands,
                      Days >= Low && (IsBlank(High) || Days <= High)) },
        If( IsBlank(b), "",
            IsBlank(b.High), $"{b.Low}+ days",
            b.Low = b.High,  $"{b.Low} day",
                             $"{b.Low}-{b.High} days" ) );

// Ageing does NOT change the chip. An item awaiting review is yellow because
// AFSVC owns it, and that comes from the status engine -- ageing is a fact
// about the queue, not a status. It is drawn as emphasis on the ROW (weight
// and a leading rule), never by recolouring the chip. A screen that recoloured
// it would be a second status engine, which is how a status engine starts
// lying.
MF_ReviewIsAged(Days: Number): Boolean = Days >= gblReviewAgeDays;
MF_DelegationWarnAt = MF_ConfigNumber("DelegationWarningThreshold", 2000);


// --- scope ---------------------------------------------------------------
// Delegable: filters on UPN, an indexed column, server-side.
// Nobody is provisioned for their own base. CAC identifies the user, the GAL
// gives their installation, and anyone at that installation may view and edit
// its EOM submissions regardless of unit. INSTALLATION is the unit of access.
//
// WARNING: this filter is PRESENTATION. Power Apps Visible and Filter() are not
// an access-control boundary — Microsoft is explicit that permissions
// implemented in an app do not remove the user's permission to the underlying
// data. The evidence library must enforce the same scope independently.
// See docs/security-open-issue.md.
gblMyScope =
    Filter('MF Security Mapping',
           UPN = gblCurrentUser.Email,
           Active_Flag = true);

gblHasAccess = CountRows(MF_LiveScope) > 0;

// Widest scope wins, ranked rather than alphabetical.
gblScopeType =
    With( { s: MF_LiveScope },
        If( "Enterprise"   in s.Scope_Type, "Enterprise",
            "Portfolio"    in s.Scope_Type, "Portfolio",
            "Installation" in s.Scope_Type, "Installation",
            "Facility"     in s.Scope_Type, "Facility",
            "None" ) );

gblRole = If("PORTFOLIO_MANAGER" in MF_LiveScope.Role, "PORTFOLIO_MANAGER", "BASE_USER");

// An expired grant is not a grant. Requested access carries an expiry so a
// departing member has a handover window, not permanent rights to a base they
// left, and the app must honour it without waiting for a cleanup job.
MF_LiveScope =
    Filter(gblMyScope, IsBlank(Expires_Date) || Expires_Date >= Today());

gblCanQC       = CountRows(Filter(MF_LiveScope, Can_QC = true)) > 0;
gblCanOnBehalf = CountRows(Filter(MF_LiveScope, Can_Submit_On_Behalf = true)) > 0;
gblCanEditReqs = CountRows(Filter(MF_LiveScope, Can_Edit_Requirements = true)) > 0;
gblCanGrant    = CountRows(Filter(MF_LiveScope, Can_Grant_Access = true)) > 0;
gblGrantScope  = First(SortByColumns(Filter(MF_LiveScope, Can_Grant_Access = true),
                                     "Grant_Scope", SortOrder.Descending)).Grant_Scope;

// Never granted by a role. Only by an explicit flag on the mapping row.
gblIsDeveloper = CountRows(Filter(MF_LiveScope, Developer_Flag = true)) > 0;
gblIsTester    = CountRows(Filter(MF_LiveScope, Tester_Flag = true))    > 0;

gblMyPortfolio    = First(MF_LiveScope).Portfolio_ID;
gblMyInstallation = First(MF_LiveScope).Installation_ID;
gblMyFacility     = First(MF_LiveScope).Facility_ID;

// Write access: read-only mode locks everyone except developers, and
// maintenance mode locks everyone except developers and admins.
// A schema mismatch disables writes for EVERYONE, developers included. Read-only
// mode is an operational decision a developer may need to work around; a schema
// mismatch is a statement that this build does not know the shape of the data,
// and a developer writing anyway is exactly how it becomes unrecoverable.
gblCanWrite     = gblSchemaMatches && (!gblReadOnlyMode || gblIsDeveloper);
gblCanEnterApp  = !gblMaintenanceMode || gblIsDeveloper || gblCanEditReqs;

MF_WriteMode    = If(gblCanWrite, DisplayMode.Edit, DisplayMode.Disabled);

MF_ReadOnlyBanner =
    If( !gblSchemaMatches,
        "This version of the app does not match the data it is connected to. " &
        "Submitting is disabled until an administrator resolves it. " &
        "Nothing you have already submitted is affected.",
        gblReadOnlyMode,
        "The app is read-only while we finish maintenance. You can view status but not submit.",
        "" );

// Admin-facing, and specific enough to act on. Never shown to a base user --
// the two version strings are a deployment detail, not their problem.
MF_SchemaMismatchDetail =
    If( gblSchemaMatches, "",
        $"CONFIGURATION_REQUIRED: this app expects schema {MF_ExpectedSchemaVersion}, " &
        $"MF_App_Config reports '{gblSchemaVersion}'. Either the lists were " &
        "provisioned from a different schema version, or MF_App_Config was not " &
        "reseeded after they were. Run provisioning/Seed-MFOpsConfiguration.ps1. " &
        "See docs/SHAREPOINT_SCHEMA_MANIFEST.md." );

// The gate, evaluated before any screen renders. Unmapped users get a clear
// route to fix it, not an empty app.
MF_StartScreen =
    If( !gblHasAccess,      scrNoAccess,
        !gblCanEnterApp,    scrMaintenance,
        scrHome );
// A schema mismatch does NOT bounce the user out. They keep read access to
// their own status, which is the thing they came for and which is still true.
// It is writing that stops.


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
// Only onboarded bases generate expected items, so only onboarded bases have
// anything to show. A base with Generation_Enabled FALSE is "not yet
// onboarded", never "compliant".
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

// Non-duty days in scope for this viewer. Small, and the same list the flow
// resolves effective dates against, so the app and EOM-01 never disagree about
// which Monday a suspense moved to.
MF_MyNonDutyDays =
    Filter( 'MF Non Duty Day',
            Active_Flag = true,
            Scope_Type = "Enterprise"
                || Scope_ID = gblMyInstallation
                || Scope_ID = gblMyPortfolio );


// --- navigation ----------------------------------------------------------
// Role-shaped: three destinations for a facility user, six for an admin.
// A feature flag removes the destination, not merely the button.
colNavigation =
    Filter(
        Table(
            { key: "home",     label: "Home",           screen: "scrHome",              flag: "",                need: "all"    },
            // Was pointed at scrInstallation, the single-installation detail
            // screen, because no package screen existed yet. It does now.
            { key: "package",  label: "My Package",     screen: "scrMyPackage",         flag: "",                need: "all"    },
            { key: "overview", label: "Overview",       screen: "scrOverview",          flag: "",                need: "qc"     },
            { key: "installs", label: "Installations",  screen: "scrInstallations",     flag: "",                need: "qc"     },
            { key: "except",   label: "Exceptions",     screen: "scrExceptions",        flag: "",                need: "qc"     },
            // Submit is a PRIMARY ACTION, not a tab: BASE_TABS in the Figma
            // build is exactly Home / My Package / Calendar, and every row
            // action on scrHome and scrMyPackage already carries the item to
            // scrUpload. A fourth tab was navigation drift.
            { key: "review",   label: "Review",         screen: "scrReview",            flag: "EOM_QC",          need: "qc"     },
            // Classification is reached from the Exceptions screen's rows
            // (btnClassify -> scrUnmatched); a parallel tab duplicated it.
            { key: "calendar", label: "Calendar",       screen: "scrCalendar",          flag: "EOM_CALENDAR",    need: "all"    },
            // Activity is an AFSVC workspace tab (approved AFSVC set:
            // Overview, Review, Installations, Exceptions, Activity, Admin).
            { key: "activity", label: "Activity",       screen: "scrActivity",          flag: "",                need: "qc"     },
            // Request access is a BUTTON on scrNoAccess in the approved
            // design (NoAccess.tsx and ScopeUnresolved.tsx both reach it that
            // way), never a tab. The screen stays; the tab goes.
            { key: "admin",    label: "Admin",          screen: "scrAdminRequirements", flag: "EOM_ADMIN_REQS",  need: "admin"  },
            { key: "diag",     label: "Diagnostics",    screen: "scrDiagnostics",       flag: "EOM_DIAGNOSTICS", need: "dev"    }
        ),
        (IsBlank(flag) || MF_IsFeatureOn(flag))
        && Switch( need,
               "all",   true,
               "write", gblCanWrite,
               "qc",    gblCanQC,
               "admin", gblCanEditReqs,
               "grant", gblCanGrant,
               "dev",   gblIsDeveloper,
               false )
    );


// --- colour tokens -------------------------------------------------------
// Declared once. No screen may use a colour literal. Every ratio is verified by
// tests/test_design_tokens.py and recorded in docs/accessibility.md.
clrStatusBlue    = ColorValue("#0F548C");
clrStatusBlueBg  = ColorValue("#EFF6FC");

// AMBER AND YELLOW ARE THE WHOLE POINT OF SIX STATES, and they were 1.16:1
// apart until this was fixed -- two near-identical browns telling a DFAC
// manager that a document they filed on time and one they never sent are the
// same kind of problem.
//
// Amber: the base still owes it and still has runway.   Amber is ORANGE.
// Yellow: AFSVC has it and the base owes nothing.       Yellow is GOLD.
//
// They are 48 degrees apart in hue and dE2000 30 apart, which holds up under
// deuteranopia, protanopia and tritanopia (dE 15-19). Luminance contrast
// BETWEEN them is only 1.06:1 and cannot usefully be raised -- see
// docs/accessibility.md -- so hue does the separating and the label and the
// icon do the guaranteeing. Neither chip is ever colour alone.
clrStatusAmber   = ColorValue("#944800");
clrStatusAmberBg = ColorValue("#FFF3E6");
clrStatusYellow  = ColorValue("#5A5800");
clrStatusYellowBg = ColorValue("#FDFAE0");

clrStatusRed     = ColorValue("#A4262C");
clrStatusRedBg   = ColorValue("#FDF3F4");
clrStatusGreen   = ColorValue("#0E700E");
clrStatusGreenBg = ColorValue("#F1FAF1");
clrStatusGray    = ColorValue("#424242");
clrStatusGrayBg  = ColorValue("#F5F5F5");
// The Figma --accent token. Was referenced by scrExceptions and DEFINED
// NOWHERE -- an undefined token the reference checker missed because its
// regex did not cover clr* names. Studio would have shown the error; the
// parity pass caught it first.
clrAccent        = ColorValue("#0F548C");
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
