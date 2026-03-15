# Bridge AI OS — One-shot full stack launcher
# Brings API, backend, auth, and frontend online. Only starts services whose paths exist.
# Usage: .\launch-full-stack.ps1
# Set BRIDGE_ROOT (e.g. E:\AOE) to use another root; missing folders under that root are skipped.

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = if ($env:BRIDGE_ROOT) { $env:BRIDGE_ROOT.TrimEnd('\') } else { $repoRoot }

# Bridge API (run-backend.ps1)
$backendScript = if (Test-Path "$root\run-backend.ps1") { "$root\run-backend.ps1" } else { "$repoRoot\run-backend.ps1" }
if (Test-Path $backendScript) {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Minimized -File `"$backendScript`""
    Write-Host "Started: Bridge API (run-backend.ps1)" -ForegroundColor Green
} else {
    Write-Host "Skip: run-backend.ps1 not found under $root or $repoRoot" -ForegroundColor Yellow
}

# bridge-backend
$backendDir = if (Test-Path "$root\bridge-backend") { "$root\bridge-backend" } else { "$repoRoot\bridge-backend" }
if (Test-Path $backendDir) {
    Start-Process powershell -ArgumentList "-NoProfile -WindowStyle Minimized -Command", "Set-Location `"$backendDir`"; npm run dev"
    Write-Host "Started: bridge-backend" -ForegroundColor Green
} else {
    Write-Host "Skip: bridge-backend not found (no $root\bridge-backend or $repoRoot\bridge-backend)" -ForegroundColor Yellow
}

# bridge-auth
$authDir = if (Test-Path "$root\bridge-auth") { "$root\bridge-auth" } else { "$repoRoot\bridge-auth" }
if (Test-Path $authDir) {
    Start-Process powershell -ArgumentList "-NoProfile -WindowStyle Minimized -Command", "Set-Location `"$authDir`"; npm run dev"
    Write-Host "Started: bridge-auth" -ForegroundColor Green
} else {
    Write-Host "Skip: bridge-auth not found (no $root\bridge-auth or $repoRoot\bridge-auth)" -ForegroundColor Yellow
}

# frontend
$frontendDir = if (Test-Path "$root\frontend") { "$root\frontend" } else { "$repoRoot\frontend" }
if (Test-Path $frontendDir) {
    Start-Process powershell -ArgumentList "-NoProfile -WindowStyle Minimized -Command", "Set-Location `"$frontendDir`"; npm run dev"
    Write-Host "Started: frontend" -ForegroundColor Green
} else {
    Write-Host "Skip: frontend not found (no $root\frontend or $repoRoot\frontend)" -ForegroundColor Yellow
}

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Bridge AI OS stack launching..." -ForegroundColor Cyan
Write-Host ""
Write-Host "API        -> http://localhost:8000"
Write-Host "Backend    -> http://localhost:3001"
Write-Host "Auth       -> http://localhost:3030"
Write-Host "Frontend   -> http://localhost:3020 (or 3021 if 3020 in use)"
Write-Host "Dashboard  -> http://localhost:3000"
Write-Host "Worker     -> https://api.bridge-ai-os.tech"
Write-Host ""
if ($env:BRIDGE_ROOT) {
    Write-Host "BRIDGE_ROOT=$env:BRIDGE_ROOT (missing components skipped or use repo: $repoRoot)" -ForegroundColor Gray
} else {
    Write-Host "Set BRIDGE_ROOT (e.g. E:\AOE) if stack lives outside this repo." -ForegroundColor Gray
}
