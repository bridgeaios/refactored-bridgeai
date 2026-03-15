# Determinator finalization: set RUN VERSION and deployed = true.
# Run after consolidate + orchestrate + validate. Traceable, reversible (edit JSON to revert).
# Usage: .\scripts\determinator-finalize.ps1 [-RunVersion "1.0.1"]

param([string] $RunVersion)

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$dataDir = Join-Path $projectRoot "data"
$versionPath = Join-Path $dataDir "determinator-run-version.json"

if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

$version = if ($RunVersion) { $RunVersion } else {
    $v = "1.0.0"
    if (Test-Path $versionPath) {
        try {
            $o = Get-Content $versionPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($o.runVersion) { $o.runVersion } else { $v }
        } catch { $v }
    } else { $v }
}

$now = [System.DateTime]::UtcNow.ToString("o")
$payload = @{
    runVersion = $version
    generatedAt = $now
    deployed = $true
    description = "Set deployed=true after finalization. Traceable, contract-grade."
} | ConvertTo-Json -Depth 3

Set-Content -Path $versionPath -Value $payload -Encoding UTF8
Write-Host "Determinator finalized: runVersion=$version, deployed=true, generatedAt=$now" -ForegroundColor Green
Write-Host "File: $versionPath" -ForegroundColor Gray
