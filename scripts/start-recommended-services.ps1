# BridgeLiveWall — Start recommended services that are not yet running (ports 8000, 3001, 3030, 3020)
# Run from repo root. Starts each service in a new minimized window if its port is not listening.

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
Set-Location $projectRoot

function Test-PortListening($port) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $conn -and $conn.Count -gt 0)
    } catch { return $false }
}

function Start-ServiceWindow($name, $port, $scriptBlock) {
    if (Test-PortListening $port) {
        Write-Host "$name (port $port) already listening." -ForegroundColor Green
        return
    }
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($scriptBlock))
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle Minimized", "-EncodedCommand", $encoded
    Write-Host "Started $name (port $port) in new window." -ForegroundColor Cyan
}

# Backend (Bridge API) — port 8000
Start-ServiceWindow "Bridge API" 8000 "Set-Location '$projectRoot'; & '$projectRoot\run-backend.ps1'"

# bridge-backend — port 3001
Start-ServiceWindow "Bridge Backend" 3001 "Set-Location '$projectRoot\bridge-backend'; npm run start"

# bridge-auth — port 3030 (requires Redis on 6379)
Start-ServiceWindow "Bridge Auth" 3030 "Set-Location '$projectRoot\bridge-auth'; node server.js"

# Frontend — port 3020 (serve) or 5173 (vite dev)
if (-not (Test-PortListening 3020) -and -not (Test-PortListening 5173)) {
    $scriptBlock = "Set-Location '$projectRoot\frontend'; npm run start"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($scriptBlock))
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle Minimized", "-EncodedCommand", $encoded
    Write-Host "Started Frontend (port 3020 or 5173) in new window." -ForegroundColor Cyan
} else {
    Write-Host "Frontend (3020/5173) already listening." -ForegroundColor Green
}

Write-Host ""
Write-Host "Run .\audit-wall.ps1 to verify ports. Ensure Redis is running (6379) for bridge-auth." -ForegroundColor Cyan
