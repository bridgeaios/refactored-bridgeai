# Sync all digital twins on this system; wiki-style version control; scan C:\Downloads
# Writes: data/twin-registry.json, docs/WIKI-VERSIONS.md
# Run: .\scripts\sync-twins-wiki.ps1

$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot

# Load config
$configPath = Join-Path $projectRoot "config\bridge-wall.config.json"
$apiBase = "http://localhost:8000"
$registryPath = Join-Path $projectRoot "data\twin-registry.json"
$wikiPath = Join-Path $projectRoot "docs\WIKI-VERSIONS.md"
$downloadsPaths = @(
    "C:\Users\$env:USERNAME\Downloads",
    "C:\Downloads"
)
$versionedPatterns = @("*bridge*", "*living*", "*twin*", "*neural*", "*.html", "manifest.json", "*.json")

if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.twinsSync) {
            $ts = $cfg.twinsSync
            if ($ts.apiBaseUrl) { $apiBase = $ts.apiBaseUrl.TrimEnd("/") }
            if ($ts.registryPath) { $registryPath = Join-Path $projectRoot $ts.registryPath }
            if ($ts.wikiPath) { $wikiPath = Join-Path $projectRoot $ts.wikiPath }
            if ($ts.downloadsPaths) {
                $downloadsPaths = @($ts.downloadsPaths) | ForEach-Object { $_ -replace '%USERNAME%', $env:USERNAME }
            }
            if ($ts.versionedPatterns) { $versionedPatterns = @($ts.versionedPatterns) }
        }
    } catch { }
}

# Ensure output dirs
$registryDir = Split-Path $registryPath -Parent
$wikiDir = Split-Path $wikiPath -Parent
if (-not (Test-Path $registryDir)) { New-Item -ItemType Directory -Path $registryDir -Force | Out-Null }
if (-not (Test-Path $wikiDir)) { New-Item -ItemType Directory -Path $wikiDir -Force | Out-Null }

$syncedAt = (Get-Date -Format "o")
$api = @{}
$apiEndpoints = @(
    @{ key = "twins"; url = "$apiBase/api/twins" },
    @{ key = "leaderboard"; url = "$apiBase/api/twins/leaderboard" },
    @{ key = "stateSnapshot"; url = "$apiBase/api/state/snapshot" },
    @{ key = "sharedXml"; url = "$apiBase/api/twin/shared-xml" },
    @{ key = "envKeys"; url = "$apiBase/api/twin/env-keys" }
)
foreach ($ep in $apiEndpoints) {
    try {
        $api[$ep.key] = Invoke-RestMethod -Uri $ep.url -Method Get -TimeoutSec 5 -ErrorAction Stop
    } catch {
        $api[$ep.key] = @{ _error = $_.Exception.Message }
    }
}

# Summarize shared XML and env-keys for registry (no secrets)
if ($api.sharedXml -and -not $api.sharedXml._error) {
    $xmlStr = if ($api.sharedXml -is [string]) { $api.sharedXml } else { $api.sharedXml | ConvertTo-Json -Compress }
    $api.sharedXmlSummary = @{ length = $xmlStr.Length; preview = $xmlStr.Substring(0, [Math]::Min(200, $xmlStr.Length)) }
}
if ($api.envKeys -and -not $api.envKeys._error) {
    $api.envKeysSummary = if ($api.envKeys.summary) { $api.envKeys.summary } else { $api.envKeys }
}

# Scan Downloads for versioned artifacts (dedupe by path)
$seenPaths = @{}
$downloadsArtifacts = @()
foreach ($dir in $downloadsPaths) {
    if (-not (Test-Path $dir)) { continue }
    foreach ($pattern in $versionedPatterns) {
        try {
            $files = Get-ChildItem -Path $dir -Filter $pattern -File -ErrorAction SilentlyContinue
            foreach ($f in $files) {
                if ($seenPaths[$f.FullName]) { continue }
                $seenPaths[$f.FullName] = $true
                $downloadsArtifacts += @{ path = $f.FullName; name = $f.Name; lastWrite = $f.LastWriteTime.ToString("o"); size = $f.Length; sourceDir = $dir }
            }
        } catch { }
    }
    try {
        $allFiles = Get-ChildItem -Path $dir -File -ErrorAction SilentlyContinue
        foreach ($f in $allFiles) {
            $nameLower = $f.Name.ToLower()
            if ($nameLower -like "*bridge*" -or $nameLower -like "*living*" -or $nameLower -like "*twin*" -or $nameLower -like "*neural*") {
                if ($seenPaths[$f.FullName]) { continue }
                $seenPaths[$f.FullName] = $true
                $downloadsArtifacts += @{ path = $f.FullName; name = $f.Name; lastWrite = $f.LastWriteTime.ToString("o"); size = $f.Length; sourceDir = $dir }
            }
        }
    } catch { }
}

$registry = @{
    syncedAt   = $syncedAt
    apiBaseUrl = $apiBase
    api        = @{
        twins         = $api.twins
        leaderboard   = $api.leaderboard
        stateSnapshot = $api.stateSnapshot
        sharedXmlSummary = $api.sharedXmlSummary
        envKeysSummary   = $api.envKeysSummary
    }
    system     = @{
        downloadsPaths = $downloadsPaths
        downloadsArtifacts = $downloadsArtifacts
    }
}
$registry | ConvertTo-Json -Depth 10 | Set-Content $registryPath -Encoding UTF8
Write-Host "Registry written: $registryPath"

# Build wiki-style WIKI-VERSIONS.md
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine('# Digital Twins - Wiki-Style Version Control')
[void]$sb.AppendLine("")
[void]$sb.AppendLine("**Synced:** $syncedAt")
[void]$sb.AppendLine("**API base:** $apiBase")
[void]$sb.AppendLine("")
[void]$sb.AppendLine('---')
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## 1. System state version")
if ($api.stateSnapshot -and -not $api.stateSnapshot._error) {
    $v = $api.stateSnapshot.state_version
    $h = $api.stateSnapshot.state_hash
    [void]$sb.AppendLine("- **State version:** $v")
    [void]$sb.AppendLine("- **State hash:** $h")
} else {
    [void]$sb.AppendLine("- API unreachable or snapshot failed.")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## 2. All digital twins (this system)")
if ($api.twins -and -not $api.twins._error -and ($api.twins | Measure-Object).Count -ge 0) {
    [void]$sb.AppendLine('| Id | Name | Completed | In progress | Total score | Trades | DEX PnL |')
    [void]$sb.AppendLine('|----|------|-----------|-------------|-------------|--------|---------|')
    foreach ($t in $api.twins) {
        $id = $t.id; $name = $t.name; $c = $t.completed; $ip = $t.in_progress
        $ts = $t.total_score; $tr = $t.trades_executed; $pnl = $t.dex_pnl
        [void]$sb.AppendLine("| $id | $name | $c | $ip | $ts | $tr | $pnl |")
    }
} else {
    [void]$sb.AppendLine("- No twins data (API down or error).")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## 3. Leaderboard")
if ($api.leaderboard -and -not $api.leaderboard._error) {
    foreach ($e in $api.leaderboard) {
        [void]$sb.AppendLine("- **#$($e.rank)** $($e.name) - completed: $($e.completed), trades: $($e.trades_executed), score: $($e.total_score), dex_pnl: $($e.dex_pnl)")
    }
} else {
    [void]$sb.AppendLine("- Leaderboard unavailable.")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## 4. Versioned artifacts (C:\\Downloads)")
[void]$sb.AppendLine("All versions and wiki-type files found in Downloads:")
[void]$sb.AppendLine("")
[void]$sb.AppendLine('| Name | Last modified | Size | Path |')
[void]$sb.AppendLine('|------|---------------|------|------|')
foreach ($a in $downloadsArtifacts) {
    $pathEscaped = $a.path -replace '\|', '\|'
    [void]$sb.AppendLine("| $($a.name) | $($a.lastWrite) | $($a.size) | ``$pathEscaped`` |")
}
if ($downloadsArtifacts.Count -eq 0) {
    [void]$sb.AppendLine("- No matching artifacts in Downloads.")
}
[void]$sb.AppendLine("")
[void]$sb.AppendLine('---')
[void]$sb.AppendLine("To re-sync: ``.\scripts\sync-twins-wiki.ps1``")
[void]$sb.AppendLine("To view registry JSON: ``data/twin-registry.json``")

$sb.ToString() | Set-Content $wikiPath -Encoding UTF8
Write-Host "Wiki written: $wikiPath"

# Write static HTML viewer (inline registry so it works from file://)
$htmlPath = Join-Path $wikiDir "twin-wiki.html"
$registryJsonEscaped = ($registry | ConvertTo-Json -Depth 10 -Compress) -replace '<', '\u003c' -replace '>', '\u003e' -replace '&', '\u0026'
$htmlContent = @"
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Digital Twins — All Versions</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 1rem; }
    h1 { border-bottom: 1px solid #ccc; }
    section { margin: 1.5rem 0; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }
    th { background: #f5f5f5; }
    .path { font-size: 0.85em; word-break: break-all; }
    a.local { color: #06c; }
    .meta { color: #666; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>Digital Twins — All Versions (Wiki)</h1>
  <p class="meta">Synced: <span id="syncedAt"></span> | API: <span id="apiBase"></span></p>
  <section>
    <h2>State version</h2>
    <p id="stateVersion"></p>
  </section>
  <section>
    <h2>All twins</h2>
    <table id="twinsTable"><thead><tr><th>Id</th><th>Name</th><th>Completed</th><th>In progress</th><th>Score</th><th>Trades</th><th>DEX PnL</th></tr></thead><tbody></tbody></table>
  </section>
  <section>
    <h2>Leaderboard</h2>
    <ol id="leaderboard"></ol>
  </section>
  <section>
    <h2>Versioned artifacts (C:\Downloads)</h2>
    <p>All versions — open path in Explorer or use link below.</p>
    <table><thead><tr><th>Name</th><th>Modified</th><th>Size</th><th>Open</th></tr></thead><tbody id="artifacts"></tbody></table>
  </section>
  <script>
    var REGISTRY = $registryJsonEscaped;
    document.getElementById('syncedAt').textContent = REGISTRY.syncedAt || '';
    document.getElementById('apiBase').textContent = REGISTRY.apiBaseUrl || '';
    var snap = REGISTRY.api && REGISTRY.api.stateSnapshot;
    if (snap && !snap._error) {
      document.getElementById('stateVersion').innerHTML = 'Version: <strong>' + snap.state_version + '</strong> | Hash: <code>' + (snap.state_hash || '') + '</code>';
    } else {
      document.getElementById('stateVersion').textContent = 'API unreachable or snapshot failed.';
    }
    var twins = REGISTRY.api && REGISTRY.api.twins;
    if (Array.isArray(twins) && !twins[0]._error) {
      var tbody = document.querySelector('#twinsTable tbody');
      twins.forEach(function(t) {
        var tr = document.createElement('tr');
        tr.innerHTML = '<td>' + t.id + '</td><td>' + t.name + '</td><td>' + t.completed + '</td><td>' + t.in_progress + '</td><td>' + t.total_score + '</td><td>' + (t.trades_executed || 0) + '</td><td>' + (t.dex_pnl || 0) + '</td>';
        tbody.appendChild(tr);
      });
    }
    var lb = REGISTRY.api && REGISTRY.api.leaderboard;
    if (Array.isArray(lb) && !lb[0]._error) {
      var ol = document.getElementById('leaderboard');
      lb.forEach(function(e) {
        var li = document.createElement('li');
        li.textContent = '#' + e.rank + ' ' + e.name + ' — completed: ' + e.completed + ', trades: ' + e.trades_executed + ', score: ' + e.total_score;
        ol.appendChild(li);
      });
    }
    var artifacts = REGISTRY.system && REGISTRY.system.downloadsArtifacts || [];
    var artTbody = document.getElementById('artifacts');
    artifacts.forEach(function(a) {
      var tr = document.createElement('tr');
      var fileUrl = 'file:///' + a.path.replace(/\\\\/g, '/').replace(/\\/g, '/').replace(/^\\\\?/, '');
      var openLink = '<a class="local" href="' + fileUrl + '" target="_blank">Open</a>';
      tr.innerHTML = '<td>' + a.name + '</td><td>' + a.lastWrite + '</td><td>' + a.size + '</td><td>' + openLink + '</td>';
      artTbody.appendChild(tr);
    });
    if (artifacts.length === 0) artTbody.innerHTML = '<tr><td colspan="4">No artifacts in Downloads.</td></tr>';
  </script>
</body>
</html>
"@
$htmlContent | Set-Content $htmlPath -Encoding UTF8
Write-Host "HTML viewer: $htmlPath"
Write-Host "Done. Open docs/WIKI-VERSIONS.md, docs/twin-wiki.html, or data/twin-registry.json for all versions and twins."
