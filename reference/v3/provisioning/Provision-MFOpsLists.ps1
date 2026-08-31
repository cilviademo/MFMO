# Provision Mission Feeding Operations lists.
# PnP.PowerShell. Run against the DEV site first.
#   Connect-PnPOnline -Url $SiteUrl -Interactive
# GCC High note: use -AzureEnvironment USGovernmentHigh on Connect-PnPOnline.

param([Parameter(Mandatory=$true)][string]$SiteUrl)

Connect-PnPOnline -Url $SiteUrl -Interactive -AzureEnvironment USGovernmentHigh

# --- MF_Installation : One row per installation
$list = Get-PnPList -Identity "MF Installation" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF Installation" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF Installation" -DisplayName "Installation_ID" -InternalName "Installation_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Installation" -DisplayName "Installation_Name" -InternalName "Installation_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Installation" -DisplayName "Portfolio_ID" -InternalName "Portfolio_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Installation" -DisplayName "MAJCOM" -InternalName "MAJCOM" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Installation" -DisplayName "EOM_Folder_URL" -InternalName "EOM_Folder_URL" -Type URL -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Installation" -DisplayName "Active_Flag" -InternalName "Active_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF Installation" -Identity "Installation_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF Installation" -Identity "Portfolio_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_Facility : One row per feeding facility
$list = Get-PnPList -Identity "MF Facility" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF Facility" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF Facility" -DisplayName "Facility_ID" -InternalName "Facility_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Facility" -DisplayName "Installation_ID" -InternalName "Installation_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Facility" -DisplayName "Facility_Name" -InternalName "Facility_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Facility" -DisplayName "Facility_Type" -InternalName "Facility_Type" -Type Choice -Required -Choices "Main DFAC","Flight Kitchen","Kiosk","Satellite","MAF","Contract Cafe" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Facility" -DisplayName "Operating_Model" -InternalName "Operating_Model" -Type Choice -Required -Choices "Legacy/APF","Food 2.0","MAFFO/MAF","AOR/CDS" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Facility" -DisplayName "Contract_ID" -InternalName "Contract_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Facility" -DisplayName "Active_Flag" -InternalName "Active_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF Facility" -Identity "Facility_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF Facility" -Identity "Installation_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_EOM_Requirement : One row per document requirement per operating model
$list = Get-PnPList -Identity "MF EOM Requirement" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF EOM Requirement" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF EOM Requirement" -DisplayName "Requirement_ID" -InternalName "Requirement_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Document_Code" -InternalName "Document_Code" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Document_Name" -InternalName "Document_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Applicable_Model" -InternalName "Applicable_Model" -Type Choice -Required -Choices "Legacy/APF","Food 2.0","MAFFO/MAF","AOR/CDS","All" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Requirement_Scope" -InternalName "Requirement_Scope" -Type Choice -Required -Choices "Facility","Installation","Contract" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Applicable_Facility_Types" -InternalName "Applicable_Facility_Types" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Frequency" -InternalName "Frequency" -Type Choice -Required -Choices "Monthly","Quarterly","Semiannual","Annual","Conditional" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Required_Flag" -InternalName "Required_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Due_Day" -InternalName "Due_Day" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Due_Offset_Months" -InternalName "Due_Offset_Months" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "QC_Required" -InternalName "QC_Required" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Accepted_File_Types" -InternalName "Accepted_File_Types" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Authority_Reference" -InternalName "Authority_Reference" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Authority_Status" -InternalName "Authority_Status" -Type Choice -Required -Choices "Verified","UNVERIFIED","Management decision" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Sort_Order" -InternalName "Sort_Order" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Requirement" -DisplayName "Active_Flag" -InternalName "Active_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF EOM Requirement" -Identity "Requirement_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_EOM_Item : One PERSISTENT row per expected submission per reporting period
$list = Get-PnPList -Identity "MF EOM Item" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF EOM Item" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF EOM Item" -DisplayName "EOM_Item_ID" -InternalName "EOM_Item_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "EOM_Item_Key" -InternalName "EOM_Item_Key" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Portfolio_ID" -InternalName "Portfolio_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Installation_ID" -InternalName "Installation_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Facility_ID" -InternalName "Facility_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Contract_ID" -InternalName "Contract_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Reporting_Period" -InternalName "Reporting_Period" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Requirement_ID" -InternalName "Requirement_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Requirement_Scope" -InternalName "Requirement_Scope" -Type Choice -Required -Choices "Facility","Installation","Contract" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Required_Flag" -InternalName "Required_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Due_Date" -InternalName "Due_Date" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Current_Submission_ID" -InternalName "Current_Submission_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Received_Flag" -InternalName "Received_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Final_Status" -InternalName "Final_Status" -Type Choice -Required -Choices "NOT_APPLICABLE","NOT_DUE","PENDING_VALIDATION","OVERDUE","NOT_SATISFIED","CORRECTION_REQUIRED","RECEIVED_PENDING_QC","ACCEPTED" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Action_Owner" -InternalName "Action_Owner" -Type Choice -Required -Choices "Facility","Reviewer","Admin","None" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Action_Required" -InternalName "Action_Required" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Status_Code" -InternalName "Status_Code" -Type Number -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Exception_Flag" -InternalName "Exception_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Correction_Due" -InternalName "Correction_Due" -Type DateTime -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Waived_Flag" -InternalName "Waived_Flag" -Type Boolean -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Item" -DisplayName "Waiver_Reason" -InternalName "Waiver_Reason" -Type Note -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF EOM Item" -Identity "EOM_Item_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "EOM_Item_Key" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "Portfolio_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "Installation_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "Facility_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "Reporting_Period" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "Requirement_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Item" -Identity "Status_Code" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_EOM_Submission : One row per uploaded file version
$list = Get-PnPList -Identity "MF EOM Submission" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF EOM Submission" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF EOM Submission" -DisplayName "Submission_ID" -InternalName "Submission_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "EOM_Item_ID" -InternalName "EOM_Item_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Version_No" -InternalName "Version_No" -Type Number -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "File_Name" -InternalName "File_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "File_URL" -InternalName "File_URL" -Type URL -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "File_Size_KB" -InternalName "File_Size_KB" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Uploaded_By" -InternalName "Uploaded_By" -Type User -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Uploaded_DateTime" -InternalName "Uploaded_DateTime" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Submitted_On_Behalf_Of" -InternalName "Submitted_On_Behalf_Of" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Intake_Method" -InternalName "Intake_Method" -Type Choice -Required -Choices "App upload","Folder drop","Manual classification" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Classification_Method" -InternalName "Classification_Method" -Type Choice -Choices "Declared at upload","Folder context","Document content","AI Builder","Manual" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Classification_Status" -InternalName "Classification_Status" -Type Choice -Choices "Pending","Classified","Needs Review","Failed" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Last_Error_Code" -InternalName "Last_Error_Code" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Last_Error_Message" -InternalName "Last_Error_Message" -Type Note -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Last_Processing_DateTime" -InternalName "Last_Processing_DateTime" -Type DateTime -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Retry_Count" -InternalName "Retry_Count" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Source_Path" -InternalName "Source_Path" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "SharePoint_File_ID" -InternalName "SharePoint_File_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Classification_Confidence" -InternalName "Classification_Confidence" -Type Choice -Choices "Declared","High","Low","Unresolved" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Is_Current" -InternalName "Is_Current" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "Superseded_By" -InternalName "Superseded_By" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "QC_Status" -InternalName "QC_Status" -Type Choice -Required -Choices "Pending Review","Accepted","Correction Required","Wrong Document","Not Applicable" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "QC_By" -InternalName "QC_By" -Type User -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "QC_DateTime" -InternalName "QC_DateTime" -Type DateTime -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Submission" -DisplayName "QC_Comment" -InternalName "QC_Comment" -Type Note -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF EOM Submission" -Identity "Submission_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Submission" -Identity "EOM_Item_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Submission" -Identity "Uploaded_DateTime" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_Unmatched_File : One row per file found in the FY folder that could not be resolved
$list = Get-PnPList -Identity "MF Unmatched File" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF Unmatched File" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF Unmatched File" -DisplayName "Unmatched_ID" -InternalName "Unmatched_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "File_Name" -InternalName "File_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "File_URL" -InternalName "File_URL" -Type URL -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Portfolio_ID" -InternalName "Portfolio_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Fiscal_Year" -InternalName "Fiscal_Year" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Discovered_DateTime" -InternalName "Discovered_DateTime" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Uploaded_By" -InternalName "Uploaded_By" -Type User -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Suggested_Installation_ID" -InternalName "Suggested_Installation_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Suggested_Document_Code" -InternalName "Suggested_Document_Code" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Resolution_Status" -InternalName "Resolution_Status" -Type Choice -Required -Choices "Needs Classification","Classified","Not an EOM document","Duplicate" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Resolved_Submission_ID" -InternalName "Resolved_Submission_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Resolved_By" -InternalName "Resolved_By" -Type User -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Unmatched File" -DisplayName "Resolved_DateTime" -InternalName "Resolved_DateTime" -Type DateTime -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF Unmatched File" -Identity "Unmatched_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_Security_Mapping : One row per user per granted scope
$list = Get-PnPList -Identity "MF Security Mapping" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF Security Mapping" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF Security Mapping" -DisplayName "Security_ID" -InternalName "Security_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "UPN" -InternalName "UPN" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Scope_Type" -InternalName "Scope_Type" -Type Choice -Required -Choices "Enterprise","Portfolio","Installation","Facility" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Portfolio_ID" -InternalName "Portfolio_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Installation_ID" -InternalName "Installation_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Facility_ID" -InternalName "Facility_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Role" -InternalName "Role" -Type Choice -Required -Choices "DFAC Manager","Accountant","MFM","Portfolio Manager","AFSVC Leadership","Admin" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Can_QC" -InternalName "Can_QC" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Can_Submit_On_Behalf" -InternalName "Can_Submit_On_Behalf" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Can_Edit_Requirements" -InternalName "Can_Edit_Requirements" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Developer_Flag" -InternalName "Developer_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Tester_Flag" -InternalName "Tester_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Security Mapping" -DisplayName "Active_Flag" -InternalName "Active_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF Security Mapping" -Identity "Security_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF Security Mapping" -Identity "UPN" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_EOM_Audit : One row per state change
$list = Get-PnPList -Identity "MF EOM Audit" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF EOM Audit" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF EOM Audit" -DisplayName "Audit_ID" -InternalName "Audit_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Entity_Type" -InternalName "Entity_Type" -Type Choice -Required -Choices "EOM_Item","EOM_Submission","Requirement" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Entity_ID" -InternalName "Entity_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Action" -InternalName "Action" -Type Choice -Required -Choices "Generated","Uploaded","QC Accepted","QC Correction Required","QC Wrong Document","Waived","Reclassified","Status Recalculated" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Actor_UPN" -InternalName "Actor_UPN" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Action_DateTime" -InternalName "Action_DateTime" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Old_Value" -InternalName "Old_Value" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "New_Value" -InternalName "New_Value" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Audit" -DisplayName "Detail" -InternalName "Detail" -Type Note -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF EOM Audit" -Identity "Audit_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Audit" -Identity "Entity_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_App_Config : One row per configuration key
$list = Get-PnPList -Identity "MF App Config" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF App Config" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF App Config" -DisplayName "Config_Key" -InternalName "Config_Key" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Config" -DisplayName "Config_Value" -InternalName "Config_Value" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Config" -DisplayName "Config_Type" -InternalName "Config_Type" -Type Choice -Required -Choices "String","Boolean","Number","Date" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Config" -DisplayName "Description" -InternalName "Description" -Type Note -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Config" -DisplayName "Admin_Only" -InternalName "Admin_Only" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Config" -DisplayName "Active_Flag" -InternalName "Active_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF App Config" -Identity "Config_Key" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_Feature_Flags : One row per feature
$list = Get-PnPList -Identity "MF Feature Flags" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF Feature Flags" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF Feature Flags" -DisplayName "Feature_Key" -InternalName "Feature_Key" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Feature Flags" -DisplayName "Feature_Name" -InternalName "Feature_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Feature Flags" -DisplayName "Enabled_Prod" -InternalName "Enabled_Prod" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Feature Flags" -DisplayName "Enabled_Testers" -InternalName "Enabled_Testers" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Feature Flags" -DisplayName "Minimum_Role" -InternalName "Minimum_Role" -Type Choice -Required -Choices "DFAC Manager","Accountant","MFM","Portfolio Manager","AFSVC Leadership","Admin","Developer" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Feature Flags" -DisplayName "Effective_Date" -InternalName "Effective_Date" -Type DateTime -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF Feature Flags" -DisplayName "Notes" -InternalName "Notes" -Type Note -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF Feature Flags" -Identity "Feature_Key" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_App_Event_Log : One row per meaningful business event
$list = Get-PnPList -Identity "MF App Event Log" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF App Event Log" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF App Event Log" -DisplayName "Event_ID" -InternalName "Event_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Event_DateTime" -InternalName "Event_DateTime" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "User_UPN" -InternalName "User_UPN" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Role" -InternalName "Role" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Portfolio_ID" -InternalName "Portfolio_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Installation_ID" -InternalName "Installation_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Facility_ID" -InternalName "Facility_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Event_Type" -InternalName "Event_Type" -Type Choice -Required -Choices "AppOpened","DocumentDiscovered","SubmissionCreated","VersionSuperseded","ClassificationSucceeded","ClassificationUncertain","ManualClassification","ExpectedItemMatched","QCAccepted","QCCorrectionRequired","QCWrongDocument","ExpectedGenerationFailed","ReconciliationMismatch","FlowFailure","PermissionDenied","MaintenanceModeBlocked" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Record_ID" -InternalName "Record_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Result" -InternalName "Result" -Type Choice -Required -Choices "Success","Warning","Failure" -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Error_Code" -InternalName "Error_Code" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "Error_Message" -InternalName "Error_Message" -Type Note -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF App Event Log" -DisplayName "App_Version" -InternalName "App_Version" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF App Event Log" -Identity "Event_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF App Event Log" -Identity "Event_DateTime" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF App Event Log" -Identity "Installation_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

# --- MF_EOM_Status : One flat row per EOM item — the canonical Power BI fact
$list = Get-PnPList -Identity "MF EOM Status" -ErrorAction SilentlyContinue
if ($null -eq $list) {
    $list = New-PnPList -Title "MF EOM Status" -Template GenericList -OnQuickLaunch
}
Add-PnPField -List "MF EOM Status" -DisplayName "Status_ID" -InternalName "Status_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "EOM_Item_ID" -InternalName "EOM_Item_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Reporting_Period" -InternalName "Reporting_Period" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Fiscal_Year" -InternalName "Fiscal_Year" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Portfolio_ID" -InternalName "Portfolio_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Installation_ID" -InternalName "Installation_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Installation_Name" -InternalName "Installation_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Facility_ID" -InternalName "Facility_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Facility_Name" -InternalName "Facility_Name" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Operating_Model" -InternalName "Operating_Model" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Contract_ID" -InternalName "Contract_ID" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Requirement_ID" -InternalName "Requirement_ID" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Requirement_Name" -InternalName "Requirement_Name" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Document_Code" -InternalName "Document_Code" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Requirement_Scope" -InternalName "Requirement_Scope" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Authority_Status" -InternalName "Authority_Status" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Required_Flag" -InternalName "Required_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Due_Date" -InternalName "Due_Date" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Received_Flag" -InternalName "Received_Flag" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Received_DateTime" -InternalName "Received_DateTime" -Type DateTime -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Version_No" -InternalName "Version_No" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "QC_Status" -InternalName "QC_Status" -Type Text -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Final_Status" -InternalName "Final_Status" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Status_Code" -InternalName "Status_Code" -Type Number -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Status_Semantic" -InternalName "Status_Semantic" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Action_Owner" -InternalName "Action_Owner" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Action_Required" -InternalName "Action_Required" -Type Boolean -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Package_State" -InternalName "Package_State" -Type Text -Required -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Days_Late" -InternalName "Days_Late" -Type Number -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "On_Time_Flag" -InternalName "On_Time_Flag" -Type Boolean -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Current_File_URL" -InternalName "Current_File_URL" -Type URL -ErrorAction SilentlyContinue | Out-Null
Add-PnPField -List "MF EOM Status" -DisplayName "Generated_DateTime" -InternalName "Generated_DateTime" -Type DateTime -Required -ErrorAction SilentlyContinue | Out-Null
# Index before the list crosses 5,000 items. You cannot index after.
Set-PnPField -List "MF EOM Status" -Identity "Status_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Status" -Identity "EOM_Item_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Status" -Identity "Reporting_Period" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Status" -Identity "Portfolio_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null
Set-PnPField -List "MF EOM Status" -Identity "Installation_ID" -Values @{Indexed=$true} -ErrorAction SilentlyContinue | Out-Null

Write-Host "Provisioning complete." -ForegroundColor Green