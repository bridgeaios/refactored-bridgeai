# Start Determinator Boot Agent on port 4201 (RBAC HRE).
# Set DETERMINATOR_NEXT_URL to redirect after login (default http://localhost:8000).
# Usage: .\scripts\serve-determinator-boot.ps1

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$agentPath = Join-Path $scriptRoot "determinator-boot-agent.js"

function Import-DotEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }
        $name = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if (-not (Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue)) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

if (-not (Test-Path $agentPath)) {
    Write-Host "Missing $agentPath" -ForegroundColor Red
    exit 1
}

$envSources = @(
    (Join-Path $projectRoot '.env'),
    'D:\.env.unified',
    'D:\.env',
    'C:\Users\supas\.cursor\worktrees\BridgeLiveWall\iru\.env'
)
foreach ($envPath in $envSources) {
    Import-DotEnvFile -Path $envPath
}

$env:PORT = if ($env:DETERMINATOR_PORT) { $env:DETERMINATOR_PORT } else { '4201' }
if (-not $env:DETERMINATOR_NEXT_URL) { $env:DETERMINATOR_NEXT_URL = 'http://localhost:8000' }
if (-not $env:FRONTEND_URL) { $env:FRONTEND_URL = 'http://localhost:3020' }
if (-not $env:GOOGLE_REDIRECT_URI) { $env:GOOGLE_REDIRECT_URI = "http://localhost:$($env:PORT)/auth/google/callback" }

Write-Host "Starting Determinator Boot Agent on port $env:PORT" -ForegroundColor Cyan
Write-Host "RBAC login: http://localhost:$env:PORT/" -ForegroundColor Cyan
Write-Host "Next URL after auth: $env:DETERMINATOR_NEXT_URL" -ForegroundColor Gray
Write-Host "Google auth ready: $([bool]$env:GOOGLE_CLIENT_ID -and [bool]$env:GOOGLE_CLIENT_SECRET)" -ForegroundColor Gray
Set-Location $projectRoot
node $agentPath
