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

// --- applicability, defined once -----------------------------------------
// These two mirror model_applies() and facility_type_applies() in
// scripts/generate_expected_items.py line for line, and
// tests/test_duplication.py holds them to it. EOM-01 decides what is EXPECTED;
// these decide what a user may FILE against. Different questions, deliberately
// the same predicate -- a dropdown that offers a requirement EOM-01 would
// never generate, or hides one it would, is a dropdown that argues with the
// checklist beside it.

// 'All' applies regardless of model. A facility with NO model -- the NO_DFAC
// registry rows -- matches nothing: a base with no feeding facility owes no
// 1119.
MF_ModelApplies(ApplicableModel: Text, OperatingModel: Text): Boolean =
    !IsBlank(Trim(OperatingModel))
    && ( ApplicableModel = "All" || ApplicableModel = OperatingModel );

// A blank REQUIREMENT list means every type. A blank FACILITY type means
// unknown, and unknown MATCHES -- the QRG carries no facility type for any
// row, so excluding on it would hide every type-scoped requirement from every
// facility.
//
// The inline predicate this replaced got the blank-type case right only by
// accident, and got a real type that is a substring of another wrong. See
// docs/DUPLICATION_AUDIT.md for what it was and why it looked correct.
//
// Matching is on a DELIMITED EXACT TERM: both sides are wrapped in the
// separator so ";MAF;" cannot match inside ";MAFFO;". Spaces around the
// separators are normalised first, because the seed writes
// "Main DFAC; Flight Kitchen" and a human editing the list will too.
MF_FacilityTypeApplies(ApplicableTypes: Text, FacilityType: Text): Boolean =
    IsBlank(Trim(ApplicableTypes))
    || IsBlank(Trim(FacilityType))
    || With( { list: ";" & Substitute(Substitute(Trim(ApplicableTypes),
                                                 "; ", ";"), " ;", ";") & ";" },
             (";" & Trim(FacilityType) & ";") in list );

// Facility-scope requirements applicable to ONE facility's model and type.
// Installation- and Contract-scope requirements are deliberately absent: they
// belong on the installation screen, not in a facility's upload box, and
// putting them here is how a DFAC manager ends up filing the base's SIK bill.
//
// DELEGATION: Active_Flag and Requirement_Scope are indexed and delegable, and
// MF EOM Requirement holds ~13 rows -- three orders of magnitude below the
// ceiling -- so the two applicability predicates run client-side without risk.
// This is the ONLY place in the app where that is acceptable, and it is
// acceptable only because the table is bounded by the requirement catalogue.
MF_RequirementChoices(OperatingModel: Text, FacilityType: Text): Table =
    SortByColumns(
        Filter( Filter( 'MF EOM Requirement',
                        Active_Flag = true,
                        Requirement_Scope = "Facility" ),
                MF_ModelApplies(Applicable_Model, OperatingModel),
                MF_FacilityTypeApplies(Applicable_Facility_Types, FacilityType) ),
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
