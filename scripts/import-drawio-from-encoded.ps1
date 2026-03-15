# Decode URL-encoded draw.io (mxGraphModel) and save as .drawio.xml
# Usage:
#   .\scripts\import-drawio-from-encoded.ps1
#     (reads docs/diagrams/encoded_diagram.txt, writes docs/diagrams/digital-ecosystem-evolution.drawio.xml)
#   .\scripts\import-drawio-from-encoded.ps1 -EncodedPath "path\to\encoded.txt" -OutputPath "path\to\out.drawio.xml"

param(
    [string]$EncodedPath = "",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$diagramsDir = Join-Path $projectRoot "docs\diagrams"

if (-not $EncodedPath) { $EncodedPath = Join-Path $diagramsDir "encoded_diagram.txt" }
if (-not $OutputPath) { $OutputPath = Join-Path $diagramsDir "digital-ecosystem-evolution.drawio.xml" }

if (-not (Test-Path $EncodedPath)) {
    Write-Host "Encoded file not found: $EncodedPath"
    Write-Host "Paste your URL-encoded draw.io XML into that file (e.g. content starting with %3CmxGraphModel%3E), then run this script again."
    exit 1
}

$encoded = Get-Content -Raw -Path $EncodedPath -Encoding UTF8
$decoded = [System.Net.WebUtility]::UrlDecode($encoded)

$outDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

$decoded | Set-Content -Path $OutputPath -Encoding UTF8
Write-Host "Decoded diagram written: $OutputPath"
Write-Host "Open in draw.io (app.diagrams.net) or VS Code with Draw.io extension."
