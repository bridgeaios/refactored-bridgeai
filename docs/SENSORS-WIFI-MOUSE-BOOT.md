# WiFi RF and Mouse Tracker from Boot

Optional boot-time sensors that run at Windows logon and POST samples to the Bridge API. Useful for live dashboards and telemetry.

## What runs

| Sensor        | Script                    | Default interval | API endpoint           |
|---------------|---------------------------|------------------|------------------------|
| WiFi RF       | `scripts/wifi-rf-boot.ps1`  | 15 s             | `POST /api/sensors/wifi`  |
| Mouse tracker | `scripts/mouse-tracker-boot.ps1` | 5 s              | `POST /api/sensors/mouse` |

- **WiFi RF**: Uses `netsh wlan show interfaces`; sends `ssid`, `signal`, `signalPercent`, `state`.
- **Mouse tracker**: Uses `System.Windows.Forms.Cursor.Position`; sends `x`, `y`, `moved`, `source`.

Data is stored in memory (Redis when available). Latest sample is returned by:

- `GET /api/sensors/wifi` and `GET /api/sensors/mouse`
- Included in `GET /api/live/map` and `GET /api/live/report` under `sensors.wifi` and `sensors.mouse`.

## Enable at boot

1. Ensure the Bridge API is running at logon (e.g. run `install-startup.ps1` for the backend).
2. Run once:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install-sensors-boot.ps1
   ```
3. This adds two Startup shortcuts:
   - **BridgeLiveWall-WifiRf** → `scripts/wifi-rf-boot.ps1`
   - **BridgeLiveWall-MouseTracker** → `scripts/mouse-tracker-boot.ps1`

After next logon, both scripts run minimized and POST to the API every few seconds.

## Configuration

- **Config**: `config/bridge-wall.config.json` → `sensors.wifi_rf` and `sensors.mouse_tracker` (enabled, scriptPath, reportIntervalMs, endpoint). Intervals in the scripts are not read from config; use env below.
- **Env**:
  - `BRIDGE_API_URL` — API base (default `http://localhost:8000`).
  - `BRIDGE_SENSOR_WIFI_INTERVAL_SEC` — WiFi report interval in seconds (default 15).
  - `BRIDGE_SENSOR_MOUSE_INTERVAL_SEC` — Mouse report interval in seconds (default 5).

## Disable

- Remove the shortcuts from **Startup**:
  - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BridgeLiveWall-WifiRf.lnk`
  - `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BridgeLiveWall-MouseTracker.lnk`
- Or set `sensors.wifi_rf.enabled` / `sensors.mouse_tracker.enabled` to `false` in config (scripts still run if started; config is for documentation and future automation).

## Flow

1. User logs in → Startup runs backend (if installed) and sensor scripts.
2. Sensor scripts loop: sample → POST to `/api/sensors/wifi` or `/api/sensors/mouse`.
3. Backend stores latest sample in memory (Redis keys `bridge:sensor:wifi:latest`, `bridge:sensor:mouse:latest`).
4. Dashboard or any client can poll `GET /api/live/report` or `GET /api/sensors/wifi` and `GET /api/sensors/mouse` to show live WiFi and cursor state.
