// =============================================================================
// App.Formulas.fx  —  named formulas over a bloated OnStart.
//
// Named formulas are declarative and lazily evaluated: they recompute when
// their inputs change and they cost nothing until read. OnStart is imperative,
// runs once, blocks the first screen, and goes stale the moment configuration
// changes underneath it. Everything that CAN be a named formula IS one; App
// OnStart is reduced to the four things that genuinely cannot be
// (see canvas-app/src/App.pa.yaml).
//
// Prefer With() for scoped subformulas over chains of Set(). A Set() chain
// creates order dependencies between lines that no reader can see.
//
// Load order does not matter here. Named formulas resolve by dependency.
// =============================================================================


// -----------------------------------------------------------------------------
// Configuration. No URL, site GUID or list name is hard-coded anywhere.
// Every one of these reads MF_App_Config, and every one has a compiled default
// that is safe when the list is unreachable.
// -----------------------------------------------------------------------------
MF_ConfigRows =
    Filter(MF_App_Config, Is_Active = true);

MF_Config(Key: Text, Fallback: Text): Text =
    With(
        { row: LookUp(MF_ConfigRows, Title = Key) },
        If(IsBlank(row.Config_Value), Fallback, row.Config_Value)
    );

MF_ConfigNumber(Key: Text, Fallback: Number): Number =
    With(
        { v: MF_Config(Key, "") },
        If(IsBlank(v) || !IsNumeric(v), Fallback, Value(v))
    );

MF_ConfigBool(Key: Text, Fallback: Boolean): Boolean =
    With(
        { v: Lower(MF_Config(Key, "")) },
        Switch(v, "true", true, "false", false, Fallback)
    );

gblAppVersion       = MF_Config("AppVersion", "0.0.0-unconfigured");
gblSchemaVersion    = MF_Config("SchemaVersion", "unknown");
gblTenantCloud      = MF_Config("TenantCloud", "UNKNOWN");
gblSiteUrl          = MF_Config("SiteUrl", "");
gblEvidencePath     = MF_Config("EvidenceLibraryPath", "");
gblSupportContact   = MF_Config("SupportContact", "");
gblMaintenanceText  = MF_Config("MaintenanceMessage", "Mission Feeding Operations is temporarily unavailable.");

// The kill switch. Fallback FALSE on both: a configuration outage must not
// lock every user out, and must not silently unlock writes either — the flows
// enforce ReadOnlyMode independently, so FALSE here is safe.
MF_MaintenanceMode  = MF_ConfigBool("MaintenanceMode", false);
MF_ReadOnlyMode     = MF_ConfigBool("ReadOnlyMode", false);

MF_DueSoonWindowDays = MF_ConfigNumber("DueSoonWindowDays", 7);
MF_MaxUploadBytes    = MF_ConfigNumber("MaxUploadSizeMB", 50) * 1024 * 1024;
MF_PageSize          = MF_ConfigNumber("DefaultPageSize", 100);
MF_DelegationWarnAt  = MF_ConfigNumber("DelegationWarningThreshold", 2000);


// -----------------------------------------------------------------------------
// Feature flags. Everything outside the R1 core degrades gracefully behind one.
// Default_Value is what we fall back to when the list is unreachable, so an
// outage never turns an optional dependency ON.
// -----------------------------------------------------------------------------
MF_FlagRows = Filter(MF_Feature_Flags, Is_Active = true);

MF_Flag(FlagName: Text): Boolean =
    With(
        { f: LookUp(MF_FlagRows, Title = FlagName) },
        If(
            IsBlank(f.Title),
            false,                                  // unknown flag is OFF
            Switch(
                f.Scope,
                "Global", f.Flag_Value,
                "Role",   f.Flag_Value && (gblRole in Split(f.Enabled_For_Roles, ";").Value),
                "User",   f.Flag_Value && (Lower(gblCurrentUser.Email) in Lower(f.Enabled_For_UPNs)),
                f.Default_Value
            )
        )
    );

// A flag whose Requires_Capability gate is not GREEN is refused regardless of
// its value. See docs/government-environment-mode.md.
MF_FlagEnabled(FlagName: Text): Boolean =
    With(
        { f: LookUp(MF_FlagRows, Title = FlagName) },
        MF_Flag(FlagName) &&
        (IsBlank(f.Requires_Capability) || MF_Config(f.Requires_Capability, "RED") = "GREEN")
    );


// -----------------------------------------------------------------------------
// Identity and role. No sign-in: CAC resolves identity before the app loads,
// so there is no credential control, no sign-in screen and nothing to tab past.
// -----------------------------------------------------------------------------
gblCurrentUser = User();

MF_MyMappings =
    Filter(
        MF_Security_Mapping,
        Is_Active = true,
        Principal_UPN = gblCurrentUser.Email          // delegable: indexed equality
    );

MF_HasAnyAccess = CountRows(MF_MyMappings) > 0;

// Highest privilege wins. Ranked, not alphabetical.
gblRole =
    With(
        { r: MF_MyMappings },
        If( "Admin" in r.Role,               "Admin",
            "PortfolioManager" in r.Role,    "PortfolioManager",
            "InstallationManager" in r.Role, "InstallationManager",
            "Reviewer" in r.Role,            "Reviewer",
            "FacilityManager" in r.Role,     "FacilityManager",
            "FacilityUser" in r.Role,        "FacilityUser",
            "None"
        )
    );

// Never granted by a role. Only by an explicit flag on the mapping row.
MF_IsDeveloper = CountRows(Filter(MF_MyMappings, Developer_Flag = true)) > 0;
MF_IsTester    = CountRows(Filter(MF_MyMappings, Tester_Flag = true))    > 0;

// The scopes this user may see. One security mapping serves app filtering and
// Power BI RLS; these three tables are the app half of it.
MF_MyFacilityIDs =
    Distinct(Filter(MF_MyMappings, Scope_Type = "Facility"), Scope_ID).Value;
MF_MyInstallationIDs =
    Distinct(Filter(MF_MyMappings, Scope_Type = "Installation"), Scope_ID).Value;
MF_MyPortfolioIDs =
    Distinct(Filter(MF_MyMappings, Scope_Type = "Portfolio"), Scope_ID).Value;
MF_IsGlobalScope =
    CountRows(Filter(MF_MyMappings, Scope_Type = "Global")) > 0;

// Facilities the user may act on, resolved once. Small table; safe to hold.
MF_MyFacilities =
    If( MF_IsGlobalScope,
        Filter(MF_Facility, Is_Active = true),
        Filter(
            MF_Facility,
            Is_Active = true,
            Facility_ID in MF_MyFacilityIDs
                || Installation_ID in MF_MyInstallationIDs
                || Portfolio_ID in MF_MyPortfolioIDs
        )
    );

gblCurrentFacility = First(MF_MyFacilities);


// -----------------------------------------------------------------------------
// Reporting periods.
// -----------------------------------------------------------------------------
MF_OpenPeriods =
    SortByColumns(
        Filter(MF_Reporting_Period, Period_State in ["OPEN", "CLOSING"]),
        "Period_End", SortOrder.Descending
    );

MF_CurrentPeriod = First(MF_OpenPeriods);

MF_SelectablePeriods =
    SortByColumns(
        Filter(
            MF_Reporting_Period,
            Period_End >= DateAdd(Today(), -MF_ConfigNumber("OpenPeriodLookbackMonths", 3), Months)
        ),
        "Period_End", SortOrder.Descending
    );


// -----------------------------------------------------------------------------
// Gate. Evaluated before any screen renders. See App.pa.yaml StartScreen.
// -----------------------------------------------------------------------------
MF_StartScreen =
    If( MF_MaintenanceMode && !MF_IsDeveloper, scrMaintenance,
        !MF_HasAnyAccess,                     scrNoAccess,
        scrHome
    );

// Every write affordance binds DisplayMode to this. The disabled control is a
// courtesy; the flow-side check on the same config key is the control.
MF_WriteMode =
    If(MF_ReadOnlyMode, DisplayMode.Disabled, DisplayMode.Edit);

MF_ReadOnlyBanner =
    If(MF_ReadOnlyMode,
       "Read-only mode: submissions and reviews are paused. Contact " & gblSupportContact & ".",
       "");


// -----------------------------------------------------------------------------
// Colour tokens. Declared once. No screen may use a colour literal.
// Ratios verified in docs/accessibility.md gate A5.
// -----------------------------------------------------------------------------
clrStatusBlue      = ColorValue("#0F548C");
clrStatusBlueBg    = ColorValue("#EFF6FC");
clrStatusAmber     = ColorValue("#8A5300");
clrStatusAmberBg   = ColorValue("#FFF9F0");
clrStatusRed       = ColorValue("#A4262C");
clrStatusRedBg     = ColorValue("#FDF3F4");
clrStatusGreen     = ColorValue("#0E700E");
clrStatusGreenBg   = ColorValue("#F1FAF1");
clrStatusGray      = ColorValue("#424242");
clrStatusGrayBg    = ColorValue("#F5F5F5");
clrText            = ColorValue("#242424");
clrTextSecondary   = ColorValue("#616161");
clrSurface         = ColorValue("#FFFFFF");
clrSurfaceAlt      = ColorValue("#FAF9F8");
clrBorder          = ColorValue("#D1D1D1");
clrFocus           = ColorValue("#0F6CBD");

MF_StatusForeground(FinalStatus: Text): Color =
    Switch(FinalStatus,
        "Blue",  clrStatusBlue,
        "Amber", clrStatusAmber,
        "Red",   clrStatusRed,
        "Green", clrStatusGreen,
        clrStatusGray);

MF_StatusBackground(FinalStatus: Text): Color =
    Switch(FinalStatus,
        "Blue",  clrStatusBlueBg,
        "Amber", clrStatusAmberBg,
        "Red",   clrStatusRedBg,
        "Green", clrStatusGreenBg,
        clrStatusGrayBg);


// -----------------------------------------------------------------------------
// Navigation. Built as a table so scrHome's nav gallery has no per-item logic
// and a feature flag demonstrably removes a screen rather than hiding a button.
// -----------------------------------------------------------------------------
colNavigation =
    Filter(
        Table(
            { key: "home",     label: "My work",           screen: "scrHome",              icon: "Home",      roles: "*",                                                   flag: ""                    },
            { key: "upload",   label: "Submit a document", screen: "scrUpload",            icon: "Upload",    roles: "*",                                                   flag: "EnableAppUpload"     },
            { key: "inst",     label: "Installation",      screen: "scrInstallation",      icon: "Org",       roles: "InstallationManager;PortfolioManager;Admin;Reviewer",  flag: ""                    },
            { key: "review",   label: "Review queue",      screen: "scrReview",            icon: "View",      roles: "Reviewer;InstallationManager;Admin",                   flag: ""                    },
            { key: "unmatch",  label: "Needs classification", screen: "scrUnmatched",      icon: "Help",      roles: "Reviewer;InstallationManager;Admin",                   flag: "EnableUnmatchedQueue"},
            { key: "history",  label: "History",           screen: "scrHistory",           icon: "History",   roles: "*",                                                   flag: ""                    },
            { key: "admin",    label: "Requirements",      screen: "scrAdminRequirements", icon: "Settings",  roles: "Admin;PortfolioManager",                              flag: ""                    },
            { key: "diag",     label: "Diagnostics",       screen: "scrDiagnostics",       icon: "Tools",     roles: "*",                                                   flag: "EnableDiagnosticsScreen" }
        ),
        (roles = "*" || gblRole in Split(roles, ";").Value)
        && (IsBlank(flag) || MF_FlagEnabled(flag))
        // scrDiagnostics additionally requires the mapping-level flag. A normal
        // user must not reach it by any navigation, deep link or keyboard route.
        && (key <> "diag" || MF_IsDeveloper)
    );


// -----------------------------------------------------------------------------
// Telemetry. Structured business events, not a debug log. Every row answers a
// question somebody will ask about the programme.
//
// Called as a behaviour function from OnVisible / OnSelect, so it lives here as
// a formula only for the payload; the Patch itself is in the control.
// -----------------------------------------------------------------------------
gblSessionId = GUID();

MF_TelemetryRow(EventType: Text, Severity: Text, ScreenName: Text, EntityId: Text, Detail: Text) =
    {
        Title:          Text(gblSessionId) & "|" & EventType,
        Event_Time:     Now(),
        Event_Type:     EventType,
        Severity:       Severity,
        User_UPN:       gblCurrentUser.Email,
        App_Version:    gblAppVersion,
        Screen_Name:    ScreenName,
        Correlation_ID: Text(gblSessionId),
        Entity_ID:      EntityId,
        Detail_Json:    Detail
    };

// Sampling applies to ScreenView only. Upload, QCDecision, AccessDenied and
// Error are always written — the events that matter are never sampled away.
MF_ShouldLog(EventType: Text): Boolean =
    EventType in ["Upload", "UploadFailed", "QCDecision", "AccessDenied", "Error", "AppOpen"]
    || Rand() * 100 <= MF_ConfigNumber("TelemetrySamplingPercent", 100);
