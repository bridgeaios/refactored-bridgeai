# BridgeLiveWall — Add WiFi RF + mouse tracker to Windows Startup
# Run once: powershell -ExecutionPolicy Bypass -File install-sensors-boot.ps1
# Requires Bridge API running (e.g. run-backend.ps1 or install-startup.ps1) so sensors can POST.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$startupDir = [Environment]::GetFolderPath('Startup')

$scripts = @(
    @{
        Name = "BridgeLiveWall-WifiRf"
        Script = "scripts\wifi-rf-boot.ps1"
        Description = "Bridge WiFi RF sensor (POST to API)"
    },
    @{
        Name = "BridgeLiveWall-MouseTracker"
        Script = "scripts\mouse-tracker-boot.ps1"
        Description = "Bridge mouse tracker (POST to API)"
    }
)

$WshShell = New-Object -ComObject WScript.Shell
foreach ($item in $scripts) {
    $scriptPath = Join-Path $projectRoot $item.Script
    if (-not (Test-Path $scriptPath)) {
        Write-Host "Skip (not found): $scriptPath" -ForegroundColor Yellow
        continue
    }
    $shortcutPath = Join-Path $startupDir "$($item.Name).lnk"
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Minimized -File `"$scriptPath`""
    $Shortcut.WorkingDirectory = $projectRoot
    $Shortcut.Description = $item.Description
    $Shortcut.Save()
    Write-Host "Added to Startup: $shortcutPath" -ForegroundColor Green
}

Write-Host "Sensors will start at logon and POST to Bridge API (default http://localhost:8000). Set BRIDGE_API_URL if needed." -ForegroundColor Cyan
Write-Host "To remove: delete the BridgeLiveWall-WifiRf and BridgeLiveWall-MouseTracker shortcuts from Startup." -ForegroundColor Cyan
