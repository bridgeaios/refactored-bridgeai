# Bridge AI OS — API Mesh Orchestrator (Active Controller)
# Probes endpoints AND executes value: allocates top task to twin when score > threshold.
# Usage: .\scripts\orchestrate-api-mesh.ps1 [-BaseUrl "http://localhost:8000"] [-TwinId "alpha"] [-Execute]

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$TwinId = "alpha",
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")
$MIN_SCORE = 0.2

Write-Host "Bridge AI OS — API Mesh" -ForegroundColor Cyan
Write-Host "Base: $BaseUrl" -ForegroundColor Gray
Write-Host ""

# Probe
$endpoints = @(
    @{ Name = "Health"; Path = "/api/health" },
    @{ Name = "Live Report"; Path = "/api/live/report" },
    @{ Name = "Marketplace Tasks"; Path = "/api/marketplace/tasks?twin_id=$TwinId" },
    @{ Name = "State Snapshot"; Path = "/api/state/snapshot" }
)

foreach ($ep in $endpoints) {
    try {
        $r = Invoke-RestMethod -Uri "$BaseUrl$($ep.Path)" -Method Get -TimeoutSec 5
        $ok = $true
        $summary = "OK"
        if ($ep.Path -like "*marketplace*") {
            $count = if ($r -is [array]) { $r.Count } else { 0 }
            $summary = "Tasks: $count"
            if ($count -gt 0 -and $r[0]._priority_score) {
                $summary += " | Top: $($r[0]._priority_score)"
            }
        }
        if ($ep.Path -like "*snapshot*" -and $r.priority_distribution) {
            $summary += " | P50: $($r.priority_distribution.p50)"
        }
    } catch {
        $ok = $false
        $summary = $_.Exception.Message
    }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host "  $($ep.Name): " -NoNewline
    Write-Host $summary -ForegroundColor $color
}

# Active: allocate top task if score > threshold
if ($Execute) {
    Write-Host ""
    try {
        $tasks = Invoke-RestMethod -Uri "$BaseUrl/api/marketplace/tasks?twin_id=$TwinId" -Method Get -TimeoutSec 5
        $top = if ($tasks -is [array] -and $tasks.Count -gt 0) { $tasks[0] } else { $null }
        if ($top -and [float]$top._priority_score -gt $MIN_SCORE) {
            $body = @{ twin_id = $TwinId } | ConvertTo-Json
            $res = Invoke-RestMethod -Uri "$BaseUrl/api/twins/allocate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5
            Write-Host "  [Execute] Allocated task $($res.task.id) to $TwinId (score: $($res.priority_score))" -ForegroundColor Cyan
        } else {
            Write-Host "  [Execute] No admissible task (top score <= $MIN_SCORE)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  [Execute] Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Done. Use -Execute to allocate top task." -ForegroundColor Gray
