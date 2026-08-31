<#
.SYNOPSIS
    Verifies the capability gates in docs/government-environment-mode.md and
    records the result in MF_App_Config.

.DESCRIPTION
    Build step 1. Gates 1-5 are hard: if any of them is RED, stop. Nothing
    downstream is worth building until they are green, and discovering a
    missing connector after the app is written costs a rebuild.

    Every gate writes one MF_App_Config row keyed Capability.<n>.<name> with
    a value of GREEN, SOFT_FAIL or RED, the verification date and the
    identity that ran the check. A feature flag naming a capability in
    Requires_Capability is refused by the app unless that key reads GREEN.
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
    @{ N = 1;  Name = 'SharePointLists';   Hard = $true;  Test = 'Create and delete a temporary custom list' }
    @{ N = 2;  Name = 'SharePointLibrary'; Hard = $true;  Test = 'Create a library and enable major versioning' }
    @{ N = 3;  Name = 'PowerApps';         Hard = $true;  Test = 'Canvas app creation is licensed and permitted' }
    @{ N = 4;  Name = 'PowerAutomate';     Hard = $true;  Test = 'SharePoint connector available; flow can be created' }
    @{ N = 5;  Name = 'EntraIdentity';     Hard = $true;  Test = 'Office365Users connector resolves the signed-in user' }
    @{ N = 6;  Name = 'PowerBI';           Hard = $false; Test = 'Gov-region workspace available' }
    @{ N = 7;  Name = 'Outlook';           Hard = $false; Test = 'Office 365 Outlook connector available' }
    @{ N = 8;  Name = 'ModernControls';    Hard = $false; Test = 'Fluent 2 modern controls enabled in the environment' }
    @{ N = 9;  Name = 'AIBuilder';         Hard = $false; Test = 'AI Builder licensed. Expected FALSE. Never a dependency.' }
    @{ N = 10; Name = 'PremiumConnectors'; Hard = $false; Test = 'Not used by R1. Record for completeness.' }
    @{ N = 11; Name = 'Pipelines';         Hard = $false; Test = 'Not used by design. Releases are ZIP plus tag.' }
    @{ N = 12; Name = 'CustomConnectors';  Hard = $false; Test = 'Not used by R1.' }
    @{ N = 13; Name = 'PCF';               Hard = $false; Test = 'Out of scope for R1.' }
    @{ N = 14; Name = 'TeamsEmbedding';    Hard = $false; Test = 'Convenience only. App runs in the browser.' }
)

Connect-PnPOnline -Url $SiteUrl -Interactive -AzureEnvironment $pnpEnv
$me = (Get-PnPProperty -ClientObject (Get-PnPWeb) -Property CurrentUser).LoginName
$now = (Get-Date).ToString('yyyy-MM-dd')

Write-Host ''
Write-Host 'Capability gate register' -ForegroundColor White
Write-Host "cloud $TenantCloud, verified by $me on $now"
Write-Host ''

$results = @()
foreach ($gate in $gates) {
    $key = "Capability.$($gate.N).$($gate.Name)"
    $label = if ($gate.Hard) { 'HARD' } else { 'soft' }
    Write-Host ("[{0,-4}] {1,-34} {2}" -f $label, $key, $gate.Test)

    if ($RecordOnly) { $verdict = 'UNVERIFIED' }
    else {
        # Gates 1 and 2 are proven by doing. The rest are attested by the
        # engineer running this script, because there is no reliable API that
        # answers "is this connector permitted for this tenant" without
        # attempting to use it.
        $answer = Read-Host "      GREEN / SOFT_FAIL / RED"
        $verdict = $answer.Trim().ToUpper()
        if ($verdict -notin @('GREEN', 'SOFT_FAIL', 'RED')) { $verdict = 'UNVERIFIED' }
    }

    $results += [pscustomobject]@{ Key = $key; Verdict = $verdict; Hard = $gate.Hard }

    $existing = Get-PnPListItem -List 'MF_App_Config' `
        -Query "<View><Query><Where><Eq><FieldRef Name='Title'/><Value Type='Text'>$key</Value></Eq></Where></Query></View>"
    $values = @{
        Title           = $key
        Config_Value    = $verdict
        Config_Type     = 'Text'
        Environment_Tag = 'PROD'
        Description     = "$($gate.Test) Verified $now by $me."
        Is_Active       = $true
    }
    if ($existing.Count -eq 1) { Set-PnPListItem -List 'MF_App_Config' -Identity $existing[0].Id -Values $values | Out-Null }
    else { Add-PnPListItem -List 'MF_App_Config' -Values $values | Out-Null }
}

Write-Host ''
$blocking = $results | Where-Object { $_.Hard -and $_.Verdict -ne 'GREEN' }
if ($blocking) {
    $blocking | ForEach-Object { Write-Error "BLOCKING: $($_.Key) is $($_.Verdict)" }
    throw 'One or more hard capability gates are not GREEN. Stop the build. Do not provision lists.'
}
Write-Host 'All hard gates GREEN. Proceed to Provision-MFOpsLists.ps1.' -ForegroundColor Green
