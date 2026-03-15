# BridgeLiveWall — Read .env1 and apply into repo .env
# Source: repo\.env1, then E:\AOE\.env1. Run from repo root.

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoEnv = Join-Path $scriptRoot ".env"
$env1Repo = Join-Path $scriptRoot ".env1"
$env1Aoe = "E:\AOE\.env1"

$sourcePath = $null
if (Test-Path $env1Repo) { $sourcePath = $env1Repo }
elseif (Test-Path $env1Aoe) { $sourcePath = $env1Aoe }

if (-not $sourcePath) {
    Write-Host ".env1 not found in repo or E:\AOE. Creating $env1Repo from .env.example..." -ForegroundColor Yellow
    $example = Join-Path $scriptRoot ".env.example"
    if (Test-Path $example) {
        Copy-Item $example $env1Repo
        Write-Host "Created .env1. Edit .env1 then run .\apply-env1.ps1 again." -ForegroundColor Cyan
        exit 0
    }
    Write-Host "No .env.example to copy. Create .env1 with KEY=VALUE lines and run again." -ForegroundColor Red
    exit 1
}

function Parse-EnvFile($path) {
    $vars = @{}
    $lines = Get-Content $path -Encoding UTF8 -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        $line = $line.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { continue }
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            $vars[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
        }
    }
    return $vars
}

function Write-EnvFile($path, $vars) {
    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine("# Applied from .env1. Edit .env1 to change.")
    [void]$sb.AppendLine("# See KEYS-REQUIRED.md. Do not commit real secrets.")
    [void]$sb.AppendLine("")
    foreach ($k in ($vars.Keys | Sort-Object)) {
        $v = $vars[$k]
        if ($v -match '\s|#') { $v = "`"$v`"" }
        [void]$sb.AppendLine("$k=$v")
    }
    [System.IO.File]::WriteAllText($path, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
}

$fromEnv1 = Parse-EnvFile $sourcePath
if ($fromEnv1.Count -eq 0) {
    Write-Host "No KEY=VALUE lines in $sourcePath. Add keys there first." -ForegroundColor Yellow
    exit 1
}

$merged = @{}
if (Test-Path $repoEnv) { $merged = Parse-EnvFile $repoEnv }
foreach ($k in $fromEnv1.Keys) { $merged[$k] = $fromEnv1[$k] }

Write-EnvFile $repoEnv $merged
Write-Host "Applied $($fromEnv1.Count) env vars from $sourcePath into $repoEnv" -ForegroundColor Green
Write-Host "Run .\audit-wall.ps1 or .\run-backend.ps1" -ForegroundColor Cyan
