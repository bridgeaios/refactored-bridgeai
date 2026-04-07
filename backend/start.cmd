@echo off
cd /d E:\BridgeAI\BridgeLiveWall\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003
