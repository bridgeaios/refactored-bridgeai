# Bridge AI OS - Full Stack Boot
# Starts all services in dependency order, waits for Bridge API health, then registers
# every service in the central project registry (single source of truth).
#
# Usage: .\launch-full-stack.ps1
# Optional: set $env:BRIDGE_ROOT to use a different root (e.g. E:\AOE)

$ErrorActionPreference = "SilentlyContinue"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root     = if ($env:BRIDGE_ROOT) { $env:BRIDGE_ROOT.TrimEnd('\') } else { $repoRoot }
$apiBase  = "http://localhost:8000"

function Clear-Port($port) {
    $pids = (netstat -ano 2>$null | Select-String ":$port\s" | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Sort-Object -Unique | Where-Object { $_ -match '^\d+$' -and $_ -ne '0' })
    foreach ($p in $pids) {
        try { Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue } catch {}
    }
}

function Start-Service-Window($label, $command, $workDir) {
    Start-Process powershell -ArgumentList `
        "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -Command",
        "Set-Location '$workDir'; $command" | Out-Null
    Write-Host "  [start] $label" -ForegroundColor Green
}

function Wait-API($url, $maxSec = 60) {
    Write-Host ""
    Write-Host "Waiting for Bridge API..." -ForegroundColor Cyan
    $deadline = (Get-Date).AddSeconds($maxSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $checkUrl = $url -replace "localhost","127.0.0.1"
            $r = Invoke-RestMethod "$checkUrl/health" -TimeoutSec 2 -ErrorAction Stop
            if ($r.status -eq "ok" -and $r.service -eq "bridge-live-wall") {
                Write-Host "  Bridge API online (bridge-live-wall)" -ForegroundColor Green
                return $true
            }
        } catch {}
        Start-Sleep -Milliseconds 800
    }
    Write-Host "  Bridge API did not respond in ${maxSec}s - continuing anyway" -ForegroundColor Yellow
    return $false
}

function Register-Project($id, $label, $type, $baseUrl, $port, $health, $capabilities) {
    try {
        $body = @{
            id           = $id
            label        = $label
            type         = $type
            baseUrl      = $baseUrl
            port         = $port
            health       = $health
            capabilities = $capabilities
            status       = "online"
        } | ConvertTo-Json -Compress
        Invoke-RestMethod "$apiBase/api/projects/register" `
            -Method Post -Body $body -ContentType "application/json" `
            -TimeoutSec 5 -ErrorAction Stop | Out-Null
        Write-Host "  [registered] $label" -ForegroundColor DarkCyan
    } catch {
        Write-Host "  [skip register] $label - $($_.Exception.Message)" -ForegroundColor DarkGray
    }
}

# --- 1. Bridge API (starts first - everything else registers against it) -----
Write-Host ""
Write-Host "Bridge AI OS - Full Boot" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Clearing ports..." -ForegroundColor DarkGray
# Kill stale Python/Node processes that hold our ports
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node   -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Clear-Port 8000
Clear-Port 3030
Clear-Port 3001
Clear-Port 4201
Clear-Port 4202
Start-Sleep -Seconds 1
Write-Host ""
Write-Host "Services:" -ForegroundColor White

$backendScript = if (Test-Path "$root\run-backend.ps1") { "$root\run-backend.ps1" } else { "$repoRoot\run-backend.ps1" }
if (Test-Path $backendScript) {
    Start-Process powershell -ArgumentList `
        "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$backendScript`""
    Write-Host "  [start] Bridge API :8000  (run-backend.ps1)" -ForegroundColor Green
} else {
    Write-Host "  [skip] run-backend.ps1 not found" -ForegroundColor Yellow
}

# --- 2. Determinator Boot Agent :4201 ----------------------------------------
$detScript = "$repoRoot\scripts\serve-determinator-boot.ps1"
if (Test-Path $detScript) {
    Start-Process powershell -ArgumentList `
        "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$detScript`""
    Write-Host "  [start] Determinator :4201  (RBAC + System Map)" -ForegroundColor Green
} else {
    Write-Host "  [skip] serve-determinator-boot.ps1 not found" -ForegroundColor Yellow
}

# --- 3. Taurus Showcase :4202 -------------------------------------------------
$taurusScript   = "$repoRoot\scripts\serve-taurus-showcase.ps1"
$taurusServerJs = "$repoRoot\scripts\taurus-showcase-server.js"
if ((Test-Path $taurusScript) -and (Test-Path $taurusServerJs)) {
    Start-Process powershell -ArgumentList `
        "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$taurusScript`""
    Write-Host "  [start] Taurus :4202  (Gamification / Showcase)" -ForegroundColor Green
} else {
    Write-Host "  [skip] Taurus - script or server JS not found" -ForegroundColor Yellow
}

# --- 4. bridge-auth :3030 -----------------------------------------------------
$authDir = if (Test-Path "$root\bridge-auth") { "$root\bridge-auth" } else { "$repoRoot\bridge-auth" }
if (Test-Path $authDir) {
    Start-Service-Window "bridge-auth :3030" "npm run dev" $authDir
} else {
    Write-Host "  [skip] bridge-auth not found" -ForegroundColor Yellow
}

# --- 5. bridge-backend :3001 --------------------------------------------------
$backendDir = if (Test-Path "$root\bridge-backend") { "$root\bridge-backend" } else { "$repoRoot\bridge-backend" }
if (Test-Path $backendDir) {
    Start-Service-Window "bridge-backend :3001" "npm run dev" $backendDir
} else {
    Write-Host "  [skip] bridge-backend not found" -ForegroundColor Yellow
}

# --- 6. Frontend :3020 --------------------------------------------------------
$frontendDir = if (Test-Path "$root\frontend") { "$root\frontend" } else { "$repoRoot\frontend" }
if (Test-Path $frontendDir) {
    Start-Service-Window "Frontend :3020  (Digital Twin)" "npm run dev" $frontendDir
} else {
    Write-Host "  [skip] frontend not found" -ForegroundColor Yellow
}

# --- Wait for API then register all services ----------------------------------
$apiOnline = Wait-API $apiBase 40

if ($apiOnline) {
    Start-Sleep -Seconds 3
    Write-Host ""
    Write-Host "Registering services in project registry..." -ForegroundColor Cyan

    Register-Project "bridge-api"      "Bridge API"              "api"      "http://localhost:8000" 8000 "/health"  @("state","twins","marketplace","ubi","replication","speech","emotion","projects")
    Register-Project "bridge-frontend" "Digital Twin Frontend"   "frontend" "http://localhost:3020" 3020 $null      @("digital-twin","gateway","join","agents","executive-dashboard","docs")
    Register-Project "determinator"    "Determinator Boot Agent" "auth"     "http://localhost:4201" 4201 $null      @("rbac","system-map","login")
    Register-Project "bridge-auth"     "Bridge Auth"             "auth"     "http://localhost:3030" 3030 "/health"  @("siwe","jwt","redis-sessions")
    Register-Project "taurus"          "Taurus Showcase"         "service"  "http://localhost:4202" 4202 "/health"  @("gamification","showcase","security")
    if (Test-Path $backendDir) {
        Register-Project "bridge-backend" "Bridge Backend"       "service"  "http://localhost:3001" 3001 "/health"  @("sovereign-entry","siwe","sqlite-nonce")
    }
}

# --- Summary ------------------------------------------------------------------
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " Bridge AI OS - Live" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Bridge API      http://localhost:8000"
Write-Host "  API Docs        http://localhost:8000/docs"
Write-Host "  Frontend        http://localhost:3020"
Write-Host "  Gateway         http://localhost:3020/gateway/"
Write-Host "  Agents          http://localhost:3020/agents.html"
Write-Host "  Executive       http://localhost:3020/executive-dashboard.html"
Write-Host "  System Map      http://localhost:4201/system-map.html"
Write-Host "  Determinator    http://localhost:4201"
Write-Host "  Taurus          http://localhost:4202"
Write-Host "  bridge-auth     http://localhost:3030"
Write-Host "  bridge-backend  http://localhost:3001"
Write-Host ""
Write-Host "  Project Registry (single source of truth):" -ForegroundColor Cyan
Write-Host "  $apiBase/api/projects" -ForegroundColor White
Write-Host ""
Write-Host "  Production API  https://api.bridge-ai-os.tech"
Write-Host ""
if ($env:BRIDGE_ROOT) {
    Write-Host "  BRIDGE_ROOT=$env:BRIDGE_ROOT" -ForegroundColor DarkGray
}
Write-Host "=====================================================" -ForegroundColor Cyan
