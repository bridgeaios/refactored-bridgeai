# BridgeLiveWall — Add backend to Windows Startup
# Run once: powershell -ExecutionPolicy Bypass -File install-startup.ps1

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$startupDir = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir "BridgeLiveWall-Backend.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Minimized -File `"$projectRoot\run-backend.ps1`""
$Shortcut.WorkingDirectory = $projectRoot
$Shortcut.Description = "Bridge AI OS Backend (port 8000)"
$Shortcut.Save()

Write-Host "Added to Startup: $shortcutPath" -ForegroundColor Green
Write-Host "Backend will start when you log in. To remove: delete the shortcut." -ForegroundColor Cyan
