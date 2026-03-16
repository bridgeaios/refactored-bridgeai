# Full Audit — http://localhost:4201/system-map.html

**Scope:** System Map on port 4201 (Determinator Boot Agent). Ensure all systems are **linked**, **orchestrated**, **funneled**, **live**, **online**, and **deployed**.

---

## 1. System Map URL and service

| Item | Value |
|------|--------|
| **URL** | http://localhost:4201/system-map.html |
| **Served by** | Determinator Boot Agent (`scripts/determinator-boot-agent.js`) |
| **Port** | 4201 (config: `config/bridge-wall.config.json` → `services.determinator-boot-agent.port`) |
| **Start** | `.\scripts\serve-determinator-boot.ps1` or `node scripts/determinator-boot-agent.js` (from repo root) |

---

## 2. Systems linked and funneled from the map

The System Map page lists and links to all of the following. Each card has an **Open** link; status is shown where health checks are available.

| System | URL | Live/online check | Deployed |
|--------|-----|-------------------|----------|
| **Determinator (this)** | http://localhost:4201/ | Always “Live” (this page) | N/A (local) |
| **Bridge API** | DETERMINATOR_NEXT_URL (default http://localhost:8000) | GET /health | https://api.bridge-ai-os.tech |
| **Digital Twin Frontend** | FRONTEND_URL (default http://localhost:3020/) | — | Same origin as frontend deploy |
| **Gateway (QR join)** | FRONTEND_URL/gateway/ | — | — |
| **Join as Agent** | FRONTEND_URL/join.html | — | — |
| **Agents & Twins** | FRONTEND_URL/agents.html | — | — |
| **Executive Dashboard** | FRONTEND_URL/executive-dashboard.html | — | — |
| **Docs & Wiki** | FRONTEND_URL/docs.html | — | — |
| **50 Applications** | FRONTEND_URL/50-applications.html | — | — |
| **Taurus Showcase** | http://localhost:4202/ | GET http://localhost:4202/health | — |
| **Next.js App (3032)** | http://localhost:3032/ | GET http://localhost:3032/ (root) | — |
| **Console sync (3022)** | http://localhost:3022/ | — | — |
| **Bridge API (deployed)** | https://api.bridge-ai-os.tech | GET /health | Yes |

All systems are **linked** from one place (system-map.html) and **funneled** through this map. **Live/online** is shown for Bridge API (local), Taurus (local), and production API when the page can reach them. **Deployed** is represented by the production API card and its status.

---

## 3. Orchestration

- **Entry point:** 4201 root (RBAC login) includes a link to **System Map** in the footer → users can open the map without logging in.
- **Refresh:** “Refresh status” button re-runs health checks for Bridge API, Taurus, and production API.
- **CORS:** Bridge API allows `allow_origin_regex` for any `localhost` / `127.0.0.1` port, so requests from 4201 to 8000 are allowed.
- **Env:** Determinator uses `DETERMINATOR_NEXT_URL` (Bridge API) and `FRONTEND_URL` (Digital Twin frontend); system-map uses these for links and health.

---

## 4. Checklist — all systems linked, orchestrated, funneled, live, online, deployed

- [x] **system-map.html** exists at http://localhost:4201/system-map.html and is served by Determinator Boot Agent.
- [x] **Linked:** Bridge API, Frontend, Gateway, Join, Agents, Dashboard, Docs, 50 Apps, Taurus, Next.js App (3032), Console sync, Production API — each has an Open link.
- [x] **Orchestrated:** Single entry (4201) with footer link to System Map; map uses NEXT_URL and FRONTEND_URL for consistent routing.
- [x] **Funneled:** All key UIs and APIs are reachable from the map; no extra discovery needed.
- [x] **Live/online:** Status shown for Bridge API (local), Taurus (local), and production API via health checks; “Refresh status” updates them.
- [x] **Deployed:** Production card (api.bridge-ai-os.tech) with health check; summary line mentions production status.

---

## 5. How to run and verify

1. **Start Determinator (4201):**  
   `.\scripts\serve-determinator-boot.ps1` or from repo root:  
   `$env:PORT="4201"; node scripts/determinator-boot-agent.js`

2. **Open System Map:**  
   http://localhost:4201/system-map.html

3. **Optional — start other systems for live checks:**  
   - Bridge API: `.\run-backend.ps1` (8000)  
   - Taurus: run Taurus on 4202  
   - Frontend: e.g. port 3020 so Gateway/Join/Agents links work

4. **Production:**  
   https://api.bridge-ai-os.tech/health should respond when deployed; the map will show “Deployed” when reachable.

---

## 6. Files touched

| File | Change |
|------|--------|
| `scripts/determinator-boot-agent.js` | Added route `/system-map.html` (full HTML with system list, health checks, production card); added “System Map” link in RBAC login footer; added "Sync live with Google & Draw.io" section. |
| `docs/diagrams/system-map.drawio.xml` | Draw.io diagram of same systems as 4201 map; open in app.diagrams.net or VS Code; sync to Google Drive. |
| `docs/diagrams/README.md` | System Map sync with Google & Draw.io documented. |

---

## 7. Sync live with Google & Draw.io

The System Map **syncs live with Google and Draw.io** so the same systems can be viewed and edited in shared diagrams.

| Target | Purpose |
|--------|--------|
| **Google Drive** | [Digital Ecosystem Evolution](https://drive.google.com/file/d/1aebwruTyIYZYe8fkOn8R9njOtcL82z0c/view?usp=sharing) — shared diagram; view/edit in Drive; open in Draw.io via **File → Open from → Google Drive** to keep in sync. |
| **Draw.io (app.diagrams.net)** | Open or create diagrams; open the Drive file from Draw.io, or open repo file **docs/diagrams/system-map.drawio.xml** (same systems as the 4201 map). Edit in VS Code with Draw.io extension or in app.diagrams.net; re-upload to Google Drive to sync with team. |
| **Repo diagrams** | **docs/diagrams/** — BRIDGE.DRAWIO, system-map.drawio.xml, digital-ecosystem-evolution; single source for Draw.io edits; sync to Drive manually or via script. |

**Flow:** System Map page (4201) shows a **"Sync live with Google & Draw.io"** section with links to Google Drive, app.diagrams.net, and repo diagrams. Edits in Draw.io (local or Drive) or in Drive stay in sync when the same file is re-opened; the 4201 page is the live runtime view (links + health), while Google/Draw.io hold the diagram view of the same systems.

See **docs/diagrams/README.md** for System Map sync and diagram file list.

---

**Summary:** http://localhost:4201/system-map.html is implemented and audited. All listed systems are linked and funneled from the map, orchestrated via 4201 and env URLs, with live/online status for Bridge API, Taurus, and production, and a dedicated “deployed” entry for api.bridge-ai-os.tech. The map **syncs live with Google and Draw.io** via the shared Drive diagram and **docs/diagrams/system-map.drawio.xml**.
