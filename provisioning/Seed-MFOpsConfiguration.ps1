<#
.SYNOPSIS
    Seeds MF_EOM_Requirement, MF_App_Config and MF_Feature_Flags from
    configuration/*.csv, and optionally the sample dimension data.

.DESCRIPTION
    Idempotent. Every list has a declared unique key in scripts/eom_schema.py;
    a row whose key already exists is updated, never duplicated. Run it as
    often as you like.

    Order matters. Configuration and requirements first, then the real
    installation, facility and security rows. EOM-01 must not run until all of
    them are present, because a missing facility silently produces fewer
    expected items rather than an error.

.PARAMETER IncludeSampleData
    Also seed the *.sample.csv dimension files. Test tenant only. Production
    seeds the real rows, which are not committed to this repository.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [Parameter(Mandatory = $true)][ValidateSet('UsGov', 'UsGovHigh', 'UsGovDod')][string] $TenantCloud,
    [string] $ConfigDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'configuration'),
    [switch] $IncludeRegistry,
    [switch] $IncludeSampleData
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$pnpEnv = switch ($TenantCloud) {
    'UsGov'     { 'USGovernment' }
    'UsGovHigh' { 'USGovernmentHigh' }
    'UsGovDod'  { 'USGovernmentDoD' }
}

# list -> (csv, unique key). The key matches unique_key in scripts/eom_schema.py
# and is what makes this idempotent.
$core = @(
    @{ List = 'MF_App_Config';          File = 'app-config.csv';             Key = 'Config_Key' },
    @{ List = 'MF_Feature_Flags';       File = 'feature-flags.csv';          Key = 'Feature_Key' },
    @{ List = 'MF_EOM_Requirement';     File = 'requirements.csv';           Key = 'Requirement_ID' },
    @{ List = 'MF_Notification_Rule';   File = 'notification-rules.csv';     Key = 'Rule_ID' },
    @{ List = 'MF_Document_Destination'; File = 'document-destinations.csv'; Key = 'Destination_ID' }
)

# The registry is real, seeded from the QRG by scripts/gen_registry.py. It is not
# sample data. Every installation row carries Generation_Enabled FALSE, so
# importing it onboards nobody -- see Gate 3 in docs/DEPLOYMENT.md.
$registry = @(
    @{ List = 'MF_Installation'; File = 'installations.csv'; Key = 'Installation_ID' },
    @{ List = 'MF_Facility';     File = 'facilities.csv';    Key = 'Facility_ID' }
)

$samples = @(
    @{ List = 'MF_Security_Mapping'; File = 'security-mapping.sample.csv'; Key = 'Security_ID' },
    @{ List = 'MF_Non_Duty_Day';     File = 'non-duty-days.sample.csv';    Key = 'Non_Duty_ID' }
)

# Columns that must be written as a real null rather than an empty string.
# Facility_ID on an installation-scope row is the one that breaks everything
# downstream if it becomes ''.
$nullableKeys = @('Facility_ID', 'Contract_ID', 'Installation_ID', 'Portfolio_ID',
                  'Suggested_Installation_ID', 'Suggested_Document_Code')

function ConvertTo-FieldValues {
    param([hashtable] $Row)

    $values = @{}
    foreach ($k in $Row.Keys) {
        $v = "$($Row[$k])".Trim()
        if ([string]::IsNullOrWhiteSpace($v)) {
            # Blank stays blank: null, never empty string.
            continue
        }
        if ($v -in @('TRUE', 'FALSE')) { $values[$k] = ($v -eq 'TRUE'); continue }
        $values[$k] = $v
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

        $values = ConvertTo-FieldValues -Row $ht

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
if ($IncludeRegistry) {
    foreach ($seed in $registry) {
        Import-Seed -ListName $seed.List -CsvPath (Join-Path $ConfigDir $seed.File) -KeyColumn $seed.Key
    }
}
if ($IncludeSampleData) {
    Write-Warning 'Seeding SAMPLE dimension data. Do not do this in production.'
    foreach ($seed in $samples) {
        Import-Seed -ListName $seed.List -CsvPath (Join-Path $ConfigDir $seed.File) -KeyColumn $seed.Key
    }
}

# One of the two answers that gate everything. Record it now that we know it.
$cloudRow = Get-PnPListItem -List 'MF_App_Config' `
    -Query "<View><Query><Where><Eq><FieldRef Name='Config_Key'/><Value Type='Text'>TenantCloud</Value></Eq></Where></Query></View>"
if ($cloudRow.Count -eq 1) {
    Set-PnPListItem -List 'MF_App_Config' -Identity $cloudRow[0].Id -Values @{ Config_Value = $TenantCloud } | Out-Null
    Write-Host "==> MF_App_Config.TenantCloud set to $TenantCloud" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Seeding complete.' -ForegroundColor Green
Write-Host ''
Write-Host 'Two things ship deliberately switched off. Neither is an incomplete seed.' -ForegroundColor Yellow
Write-Host ''
Write-Host '  Requirements whose authority is UNVERIFIED cannot drive an adverse status'   -ForegroundColor Yellow
Write-Host '  until a reference is confirmed on scrAdminRequirements.'                     -ForegroundColor Yellow
Write-Host ''
Write-Host '  All four document destinations ship with Site_URL blank and Active_Flag'     -ForegroundColor Yellow
Write-Host '  FALSE. EOM-02 fails closed until somebody opens each of the four SITE'       -ForegroundColor Yellow
Write-Host '  COLLECTIONS -- they are not four channels in one team -- and records what'   -ForegroundColor Yellow
Write-Host '  is actually there. deployment/site-bindings.md is the checklist.'            -ForegroundColor Yellow
