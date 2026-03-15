# Mark a founder objective complete. Updates founder-todo.json.
# Usage: .\mark-objective.ps1 -Id "obj-1"
#        .\mark-objective.ps1 -Id "obj-1" -Complete
# When objective is met, next wallpaper refresh (run-wallpaper-live.ps1) will show it.

param(
    [Parameter(Mandatory=$true)]
    [string]$Id,
    [switch]$Complete = $true
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$path = Join-Path $scriptRoot "founder-todo.json"

if (-not (Test-Path $path)) {
    Write-Error "founder-todo.json not found at $path"
    exit 1
}

$data = Get-Content $path -Raw | ConvertFrom-Json
$obj = $data.objectives | Where-Object { $_.id -eq $Id }
if (-not $obj) {
    Write-Error "Objective '$Id' not found"
    exit 1
}

$obj.status = "complete"
$obj.completedAt = (Get-Date -Format "o")
$data.updatedAt = (Get-Date -Format "o")

$data | ConvertTo-Json -Depth 10 | Set-Content $path -Encoding UTF8
Write-Host "Marked $Id complete. Wallpaper will update on next refresh."
