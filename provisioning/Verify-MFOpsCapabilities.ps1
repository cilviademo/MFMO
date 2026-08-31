<#
.SYNOPSIS
    Verifies the capability gate register in docs/government-environment-mode.md
    and records the result in MF_App_Config.

.DESCRIPTION
    Build step 1. Microsoft availability does not equal local DAF
    authorization: new connectors are disabled by default in GCC High and DoD
    until an administrator reviews them, so nothing here is assumed.

    The four MVP dependencies are blockers. If any is unavailable, stop —
    discovering a missing connector after the app is written costs a rebuild.

    Each gate writes one MF_App_Config row keyed Capability.<Name>, with the
    verdict, the date and the identity that checked it.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [Parameter(Mandatory = $true)][ValidateSet('UsGov', 'UsGovHigh', 'UsGovDod')][string] $TenantCloud,
    [switch] $RecordOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$pnpEnv = switch ($TenantCloud) {
    'UsGov'     { 'USGovernment' }
    'UsGovHigh' { 'USGovernmentHigh' }
    'UsGovDod'  { 'USGovernmentDoD' }
}

$gates = @(
    @{ Name = 'SharePointOnline'; Blocker = $true;  Test = 'SharePoint Online connector, custom list and library creation' }
    @{ Name = 'PowerAppsCanvas';  Blocker = $true;  Test = 'Canvas app creation licensed and permitted' }
    @{ Name = 'PowerAutomate';    Blocker = $true;  Test = 'Flow creation with the SharePoint connector' }
    @{ Name = 'PowerBIGov';       Blocker = $true;  Test = 'Power BI gov service. Confirm the service URL for this cloud.' }
    @{ Name = 'Office365Users';   Blocker = $false; Test = 'Identity connector. Fallback: UPN text only.' }
    @{ Name = 'Solutions';        Blocker = $false; Test = 'Solution import. Fallback: unmanaged component export.' }
    @{ Name = 'PacCli';           Blocker = $false; Test = 'PAC CLI authorized against this tenant. Fallback: manual export.' }
    @{ Name = 'EnvironmentVars';  Blocker = $false; Test = 'Environment variables. Fallback: MF_App_Config rows.' }
    @{ Name = 'ModernControls';   Blocker = $false; Test = 'Fluent 2 modern controls. Fallback: classic, recorded as a variance.' }
    @{ Name = 'AIBuilder';        Blocker = $false; Test = 'Expected FALSE. Tier 3 only. Never a dependency.' }
    @{ Name = 'PCFCreatorKit';    Blocker = $false; Test = 'Not used in R1. Native modern controls first.' }
    @{ Name = 'CodeApps';         Blocker = $false; Test = 'Not used. Requires admin enablement.' }
    @{ Name = 'CustomConnectors'; Blocker = $false; Test = 'Not used.' }
    @{ Name = 'HttpGraph';        Blocker = $false; Test = 'Not used.' }
    @{ Name = 'Dataverse';        Blocker = $false; Test = 'Not used.' }
    @{ Name = 'Pipelines';        Blocker = $false; Test = 'Not used by design. Requires Managed Environments and premium licensing.' }
)

Connect-PnPOnline -Url $SiteUrl -Interactive -AzureEnvironment $pnpEnv
$me  = (Get-PnPProperty -ClientObject (Get-PnPWeb) -Property CurrentUser).LoginName
$now = (Get-Date).ToString('yyyy-MM-dd')

Write-Host ''
Write-Host "Capability gate register - $TenantCloud, verified by $me on $now" -ForegroundColor White
Write-Host ''

$results = @()
foreach ($gate in $gates) {
    $key   = "Capability.$($gate.Name)"
    $label = if ($gate.Blocker) { 'BLOCKER' } else { 'soft   ' }
    Write-Host ("[{0}] {1,-28} {2}" -f $label, $key, $gate.Test)

    if ($RecordOnly) { $verdict = 'UNVERIFIED' }
    else {
        # There is no reliable API that answers "is this connector permitted for
        # this tenant" without attempting to use it, so these are attested by
        # the engineer running the script and recorded with their name.
        $answer  = Read-Host '      AVAILABLE / UNAVAILABLE / NOT_APPLICABLE'
        $verdict = $answer.Trim().ToUpper()
        if ($verdict -notin @('AVAILABLE', 'UNAVAILABLE', 'NOT_APPLICABLE')) { $verdict = 'UNVERIFIED' }
    }

    $results += [pscustomobject]@{ Key = $key; Verdict = $verdict; Blocker = $gate.Blocker }

    $existing = Get-PnPListItem -List 'MF_App_Config' `
        -Query "<View><Query><Where><Eq><FieldRef Name='Config_Key'/><Value Type='Text'>$key</Value></Eq></Where></Query></View>"
    $values = @{
        Config_Key   = $key
        Config_Value = $verdict
        Config_Type  = 'String'
        Description  = "$($gate.Test) Verified $now by $me."
        Admin_Only   = $true
        Active_Flag  = $true
    }
    if ($existing.Count -eq 1) { Set-PnPListItem -List 'MF_App_Config' -Identity $existing[0].Id -Values $values | Out-Null }
    else { Add-PnPListItem -List 'MF_App_Config' -Values $values | Out-Null }
}

Write-Host ''
$blocking = $results | Where-Object { $_.Blocker -and $_.Verdict -ne 'AVAILABLE' }
if ($blocking) {
    $blocking | ForEach-Object { Write-Error "BLOCKING: $($_.Key) is $($_.Verdict)" }
    throw 'One or more MVP dependencies are unavailable. Stop the build. Do not provision lists.'
}
Write-Host 'All MVP dependencies available. Proceed to Provision-MFOpsLists.ps1.' -ForegroundColor Green
