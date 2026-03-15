# BridgeLiveWall - Live Wallpaper Runner
# Runs update.ps1 periodically so the wallpaper reflects current system status.
# Run this at login (or via Task Scheduler) to keep the wallpaper live.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$updateScript = Join-Path $scriptDir "update.ps1"
$intervalSec = 60  # Refresh every 60 seconds

Write-Host "BridgeLiveWall: Starting live wallpaper. Refresh every $intervalSec seconds. Ctrl+C to stop."
while ($true) {
    try {
        & $updateScript
    } catch {
        Write-Warning "Wallpaper update failed: $_"
    }
    Start-Sleep -Seconds $intervalSec
}
