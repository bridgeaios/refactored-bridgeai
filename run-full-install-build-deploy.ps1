# Full run: Install -> Build -> Debug -> Deploy with full log and goal=task alignment.
# Usage: .\run-full-install-build-deploy.ps1 [-SkipDeploy] [-ApproveStateOnce]
# Log: logs/full-install-build-deploy.log  Goals: data/goals-tasks.json

param(
    [switch] $SkipDeploy,
    [switch] $ApproveStateOnce
)

$ErrorActionPreference = "Continue"
$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "full-install-build-deploy.log"
$goalsPath = Join-Path $projectRoot "data\goals-tasks.json"
$auditPath = Join-Path $projectRoot "audit-results.json"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log { param($msg) $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; $line = "[$ts] $msg"; Write-Host $line; Add-Content -Path $logFile -Value $line -Encoding UTF8 }
function Get-AuditCritical { if (-not (Test-Path $auditPath)) { return -1 }; try { $j = Get-Content $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json; return [int]$j.summary.criticalCount } catch { return -1 } }

Set-Location $projectRoot
Write-Log "=== FULL RUN START (goal = task = goal) ==="

# --- Goal 1: Install ---
Write-Log "=== GOAL: Install all ==="
& (Join-Path $projectRoot "install-all.ps1") 2>&1 | ForEach-Object { Write-Log $_ }
$installOk = $LASTEXITCODE -eq 0
Write-Log "Install result: $(if ($installOk) { 'OK' } else { 'FAIL' })"

# --- Goal 2: Build (frontend + state verify) ---
Write-Log "=== GOAL: Build frontend ==="
$feDir = Join-Path $projectRoot "frontend"
$buildOk = $true
if (Test-Path (Join-Path $feDir "package.json")) {
    Push-Location $feDir
    & npm run build 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { $buildOk = $false }
    Pop-Location
} else {
    Write-Log "Frontend not found; skip build."
}
Write-Log "Build result: $(if ($buildOk) { 'OK' } else { 'FAIL' })"

# --- Goal 3 & 4: Audit + Apply ---
Write-Log "=== GOAL: Audit + Apply ==="
& (Join-Path $projectRoot "audit-wall.ps1") 2>&1 | Out-Null
$critical = Get-AuditCritical
Write-Log "Audit critical count: $critical"
if ($critical -gt 0) {
    & (Join-Path $projectRoot "apply-keys.ps1") 2>&1 | ForEach-Object { Write-Log $_ }
    & (Join-Path $projectRoot "audit-wall.ps1") 2>&1 | Out-Null
    $critical = Get-AuditCritical
    Write-Log "After apply, critical: $critical"
}
$ensurePath = Join-Path $projectRoot "scripts\ensure-optional-paths.ps1"
if (Test-Path $ensurePath) { & $ensurePath 2>&1 | Out-Null }
$auditOk = $critical -eq 0

# --- Goal 5: Debug (state verify + pytest) ---
Write-Log "=== GOAL: Debug (state verify + pytest) ==="
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
$stateOk = $true
$testsOk = $true

if ($node) {
    $verifyScript = Join-Path $projectRoot "tools\state\verify.cjs"
    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath $node -ArgumentList "`"$verifyScript`"" -WorkingDirectory $projectRoot -Wait -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
        Get-Content $tmpOut, $tmpErr -ErrorAction SilentlyContinue | ForEach-Object { Write-Log $_ }
        if ($proc.ExitCode -eq 2) {
            if ($ApproveStateOnce) {
                Write-Log "Approving state once..."
                $proc2 = Start-Process -FilePath $node -ArgumentList "`"$verifyScript`"", "--approve" -WorkingDirectory $projectRoot -Wait -NoNewWindow -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
                Get-Content $tmpOut, $tmpErr -ErrorAction SilentlyContinue | ForEach-Object { Write-Log $_ }
            } else {
                $stateOk = $false
            }
        }
    } finally { Remove-Item $tmpOut, $tmpErr -Force -ErrorAction SilentlyContinue }
} else { Write-Log "Node not found; skip state verify." }

if ($py) {
    $env:PYTHONPATH = Join-Path $projectRoot "backend"
    & $py -m pytest (Join-Path $projectRoot "tests") -v --tb=short 2>&1 | ForEach-Object { Write-Log $_ }
    if ($LASTEXITCODE -ne 0) { $testsOk = $false }
} else { Write-Log "Python not found; skip pytest." }

Write-Log "State verify: $(if ($stateOk) { 'OK' } else { 'FAIL' }); Pytest: $(if ($testsOk) { 'OK' } else { 'FAIL' })"

# --- Goal 6: Deploy ---
$deployOk = $true
if (-not $SkipDeploy) {
    Write-Log "=== GOAL: Deploy (Worker) ==="
    $workerDir = Join-Path $projectRoot "worker"
    if (Test-Path (Join-Path $workerDir "wrangler.toml")) {
        Push-Location $workerDir
        $ErrorActionPreference = "Continue"
        $deployOut = & npx wrangler deploy 2>&1
        $deployOut | ForEach-Object { Write-Log $_ }
        if ($deployOut -notmatch "Deployed|Uploaded") { $deployOk = $false }
        Pop-Location
    } else {
        Write-Log "Worker wrangler.toml not found; skip deploy."
    }
    Write-Log "Deploy result: $(if ($deployOk) { 'OK' } else { 'CHECK' })"
} else {
    Write-Log "Skip deploy ( -SkipDeploy )."
}

# --- Summary + goals update ---
$allOk = $installOk -and $buildOk -and $auditOk -and $stateOk -and $testsOk -and ($SkipDeploy -or $deployOk)
Write-Log "=== FULL RUN END ==="
Write-Log "Result: $(if ($allOk) { 'ALL OK' } else { 'SOME FAIL' }) | Install=$installOk Build=$buildOk Audit=$auditOk State=$stateOk Tests=$testsOk Deploy=$deployOk"
Write-Log "Log: $logFile | Goals: $goalsPath"

# Update goals-tasks lastRun
if (Test-Path $goalsPath) {
    try {
        $goals = Get-Content $goalsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $goals.updatedAt = (Get-Date -Format "o")
        $goals.lastRun = @{
            at = (Get-Date -Format "o")
            installOk = $installOk
            buildOk = $buildOk
            auditOk = $auditOk
            stateOk = $stateOk
            testsOk = $testsOk
            deployOk = $deployOk
            allOk = $allOk
            logFile = $logFile
        }
        $goals | ConvertTo-Json -Depth 5 | Set-Content -Path $goalsPath -Encoding UTF8
    } catch { }
}

if ($allOk) { exit 0 }
exit 1
