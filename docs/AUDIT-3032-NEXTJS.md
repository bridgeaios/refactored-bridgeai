# Full Audit — http://localhost:3032/ (Next.js App)

**Scope:** Ensure the Next.js app on port 3032 is **connected and synced with the entire system** — config, System Map, docs, audit script, and cross-links.

---

## 1. Service and URL

| Item | Value |
|------|--------|
| **URL** | http://localhost:3032/ |
| **Port** | 3032 |
| **Label** | Next.js App (root) |
| **Config** | `config/bridge-wall.config.json` → `services.nextjs-app` |
| **Env** | PORT, DASHBOARD_PORT (optional) |

---

## 2. Connection and sync with the system

### 2.1 Config (bridge-wall.config.json)

- **services.nextjs-app** — port 3032, label "Next.js App (root)", baseUrl http://localhost:3032.
- **ports.registry** — 3032 included so the port is recognized system-wide.
- **ports.defaults.nextjs-app** — 3032.

The audit script (`audit-wall.ps1`) reads `config.services` and checks each service port; 3032 is therefore included in the port check and will appear in audit results as "Next.js App (root) listening" or "not running".

### 2.2 System Map (4201)

- **System Map** at http://localhost:4201/system-map.html includes a card **Next.js App (3032)**.
- **Link:** Open → http://localhost:3032/
- **Live status:** Health check via GET http://localhost:3032/ (root); status shown as Live/Offline on the map.
- **Summary line:** "Next.js (3032): Live | Offline" in the map summary.

So 3032 is **linked**, **orchestrated**, and **funneled** from the System Map like the other systems.

### 2.3 Docs (frontend)

- **frontend/public/docs.html** — Ports section lists **3032 — Next.js App (root)** with link to http://localhost:3032/.
- **Frontend routes table** — Row "Next.js App (3032)" with link and description "Next.js root app — synced with system; linked from System Map".
- **System Map (4201)** linked from docs so users can reach the map (and from it, 3032).

### 2.4 CLAUDE.md and references

- **CLAUDE.md** — Port map and local URLs include 3032 (Next.js app); wired flow references System Map and linked systems.
- **docs/AUDIT-SYSTEM-MAP-4201.md** — Systems table includes **Next.js App (3032)** with URL and live check.

### 2.5 Draw.io / Google sync

- **docs/diagrams/README.md** and **system-map.drawio.xml** — System Map sync with Google & Draw.io includes the same set of systems; add "Next.js (3032)" to the diagram if you keep it in sync with the live map.

---

## 3. Checklist — connected and synced

- [x] **Config** — 3032 in `services.nextjs-app` and `ports.registry` / `ports.defaults`.
- [x] **Audit script** — audit-wall.ps1 checks 3032 (via config.services) and reports listening or not.
- [x] **System Map** — Next.js App (3032) card with Open link and live health check (GET /).
- [x] **Docs** — 3032 in Ports section and in Frontend routes table with link to http://localhost:3032/.
- [x] **CLAUDE.md** — 3032 in port map and local URLs.
- [x] **AUDIT-SYSTEM-MAP-4201.md** — Next.js App (3032) in systems table.

---

## 4. How to run and verify

1. **Start Next.js app (3032):** From the Next.js project root (e.g. AOE or app that binds to 3032), run the dev/server with `PORT=3032` or `DASHBOARD_PORT=3032` as configured.
2. **Open System Map:** http://localhost:4201/system-map.html — confirm **Next.js App (3032)** card shows **Live** when the app is running, **Offline** when not.
3. **Open 3032:** http://localhost:3032/ — confirm the app loads.
4. **Audit:** Run `.\audit-wall.ps1` — under OK you should see "Next.js App (root) (3032) listening" when 3032 is up; otherwise a recommendation "Next.js App (root) not running (port 3032)".
5. **Docs:** Open http://localhost:3020/docs.html (or frontend root)/docs.html — confirm link to Next.js App (3032) and System Map.

---

## 5. Files touched (for 3032 integration)

| File | Change |
|------|--------|
| `config/bridge-wall.config.json` | Added `services.nextjs-app` (port 3032), 3032 in `ports.registry` and `ports.defaults`. |
| `scripts/determinator-boot-agent.js` | Added Next.js App (3032) to System Map SYSTEMS array; health check GET http://localhost:3032/; summary line includes Next.js (3032) status. |
| `frontend/public/docs.html` | Added 3032 to Ports section with link; added Frontend routes row for Next.js App (3032); added System Map (4201) row. |
| `docs/AUDIT-SYSTEM-MAP-4201.md` | Added Next.js App (3032) to systems table. |
| `docs/AUDIT-3032-NEXTJS.md` | This audit document. |

---

## 6. Optional: Next.js app ↔ Bridge API

If the Next.js app on 3032 must call the Bridge API (e.g. for auth or data):

- **Bridge API** runs on http://localhost:8000 (or https://api.bridge-ai-os.tech in production).
- **CORS:** Backend allows localhost origins; requests from 3032 to 8000 are allowed.
- **Env in Next.js:** Set `NEXT_PUBLIC_API_URL` or equivalent to `http://localhost:8000` for local dev.
- **Human API / services:** GET /api/human and GET /api/services (if added) can be used from the Next.js app for dashboard or status.

---

**Summary:** http://localhost:3032/ is fully audited and **connected and synced** with the entire system: config, System Map (4201), docs, audit script, and CLAUDE.md. Start the Next.js app on 3032 and use the System Map to see live status and open it alongside all other systems.
