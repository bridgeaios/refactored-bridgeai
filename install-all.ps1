# BridgeLiveWall — Install all dependencies (Python backend + Node bridge-backend + optional frontend)
# Run before first use or after pull. Used by run-full-loop.ps1.

$ErrorActionPreference = "Stop"
$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $projectRoot

function Get-PythonPath {
    $paths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe",
        "$env:USERPROFILE\miniconda3\python.exe",
        "$env:USERPROFILE\anaconda3\python.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    $found = Get-Command python -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    return $null
}

$failed = $false

# 1. Python backend
$py = Get-PythonPath
if (-not $py) {
    Write-Host "Python not found. Install Python 3.12 (e.g. winget install Python.Python.3.12) then re-run." -ForegroundColor Red
    exit 1
}
$reqPath = Join-Path $projectRoot "backend\app\requirements.txt"
if (Test-Path $reqPath) {
    Write-Host "Installing Python backend deps..." -ForegroundColor Cyan
    & $py -m pip install -r $reqPath -q
    if ($LASTEXITCODE -ne 0) { $failed = $true }
} else {
    Write-Host "backend\app\requirements.txt not found; skipping pip install." -ForegroundColor Yellow
}

# 2. bridge-backend (Node)
$bbPath = Join-Path $projectRoot "bridge-backend\package.json"
if (Test-Path $bbPath) {
    Write-Host "Installing bridge-backend (npm)..." -ForegroundColor Cyan
    Push-Location (Join-Path $projectRoot "bridge-backend")
    npm install 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
} else {
    Write-Host "bridge-backend\package.json not found; skipping." -ForegroundColor Yellow
}

# 3. Optional frontend
$fePath = Join-Path $projectRoot "frontend\package.json"
if (Test-Path $fePath) {
    Write-Host "Installing frontend (npm)..." -ForegroundColor Cyan
    Push-Location (Join-Path $projectRoot "frontend")
    npm install 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
}

if ($failed) {
    Write-Host "One or more install steps failed." -ForegroundColor Red
    exit 1
}
Write-Host "Install all done." -ForegroundColor Green
