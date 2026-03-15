# Start Determinator Boot Agent on port 4201 (RBAC HRE).
# Set DETERMINATOR_NEXT_URL to redirect after login (default http://localhost:8000).
# Usage: .\scripts\serve-determinator-boot.ps1

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$agentPath = Join-Path $scriptRoot "determinator-boot-agent.js"

if (-not (Test-Path $agentPath)) {
    Write-Host "Missing $agentPath" -ForegroundColor Red
    exit 1
}

$env:PORT = if ($env:PORT) { $env:PORT } else { "4201" }
if (-not $env:DETERMINATOR_NEXT_URL) { $env:DETERMINATOR_NEXT_URL = "http://localhost:8000" }

Write-Host "Starting Determinator Boot Agent on port $env:PORT" -ForegroundColor Cyan
Write-Host "RBAC login: http://localhost:$env:PORT/" -ForegroundColor Cyan
Write-Host "Next URL after auth: $env:DETERMINATOR_NEXT_URL" -ForegroundColor Gray
Set-Location $projectRoot
node $agentPath
