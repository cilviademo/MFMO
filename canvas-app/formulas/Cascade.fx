// =============================================================================
// Cascade.fx — the cascading reference-data sources.
//
// Requirements are driven by the FACILITY's operating model, never the
// installation's. One base can run a legacy DFAC and a Food 2.0 cafe, and the
// two generate different requirement sets.
//
// These are the drop boxes on the upload and classification screens. They ARE
// MF EOM Requirement, filtered — there is no 'if Legacy then require 1119'
// anywhere in the app, and changing a requirement next year is a list edit.
// =============================================================================

// Installations the viewer may see. Small; resolved in App.Formulas.
MF_InstallationChoices =
    SortByColumns(MF_MyInstallations, "Installation_Name", SortOrder.Ascending);

// Facilities at the selected installation, within the viewer's scope.
MF_FacilityChoices(InstallationId: Text): Table =
    SortByColumns(
        Filter(MF_MyFacilities, Installation_ID = InstallationId),
        "Facility_Name", SortOrder.Ascending );

// Facility-scope requirements applicable to ONE facility's model and type.
// Installation- and Contract-scope requirements are deliberately absent: they
// belong on the installation screen, not in a facility's upload box, and
// putting them here is how a DFAC manager ends up filing the base's SIK bill.
MF_RequirementChoices(OperatingModel: Text, FacilityType: Text): Table =
    SortByColumns(
        Filter( 'MF EOM Requirement',
                Active_Flag = true,
                Requirement_Scope = "Facility",
                Applicable_Model = OperatingModel || Applicable_Model = "All",
                IsBlank(Applicable_Facility_Types)
                    || FacilityType in Applicable_Facility_Types ),
        "Sort_Order", SortOrder.Ascending );

// Installation- and Contract-scope requirements for the installation screen.
MF_SharedRequirementChoices(OperatingModels: Table): Table =
    SortByColumns(
        Filter( 'MF EOM Requirement',
                Active_Flag = true,
                Requirement_Scope <> "Facility" ),
        "Sort_Order", SortOrder.Ascending );

// An unverified requirement still appears — people must be able to file
// against it — but it renders dimmed with the reason available, and it can
// never drive an adverse status. See StatusEngine.fx rule 2.
MF_RequirementIsProvisional(RequirementId: Text): Boolean =
    LookUp('MF EOM Requirement', Requirement_ID = RequirementId).Authority_Status = "UNVERIFIED";

MF_RequirementAuthorityNote(RequirementId: Text): Text =
    With( { r: LookUp('MF EOM Requirement', Requirement_ID = RequirementId) },
        If( r.Authority_Status = "UNVERIFIED",
            "Provisional: " & Coalesce(r.Authority_Reference, "authority not yet confirmed") &
            ". You can still file against it, and its absence is not a finding.",
            Coalesce(r.Authority_Reference, "") ) );

// On-behalf targets. Visible only to MFM, Portfolio Manager and Admin.
// Without this an emailed document uploaded by AFSVC misattributes to AFSVC
// and the missing/overdue counts go wrong silently.
MF_OnBehalfChoices =
    If( gblCanOnBehalf,
        SortByColumns(MF_MyFacilities, "Facility_Name", SortOrder.Ascending),
        Blank() );
