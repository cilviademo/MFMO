# Discover-MFDestinations.ps1
#
# Reads the four Mission Feeding portfolio sites and reports what is actually
# there: the real library name, the real Monthly Data Call root, and — the part
# nobody can guess — the actual naming pattern of the FY and month folders.
#
# READ-ONLY. Creates nothing, changes nothing, uploads nothing.
#
# Run it once, paste the output back, and the destination configuration writes
# itself. Ten minutes here prevents a month of files landing at root.
#
# Usage:
#   .\Discover-MFDestinations.ps1 -SiteUrls @(
#       "https://<tenant>/sites/DAFMissionFeeding-Portfolio1",
#       "https://<tenant>/sites/DAFMissionFeeding-Legacy_Portfolio2",
#       "https://<tenant>/sites/DAFMissionFeeding-Portfolio3",
#       "https://<tenant>/sites/DAFMissionFeeding-Portfolio4"
#   )
#
# Portfolio 2's site slug contains "Legacy_" and the others do not. Do not
# build these URLs by pattern.

param(
    [Parameter(Mandatory = $true)][string[]] $SiteUrls,
    [ValidateSet("USGovernmentDoD","USGovernmentHigh","USGovernment","Production")]
    [string] $Cloud = "USGovernmentDoD",
    [string] $OutFile = ".\discovery-output.csv"
)

$ErrorActionPreference = "Stop"
$results = @()

function Show($msg, $colour = "Gray") { Write-Host $msg -ForegroundColor $colour }

for ($i = 0; $i -lt $SiteUrls.Count; $i++) {
    $url = $SiteUrls[$i]
    $portfolio = "PORTFOLIO $($i + 1)"

    Show "`n============================================================" Cyan
    Show " $portfolio" Cyan
    Show " $url" DarkGray
    Show "============================================================" Cyan

    try {
        Connect-PnPOnline -Url $url -Interactive -AzureEnvironment $Cloud
    } catch {
        Show " CONNECT FAILED: $($_.Exception.Message)" Red
        Show " Check the URL and that you have at least Read on this site." DarkGray
        $results += [pscustomobject]@{
            Portfolio = $portfolio; SiteUrl = $url; Library = ""; RootFolder = ""
            FYFolders = ""; MonthFolderSample = ""; Status = "CONNECT FAILED"
        }
        continue
    }

    # ---- libraries -------------------------------------------------------
    $libs = Get-PnPList | Where-Object { $_.BaseTemplate -eq 101 -and -not $_.Hidden }
    Show "`n Document libraries:" White
    foreach ($l in $libs) {
        Show ("   {0,-32} entity: {1}" -f $l.Title, $l.EntityTypeName)
    }

    # ---- find the Monthly Data Call root ---------------------------------
    $root = $null
    $lib  = $null
    foreach ($l in $libs) {
        try {
            $items = Get-PnPListItem -List $l -PageSize 500 -Fields "FileRef","FSObjType" |
                     Where-Object { $_["FSObjType"] -eq 1 }
        } catch { continue }

        $match = $items | Where-Object { $_["FileRef"] -match "Monthly\s*Data\s*Call" } |
                 Sort-Object { $_["FileRef"].Length } | Select-Object -First 1
        if ($match) { $root = $match["FileRef"]; $lib = $l.Title; break }
    }

    if (-not $root) {
        Show "`n NO 'Monthly Data Call' FOLDER FOUND" Yellow
        Show " Folders present at the top level:" DarkGray
        foreach ($l in $libs) {
            $tops = Get-PnPFolderItem -FolderSiteRelativeUrl $l.RootFolder.ServerRelativeUrl `
                    -ItemType Folder -ErrorAction SilentlyContinue
            foreach ($t in $tops) { Show "   $($l.Title)/$($t.Name)" DarkGray }
        }
        $results += [pscustomobject]@{
            Portfolio = $portfolio; SiteUrl = $url; Library = ""; RootFolder = ""
            FYFolders = ""; MonthFolderSample = ""; Status = "ROOT NOT FOUND"
        }
        continue
    }

    Show "`n Library:      $lib" Green
    Show " Root folder:  $root" Green

    # ---- FY folders ------------------------------------------------------
    $fyFolders = Get-PnPFolderItem -FolderSiteRelativeUrl $root -ItemType Folder |
                 Select-Object -ExpandProperty Name | Sort-Object
    Show "`n FY folders:" White
    if ($fyFolders) { foreach ($f in $fyFolders) { Show "   $f" } }
    else { Show "   (none)" Yellow }

    # ---- month folders — the important part -------------------------------
    $sample = ""
    $fy26 = $fyFolders | Where-Object { $_ -match "26" } | Select-Object -First 1
    if ($fy26) {
        $months = Get-PnPFolderItem -FolderSiteRelativeUrl "$root/$fy26" -ItemType Folder |
                  Select-Object -ExpandProperty Name | Sort-Object
        Show "`n Month folders inside '$fy26':" White
        if ($months) {
            foreach ($m in $months) { Show "   $m" }
            $sample = $months -join " | "
        } else {
            Show "   (none)" Yellow
        }

        # one level deeper, in case installations sit under the month
        $firstMonth = $months | Select-Object -First 1
        if ($firstMonth) {
            $sub = Get-PnPFolderItem -FolderSiteRelativeUrl "$root/$fy26/$firstMonth" `
                   -ItemType Folder -ErrorAction SilentlyContinue |
                   Select-Object -ExpandProperty Name
            if ($sub) {
                Show "`n Inside '$firstMonth' (installation folders?):" White
                foreach ($s in ($sub | Select-Object -First 12)) { Show "   $s" }
                if ($sub.Count -gt 12) { Show "   ... $($sub.Count - 12) more" DarkGray }
            } else {
                Show "`n '$firstMonth' has no subfolders — files sit directly in the month." DarkGray
            }
        }
    }

    $results += [pscustomobject]@{
        Portfolio         = $portfolio
        SiteUrl           = $url
        Library           = $lib
        RootFolder        = $root
        FYFolders         = ($fyFolders -join " | ")
        MonthFolderSample = $sample
        Status            = "OK"
    }

    Disconnect-PnPOnline
}

$results | Export-Csv -Path $OutFile -NoTypeInformation -Encoding UTF8

Show "`n============================================================" Cyan
Show " SUMMARY" Cyan
Show "============================================================" Cyan
$results | Format-Table Portfolio, Library, Status -AutoSize

Show "`n Written to $OutFile" Green
Show ""
Show " Send that file back. It carries the four site URLs, the real library" DarkGray
Show " and root folder names, and the actual month folder naming — which is" DarkGray
Show " the one thing nobody can guess and the thing that decides whether" DarkGray
Show " uploads land in the right place or at the root." DarkGray
Show ""
Show " Nothing was created or modified." DarkGray
