# CLAUDE.md — AOE / Bridge AI OS (BridgeLiveWall)

Single system overview aligned with **BridgeLiveWall** config, System Map (4201), and docs. For AOE/Supaco planning alignment see **docs/INTEGRATION-NOTES-AOE-SUPACO.md**.

---

## Project Overview

AI-powered automation SaaS for marketing agencies and SMBs. Goal: first paying client → $17K MRR → $50K MRR. Pricing: Starter $499/mo, Growth $799/mo.

**This repo (BridgeLiveWall):** Bridge AI OS — Digital Twin frontend, Bridge API (8000), Determinator Boot Agent (4201), System Map, Gateway/Join, integrated platforms (Supac, Taurus, Wiki). Config: **config/bridge-wall.config.json**. Deployed API: **https://api.bridge-ai-os.tech**.

---

## Canonical Domain Map

### SUPACO (Product layer)

| Domain      | Role |
|------------|------|
| supaco.ai  | PRIMARY — API + Auth (JWT) |
| supaco.io  | ALIAS → supaco.ai (marketing/landing) |
| supaco.co.za | ALIAS → supaco.ai (SA variant) |
| supaco.team / .tech / .xyz | Brand protection |

### BRIDGE-AI-OS (Economic platform)

| Domain | Role |
|--------|------|
| bridge-ai-os.com | PRIMARY — Economic engine |
| bridge-ai-os.co.za | ALIAS → bridge-ai-os.com (SA variant) |
| bridge-ai-os.org | ALIAS → bridge-ai-os.com |
| bridge-ai-os.tech | ALIAS → bridge-ai-os.com (API worker: api.bridge-ai-os.tech) |
| bridge-ai-os.xyz | ALIAS → bridge-ai-os.com |
| gateway.bridge-ai-os.co.za | Public gateway endpoint |

### Treasury

| Domain | Role |
|--------|------|
| ai-os.co.za | Internal financial ops (Zero Trust) |

### Routing Matrix

- supaco.ai/* → API / Auth (JWT)
- supaco.io/* → Landing → supaco.ai
- bridge-ai-os.com/* → Economic Engine
- api.bridge-ai-os.tech → Bridge API (Worker)
- ai-os.co.za/internal/* → Treasury (admin only)

### Email

- support@bridge-ai-os.com  
- sales@bridge-ai-os.com  

---

## Config Mismatches (to fix)

- **website/wrangler.toml** — If redirect is .com → .tech: **WRONG**. .com is PRIMARY; .tech should redirect TO .com where appropriate. API at api.bridge-ai-os.tech is correct.
- **edge/wrangler.toml** — SPINE_ORIGIN should point to spine.bridge-ai-os.com (not .tech) when spine is on primary domain.
- **supaco.ai** — Not yet referenced in wrangler/vercel config in this repo; add when integrating.
- **vercel.json** — If builds from app-builder/, confirm app/ is the intended target for this repo.

---

## Key Subsystems

### BridgeLiveWall (this repo)

| Service | Port | Description |
|---------|------|-------------|
| **Bridge API** | **8000** | Python FastAPI; /api/*, /health; cortex, twins, live/report, services. See backend/app/routes/api.py. |
| **Determinator Boot Agent** | **4201** | RBAC login → next URL; **System Map** at http://localhost:4201/system-map.html. scripts/determinator-boot-agent.js. |
| **Digital Twin Frontend** | **3020** | Vite; index, gateway, join, agents, executive-dashboard, 50-applications, settings, docs. |
| **Console sync** | **3022** | Digital Twin console sync (config ports.registry). |
| **Taurus Showcase** | **4202** | Gamification / showcase; GET /health. config services.taurus-showcase. |
| **bridge-backend** | 3001 | Sovereign entry ladder (optional). |
| **bridge-auth** | 3030 | SIWE, JWT, Redis sessions (optional). |
| **Frontend dev** | 5173 | Vite dev server. |
| **Installer** | 7777 | Optional. |
| **Redis** | 6379 | Sessions/store. |

### AOE / other repos (reference)

| Service | Port | Note |
|---------|------|------|
| llm-gateway | 8080 | OpenRouter proxy; ledger, event bus. |
| bridge_ai_os (dashboard bridge) | **8082** | bridge_server.ps1 — NOT 8080. GET /api/stats, /api/agents. |
| v1/dashboard | 3000 or $DASHBOARD_PORT | Main app dashboard. In **integrated flows use 4201** (Determinator) as dashboard entry — see docs/INTEGRATION-NOTES-AOE-SUPACO.md. |
| Spine API | 4000 | v1/spine. |
| revenue-engine | 4001 | bridge_ai_os. |
| Next.js app | 3032 | Root. |
| Other v1/supaco | 3100, 3101, 3103, 3002, 3004, 3005, 3010, 3011 | Per AOE port map. |

---

## Port Map (canonical)

| Port | Service (BridgeLiveWall) |
|------|---------------------------|
| 8000 | Bridge API |
| 3020 | Frontend (Digital Twin, Gateway, Join, Agents, Dashboard, 50 Apps, Docs) |
| 4201 | Determinator Boot Agent — RBAC + **System Map** |
| 4202 | Taurus Showcase |
| 3022 | Console sync |
| 3000 | Dashboard (optional placeholder; integrated flows use 4201) |
| 3001 | bridge-backend |
| 3030 | bridge-auth |
| 5173 | Vite dev |
| 7777 | Installer |
| 6379 | Redis |

| Port | Service (AOE / other) |
|------|------------------------|
| 3000 | v1/dashboard |
| 3032 | Next.js |
| 4000 | Spine API |
| 4001 | revenue-engine |
| 8080 | llm-gateway |
| 8082 | bridge_server.ps1 |

---

## Local URLs (after boot)

Start Bridge API: `.\run-backend.ps1`. Start Determinator: `.\scripts\serve-determinator-boot.ps1` or `node scripts/determinator-boot-agent.js` (PORT=4201). Start frontend: from frontend dir `npm run dev` (5173) or prod on 3020.

| Service | URL |
|---------|-----|
| **System Map** | http://localhost:4201/system-map.html |
| **Determinator (RBAC)** | http://localhost:4201/ |
| **Bridge API** | http://localhost:8000 |
| **Frontend (Digital Twin)** | http://localhost:3020/ |
| **Gateway (QR join)** | http://localhost:3020/gateway/ |
| **Join as Agent** | http://localhost:3020/join.html |
| **Executive Dashboard** | http://localhost:3020/executive-dashboard.html |
| **50 Applications** | http://localhost:3020/50-applications.html |
| **Agents & Twins** | http://localhost:3020/agents.html |
| **Docs** | http://localhost:3020/docs.html |
| **Taurus** | http://localhost:4202/ |
| **Production API** | https://api.bridge-ai-os.tech |

---

## Wired flow (start → dashboard)

- **Entry:** Landing at http://localhost:3020/ or http://localhost:3020/landing.html (or 4201 → login → next URL).
- **Nav (hub):** Digital Twin | Gateway | Join | Agents | Executive Dashboard | 50 Applications | Settings | Docs | **System Map** (4201). Same nav on index, gateway, join, agents, dashboard, 50-applications, settings, docs.
- **Flow:** Landing → Gateway / Join → Digital Twin; System Map (4201) links all systems and shows live status; Dashboard (executive-dashboard.html on 3020). See **docs/AUDIT-FRONTEND-BACKEND-CLOUD.md**, **docs/AUDIT-SYSTEM-MAP-4201.md**.
- **System Map sync:** System Map (4201) syncs live with **Google Drive** and **Draw.io** — see docs/diagrams/README.md and system-map.html section “Sync live with Google & Draw.io”.

---

## Monitor / keep services up

- **BridgeLiveWall:** Use `.\run-backend.ps1` for API; `.\scripts\serve-determinator-boot.ps1` for 4201; start frontend and Taurus as needed. Optional: **scripts/start-recommended-services.ps1** (bridge-auth, frontend, dashboard). See STATUS-AND-CAPABILITIES.md.
- **AOE:** `npm run monitor` from AOE repo root; config scripts/monitor-services.config.json. See docs/MONITOR_AGENT.md in AOE.

---

## Known Issues / Next Steps

- **Vercel deploy** — app.supaco.ai may return CF 1016; verify CNAME → Vercel in Cloudflare DNS.
- **Edge worker** — Set SPINE_URL + VERCEL_URL secrets; `cd edge && npx wrangler deploy`.
- **supaco-api worker** — workers/supaco-api/; `npx wrangler deploy` and `wrangler secret put SPINE_API`.
- **bridge-ai-os.tech DNS** — Ensure CNAME/records in Cloudflare as needed for api.bridge-ai-os.tech.
- **Spine** — In-memory only; wallet/ledger/referral/leaderboard lost on restart; SQLite persistence needed.
- **Fund Management** — No idempotency keys on credit/revenue operations yet.

---

## Previously Reported — Now Fixed

- Payment keys (PAYSTACK, PAYPAL, RESEND) — set in .env.
- Welcome email — wired in v1/notifications (AOE).
- bridge_server.ps1 — on port 8082 (no conflict with 8080).
- CORS — fixed on llm-gateway and v1/dashboard (AOE).
- edge/wrangler.toml — uses SPINE_URL + VERCEL_URL (SPINE_ORIGIN removed).
- LLM Gateway ledger — rotation cap (e.g. 10k) added (AOE).
- **Dashboard port in integrated flows** — Use **4201** (Determinator) when referring to “Dashboard” in BridgeLiveWall/AOE alignment — see docs/INTEGRATION-NOTES-AOE-SUPACO.md.

---

## Environment Variables

**BridgeLiveWall (this repo):**

- Bridge API: PORT (8000), BRIDGE_* (cortex, replication, etc.). See .env and config.
- Determinator: PORT=4201, DETERMINATOR_NEXT_URL (e.g. http://localhost:8000), FRONTEND_URL (e.g. http://localhost:3020).
- Frontend: PORT, VITE_*; API base from settings or proxy to 8000.
- Auth (bridge-auth): BRIDGE_SIWE_*, REDIS_URL, NODE_ENV.

**AOE / shared (reference):**

- OPENROUTER_API_KEY, PAYSTACK_*, PAYPAL_*, RESEND_API_KEY, EMAIL_FROM, NEXTAUTH_*, DASHBOARD_URL — set as needed.
- SPINE_URL, VERCEL_URL — for edge worker deploy.
- SPINE_API — for supaco-api worker deploy.

---

## References

| Doc | Purpose |
|-----|---------|
| **config/bridge-wall.config.json** | Ports, services, api.baseUrls, integratedPlatforms, twinsSync, sensors. |
| **docs/AUDIT-SYSTEM-MAP-4201.md** | System Map (4201) audit; Google & Draw.io sync. |
| **docs/AUDIT-3032-NEXTJS.md** | Full audit for http://localhost:3032/ (Next.js app); connected and synced with entire system. |
| **docs/AUDIT-FRONTEND-BACKEND-CLOUD.md** | Frontend pages, backend API, cloud; System Map link. |
| **docs/INTEGRATION-NOTES-AOE-SUPACO.md** | Port alignment (4201 = Dashboard in flows), known issues, AOE refs. |
| **docs/diagrams/README.md** | System Map sync with Google & Draw.io; system-map.drawio.xml. |
| **STATUS-AND-CAPABILITIES.md** | Full status, services, deploy, capabilities. |
| **docs/MARVIN-FULL-RUNDOWN.md** | Agent context, APIs, run/deploy, docs. |
