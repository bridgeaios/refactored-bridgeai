# One-shot: bring in storage from Google Drive, new Google Sheet, or local Excel -> data/storage-sync.json (configurable & viewable).
# Requires: gcloud CLI (for Google). For local Excel: Python + openpyxl or use .csv.
# Usage:
#   $env:GOOGLE_DRIVE_FILE_ID = "xxx"; .\scripts\google-storage-sync.ps1
#   $env:GOOGLE_SHEET_ID = "xxx"; .\scripts\google-storage-sync.ps1
#   $env:LOCAL_EXCEL_PATH = ".\config.xlsx"; .\scripts\google-storage-sync.ps1
# View: http://localhost:4202/ (Taurus Showcase) or GET http://localhost:4202/api/storage-sync

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$dataDir = Join-Path $projectRoot "data"
$outPath = Join-Path $dataDir "storage-sync.json"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

$syncedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

function Get-GcloudToken {
    $t = gcloud auth application-default print-access-token 2>$null
    if (-not $t) { Write-Host "Run: gcloud auth application-default login"; exit 1 }
    return $t
}

function Export-FromDrive {
    param([string]$FileId)
    $token = Get-GcloudToken
    $uri = "https://www.googleapis.com/drive/v3/files/$FileId?fields=mimeType,name"
    $meta = Invoke-RestMethod -Uri $uri -Headers @{ Authorization = "Bearer $token" }
    $name = $meta.name
    if ($meta.mimeType -like "*spreadsheet*") {
        $exportUri = "https://www.googleapis.com/drive/v3/files/$FileId/export?mimeType=text/csv"
        $csvPath = Join-Path $dataDir "drive_export.csv"
        Invoke-WebRequest -Uri $exportUri -Headers @{ Authorization = "Bearer $token" } -OutFile $csvPath -UseBasicParsing
        $rows = @(Import-Csv -Path $csvPath | ForEach-Object { $_.PSObject.Properties | ForEach-Object -Begin { $h = [ordered]@{} } -Process { $h[$_.Name] = $_.Value } -End { $h } })
        $out = @{ source = "google_drive"; fileId = $FileId; name = $name; syncedAt = $syncedAt; rows = $rows }
        $out | ConvertTo-Json -Depth 10 | Set-Content -Path $outPath -Encoding UTF8
    } else {
        $dlUri = "https://www.googleapis.com/drive/v3/files/$FileId?alt=media"
        $binPath = Join-Path $dataDir "drive_file"
        Invoke-WebRequest -Uri $dlUri -Headers @{ Authorization = "Bearer $token" } -OutFile $binPath -UseBasicParsing
        @{ source = "google_drive"; fileId = $FileId; name = $name; syncedAt = $syncedAt; localPath = "data/drive_file" } | ConvertTo-Json | Set-Content -Path $outPath -Encoding UTF8
    }
}

function Export-FromSheet {
    param([string]$SheetId, [string]$Range = "A1:Z1000")
    $token = Get-GcloudToken
    $uri = "https://sheets.googleapis.com/v4/spreadsheets/$SheetId/values/$Range"
    $r = Invoke-RestMethod -Uri $uri -Headers @{ Authorization = "Bearer $token" }
    $vals = $r.values
    $headers = $vals[0]
    $rows = @()
    for ($i = 1; $i -lt $vals.Count; $i++) {
        $row = @{}
        for ($j = 0; $j -lt $headers.Count; $j++) {
            $row[$headers[$j]] = if ($j -lt $vals[$i].Count) { $vals[$i][$j] } else { $null }
        }
        $rows += $row
    }
    @{ source = "google_sheet"; sheetId = $SheetId; range = $Range; syncedAt = $syncedAt; headers = $headers; rows = $rows } | ConvertTo-Json -Depth 10 | Set-Content -Path $outPath -Encoding UTF8
}

function Export-FromLocalExcel {
    param([string]$Path)
    if (-not (Test-Path $Path)) { Write-Host "File not found: $Path"; exit 1 }
    $ext = [System.IO.Path]::GetExtension($Path).ToLower()
    if ($ext -eq ".csv") {
        $rows = @(Import-Csv -Path $Path | ForEach-Object { $_.PSObject.Properties | ForEach-Object -Begin { $h = [ordered]@{} } -Process { $h[$_.Name] = $_.Value } -End { $h } })
        @{ source = "local_excel"; path = $Path; syncedAt = $syncedAt; rows = $rows } | ConvertTo-Json -Depth 10 | Set-Content -Path $outPath -Encoding UTF8
    } else {
        $py = Join-Path $scriptRoot "read-excel-to-json.py"
        if (Test-Path $py) {
            & python $py $Path $outPath
        } else {
            @{ source = "local_excel"; path = $Path; syncedAt = $syncedAt; error = "read-excel-to-json.py not found or openpyxl required" } | ConvertTo-Json | Set-Content -Path $outPath -Encoding UTF8
        }
    }
}

if ($env:GOOGLE_DRIVE_FILE_ID) {
    Export-FromDrive -FileId $env:GOOGLE_DRIVE_FILE_ID
} elseif ($env:GOOGLE_SHEET_ID) {
    $range = if ($env:GOOGLE_SHEET_RANGE) { $env:GOOGLE_SHEET_RANGE } else { "A1:Z1000" }
    Export-FromSheet -SheetId $env:GOOGLE_SHEET_ID -Range $range
} elseif ($env:LOCAL_EXCEL_PATH) {
    Export-FromLocalExcel -Path $env:LOCAL_EXCEL_PATH
} else {
    @{ source = "none"; syncedAt = $syncedAt; hint = "Set GOOGLE_DRIVE_FILE_ID, GOOGLE_SHEET_ID, or LOCAL_EXCEL_PATH" } | ConvertTo-Json | Set-Content -Path $outPath -Encoding UTF8
    Write-Host "No source set. Wrote placeholder. Set env: GOOGLE_DRIVE_FILE_ID, GOOGLE_SHEET_ID, or LOCAL_EXCEL_PATH"
}

Write-Host "Wrote $outPath"
Write-Host "Viewable: http://localhost:4202/api/storage-sync  (start Taurus Showcase: .\scripts\serve-taurus-showcase.ps1)"
