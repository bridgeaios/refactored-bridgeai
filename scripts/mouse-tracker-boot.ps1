# BridgeLiveWall — Mouse tracker (run at boot / logon)
# Samples cursor position and POSTs to Bridge API. Run minimized from Startup/Task Scheduler.

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$baseUrl = if ($env:BRIDGE_API_URL) { $env:BRIDGE_API_URL.TrimEnd("/") } else { "http://localhost:8000" }
$intervalSec = if ($env:BRIDGE_SENSOR_MOUSE_INTERVAL_SEC) { [int]$env:BRIDGE_SENSOR_MOUSE_INTERVAL_SEC } else { 5 }

Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
if (-not ([System.Management.Automation.PSTypeName]'System.Windows.Forms.Cursor').Type) {
    # Fallback: post placeholder if Forms not available (e.g. headless)
    $hasForms = $false
} else {
    $hasForms = $true
}

function Get-MouseSample {
    if (-not $hasForms) {
        return @{ x = 0; y = 0; moved = $false; source = "unavailable" }
    }
    try {
        $p = [System.Windows.Forms.Cursor]::Position
        return @{
            x = $p.X
            y = $p.Y
            moved = $true
            source = "System.Windows.Forms.Cursor"
        }
    } catch {
        return @{ x = 0; y = 0; moved = $false; source = "error" }
    }
}

function Send-MouseSample {
    param($payload)
    try {
        $body = $payload | ConvertTo-Json -Compress
        $uri = "$baseUrl/api/sensors/mouse"
        Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
    } catch {
        # Silently continue; API may not be up at boot
    }
}

# Loop: sample and POST every $intervalSec seconds
while ($true) {
    $sample = Get-MouseSample
    Send-MouseSample -payload $sample
    Start-Sleep -Seconds $intervalSec
}
