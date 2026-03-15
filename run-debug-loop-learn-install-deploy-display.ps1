# Debug -> Loop (audit/fix) -> Learn -> Install -> Deploy -> Display
# One pipeline: verify state + pytest, then audit loop, learn (goals/tasks), install, deploy, then show display URLs.
# Usage: .\run-debug-loop-learn-install-deploy-display.ps1 [-SkipDeploy] [-SkipDisplay] [-ApproveStateOnce]

param(
    [switch] $SkipDeploy,
    [switch] $SkipDisplay,
    [switch] $ApproveStateOnce,
    [int] $MaxLoopRounds = 3
)

$ErrorActionPreference = "Continue"
$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$auditPath = Join-Path $projectRoot "audit-results.json"
$goalsPath = Join-Path $projectRoot "data\goals-tasks.json"
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    foreach ($p in @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe")) {
        if (Test-Path $p) { $py = $p; break }
    }
}

Set-Location $projectRoot

function Get-Critical {
    if (-not (Test-Path $auditPath)) { return -1 }
    try { return [int](Get-Content $auditPath -Raw | ConvertFrom-Json).summary.criticalCount } catch { return -1 }
}

# --- DEBUG ---
Write-Host "`n=== DEBUG ===" -ForegroundColor Magenta
$stateOk = $true
if ($node) {
    $v = Join-Path $projectRoot "tools\state\verify.cjs"
    $t1 = [System.IO.Path]::GetTempFileName()
    $t2 = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath $node -ArgumentList "`"$v`"" -WorkingDirectory $projectRoot -Wait -NoNewWindow -PassThru -RedirectStandardOutput $t1 -RedirectStandardError $t2
        Get-Content $t1, $t2 -ErrorAction SilentlyContinue | Write-Host
        if ($proc.ExitCode -eq 2 -and $ApproveStateOnce) {
            Start-Process -FilePath $node -ArgumentList "`"$v`"", "--approve" -WorkingDirectory $projectRoot -Wait -NoNewWindow -RedirectStandardOutput $t1 -RedirectStandardError $t2 | Out-Null
        } elseif ($proc.ExitCode -eq 2) { $stateOk = $false }
    } finally { Remove-Item $t1, $t2 -Force -ErrorAction SilentlyContinue }
}
$testsOk = $true
if ($py) {
    $env:PYTHONPATH = Join-Path $projectRoot "backend"
    & $py -m pytest (Join-Path $projectRoot "tests") -v --tb=short 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) { $testsOk = $false }
}
Write-Host "Debug: state=$stateOk tests=$testsOk" -ForegroundColor $(if ($stateOk -and $testsOk) { "Green" } else { "Yellow" })

# --- LOOP (audit -> fix -> re-audit) ---
Write-Host "`n=== LOOP (audit/fix until 0 critical or $MaxLoopRounds rounds) ===" -ForegroundColor Magenta
$r = 0
do {
    $r++
    & (Join-Path $projectRoot "audit-wall.ps1") 2>&1 | Out-Null
    $c = Get-Critical
    Write-Host "Round $r critical=$c" -ForegroundColor Cyan
    if ($c -eq 0) { break }
    if (Test-Path "E:\AOE\.env") { & (Join-Path $projectRoot "inject-env-from-aoe.ps1") 2>&1 | Out-Null }
    & (Join-Path $projectRoot "apply-keys.ps1") 2>&1 | Out-Null
} while ($c -gt 0 -and $r -lt $MaxLoopRounds)
$auditOk = (Get-Critical) -eq 0

# --- LEARN (update goals/tasks, ensure paths) ---
Write-Host "`n=== LEARN ===" -ForegroundColor Magenta
$ensurePath = Join-Path $projectRoot "scripts\ensure-optional-paths.ps1"
if (Test-Path $ensurePath) { & $ensurePath 2>&1 | Out-Null }
if (Test-Path $goalsPath) {
    try {
        $g = Get-Content $goalsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $g.updatedAt = (Get-Date -Format "o")
        $g.lastRun = @{ at = (Get-Date -Format "o"); debug = @{ stateOk = $stateOk; testsOk = $testsOk }; auditOk = $auditOk }
        $g | ConvertTo-Json -Depth 5 | Set-Content -Path $goalsPath -Encoding UTF8
    } catch { }
}
Write-Host "Goals/tasks updated; optional paths ensured." -ForegroundColor Green

# --- INSTALL ---
Write-Host "`n=== INSTALL ===" -ForegroundColor Magenta
& (Join-Path $projectRoot "install-all.ps1") 2>&1 | Write-Host
$installOk = $LASTEXITCODE -eq 0

# --- DEPLOY ---
$deployOk = $true
if (-not $SkipDeploy) {
    Write-Host "`n=== DEPLOY ===" -ForegroundColor Magenta
    $workerDir = Join-Path $projectRoot "worker"
    if (Test-Path (Join-Path $workerDir "wrangler.toml")) {
        Push-Location $workerDir
        $out = & npx wrangler deploy 2>&1
        $out | Write-Host
        if ($out -notmatch "Deployed|Uploaded") { $deployOk = $false }
        Pop-Location
    }
} else { Write-Host "`n=== DEPLOY (skipped) ===" -ForegroundColor Gray }

# --- DISPLAY ---
Write-Host "`n=== DISPLAY ===" -ForegroundColor Magenta
$urls = @(
    "Frontend    http://localhost:3020/",
    "Dashboard   http://localhost:3000/",
    "Bridge API  http://localhost:8000/",
    "Live report http://localhost:8000/api/live/report",
    "Taurus      http://localhost:4202/",
    "Worker      https://api.bridge-ai-os.tech"
)
foreach ($u in $urls) { Write-Host $u -ForegroundColor Cyan }
if (-not $SkipDisplay) {
    $open = $null
    if (Get-Command Start-Process -ErrorAction SilentlyContinue) {
        try {
            Start-Process "http://localhost:3020/"
        } catch { }
    }
}
Write-Host "`nDone. Debug=$stateOk,$testsOk Loop=$auditOk Install=$installOk Deploy=$deployOk" -ForegroundColor Green
