// Cascading dropdown sources.
// Requirements are driven by the FACILITY's operating model, never the
// installation's — Lackland can run a legacy DFAC and a Food 2.0 cafe.

// ddInstallation.Items
Sort( colMyInstallations, Installation_Name )

// ddFacility.Items — filtered by the selected installation
Sort( Filter( colMyFacilities,
        Installation_ID = ddInstallation.Selected.Installation_ID ),
      Facility_Name )

// ddRequirement.Items — filtered by the selected FACILITY's model and type.
// Facility-scope only; installation and contract scope live on the
// installation screen, not the facility upload box.
Sort(
    Filter( 'MF EOM Requirement',
        Active_Flag = true,
        Requirement_Scope = "Facility",
        Applicable_Model = ddFacility.Selected.Operating_Model Or Applicable_Model = "All",
        IsBlank(Applicable_Facility_Types)
            Or ddFacility.Selected.Facility_Type in Applicable_Facility_Types
    ),
    Sort_Order
)

// ddPeriod.Items — last 13 closed months, newest first
ForAll( Sequence(13, 0, 1) As n,
    { Period: Text( DateAdd(varToday, -1 - n.Value, Months), "yyyy-mm" ) } )

// ddOnBehalf.Visible
varCanOnBehalf
