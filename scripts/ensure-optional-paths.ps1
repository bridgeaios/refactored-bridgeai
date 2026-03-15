# BridgeLiveWall — Create optional D: (and E:) paths so audit recs can be cleared
# Run from repo root. If D: drive exists, creates D:\BridgeAI\BridgeLiveWall and D:\BridgeAI\data.

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot

$optionalPaths = @(
    "D:\BridgeAI\BridgeLiveWall",
    "D:\BridgeAI\data"
)
$created = @()
foreach ($dir in $optionalPaths) {
    $parent = Split-Path -Parent $dir
    $drive = (Split-Path -Qualifier $dir) + "\"
    if (-not (Test-Path $drive)) {
        Write-Host "Drive $drive not found; skipping $dir" -ForegroundColor Yellow
        continue
    }
    if (-not (Test-Path $dir)) {
        try {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            $created += $dir
        } catch {
            Write-Host "Failed to create $dir : $_" -ForegroundColor Red
        }
    }
}
if ($created.Count -gt 0) {
    Write-Host "Created optional paths: $($created -join ', ')" -ForegroundColor Green
} else {
    Write-Host "Optional paths already exist or D: not present. No changes." -ForegroundColor Cyan
}
Write-Host "Run .\audit-wall.ps1 to refresh audit." -ForegroundColor Cyan
