<#
.SYNOPSIS
    Provisions the MissionFeedingOperations SharePoint lists, columns and
    indexes from the generated schema.

.DESCRIPTION
    scripts/eom_schema.py is the single source of truth. This script does not
    declare a list or a column of its own; it consumes
    provisioning/schema.generated.json, which is produced by

        python3 scripts/eom_schema.py --json > provisioning/schema.generated.json

    and refuses to run against a stale or missing file.

    Indexes are created at provisioning time or never. SharePoint will not
    add an index to a list that has already crossed the 5,000-item list view
    threshold, and MF_EOM_Item passes that in the first quarter. Verify the
    indexes before seeding anything.

.PARAMETER SiteUrl
    Full URL of the SharePoint site collection. No default. No URL, site GUID
    or list name is hard-coded anywhere in this solution.

.PARAMETER TenantCloud
    UsGov, UsGovHigh or UsGovDod. Must match the tenant. The endpoints differ
    per cloud. This deployment is UsGovDod. Pointing the wrong cloud's endpoints
    at a tenant fails in ways that look like a permissions problem.

.PARAMETER WhatIf
    Report what would change without changing it. Run this first, always.

.PARAMETER EmitRestOnly
    Emit the REST payloads instead of calling SharePoint. Use when PnP
    PowerShell is unavailable and the lists must be created by another means.

.EXAMPLE
    pwsh provisioning/Provision-MFOpsLists.ps1 `
        -SiteUrl <your-site-collection-url> `
        -TenantCloud UsGovDod -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string] $SiteUrl,
    [Parameter(Mandatory = $true)][ValidateSet('UsGov', 'UsGovHigh', 'UsGovDod')][string] $TenantCloud,
    [string] $SchemaJson = (Join-Path $PSScriptRoot 'schema.generated.json'),
    [switch] $EmitRestOnly,
    [switch] $SkipIndexes
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:ExpectedSchemaVersion = '5.0'
$script:ExpectedListCount     = 17
$script:ExpectedColumnCount   = 286

# PnP's cloud identifier differs from the PAC CLI's.
$script:PnPEnvironment = switch ($TenantCloud) {
    'UsGov'     { 'USGovernment' }
    'UsGovHigh' { 'USGovernmentHigh' }
    'UsGovDod'  { 'USGovernmentDoD' }
}

function Write-Step { param([string] $Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string] $Message) Write-Host "    OK  $Message" -ForegroundColor Green }
function Write-Skip { param([string] $Message) Write-Host "    --  $Message" -ForegroundColor DarkGray }

function Assert-Schema {
    if (-not (Test-Path $SchemaJson)) {
        throw "Schema not found at '$SchemaJson'. Run: python3 scripts/eom_schema.py --json > provisioning/schema.generated.json"
    }
    $schema = Get-Content $SchemaJson -Raw | ConvertFrom-Json

    if ($schema.schema_version -ne $script:ExpectedSchemaVersion) {
        throw "Schema version mismatch: file says '$($schema.schema_version)', this script expects '$($script:ExpectedSchemaVersion)'. Regenerate the JSON or update the script deliberately."
    }
    if ($schema.list_count -ne $script:ExpectedListCount) {
        throw "Expected $($script:ExpectedListCount) lists, schema declares $($schema.list_count)."
    }
    if ($schema.column_count -ne $script:ExpectedColumnCount) {
        throw "Expected $($script:ExpectedColumnCount) columns, schema declares $($schema.column_count)."
    }
    Write-Ok "schema v$($schema.schema_version): $($schema.list_count) lists, $($schema.column_count) columns"
    return $schema
}

function Assert-CapabilityGates {
    # Gates 1-5 are hard. This function proves gate 1 and 2 by doing;
    # 3, 4 and 5 are verified by Verify-MFOpsCapabilities.ps1 and recorded
    # in MF_App_Config. Do not proceed on an unrecorded gate.
    Write-Step 'Capability gates'
    if ($TenantCloud -eq 'UNKNOWN') {
        throw 'TenantCloud is UNKNOWN. Confirm the government cloud before provisioning. See docs/government-environment-mode.md.'
    }
    Write-Ok "cloud $TenantCloud -> PnP environment $($script:PnPEnvironment)"
}

function Get-FieldXml {
    param($Column, [string] $ListName)

    $name = $Column.name
    $required = if ($Column.required) { 'TRUE' } else { 'FALSE' }
    $indexed  = if ($Column.indexed)  { 'TRUE' } else { 'FALSE' }

    switch ($Column.type) {
        'Text' {
            "<Field Type='Text' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Indexed='$indexed' MaxLength='255' />"
        }
        'Note' {
            "<Field Type='Note' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' NumLines='6' RichText='FALSE' AppendOnly='FALSE' />"
        }
        'Number' {
            "<Field Type='Number' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Indexed='$indexed' Decimals='0' />"
        }
        'Boolean' {
            "<Field Type='Boolean' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Indexed='$indexed'><Default>0</Default></Field>"
        }
        'DateTime' {
            "<Field Type='DateTime' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Indexed='$indexed' Format='DateOnly' />"
        }
        'Url' {
            "<Field Type='URL' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Format='Hyperlink' />"
        }
        'User' {
            "<Field Type='User' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' UserSelectionMode='PeopleOnly' />"
        }
        'Currency' {
            "<Field Type='Currency' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Decimals='2' />"
        }
        'Choice' {
            $type = 'Choice'
            $choices = ($Column.choices | ForEach-Object { "<CHOICE>$_</CHOICE>" }) -join ''
            # FillInChoice FALSE: the vocabularies live in eom_schema.py and a
            # free-text value would silently break the status engine.
            "<Field Type='$type' DisplayName='$name' Name='$name' StaticName='$name' Required='$required' Indexed='$indexed' Format='Dropdown' FillInChoice='FALSE'><CHOICES>$choices</CHOICES></Field>"
        }
        default { throw "Unhandled column type '$($Column.type)' on $ListName.$name" }
    }
}

function New-MFList {
    param($ListDefinition)

    $listName = $ListDefinition.name
    Write-Step "List $listName ($($ListDefinition.columns.Count) columns)"

    if ($EmitRestOnly) {
        $payload = [ordered]@{
            list    = $listName
            title   = $ListDefinition.display_name
            fields  = @($ListDefinition.columns | ForEach-Object { Get-FieldXml -Column $_ -ListName $listName })
            indexes = @($ListDefinition.indexed_columns)
        }
        $out = Join-Path $PSScriptRoot "rest/$listName.json"
        New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
        $payload | ConvertTo-Json -Depth 6 | Set-Content -Path $out -Encoding UTF8
        Write-Ok "emitted $out"
        return
    }

    $existing = Get-PnPList -Identity $listName -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        if ($PSCmdlet.ShouldProcess($listName, 'Create list')) {
            New-PnPList -Title $listName -Template GenericList -OnQuickLaunch:$false | Out-Null
            Set-PnPList -Identity $listName -Description $ListDefinition.description | Out-Null
            Write-Ok "created"
        }
    }
    else {
        Write-Skip "list exists"
    }

    # Versioning on the evidence-bearing lists. A submission row is never
    # overwritten and an audit row is never edited, so list-level history is
    # the backstop if one ever is.
    if ($listName -in @('MF_EOM_Submission', 'MF_EOM_Item', 'MF_EOM_Audit')) {
        if ($PSCmdlet.ShouldProcess($listName, 'Enable versioning')) {
            Set-PnPList -Identity $listName -EnableVersioning $true -MajorVersions 100 | Out-Null
            Write-Ok "versioning on"
        }
    }

    # The built-in Title column is NOT repurposed. Every list carries its own
    # business key (Requirement_ID, EOM_Item_ID, ...) and Title is left
    # optional and unused, because overloading it makes the key invisible in
    # every view that shows "Title".
    if ($PSCmdlet.ShouldProcess("$listName.Title", 'Make the built-in Title optional')) {
        try {
            $titleField = Get-PnPField -List $listName -Identity 'Title'
            $titleField.Required = $false
            $titleField.Update()
            Invoke-PnPQuery
        }
        catch { Write-Skip 'Title already optional' }
    }

    foreach ($column in $ListDefinition.columns) {
        $field = Get-PnPField -List $listName -Identity $column.name -ErrorAction SilentlyContinue
        if ($null -ne $field) {
            Write-Skip "$($column.name) exists"
            continue
        }
        if ($PSCmdlet.ShouldProcess("$listName.$($column.name)", "Add $($column.type) column")) {
            $xml = Get-FieldXml -Column $column -ListName $listName
            Add-PnPFieldFromXml -List $listName -FieldXml $xml | Out-Null
            Write-Ok "$($column.name) [$($column.type)]"
        }
    }

    if (-not $SkipIndexes) {
        foreach ($indexName in $ListDefinition.indexed_columns) {
            if ($indexName -eq 'Title') { continue }   # SharePoint indexes Title itself
            if ($PSCmdlet.ShouldProcess("$listName.$indexName", 'Create index')) {
                try {
                    $f = Get-PnPField -List $listName -Identity $indexName
                    if (-not $f.Indexed) {
                        $f.Indexed = $true
                        $f.Update()
                        Invoke-PnPQuery
                        Write-Ok "index $indexName"
                    }
                    else { Write-Skip "index $indexName exists" }
                }
                catch {
                    # This is the failure that cannot be repaired later.
                    Write-Warning "INDEX FAILED on $listName.$indexName : $_"
                    Write-Warning "An index cannot be added once the list passes 5,000 items. Fix this before seeding."
                    throw
                }
            }
        }
    }
}

# THIS SCRIPT CREATES NO DOCUMENT LIBRARY.
#
# An earlier design wrote every submission into one central library on this
# site. It is retired: R1 places evidence directly in its portfolio's own
# authoritative destination, and there is ONE authoritative copy. A second copy
# creates ambiguity about which is authoritative, a retention problem, and
# broken links when the two diverge. docs/DECISION_LOG.md D-01.
#
# The four destination libraries ALREADY EXIST, on four separate site
# collections, and are not provisioned from here. They are bound at import --
# deployment/site-bindings.md and deployment/DEPENDENCY_MANIFEST.md.

function Test-Indexes {
    param($Schema)
    Write-Step 'Verifying indexes'
    if ($EmitRestOnly) { Write-Skip 'skipped in REST-only mode'; return }

    $failures = @()
    foreach ($listDef in $Schema.lists) {
        foreach ($indexName in $listDef.indexed_columns) {
            if ($indexName -eq 'Title') { continue }
            $f = Get-PnPField -List $listDef.name -Identity $indexName -ErrorAction SilentlyContinue
            if ($null -eq $f) { $failures += "$($listDef.name).$indexName missing"; continue }
            if (-not $f.Indexed) { $failures += "$($listDef.name).$indexName NOT INDEXED" }
        }
        $itemCount = (Get-PnPList -Identity $listDef.name).ItemCount
        if ($itemCount -gt 5000) {
            Write-Warning "$($listDef.name) already holds $itemCount items. Indexes can no longer be added to it."
        }
    }
    if ($failures.Count -gt 0) {
        $failures | ForEach-Object { Write-Error $_ }
        throw "$($failures.Count) index verification failure(s). Do not seed data until these are resolved."
    }
    Write-Ok 'all declared indexes present'
}

# ---------------------------------------------------------------------------

Write-Host ''
Write-Host 'MissionFeedingOperations - list provisioning' -ForegroundColor White
Write-Host "site:  $SiteUrl"
Write-Host "cloud: $TenantCloud"
Write-Host ''

Assert-CapabilityGates
$schema = Assert-Schema

if (-not $EmitRestOnly) {
    Write-Step 'Connecting'
    Connect-PnPOnline -Url $SiteUrl -Interactive -AzureEnvironment $script:PnPEnvironment
    Write-Ok "connected as $((Get-PnPProperty -ClientObject (Get-PnPWeb) -Property CurrentUser).LoginName)"
}

foreach ($listDef in $schema.lists) { New-MFList -ListDefinition $listDef }
if (-not $SkipIndexes) { Test-Indexes -Schema $schema }

Write-Host ''
Write-Host 'Provisioning complete.' -ForegroundColor Green
Write-Host 'Next: seed configuration/ then run EOM-01. See docs/DEPLOYMENT.md.' -ForegroundColor White
Write-Host 'Do not seed until the index verification above passed.' -ForegroundColor Yellow
