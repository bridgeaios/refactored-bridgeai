# BridgeLiveWall — Install → Add to boot → Audit → Fix → Apply → Verify (loop until match)
# Usage: .\run-full-loop.ps1 [-MaxAuditRounds 3] [-ApproveStateOnce]
# Exits 0 when audit critical=0, state verify ok, and tests pass.

param(
    [int] $MaxAuditRounds = 3,
    [switch] $ApproveStateOnce,
    [switch] $SkipInstall,
    [switch] $SkipBoot
)

$ErrorActionPreference = "Stop"
$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $projectRoot

$auditPath = Join-Path $projectRoot "audit-results.json"
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    $pyPaths = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe")
    foreach ($p in $pyPaths) { if (Test-Path $p) { $py = $p; break } }
}

function Get-AuditCriticalCount {
    if (-not (Test-Path $auditPath)) { return -1 }
    try {
        $j = Get-Content $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json
        return [int]$j.summary.criticalCount
    } catch { return -1 }
}

# --- 1. Install all ---
if (-not $SkipInstall) {
    Write-Host "=== 1. Install all ===" -ForegroundColor Magenta
    & (Join-Path $projectRoot "install-all.ps1")
    if ($LASTEXITCODE -ne 0) { Write-Host "Install failed." -ForegroundColor Red; exit 1 }
}

# --- 2. Add to boot ---
if (-not $SkipBoot) {
    Write-Host "`n=== 2. Add to boot ===" -ForegroundColor Magenta
    & (Join-Path $projectRoot "install-startup.ps1")
    if ($LASTEXITCODE -ne 0) { Write-Host "Install-startup failed." -ForegroundColor Red; exit 1 }
}

# --- 3. Audit → Fix (apply-keys) → re-Audit until critical=0 or max rounds ---
Write-Host "`n=== 3. Audit → Fix → Apply (loop until match) ===" -ForegroundColor Magenta
$round = 0
do {
    $round++
    Write-Host "Audit round $round of $MaxAuditRounds..." -ForegroundColor Cyan
    & (Join-Path $projectRoot "audit-wall.ps1") 2>&1 | Out-Null
    $critical = Get-AuditCriticalCount
    if ($critical -eq -1) {
        Write-Host "Audit did not produce audit-results.json." -ForegroundColor Red
        exit 1
    }
    if ($critical -eq 0) {
        Write-Host "Audit OK: 0 critical." -ForegroundColor Green
        break
    }
    Write-Host "Audit: $critical critical. Injecting env from E:\AOE (digital twin) if present, then apply-keys..." -ForegroundColor Yellow
    if (Test-Path "E:\AOE\.env") { & (Join-Path $projectRoot "inject-env-from-aoe.ps1") 2>&1 | Out-Null }
    elseif (Test-Path "E:\AOE\v1\.env") { & (Join-Path $projectRoot "inject-env-from-aoe.ps1") 2>&1 | Out-Null }
    & (Join-Path $projectRoot "apply-keys.ps1") 2>&1 | Out-Null
    if ($round -ge $MaxAuditRounds) {
        Write-Host "Max rounds reached. Critical issues may require manual .env edits. See audit-results.json." -ForegroundColor Yellow
        break
    }
} while ($critical -gt 0)

# --- 4. Inject from E:\AOE (digital twin) + Apply ---
Write-Host "`n=== 4. Inject from E:\AOE + Apply ===" -ForegroundColor Magenta
if ((Test-Path "E:\AOE\.env") -or (Test-Path "E:\AOE\v1\.env")) {
    & (Join-Path $projectRoot "inject-env-from-aoe.ps1") 2>&1 | Write-Host
}
& (Join-Path $projectRoot "apply-keys.ps1") 2>&1 | Write-Host
$ensurePaths = Join-Path $projectRoot "scripts\ensure-optional-paths.ps1"
if (Test-Path $ensurePaths) { & $ensurePaths 2>&1 | Out-Null }

# --- 5. State verify ---
Write-Host "`n=== 5. State verify ===" -ForegroundColor Magenta
$stateOk = $true
if ($node) {
    $verifyScript = Join-Path $projectRoot "tools\state\verify.cjs"
    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath $node -ArgumentList "`"$verifyScript`"" -WorkingDirectory $projectRoot -Wait -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
        $verifyExit = $proc.ExitCode
        Get-Content $tmpOut, $tmpErr -ErrorAction SilentlyContinue | Write-Host
        if ($verifyExit -eq 2) {
            if ($ApproveStateOnce) {
                Write-Host "Approving state once..." -ForegroundColor Cyan
                $proc2 = Start-Process -FilePath $node -ArgumentList "`"$verifyScript`"", "--approve" -WorkingDirectory $projectRoot -Wait -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
                Get-Content $tmpOut, $tmpErr -ErrorAction SilentlyContinue | Write-Host
                if ($proc2.ExitCode -eq 0) {
                    $proc3 = Start-Process -FilePath $node -ArgumentList "`"$verifyScript`"" -WorkingDirectory $projectRoot -Wait -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
                    Get-Content $tmpOut, $tmpErr -ErrorAction SilentlyContinue | Write-Host
                    if ($proc3.ExitCode -eq 2) { $stateOk = $false }
                } else { $stateOk = $false }
            } else {
                Write-Host "State mismatch. Rerun with -ApproveStateOnce to approve, or: node tools/state/verify.cjs --approve" -ForegroundColor Yellow
                $stateOk = $false
            }
        }
    } finally {
        Remove-Item $tmpOut, $tmpErr -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Node not found; skipping state verify." -ForegroundColor Yellow
}

# --- 6. Tests ---
Write-Host "`n=== 6. Tests (pytest) ===" -ForegroundColor Magenta
$testsOk = $true
if ($py) {
    $env:PYTHONPATH = Join-Path $projectRoot "backend"
    & $py -m pytest (Join-Path $projectRoot "tests") -v --tb=short 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) { $testsOk = $false }
} else {
    Write-Host "Python not found; skipping tests." -ForegroundColor Yellow
}

# --- Result ---
$critFinal = Get-AuditCriticalCount
$allOk = ($critFinal -eq 0) -and $stateOk -and $testsOk
if ($allOk) {
    Write-Host "`nAll OK: audit 0 critical, state verify pass, tests pass." -ForegroundColor Green
    exit 0
}
Write-Host "`nNot fully OK: audit critical=$critFinal, stateOk=$stateOk, testsOk=$testsOk" -ForegroundColor Yellow
exit 1
