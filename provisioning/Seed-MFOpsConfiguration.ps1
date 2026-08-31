<#
.SYNOPSIS
    Seeds MF_Requirement, MF_App_Config, MF_Feature_Flags and the dimension
    lists from configuration/*.csv.

.DESCRIPTION
    Idempotent. Every list has a declared unique key; a row whose key already
    exists is updated, never duplicated. Run it as often as you like.

    Order matters: configuration and requirements first, then the real
    installation, facility, contract and security rows. EOM-01 must not run
    until all of them are present, because a missing facility silently
    produces fewer expected items rather than an error.

.PARAMETER IncludeSampleData
    Also seed the *.sample.csv dimension files. Use in a test tenant only.
    Production seeds the real rows, which are not committed to this repo.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [Parameter(Mandatory = $true)][ValidateSet('UsGov', 'UsGovHigh', 'UsGovDod')][string] $TenantCloud,
    [string] $ConfigDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'configuration'),
    [switch] $IncludeSampleData
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$pnpEnv = switch ($TenantCloud) {
    'UsGov'     { 'USGovernment' }
    'UsGovHigh' { 'USGovernmentHigh' }
    'UsGovDod'  { 'USGovernmentDoD' }
}

# list name -> (csv file, unique key column). The key column is what makes
# this idempotent; it matches unique_key in scripts/eom_schema.py.
$core = @(
    @{ List = 'MF_App_Config';      File = 'app_config.csv';       Key = 'Title' },
    @{ List = 'MF_Feature_Flags';   File = 'feature_flags.csv';    Key = 'Title' },
    @{ List = 'MF_Requirement';     File = 'requirements.csv';     Key = 'Requirement_ID' }
)
$samples = @(
    @{ List = 'MF_Installation';      File = 'installations.sample.csv';    Key = 'Installation_ID' },
    @{ List = 'MF_Contract';          File = 'contracts.sample.csv';        Key = 'Contract_ID' },
    @{ List = 'MF_Facility';          File = 'facilities.sample.csv';       Key = 'Facility_ID' },
    @{ List = 'MF_Reporting_Period';  File = 'reporting_periods.sample.csv'; Key = 'Period_ID' },
    @{ List = 'MF_Security_Mapping';  File = 'security_mapping.sample.csv'; Key = 'Title' }
)

function ConvertTo-FieldValues {
    param([hashtable] $Row, [string] $ListName)

    $values = @{}
    foreach ($k in $Row.Keys) {
        $v = $Row[$k]
        if ($null -eq $v -or "$v".Trim() -eq '') {
            # Blank stays blank: null, never empty string. Facility_ID on an
            # installation-scope row depends on this distinction.
            continue
        }
        if ("$v" -in @('TRUE', 'FALSE')) { $values[$k] = ("$v" -eq 'TRUE'); continue }
        if ($k -like '*Applies_To_Operating_Model') { $values[$k] = @("$v".Split(';')); continue }
        $values[$k] = "$v"
    }
    return $values
}

function Import-Seed {
    param([string] $ListName, [string] $CsvPath, [string] $KeyColumn)

    if (-not (Test-Path $CsvPath)) { throw "Seed file not found: $CsvPath" }
    $rows = Import-Csv -Path $CsvPath
    Write-Host "==> $ListName  ($($rows.Count) rows from $(Split-Path $CsvPath -Leaf))" -ForegroundColor Cyan

    $created = 0; $updated = 0
    foreach ($row in $rows) {
        $ht = @{}
        $row.PSObject.Properties | ForEach-Object { $ht[$_.Name] = $_.Value }
        $keyValue = $ht[$KeyColumn]
        if ([string]::IsNullOrWhiteSpace($keyValue)) {
            throw "$ListName : a row has no value for the unique key '$KeyColumn'."
        }

        $existing = Get-PnPListItem -List $ListName `
            -Query "<View><Query><Where><Eq><FieldRef Name='$KeyColumn'/><Value Type='Text'>$keyValue</Value></Eq></Where></Query><RowLimit>2</RowLimit></View>"

        if ($existing.Count -gt 1) {
            throw "$ListName : $KeyColumn '$keyValue' matches $($existing.Count) rows. Resolve the duplicate before re-seeding."
        }

        $values = ConvertTo-FieldValues -Row $ht -ListName $ListName

        if ($existing.Count -eq 1) {
            if ($PSCmdlet.ShouldProcess("$ListName/$keyValue", 'Update')) {
                Set-PnPListItem -List $ListName -Identity $existing[0].Id -Values $values | Out-Null
                $updated++
            }
        }
        else {
            if ($PSCmdlet.ShouldProcess("$ListName/$keyValue", 'Create')) {
                Add-PnPListItem -List $ListName -Values $values | Out-Null
                $created++
            }
        }
    }
    Write-Host "    created $created, updated $updated" -ForegroundColor Green
}

Connect-PnPOnline -Url $SiteUrl -Interactive -AzureEnvironment $pnpEnv

foreach ($seed in $core) {
    Import-Seed -ListName $seed.List -CsvPath (Join-Path $ConfigDir $seed.File) -KeyColumn $seed.Key
}
if ($IncludeSampleData) {
    Write-Warning 'Seeding SAMPLE dimension data. Do not do this in production.'
    foreach ($seed in $samples) {
        Import-Seed -ListName $seed.List -CsvPath (Join-Path $ConfigDir $seed.File) -KeyColumn $seed.Key
    }
}

# The two answers that gate everything. Refuse to leave them unset.
$cloudRow = Get-PnPListItem -List 'MF_App_Config' `
    -Query "<View><Query><Where><Eq><FieldRef Name='Title'/><Value Type='Text'>TenantCloud</Value></Eq></Where></Query></View>"
if ($cloudRow.Count -eq 1) {
    Set-PnPListItem -List 'MF_App_Config' -Identity $cloudRow[0].Id -Values @{ Config_Value = $TenantCloud } | Out-Null
    Write-Host "==> MF_App_Config.TenantCloud set to $TenantCloud" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Seeding complete.' -ForegroundColor Green
Write-Host 'Reminder: all twelve requirements seed as UNVERIFIED. None of them can drive a Red status' -ForegroundColor Yellow
Write-Host 'until an authority reference is confirmed on scrAdminRequirements. That is deliberate.' -ForegroundColor Yellow
