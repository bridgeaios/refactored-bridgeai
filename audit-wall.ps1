# Full audit for Digital Twin Wallpaper - keys, settings, Cloudflare, Hugging Face, DNS, etc.
# Output: audit-results.json (read by update.ps1)

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$outPath = Join-Path $scriptRoot "audit-results.json"

$recommendations = @()
$ok = @()
$critical = @()

# Placeholder patterns - values that indicate "not configured"
$placeholders = @(
    'your-', 'sk-your-', 'hf_your', 'your_', 'generate-a-strong', 'change-me',
    'your-cloudflare', 'your-email', 'your-domain', 'your-username', 'your-paypal',
    'sk_test_', 'pk_test_', 'xai-your-', 'gsk_your-', 'pcsk_your-', 'glhf_',
    '0x4AAAAAA'  # Turnstile test key prefix
)

function Test-IsPlaceholder($val) {
    if (-not $val -or $val.Length -lt 8) { return $true }
    foreach ($p in $placeholders) {
        if ($val -like "*$p*") { return $true }
    }
    return $false
}

function Get-EnvValue($envPath, $key) {
    if (-not (Test-Path $envPath)) { return $null }
    $content = Get-Content $envPath -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return $null }
    $match = [regex]::Match($content, "(?m)^\s*$key\s*=\s*(.+?)\s*$")
    if ($match.Success) { return $match.Groups[1].Value.Trim().Trim('"').Trim("'") }
    return $null
}

# ---- 0. CONFIG (optional) — ports from config/bridge-wall.config.json, E/C/D drives ----
$configPath = Join-Path $scriptRoot "config\bridge-wall.config.json"
$portList = @(
    @{ Port = 3000; Label = "Dashboard" },
    @{ Port = 3001; Label = "Bridge Backend" },
    @{ Port = 3020; Label = "Frontend" },
    @{ Port = 3030; Label = "Bridge Auth" },
    @{ Port = 7777; Label = "Installer" },
    @{ Port = 8000; Label = "Bridge API" },
    @{ Port = 8001; Label = "Frontend (Docker)" },
    @{ Port = 8081; Label = "Backend (Docker)" }
)
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.services) {
            $portList = @()
            $cfg.services.PSObject.Properties | ForEach-Object {
                $s = $_.Value
                $label = if ($s.label) { $s.label } else { $_.Name }
                $portList += @{ Port = $s.port; Label = $label }
            }
        }
    } catch { }
}

# ---- 1. ENV FILES ----
# Check repo root first, then E:\AOE, then config drive paths (E/C/D)
$repoEnv = Join-Path $scriptRoot ".env"
$aoeEnv = "E:\AOE\.env"
$v1Env = "E:\AOE\v1\.env"
$dEnv = "D:\BridgeAI\BridgeLiveWall\.env"
$cEnv = "$env:USERPROFILE\.bridge-wall\.env"
$envPaths = @($repoEnv, $aoeEnv, $v1Env, $dEnv, $cEnv) | Where-Object { $_ -and (Test-Path $_) }
if ($envPaths.Count -eq 0) { $envPaths = @($repoEnv, $aoeEnv, $v1Env) }
$primaryEnv = if ($envPaths.Count -gt 0) { $envPaths[0] } else { $aoeEnv }

# ---- 2. CRITICAL KEYS ----
$keyChecks = @(
    @{ Key = "OPENAI_API_KEY"; Label = "OpenAI"; Critical = $true },
    @{ Key = "HF_TOKEN"; Label = "Hugging Face"; Critical = $true },
    @{ Key = "HUGGING_FACE_API_KEY"; Label = "Hugging Face (alt)"; Critical = $true },
    @{ Key = "CLOUDFLARE_ACCOUNT_ID"; Label = "Cloudflare Account"; Critical = $true },
    @{ Key = "JWT_SECRET"; Label = "JWT Secret"; Critical = $true },
    @{ Key = "JWT_SECRET_KEY"; Label = "JWT Secret Key"; Critical = $true },
    @{ Key = "TURNSTILE_SECRET_KEY"; Label = "Cloudflare Turnstile"; Critical = $false },
    @{ Key = "ELEVENLABS_API_KEY"; Label = "ElevenLabs"; Critical = $false },
    @{ Key = "ANTHROPIC_API_KEY"; Label = "Anthropic"; Critical = $false },
    @{ Key = "SMTP_PASSWORD"; Label = "SMTP"; Critical = $false },
    @{ Key = "PAYPAL_CLIENT_ID"; Label = "PayPal"; Critical = $false },
    @{ Key = "DISCORD_BOT_TOKEN"; Label = "Discord Bot"; Critical = $false },
    @{ Key = "R2_BUCKET_NAME"; Label = "Cloudflare R2 Bucket"; Critical = $false }
)

# Dev mode: when BRIDGE_AUDIT_DEV=1, treat missing/placeholder critical keys as ok so wallpaper shows "all complete"
$auditDev = [System.Environment]::GetEnvironmentVariable("BRIDGE_AUDIT_DEV", "Process") -eq "1"
if (-not $auditDev) { $auditDev = [System.Environment]::GetEnvironmentVariable("BRIDGE_AUDIT_DEV", "User") -eq "1" }
if (-not $auditDev) { $auditDev = [System.Environment]::GetEnvironmentVariable("BRIDGE_AUDIT_DEV", "Machine") -eq "1" }

foreach ($c in $keyChecks) {
    $val = $null
    foreach ($p in $envPaths) {
        $v = Get-EnvValue $p $c.Key
        if ($v) { $val = $v; break }
    }
    if (-not $val) {
        if ($c.Critical) {
            if (-not $auditDev) { $critical += "Missing: $($c.Label) ($($c.Key))" }
            else { $ok += "$($c.Label) (dev)" }
        } else {
            $recommendations += "Optional: $($c.Label) not set"
        }
    } elseif (Test-IsPlaceholder $val) {
        $recommendations += "Configure: $($c.Label) - placeholder value"
        if ($c.Critical) {
            if (-not $auditDev) { $critical += "$($c.Label) has placeholder" }
            else { $ok += "$($c.Label) (dev)" }
        }
    } else {
        $ok += "$($c.Label) OK"
    }
}

# ---- 3. AWS CREDENTIALS ----
$awsCreds = "$env:USERPROFILE\.aws\credentials"
$awsConfig = "$env:USERPROFILE\.aws\config"
if (-not (Test-Path $awsCreds)) {
    if (-not $auditDev) { $critical += "AWS: credentials not found (~/.aws/credentials)" }
    else { $ok += "AWS (dev)" }
} else {
    $ok += "AWS credentials file exists"
}
if (-not (Test-Path $awsConfig)) {
    $recommendations += "AWS: config not found (~/.aws/config)"
}

# ---- 4. PORTS (from config: Dashboard, Bridge Backend, Frontend, Auth, Installer, Docker) ----
foreach ($p in $portList) {
    $listening = $false
    try {
        $conn = Get-NetTCPConnection -LocalPort $p.Port -State Listen -ErrorAction SilentlyContinue
        if ($conn) { $listening = $true }
    } catch { }
    if ($listening) {
        $ok += "$($p.Label) ($($p.Port)) listening"
    } else {
        $recommendations += "$($p.Label) not running (port $($p.Port))"
    }
}

# ---- 5. DNS (api.bridge-ai-os.tech) ----
$dnsOk = $false
try {
    $dns = Resolve-DnsName "api.bridge-ai-os.tech" -ErrorAction SilentlyContinue
    if ($dns -and $dns.Count -gt 0) { $dnsOk = $true }
} catch { }
if ($dnsOk) {
    $ok += "DNS api.bridge-ai-os.tech resolves"
} else {
    $recommendations += "DNS: api.bridge-ai-os.tech - add record in Cloudflare"
}

# ---- 6. R2 / Cloudflare Workers (if CLOUDFLARE_ACCOUNT_ID set) ----
$cfId = $null
foreach ($p in $envPaths) {
    $v = Get-EnvValue $p "CLOUDFLARE_ACCOUNT_ID"
    if ($v -and -not (Test-IsPlaceholder $v)) { $cfId = $v; break }
}
if ($cfId) {
    $r2 = $null
    foreach ($p in $envPaths) {
        $v = Get-EnvValue $p "R2_BUCKET_NAME"
        if ($v) { $r2 = $v; break }
    }
    if (-not $r2 -or (Test-IsPlaceholder $r2)) {
        $recommendations += "Cloudflare: set R2_BUCKET_NAME for storage"
    }
}

# ---- 7. AWS CLI ----
$awsCli = $false
try {
    $awsExe = Get-Command aws -ErrorAction SilentlyContinue
    if ($awsExe) { $awsCli = $true }
} catch { }
if (-not $awsCli) {
    try {
        if (Test-Path "C:\Program Files\Amazon\AWSCLIV2\aws.exe") { $awsCli = $true }
    } catch { }
}
if ($awsCli) {
    $ok += "AWS CLI installed"
} else {
    $recommendations += "AWS CLI not in PATH"
}

# ---- 8. E/C/D DRIVE PATHS (system-wide) ----
$drivePaths = @(
    @{ Path = "E:\AOE"; Label = "E: AOE" },
    @{ Path = "E:\BridgeAI\BridgeLiveWall"; Label = "E: BridgeLiveWall" },
    @{ Path = "E:\AOE\.env"; Label = "E: AOE .env" },
    @{ Path = "$env:USERPROFILE\.aws\credentials"; Label = "C: AWS credentials" },
    @{ Path = "D:\BridgeAI\BridgeLiveWall"; Label = "D: BridgeLiveWall (optional)" },
    @{ Path = "D:\BridgeAI\data"; Label = "D: data (optional)" }
)
foreach ($d in $drivePaths) {
    if (Test-Path $d.Path) {
        $ok += "$($d.Label) exists"
    } elseif ($d.Label -like "*optional*") {
        $recommendations += "Optional: $($d.Label) not found"
    }
}
if (Test-Path $configPath) { $ok += "Config (config\bridge-wall.config.json) found" }

# ---- 9. Build output ----
$result = @{
    timestamp = (Get-Date -Format "o")
    ok = $ok
    critical = $critical
    recommendations = $recommendations
    summary = @{
        okCount = $ok.Count
        criticalCount = $critical.Count
        recCount = $recommendations.Count
    }
}
$result | ConvertTo-Json -Depth 5 | Set-Content $outPath -Encoding UTF8
