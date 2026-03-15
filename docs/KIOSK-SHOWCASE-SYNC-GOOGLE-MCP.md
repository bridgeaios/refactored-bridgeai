# Kiosk, Showcase, Sync & Google MCP — Design and Suggestions

**Date:** 2026-03-15

This doc ties together: **run/apply audit**, **kiosk mode**, **showcase** (what to display), **sync with other projects**, and **Google MCP** so one flow supports audit, deployment, and a kiosk that can sync and showcase content (including via Google MCP).

---

## 1. Run apply audit (one command)

Use this to run the audit and apply keys/paths without the full install/boot/test loop:

```powershell
.\run-apply-audit.ps1
```

Optional: up to 2 rounds of fix (inject from E:\AOE + apply-keys) if audit reports critical issues:

```powershell
.\run-apply-audit.ps1 -MaxRounds 2
```

**What it does:**

1. Runs **audit-wall.ps1** → writes `audit-results.json`.
2. If critical &gt; 0: runs **inject-env-from-aoe.ps1** (if E:\AOE\.env exists), then **apply-keys.ps1**, then re-audits (up to `MaxRounds`).
3. Always runs **apply-keys.ps1** once (ensures .env from .env.example if missing).
4. Runs **scripts\ensure-optional-paths.ps1** (D:\BridgeAI\... if D: exists).
5. Exits 0 if final audit has 0 critical.

**When to use:** After editing .env, adding keys, or syncing from another project (e.g. AOE). For full install + boot + audit + tests use **run-full-loop.ps1** instead.

---

## 2. Kiosk mode — concept

**Goal:** A dedicated, low-interaction view of Bridge AI OS suitable for a wall display or shared screen (office, demo, event).

**Suggested behavior:**

- **Full-screen:** No browser chrome; single full-viewport page (or Electron/PWA kiosk window).
- **Single URL:** e.g. `http://localhost:3020/kiosk` or `http://localhost:3020/#/kiosk` that loads a kiosk-specific route.
- **Content:** See “Showcase (what to display)” below. Optionally auto-rotate between:
  - Live map / system status
  - Mission board + founder objectives
  - Twin leaderboard + sensors (WiFi/mouse if enabled)
  - Worker / API health + audit summary
- **Interaction:** Minimal or none (read-only). Optional: tap/click to cycle view or refresh.
- **Resilience:** If API is down, show last cached payload + “Reconnecting…” (reuse logic from frontend audit).

**Implementation options:**

- Add a **kiosk.html** (or `frontend/public/kiosk.html`) that loads a minimal JS bundle that only fetches `/api/live/report` (and optionally `/api/sensors/wifi`, `/api/sensors/mouse`) and renders cards/sections. No 3D, no terminal input.
- Or add a **kiosk** route in the existing Vite app that renders the same content in a full-screen layout (sidebar/canvas hidden).

**Sync angle:** Kiosk content can be driven by the same APIs that “sync” with other projects (live map, twin registry, wiki). So “sync” and “showcase” share the same data sources.

---

## 3. Showcase — what to display (all included)

Suggested content for kiosk/showcase so it’s “all included”:

| Block | Source | Notes |
|-------|--------|------|
| **System status** | `/api/health` or `/api/live/report` | API + Redis + Worker (from operational interpretation). |
| **Audit summary** | `audit-results.json` (file) or an API that reads it | OK / Critical / Recommendations. Run **run-apply-audit.ps1** to refresh. |
| **Live map** | `GET /api/live/map` | pboots, runbs, state version, twins, capabilities, telemetry, **sensors** (wifi, mouse), services. |
| **Live report** | `GET /api/live/report` | Same as map + `report_at`; poll every 5–10s. |
| **Mission board** | Already in live map, or `GET /api/mission/board` | Backlog / In progress / Review / Done. |
| **Founder objectives** | `GET /api/founder-todo` | Objectives and completion (e.g. X/Y complete). |
| **Twins / leaderboard** | `GET /api/twins`, `GET /api/twins/leaderboard` | From live map or direct. |
| **Sensors** | `GET /api/sensors/wifi`, `GET /api/sensors/mouse` or `sensors` in live/report | WiFi RF, mouse (if boot sensors installed). |
| **Worker / edge** | From live map or health | e.g. “https://api.bridge-ai-os.tech” status. |

So “all included” means: **audit + live map + mission + founder TODO + twins + sensors + worker** in one kiosk view (single page or rotating sections).

---

## 4. Sync with other projects

Existing and suggested sync points so the kiosk (and the rest of the stack) stay aligned with other projects:

| Sync | What | How |
|------|------|-----|
| **Twin registry / wiki** | `data/twin-registry.json`, `docs/WIKI-VERSIONS.md` | **scripts/sync-twins-wiki.ps1** — syncs twins and versioned artifacts (e.g. from C:\Downloads). |
| **E:\AOE (digital twin)** | .env, config, optional services | **inject-env-from-aoe.ps1**; **launch-full-stack.ps1** with `BRIDGE_ROOT=E:\AOE` so frontend/backend/auth from AOE are used. |
| **Live map** | Single source of truth for status | Backend serves `/api/live/map` and `/api/live/report` from memory/Redis. Any client (frontend, kiosk, another repo’s dashboard) can poll and stay in sync. |
| **Config** | `config/bridge-wall.config.json` | Shared across scripts and backend. Other projects can copy or symlink this, or read it via an API if you add one. |
| **Audit results** | `audit-results.json` | Produced by **audit-wall.ps1**; **run-apply-audit.ps1** refreshes it. Kiosk or another app can read the file (or an API that exposes it) to show “last audit” in the showcase. |

**Suggestion:** Add a small **sync-status** section in the kiosk: “Last sync: &lt;time&gt;” for twin/wiki sync and “Last audit: &lt;time&gt;” from `audit-results.json` timestamp. Optionally trigger **sync-twins-wiki.ps1** or **run-apply-audit.ps1** on a schedule (Task Scheduler) so the kiosk always shows recent data.

---

## 5. Google MCP — how it fits (and what to use)

**What is Google MCP:**  
Model Context Protocol (MCP) servers that expose Google and Google Cloud services to AI apps (e.g. Cursor, Claude, Gemini CLI). They can be remote (Google Cloud) or local (e.g. [Google’s MCP GitHub repo](https://github.com/Google/mcp)).

**Relevant for Bridge “sync and showcase”:**

1. **Google Drive MCP (community / Playbooks)**  
   - **Use case:** Sync and showcase content.  
   - Store kiosk config, copy of audit summary, or “showcase” markdown/JSON in a **Google Drive folder** (e.g. “Bridge Kiosk” or “Bridge AI OS”).  
   - AI agents (Cursor with MCP client) can use the Drive MCP to **read** that folder (e.g. list files, read “kiosk-config.json” or “audit-summary.json”).  
   - Optional: a small script or Cloud Function that writes `audit-results.json` or a summary to Drive after **run-apply-audit.ps1** so the kiosk (or another app) can read “last audit” from Drive instead of the local file.  
   - **Setup:** OAuth, Drive API, `drive.readonly` (or read/write) scope. See e.g. [Playbooks Google Drive MCP](https://playbooks.com/mcp/modelcontextprotocol-gdrive), [MCP Repository GDrive](https://mcprepository.com/modelcontextprotocol/gdrive).

2. **Google Cloud MCP (BigQuery, Cloud Logging, etc.)**  
   - **Use case:** If you move telemetry or audit data to GCP (e.g. BigQuery, Cloud Logging), AI agents can query it via [Google Cloud MCP servers](https://docs.cloud.google.com/mcp/supported-products) (BigQuery, Cloud Logging, etc.).  
   - **Showcase:** Kiosk could show “Live from BigQuery” or “Last 10 audit events from Logging” if you add a pipeline (e.g. backend posts to Logging, or exports to BigQuery).

3. **Google Calendar MCP**  
   - **Use case:** “When to show what” on the kiosk.  
   - Store events like “Demo: Bridge AI OS” or “Kiosk: show only mission board 9–12”.  
   - Cursor (or a small scheduler) uses Calendar MCP to **list events** and decide which view to show or which config to load.  
   - Kiosk app (or a local script) could call an API that “resolves” current time → config (e.g. from Calendar or from a local schedule).

4. **Cursor + Google MCP**  
   - In Cursor, you enable an MCP server that points to Google Drive (or Google Cloud).  
   - You (or the agent) then use **tools** like “read file from Drive”, “list folder”, “create file” to:  
     - Sync: e.g. “Write audit-summary.json to Drive/Bridge Kiosk/”.  
     - Showcase: e.g. “Read kiosk-config.json from Drive” and use it to decide what the kiosk displays.  
   - So “sync and showcase with Google MCP” = **use Google MCP tools from Cursor (or another MCP host) to read/write Drive (and optionally Calendar) so the kiosk and other projects stay in sync and the kiosk can show content that lives in Drive.**

**Concrete suggestions:**

- **Minimal:** Add a “Kiosk” folder in Google Drive. After **run-apply-audit.ps1**, copy `audit-results.json` (or a short summary) into that folder (manual or script). In Cursor, use Google Drive MCP to read it when you want to “showcase” audit in docs or in another app.
- **Next step:** Implement a **kiosk page** (see above) that polls `/api/live/report` and, if you add an endpoint that returns “last audit summary”, show it. Later, that summary can be filled from a job that pushes to Drive and your API reads from Drive (or from a GCP service).
- **Optional:** Configure a Google Drive MCP server in Cursor and add a short **playbook** or **skill**: “After run-apply-audit, upload audit summary to Drive folder X” and “Read kiosk config from Drive folder X” so the kiosk and other projects that read from Drive stay in sync.

---

## 6. Suggested implementation order

1. **Run apply audit** — Done. Use **run-apply-audit.ps1** regularly.  
2. **Kiosk page** — Add `frontend/public/kiosk.html` (or a /kiosk route) that displays: audit summary (from file or API), live report, mission, founder TODO, twins, sensors, worker. Optional: auto-rotate.  
3. **Sync status on kiosk** — Show “Last audit” and “Last twin/wiki sync” timestamps; optionally link to running **run-apply-audit.ps1** and **sync-twins-wiki.ps1** on a schedule.  
4. **Google MCP (Drive)** — Configure Drive MCP in Cursor; create a “Bridge Kiosk” folder; optionally script upload of audit summary after **run-apply-audit.ps1** and use MCP to read it for docs or for the kiosk.  
5. **Calendar (optional)** — Use Google Calendar MCP to drive “what to show when” on the kiosk (e.g. different views per time or event).

---

## 7. References

- **Run apply audit:** `run-apply-audit.ps1` (repo root).  
- **Full loop (install, boot, audit, apply, verify, tests):** `run-full-loop.ps1`.  
- **Operational interpretation:** `docs/OPERATIONAL-INTERPRETATION.md`.  
- **Frontend audit (UX/UI):** `docs/FRONTEND-AUDIT-UX-UI.md`.  
- **Google Cloud MCP overview:** [Google Cloud MCP servers](https://docs.cloud.google.com/mcp/overview).  
- **Google Cloud MCP supported products:** [Supported products](https://docs.cloud.google.com/mcp/supported-products).  
- **Google MCP (local) repo:** [github.com/Google/mcp](https://github.com/Google/mcp).  
- **Google Drive MCP (community):** e.g. [Playbooks GDrive MCP](https://playbooks.com/mcp/modelcontextprotocol-gdrive), [MCP Repository GDrive](https://mcprepository.com/modelcontextprotocol/gdrive).
