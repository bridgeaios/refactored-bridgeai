# Bridge Live Wall — system-wide port handling (E/C/D drives)
# Usage:
#   .\port-handler.ps1 list              — list all configured ports and status
#   .\port-handler.ps1 free 3001         — find next free port from 3001
#   .\port-handler.ps1 used 3001         — show process using port 3001
#   .\port-handler.ps1 kill 3001          — kill process on port 3001 (optional)
#   .\port-handler.ps1 config            — show config path and load from E/C/D

param(
    [Parameter(Position = 0)]
    [ValidateSet("list", "free", "used", "kill", "config")]
    [string]$Action = "list",
    [Parameter(Position = 1)]
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot

# Resolve config from E:, then D:, then C: (workspace), then project root
$configPaths = @(
    (Join-Path $projectRoot "config\bridge-wall.config.json"),
    "E:\BridgeAI\BridgeLiveWall\config\bridge-wall.config.json",
    "D:\BridgeAI\BridgeLiveWall\config\bridge-wall.config.json",
    "C:\BridgeAI\BridgeLiveWall\config\bridge-wall.config.json"
)
$configPath = $null
foreach ($p in $configPaths) {
    if (Test-Path $p) { $configPath = $p; break }
}
if (-not $configPath) { $configPath = $configPaths[0] }

function Get-PortConfig {
    if (-not (Test-Path $configPath)) {
        return @{ registry = @(3000, 3001, 3030, 3020, 5173, 6379, 7777, 8000, 8001, 8081); defaults = @{} }
    }
    $json = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $reg = @()
    if ($json.ports.registry) { $reg = @($json.ports.registry) }
    $def = @{}
    if ($json.ports.defaults) {
        $json.ports.defaults.PSObject.Properties | ForEach-Object { $def[$_.Name] = $_.Value }
    }
    $svc = @{}
    if ($json.services) {
        $json.services.PSObject.Properties | ForEach-Object {
            $svc[$_.Name] = @{ port = $_.Value.port; label = if ($_.Value.label) { $_.Value.label } else { $_.Name } }
        }
    }
    return @{ registry = $reg; defaults = $def; services = $svc; configPath = $configPath }
}

function Test-PortListening {
    param([int]$P)
    try {
        $conn = Get-NetTCPConnection -LocalPort $P -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $conn -and $conn.Count -gt 0)
    } catch { return $false }
}

function Get-ProcessOnPort {
    param([int]$P)
    try {
        $conn = Get-NetTCPConnection -LocalPort $P -State Listen -ErrorAction SilentlyContinue
        if (-not $conn) { return $null }
        $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
        $procs = @()
        foreach ($pid in $pids) {
            try {
                $procs += Get-Process -Id $pid -ErrorAction SilentlyContinue
            } catch {}
        }
        return $procs
    } catch { return $null }
}

function Get-NextFreePort {
    param([int]$StartPort, [int[]]$Range)
    $tryPort = $StartPort
    $maxAttempts = 50
    for ($i = 0; $i -lt $maxAttempts; $i++) {
        if (-not (Test-PortListening -P $tryPort)) { return $tryPort }
        if ($Range -and $i -lt $Range.Count) { $tryPort = $Range[$i] } else { $tryPort++ }
    }
    return $null
}

switch ($Action) {
    "config" {
        Write-Host "Config path: $configPath"
        Write-Host "Exists: $(Test-Path $configPath)"
        $cfg = Get-PortConfig
        Write-Host "Port registry count: $($cfg.registry.Count)"
        Write-Host "Drives: E:\, C:\, D:\ (see config for paths)"
    }
    "list" {
        $cfg = Get-PortConfig
        Write-Host "Bridge Live Wall - port status (config: $($cfg.configPath))"
        Write-Host ""
        $list = @()
        if ($cfg.services) {
            foreach ($name in $cfg.services.Keys) {
                $s = $cfg.services[$name]
                $p = $s.port
                $list += [PSCustomObject]@{ Service = $name; Port = $p; Label = $s.label; Listening = (Test-PortListening -P $p) }
            }
        }
        foreach ($p in $cfg.registry) {
            if ($list.Port -notcontains $p) {
                $list += [PSCustomObject]@{ Service = "-"; Port = $p; Label = "-"; Listening = (Test-PortListening -P $p) }
            }
        }
        $list | Sort-Object Port -Unique | Format-Table -AutoSize
    }
    "used" {
        if ($Port -le 0) { Write-Host 'Usage: .\port-handler.ps1 used <port>'; exit 1 }
        $procs = Get-ProcessOnPort -P $Port
        if (-not $procs -or $procs.Count -eq 0) {
            Write-Host "Port $Port is not in use."
        } else {
            Write-Host "Port $Port is in use by:"
            $procs | Format-Table Id, ProcessName, Path -AutoSize
        }
    }
    "free" {
        $start = if ($Port -gt 0) { $Port } else { 3001 }
        $cfg = Get-PortConfig
        $range = $cfg.registry + @(3010, 3011, 3012, 3040, 3050)
        $free = Get-NextFreePort -StartPort $start -Range $range
        if ($free) { Write-Host $free } else { Write-Host "No free port found in range."; exit 1 }
    }
    "kill" {
        if ($Port -le 0) { Write-Host 'Usage: .\port-handler.ps1 kill <port>'; exit 1 }
        $procs = Get-ProcessOnPort -P $Port
        if (-not $procs -or $procs.Count -eq 0) {
            Write-Host "Port $Port is not in use."
            exit 0
        }
        foreach ($proc in $procs) {
            Write-Host ('Killing PID ' + $proc.Id + ' - ' + $proc.ProcessName)
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Host 'Done.'
    }
}
