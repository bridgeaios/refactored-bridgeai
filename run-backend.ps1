# BridgeLiveWall - Run Backend API
# Starts uvicorn on http://localhost:8000. Install deps first: .\setup-and-test.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# Optional: verify repo state before starting (enforced in CI / production).
# Generated files (audit-results.json, twin_wall.png) are excluded so audit/wallpaper runs don't cause mismatch.
# If you see "State mutation detected", approve once: node tools/state/verify.cjs --approve
try {
    $node = (Get-Command node -ErrorAction SilentlyContinue).Source
    if ($node) {
        & $node (Join-Path $projectRoot "tools\state\verify.cjs") 2>&1 | Write-Host
        if ($LASTEXITCODE -eq 2) { Write-Host "State enforced and root mismatch. Approve with: node tools/state/verify.cjs --approve" -ForegroundColor Red; exit 2 }
    }
} catch {
    Write-Host "State verifier warning: $($_.Exception.Message)" -ForegroundColor Yellow
}

$pyPaths = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312",
    "$env:LOCALAPPDATA\Programs\Python\Python311",
    "$env:USERPROFILE\AppData\Local\Programs\Python\Python312",
    "$env:USERPROFILE\AppData\Local\Programs\Python\Python311"
)
$pyExe = $null
foreach ($dir in $pyPaths) {
    if (Test-Path "$dir\python.exe") { $pyExe = "$dir\python.exe"; break }
}
if (-not $pyExe) { $pyExe = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $pyExe) {
    Write-Host "Python not found. Run .\setup-and-test.ps1 first." -ForegroundColor Red
    exit 1
}

$pyDir = Split-Path -Parent $pyExe
$pyScripts = Join-Path (Split-Path -Parent $pyExe) "Scripts"
if ($pyDir -notin ($env:Path -split ';')) { $env:Path = "$pyDir;$pyScripts;" + $env:Path }
$env:PYTHONPATH = $projectRoot

$reloadEnabled = @('1','true','yes','on') -contains (([string]$env:BRIDGE_BACKEND_RELOAD).ToLower())
$appTarget = 'backend.app.main:app'
$appDir = $projectRoot

Write-Host "Starting Bridge AI OS API at http://localhost:8000" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "ASGI app: $appTarget" -ForegroundColor DarkGray

$uvicornArgs = @('-m','uvicorn',$appTarget,'--host','0.0.0.0','--port','8000','--app-dir',$appDir)
if ($reloadEnabled) {
    $uvicornArgs += @('--reload','--reload-dir',(Join-Path $projectRoot 'backend'))
    Write-Host "Reload: enabled" -ForegroundColor DarkGray
} else {
    Write-Host "Reload: disabled" -ForegroundColor DarkGray
}

& $pyExe @uvicornArgs
