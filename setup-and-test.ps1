# BridgeLiveWall — Setup & Run Tests
# Run in PowerShell. Installs Python if missing, then runs tests.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# Check for Python
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

$py = Get-PythonPath
if (-not $py) {
    Write-Host "Python not found. Installing via winget..." -ForegroundColor Yellow
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    Write-Host "Close and reopen this terminal, then run: .\setup-and-test.ps1" -ForegroundColor Cyan
    exit 0
}

# Add Python to PATH so 'python' works (Windows App Alias can override)
$pyDir = Split-Path -Parent $py
$pyScripts = Join-Path $pyDir "Scripts"
if ($pyDir -notin ($env:Path -split ';')) {
    $env:Path = "$pyDir;$pyScripts;" + $env:Path
}

Write-Host "Using Python: $py" -ForegroundColor Green
& $py -m pip install -r backend/app/requirements.txt -q
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "Running tests..." -ForegroundColor Green
$env:PYTHONPATH = Join-Path $projectRoot "backend"
& $py -m pytest tests/ -v
exit $LASTEXITCODE
