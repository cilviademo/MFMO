// QC — replaces the separate Portfolio QC flow entirely. The app writes state;
// EOM-04 only notices the change and notifies.
// Visible when varCanQC. Comment REQUIRED for correction and wrong document.

// btnSaveReview.OnSelect
If(
    ( rdoQC.Selected.Value in ["Correction Required", "Wrong Document"] )
        And IsBlank( txtComment.Text ),
    Notify( "A comment is required when returning a submission.", NotificationType.Error ),

    rdoQC.Selected.Value = "Correction Required" And IsBlank( dtCorrectionDue.SelectedDate ),
    Notify( "A correction suspense date is required.", NotificationType.Error ),

    With( { newCode: Switch( rdoQC.Selected.Value,
                "Accepted", 3, "Wrong Document", 1,
                "Correction Required", 2, "Not Applicable", 0, 2 ) },

        Patch( 'MF EOM Submission', galSubmissions.Selected,
            { QC_Status: rdoQC.Selected.Value, QC_By: varUser,
              QC_DateTime: Now(), QC_Comment: txtComment.Text } );

        Patch( 'MF EOM Item',
            LookUp('MF EOM Item', EOM_Item_ID = galSubmissions.Selected.EOM_Item_ID),
            { Final_Status: rdoQC.Selected.Value,
              Status_Code: newCode,
              Correction_Due: If( rdoQC.Selected.Value = "Correction Required",
                                  dtCorrectionDue.SelectedDate, Blank() ) } );

        Patch( 'MF EOM Audit', Defaults('MF EOM Audit'),
            { Audit_ID: "AUD-" & Text(Now(), "yyyymmddhhmmss"),
              Entity_Type: "EOM_Submission",
              Entity_ID: galSubmissions.Selected.Submission_ID,
              Action: "QC " & rdoQC.Selected.Value,
              Actor_UPN: varUser.Email,
              Action_DateTime: Now(),
              New_Value: rdoQC.Selected.Value,
              Detail: txtComment.Text } );

        Notify( "Review saved.", NotificationType.Success );
        Back()
    )
)
