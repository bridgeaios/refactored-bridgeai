# Start Taurus — Gamification, Dev Support & Security Showcase on port 4202.
# Usage: .\scripts\serve-taurus-showcase.ps1

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$serverPath = Join-Path $scriptRoot "taurus-showcase-server.js"

if (-not (Test-Path $serverPath)) {
    Write-Host "Missing $serverPath" -ForegroundColor Red
    exit 1
}

$env:PORT = if ($env:PORT) { $env:PORT } else { "4202" }
Write-Host "Starting Taurus Showcase on port $env:PORT" -ForegroundColor Cyan
Write-Host "Showcase: http://localhost:$env:PORT/" -ForegroundColor Cyan
Write-Host "Health:   http://localhost:$env:PORT/health" -ForegroundColor Gray
Set-Location $projectRoot
node $serverPath
