// Upload — the front door. Because installation, facility, requirement and
// period are DECLARED here, nothing downstream has to classify the file.
// Classification_Confidence = "Declared" is what keeps the stray queue small.

// btnUpload.OnSelect
With(
    { item: LookUp( 'MF EOM Item',
        Installation_ID = varSelectedInstallation.Installation_ID
        And ( IsBlank(varSelectedFacility)
              Or Facility_ID = varSelectedFacility.Facility_ID )
        And Reporting_Period = varSelectedPeriod
        And Requirement_ID  = ddRequirement.Selected.Requirement_ID ) },

    If( IsBlank(item),

        // No expected row: EOM-01 has not generated it, or this is off-cycle.
        // Do NOT silently create a tracker row — route to Needs Classification
        // so a human decides whether the requirement should exist at all.
        Notify( "No expected requirement matches that selection. Sending to Needs Classification.",
                NotificationType.Warning ),

        With( { nextVer: CountRows(Filter('MF EOM Submission',
                                          EOM_Item_ID = item.EOM_Item_ID)) + 1,
                newId:   "SUB-" & Text(Now(), "yyyymmddhhmmss") & "-" & item.EOM_Item_ID },

            // Supersede the previous current version. Nothing is overwritten.
            UpdateIf( 'MF EOM Submission',
                EOM_Item_ID = item.EOM_Item_ID And Is_Current = true,
                { Is_Current: false, Superseded_By: newId } );

            Patch( 'MF EOM Submission', Defaults('MF EOM Submission'),
                { Submission_ID: newId,
                  EOM_Item_ID: item.EOM_Item_ID,
                  Version_No: nextVer,
                  File_Name: attUpload.Attachments.Name,
                  Uploaded_By: varUser,
                  Uploaded_DateTime: Now(),
                  Submitted_On_Behalf_Of:
                      If( tglOnBehalf.Value,
                          Coalesce(varSelectedFacility.Facility_ID,
                                   varSelectedInstallation.Installation_ID), Blank() ),
                  Intake_Method: "App upload",
                  Classification_Confidence: "Declared",
                  Is_Current: true,
                  QC_Status: "Pending Review" } );

            Patch( 'MF EOM Item', item,
                { Received_Flag: true,
                  Current_Submission_ID: newId,
                  Final_Status: "Pending Review",
                  Status_Code: 2 } );

            Notify( "Submitted. Version " & nextVer & ".", NotificationType.Success );
            Reset( attUpload )
        )
    )
)
