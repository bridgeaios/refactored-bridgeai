# Bridge AI OS - Unified Runbook
# Usage: .\bridge-runbook.ps1 <command> [options]
# Commands: install | deploy | audit | update | wallpaper

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Option = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Banner {
    Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║         Bridge AI OS - Unified Runbook                    ║
║         Type '.\bridge-runbook.ps1 help' for commands    ║
╚═══════════════════════════════════════════════════════════╝
"@
}

function cmd-install {
    Write-Host ">> Running full installation..." -ForegroundColor Cyan
    
    # Environment setup
    Write-Host "[1/4] Injecting environment..." -ForegroundColor Yellow
    & "$scriptDir\inject-env-from-aoe.ps1"
    
    # Keys setup  
    Write-Host "[2/4] Applying keys..." -ForegroundColor Yellow
    & "$scriptDir\apply-keys.ps1"
    
    # Startup services
    Write-Host "[3/4] Installing startup services..." -ForegroundColor Yellow
    & "$scriptDir\install-startup.ps1"
    
    # Sensors boot
    Write-Host "[4/4] Installing sensor boot..." -ForegroundColor Yellow
    & "$scriptDir\install-sensors-boot.ps1"
    
    Write-Host "✓ Installation complete!" -ForegroundColor Green
}

function cmd-deploy {
    Write-Host ">> Deploying full stack..." -ForegroundColor Cyan
    
    # Backend
    Write-Host "[1/4] Starting backend..." -ForegroundColor Yellow
    & "$scriptDir\run-backend.ps1"
    
    # Full loop
    Write-Host "[2/4] Running full build/deploy loop..." -ForegroundColor Yellow
    & "$scriptDir\run-full-install-build-deploy.ps1"
    
    # Live wallpaper
    Write-Host "[3/4] Starting live wallpaper..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptDir\run-wallpaper-live.ps1`""
    
    Write-Host "✓ Deployment complete!" -ForegroundColor Green
}

function cmd-audit {
    Write-Host ">> Running full audit..." -ForegroundColor Cyan
    & "$scriptDir\audit-wall.ps1"
}

function cmd-update {
    Write-Host ">> Updating wallpaper..." -ForegroundColor Cyan
    & "$scriptDir\update.ps1"
}

function cmd-wallpaper {
    Write-Host ">> Starting live wallpaper (background)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptDir\run-wallpaper-live.ps1`""
    Write-Host "✓ Wallpaper started in background" -ForegroundColor Green
}

function cmd-help {
    Write-Banner
    Write-Host @"

USAGE:
    .\bridge-runbook.ps1 <command>

COMMANDS:
    install     Full system installation (env, keys, startup, sensors)
    deploy      Deploy full stack (backend + build + wallpaper)
    audit       Run full system audit
    update      Update wallpaper once
    wallpaper   Start live wallpaper (background)
    help        Show this help

ALIASES:
    .\bridge-runbook.ps1 i      → install
    .\bridge-runbook.ps1 d      → deploy  
    .\bridge-runbook.ps1 a      → audit
    .\bridge-runbook.ps1 u      → update
    .\bridge-runbook.ps1 w      → wallpaper

EXAMPLES:
    .\bridge-runbook.ps1 install
    .\bridge-runbook.ps1 deploy
    .\bridge-runbook.ps1 audit
    .\bridge-runbook.ps1 update

"@
}

function cmd-version {
    Write-Host "Bridge Runbook v1.0.0" -ForegroundColor Cyan
    Write-Host "Last updated: $(Get-Date -Format 'yyyy-MM-dd')" -ForegroundColor Gray
}

# Command router
switch ($Command.ToLower()) {
    "i"           { cmd-install }
    "install"     { cmd-install }
    "d"           { cmd-deploy }
    "deploy"      { cmd-deploy }
    "a"           { cmd-audit }
    "audit"       { cmd-audit }
    "u"           { cmd-update }
    "update"      { cmd-update }
    "w"           { cmd-wallpaper }
    "wallpaper"   { cmd-wallpaper }
    "v"           { cmd-version }
    "version"     { cmd-version }
    "h"           { cmd-help }
    "help"        { cmd-help }
    ""            { cmd-help }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Type '.\bridge-runbook.ps1 help' for available commands" -ForegroundColor Yellow
        exit 1
    }
}
