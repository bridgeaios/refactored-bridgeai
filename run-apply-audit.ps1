# Run audit, then apply (inject from AOE + apply-keys + optional paths).
# Use this for "run apply audit" without full install/boot/tests.
# Usage: .\run-apply-audit.ps1 [-MaxRounds 2]

param([int] $MaxRounds = 2)

$ErrorActionPreference = "Continue"
$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $projectRoot

$auditPath = Join-Path $projectRoot "audit-results.json"

function Get-AuditCriticalCount {
    if (-not (Test-Path $auditPath)) { return -1 }
    try {
        $j = Get-Content $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json
        return [int]$j.summary.criticalCount
    } catch { return -1 }
}

# --- 1. Audit ---
Write-Host "=== Audit ===" -ForegroundColor Cyan
& (Join-Path $projectRoot "audit-wall.ps1") 2>&1 | Out-Null
$critical = Get-AuditCriticalCount
if ($critical -eq -1) {
    Write-Host "Audit did not produce audit-results.json." -ForegroundColor Red
    exit 1
}
$summary = $null
if (Test-Path $auditPath) {
    try {
        $summary = Get-Content $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { }
}
Write-Host "OK: $($summary.summary.okCount) | Critical: $($summary.summary.criticalCount) | Recommendations: $($summary.summary.recCount)" -ForegroundColor $(if ($critical -eq 0) { "Green" } else { "Yellow" })

# --- 2. Fix loop (inject + apply) if critical ---
$round = 0
while ($critical -gt 0 -and $round -lt $MaxRounds) {
    $round++
    Write-Host "`n=== Apply (round $round) ===" -ForegroundColor Cyan
    if (Test-Path "E:\AOE\.env") { & (Join-Path $projectRoot "inject-env-from-aoe.ps1") 2>&1 | Out-Null }
    if (Test-Path "E:\AOE\v1\.env") { & (Join-Path $projectRoot "inject-env-from-aoe.ps1") 2>&1 | Out-Null }
    & (Join-Path $projectRoot "apply-keys.ps1") 2>&1 | Write-Host
    & (Join-Path $projectRoot "audit-wall.ps1") 2>&1 | Out-Null
    $critical = Get-AuditCriticalCount
    Write-Host "After apply: Critical = $critical" -ForegroundColor $(if ($critical -eq 0) { "Green" } else { "Yellow" })
}

# --- 3. Always apply once (ensure .env exists) ---
Write-Host "`n=== Apply keys (ensure .env) ===" -ForegroundColor Cyan
& (Join-Path $projectRoot "apply-keys.ps1") 2>&1 | Write-Host

# --- 4. Optional paths ---
$ensurePaths = Join-Path $projectRoot "scripts\ensure-optional-paths.ps1"
if (Test-Path $ensurePaths) {
    & $ensurePaths 2>&1 | Out-Null
    Write-Host "Optional paths ensured (D:\BridgeAI\... if D: exists)." -ForegroundColor Gray
}

Write-Host "`nDone. Audit results: $auditPath" -ForegroundColor Green
if ((Get-AuditCriticalCount) -eq 0) {
    exit 0
}
exit 1
