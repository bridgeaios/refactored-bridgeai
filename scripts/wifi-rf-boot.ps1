# BridgeLiveWall — WiFi RF sensor (run at boot / logon)
# Samples WiFi signal via netsh and POSTs to Bridge API. Run minimized from Startup/Task Scheduler.

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$baseUrl = if ($env:BRIDGE_API_URL) { $env:BRIDGE_API_URL.TrimEnd("/") } else { "http://localhost:8000" }
$intervalSec = if ($env:BRIDGE_SENSOR_WIFI_INTERVAL_SEC) { [int]$env:BRIDGE_SENSOR_WIFI_INTERVAL_SEC } else { 15 }

function Get-WifiRfSample {
    try {
        $out = netsh wlan show interfaces 2>$null
        if (-not $out) { return $null }
        $signal = $null
        $ssid = $null
        $state = $null
        foreach ($line in ($out -split "`r?`n")) {
            $line = $line.Trim()
            if ($line -match "^\s*Signal\s*:\s*(.+)") { $signal = $Matches[1].Trim() }
            if ($line -match "^\s*SSID\s*:\s*(.+)") { $ssid = $Matches[1].Trim() }
            if ($line -match "^\s*State\s*:\s*(.+)") { $state = $Matches[1].Trim() }
        }
        $signalPct = $null
        if ($signal -match "(\d+)\s*%") { $signalPct = [int]$Matches[1] }
        return @{
            ssid = $ssid
            signal = $signal
            signalPercent = $signalPct
            state = $state
            source = "netsh wlan show interfaces"
        }
    } catch {
        return $null
    }
}

function Send-WifiSample {
    param($payload)
    try {
        $body = $payload | ConvertTo-Json -Compress
        $uri = "$baseUrl/api/sensors/wifi"
        Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
    } catch {
        # Silently continue; API may not be up at boot
    }
}

# Loop: sample and POST every $intervalSec seconds
while ($true) {
    $sample = Get-WifiRfSample
    if ($sample) {
        Send-WifiSample -payload $sample
    }
    Start-Sleep -Seconds $intervalSec
}
