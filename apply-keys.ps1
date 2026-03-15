# Apply Digital Twin env keys template
# Copies .env.example to .env (if missing) so you can fill real values.
# Optionally copies to E:\AOE\.env. See KEYS-REQUIRED.md for full list.

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$example = Join-Path $scriptRoot ".env.example"
$repoEnv = Join-Path $scriptRoot ".env"
$aoeEnv = "E:\AOE\.env"

if (-not (Test-Path $example)) {
    Write-Host "Missing .env.example in repo. Create it from KEYS-REQUIRED.md."
    exit 1
}

# Apply to repo .env if missing
if (-not (Test-Path $repoEnv)) {
    Copy-Item $example $repoEnv
    Write-Host "Created $repoEnv from .env.example. Edit and add your keys."
} else {
    Write-Host "Repo .env already exists: $repoEnv"
}

# Optionally apply to E:\AOE\.env and E:\AOE\v1\.env (same order as backend/main.py)
$aoeDir = Split-Path $aoeEnv -Parent
if (Test-Path $aoeDir) {
    if (-not (Test-Path $aoeEnv)) {
        Copy-Item $example $aoeEnv
        Write-Host "Created $aoeEnv from .env.example. Edit and add your keys."
    } else {
        Write-Host "E:\AOE\.env already exists."
    }
    $v1Env = "E:\AOE\v1\.env"
    $v1Dir = Split-Path $v1Env -Parent
    if (Test-Path $v1Dir) {
        if (-not (Test-Path $v1Env)) {
            Copy-Item $example $v1Env
            Write-Host "Created $v1Env from .env.example."
        }
    }
} else {
    Write-Host "E:\AOE not found. Use repo .env only, or create E:\AOE and run again."
}

Write-Host ""
Write-Host "Next: Edit .env with real values. Then run .\audit-wall.ps1 and .\update.ps1"
Write-Host "Or ask the Twin: GET http://localhost:8000/api/twin/env-keys"
