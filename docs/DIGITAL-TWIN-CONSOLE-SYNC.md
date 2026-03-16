# Digital Twin Console — Sync and Human API

## Sync: 3000 ↔ 3022

- **Requirement:** `http://localhost:3000/digital-twin-console.html` MUST BE SYNCED WITH `http://localhost:3022/`.
- **Meaning:** The console entry point (e.g. at 3000) should redirect to or load the Digital Twin app from **port 3022** so both show the same content.
- **BridgeLiveWall:** The frontend serves `digital-twin-console.html` (in `frontend/public/`). That page redirects to `http://localhost:3022/` by default. Override with `window.__CONSOLE_SYNC_URL` before load if needed.
- **Config:** `config/bridge-wall.config.json` has `ports.defaults["console-sync"]: 3022` and `3022` in `ports.registry`. Run the frontend on 3022 when using the console sync (e.g. `PORT=3022 npm run start` or Vite with `--port 3022`).

## Human API (no HTML — JSON only)

- **Error:** `Failed to execute 'json' on 'Response': Unexpected token '<', "<!DOCTYPE "... is not valid JSON` means the client called `.json()` on a response that was HTML (e.g. 404 or error page).
- **Fix:** Point the Digital Twin Console’s “Human API” request to the Bridge API endpoint that **always returns JSON**:
  - **URL:** `GET {API_BASE}/api/human`
  - **Example:** `http://localhost:8000/api/human` (Bridge API) or `https://api.bridge-ai-os.tech/api/human`.
- **Response (JSON):** `{ ok, timestamp, telemetry, mission_board, objectives, identity_hash, spine, services, live_report_at }`. Never HTML.
- **Console implementation:** Before calling `response.json()`, check `Content-Type` includes `application/json`, or catch the parse error and show “Human API unavailable” instead of breaking.

## Kill & reboot (CLI)

Suggested one-liner (run from repo root or AOE):

```powershell
cd E:\AOE ; .\scripts\start-sovereign-node.ps1 ; .\scripts\sovereign-node-mesh.ps1 -Repair
```

Then open `http://localhost:3022/` (or the console URL that redirects to 3022).
