# Forward to repo root: run full loop from anywhere under BridgeLiveWall
& (Join-Path (Split-Path $PSScriptRoot -Parent) "run-full-loop.ps1") @args
