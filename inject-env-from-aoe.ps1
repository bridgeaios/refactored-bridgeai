# BridgeLiveWall — Get digital twin env from E:\AOE and inject into repo .env
# Use when your canonical keys live in E:\AOE\.env (or E:\AOE\v1\.env). Run from repo root.

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoEnv = Join-Path $scriptRoot ".env"
$aoeEnv = "E:\AOE\.env"
$v1Env = "E:\AOE\v1\.env"

# Source: prefer E:\AOE\.env, then E:\AOE\v1\.env
$sourcePath = $null
if (Test-Path $aoeEnv) { $sourcePath = $aoeEnv }
elseif (Test-Path $v1Env) { $sourcePath = $v1Env }

if (-not $sourcePath) {
    Write-Host "E:\AOE\.env and E:\AOE\v1\.env not found. Create one and add your keys." -ForegroundColor Red
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
    [void]$sb.AppendLine("# Injected from E:\AOE (digital twin). Edit E:\AOE\.env to change.")
    [void]$sb.AppendLine("# See KEYS-REQUIRED.md. Do not commit real secrets.")
    [void]$sb.AppendLine("")
    foreach ($k in ($vars.Keys | Sort-Object)) {
        $v = $vars[$k]
        if ($v -match '\s|#') { $v = "`"$v`"" }
        [void]$sb.AppendLine("$k=$v")
    }
    [System.IO.File]::WriteAllText($path, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
}

$twin = Parse-EnvFile $sourcePath
if ($twin.Count -eq 0) {
    Write-Host "No KEY=VALUE lines in $sourcePath. Add keys there first." -ForegroundColor Yellow
    exit 1
}

# Merge: start from repo .env if present, then overlay AOE (AOE wins)
$merged = @{}
if (Test-Path $repoEnv) {
    $merged = Parse-EnvFile $repoEnv
}
foreach ($k in $twin.Keys) {
    $merged[$k] = $twin[$k]
}

Write-EnvFile $repoEnv $merged
Write-Host "Injected $($twin.Count) env vars from $sourcePath into $repoEnv" -ForegroundColor Green
Write-Host "Run .\audit-wall.ps1 to verify, or start backend: .\run-backend.ps1" -ForegroundColor Cyan
