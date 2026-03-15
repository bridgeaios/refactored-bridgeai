# Live Map, Pboots, Runbs, Orchestrate, and Live Display

The system **handles pboots and runbs**, **maps everything**, and can **orchestrate and direct** with **live report display**.

---

## Pboots and runs (process boots and run sessions)

- **Pboots:** Each process boot is recorded (boot_id, timestamp). Stored in memory; last 100 entries.
- **Runbs:** Each run session start is recorded (run_id, started_at). Current run is kept; last 100 runs in log.
- On API startup: one boot and one run are recorded automatically.

---

## Map everything

**GET /api/live/map** returns a single payload that maps the whole system:

| Field | Description |
|-------|-------------|
| `pboots` | Last 20 process boots (boot_id, at) |
| `runbs` | Last 20 run sessions (run_id, started_at) |
| `current_run` | Active run session if any |
| `state_version` | Canonical state version |
| `state_hash` | State hash |
| `twins` | All digital twins |
| `leaderboard` | Twins leaderboard |
| `capabilities` | Capability flags (perception, speech, trade, etc.) |
| `telemetry` | Observability metrics |
| `services` | Services from config (ports, labels) |
| `wiki_registry_path` | Path to twin registry (sync script output) |
| `config_loaded` | Whether bridge-wall.config.json was loaded |

Config is read from **config/bridge-wall.config.json** when present (services, twinsSync).

---

## Report live display

**GET /api/live/report** — Same as live map plus:

- `report_at` — UTC timestamp of the report
- `live_display: true` — Indicates use for live dashboards

Poll this endpoint (e.g. every 5 seconds) to drive a live display. No WebSocket required; optional **websocket /ws/{channel}** still available for real-time events.

---

## Orchestrate and direct

**GET /api/orchestrate/directives** — Returns a list of **directives** (actions to run). The API does not execute them; the frontend or a scheduler can display them and the user (or automation) runs the script.

Each directive has:

- `id` — e.g. sync_twins_wiki, audit, refresh_wallpaper, port_list
- `label` — Short label for UI
- `script` — PowerShell command (e.g. `.\scripts\sync-twins-wiki.ps1`)
- `cwd` — Working directory (repo root)
- `description` — What the action does

Example directives:

- Sync twins and wiki
- Full audit (audit-wall.ps1)
- Refresh wallpaper (update.ps1)
- Port status (port-handler.ps1 list)

---

## Config (optional)

In **config/bridge-wall.config.json**:

- **pbootsAndRuns** — `trackBoots`, `trackRuns`, `maxLogEntries`, `liveReportPollHintSec` (hint for poll interval, e.g. 5).

---

## Summary

| Need | Endpoint or behavior |
|------|------------------------|
| Handle pboots and runbs | Recorded on startup; returned in **GET /api/live/map** and **GET /api/live/report** |
| Map everything | **GET /api/live/map** (twins, state, services, capabilities, telemetry, wiki path, pboots, runbs) |
| Orchestrate and direct | **GET /api/orchestrate/directives** (list of scripts to run; no execution from API) |
| Report live display | **GET /api/live/report** (map + report_at; poll for live dashboard) |
