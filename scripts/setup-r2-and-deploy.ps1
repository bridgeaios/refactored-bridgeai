# Bridge Live Wall — Create R2 bucket, enable Worker R2 binding, deploy, set .env
# Run from repo root: .\scripts\setup-r2-and-deploy.ps1
# Does: 1) wrangler r2 bucket create bridge-live-wall  2) uncomment [[r2_buckets]] in worker/wrangler.toml  3) wrangler deploy  4) set R2_BUCKET_NAME in .env

$ErrorActionPreference = "Stop"
# Wrangler writes warnings to stderr; we use ErrorActionPreference = Continue around wrangler calls.
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$projectRoot = Split-Path -Parent $scriptRoot
$workerDir = Join-Path $projectRoot "worker"
$wranglerPath = Join-Path $workerDir "wrangler.toml"
$envPath = Join-Path $projectRoot ".env"
$bucketName = "bridge-live-wall"

Set-Location $projectRoot

# 1. Create R2 bucket
Write-Host "1. Creating R2 bucket: $bucketName" -ForegroundColor Cyan
Set-Location $workerDir
$prevErr = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$createOut = & npx wrangler r2 bucket create $bucketName 2>&1
$ErrorActionPreference = "Stop"
if ($createOut -match "already exists|Created|created") {
    Write-Host "   Bucket exists or created." -ForegroundColor Green
} else {
    $createOut | Write-Host
}

# 2. Uncomment [[r2_buckets]] block in wrangler.toml
Write-Host "2. Enabling R2 binding in wrangler.toml" -ForegroundColor Cyan
$content = Get-Content $wranglerPath -Raw -Encoding UTF8
$content = $content -replace "# \[\[r2_buckets\]\]", "[[r2_buckets]]"
$content = $content -replace "# binding = `"BUCKET`"", "binding = `"BUCKET`""
$content = $content -replace "# bucket_name = `"bridge-live-wall`"", "bucket_name = `"bridge-live-wall`""
[System.IO.File]::WriteAllText($wranglerPath, $content, [System.Text.UTF8Encoding]::new($false))
Write-Host "   Done." -ForegroundColor Green

# 3. Deploy Worker
Write-Host "3. Deploying Worker" -ForegroundColor Cyan
$ErrorActionPreference = "Continue"
$deployOut = & npx wrangler deploy 2>&1
$ErrorActionPreference = "Stop"
$deployOut | Write-Host
if ($deployOut -match "Deployed|Uploaded") {
    Write-Host "   Deployed." -ForegroundColor Green
} else {
    Write-Host "   Check output above for errors." -ForegroundColor Yellow
}

# 4. Set R2_BUCKET_NAME in .env
Write-Host "4. Setting R2_BUCKET_NAME in .env" -ForegroundColor Cyan
function Set-EnvKey($path, $key, $value) {
    if (-not (Test-Path $path)) {
        Add-Content -Path $path -Value "${key}=${value}" -Encoding UTF8
        return
    }
    $lines = Get-Content $path -Encoding UTF8
    $found = $false
    $newLines = foreach ($line in $lines) {
        if ($line -match "^\s*$key\s*=") {
            $found = $true
            "${key}=${value}"
        } else {
            $line
        }
    }
    if (-not $found) {
        $newLines += "${key}=${value}"
    }
    $newLines | Set-Content $path -Encoding UTF8
}
Set-EnvKey $envPath "R2_BUCKET_NAME" $bucketName
Write-Host "   Set R2_BUCKET_NAME=$bucketName in $envPath" -ForegroundColor Green

Set-Location $projectRoot

# 5. Custom domain instructions
Write-Host ""
Write-Host '5. Optional - Custom domain api.bridge-ai-os.tech:' -ForegroundColor Magenta
Write-Host '   Cloudflare Dashboard -> Workers & Pages -> bridge-live-wall-api -> Settings -> Domains -> Add custom domain -> api.bridge-ai-os.tech' -ForegroundColor Gray
Write-Host ''
Write-Host 'Worker URLs:' -ForegroundColor Green
Write-Host '   https://bridge-live-wall-api.thebridgeaiagency.workers.dev' -ForegroundColor Gray
Write-Host '   https://bridge-live-wall-api.thebridgeaiagency.workers.dev/health' -ForegroundColor Gray
Write-Host ""
Write-Host 'Run .\audit-wall.ps1 to confirm DNS and R2 recommendations.' -ForegroundColor Cyan
