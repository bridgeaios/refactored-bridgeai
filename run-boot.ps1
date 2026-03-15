# BridgeLiveWall — Run Backend from any directory (for boot/startup)
# Usage: & "C:\Users\supas\BridgeLiveWall\run-boot.ps1"
# Or add to Windows Startup: Win+R → shell:startup → create shortcut to this script

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
& "$scriptDir\run-backend.ps1"
