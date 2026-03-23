# Run Bridge AI OS - API + Frontend (synced, mobile-friendly)
# Usage: .\scripts\run-bridge.ps1
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { "E:\BridgeAI\BridgeLiveWall" }

Write-Host "Bridge AI OS - starting..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" -WindowStyle Normal
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; `$env:PORT='3020'; node serve-no-cache.cjs" -WindowStyle Normal

Write-Host "API + Frontend launched in separate windows." -ForegroundColor Green
Write-Host "Open http://localhost:3020 (mobile-friendly)" -ForegroundColor Cyan
