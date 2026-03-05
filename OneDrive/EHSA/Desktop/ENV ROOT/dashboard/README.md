# Bridge AI OS — Dashboard (Treasury & Economic Engine)

Static dashboard for the Sovereign Economic Engine: live ledger, distribution routing (Agents 60% / **Treasury 20%** / Reinvest 10% / Ops 7% / Founder 3%), EVM bridge state machine, and agent list.

## Current system wiring

- **Gateway**: billing and usage from `gateway_url` (default `https://gateway.bridge-ai-os.co.za`).
- **Backend**: agents from `backend_url` (default `http://localhost:8080`). Your Bridge backend must expose `GET /api/agents`.
- **Config**: `config.json` in this folder. Edit for production (see below).

## config.json

| Key | Description |
|-----|-------------|
| `gateway_url` | Billing API base (e.g. `https://gateway.bridge-ai-os.co.za`) |
| `backend_url` | Backend API base for `/api/agents` (e.g. `https://your-backend.example.com` when deployed) |
| `api_key` | `x-api-key` sent to gateway `/billing` |
| `price_per_tps` | Price per TPS for daily revenue projection (default `0.20`) |
| `qr_target` | URL encoded in the QR code (default same as gateway host) |

For **production**: set `backend_url` to your live backend so the deployed dashboard can load agents (and ensure CORS allows your dashboard origin).

### Dashboard constants (index.html)

Billing and formula use named constants (no magic numbers): `TPS_WINDOW_SEC` = 86400, `SECONDS_PER_DAY` = 86400, `MIN_TPS` = 0.0001, `DIST` = { agents: 0.60, treasury: 0.20, reinvest: 0.10, ops: 0.07, founder: 0.03 }, `POLL_BILLING_MS` / `POLL_AGENTS_MS`, `TARGET_TPS` = 3356, `TARGET_DAILY_M` = 58.

## Sovereign Node — kill and start all

From repo root (ENV ROOT):

- **Kill all:** `.\sovereign_node_kill.ps1` — stops processes on ports 8080, 8082, 4000, 4200, 3031.
- **Start (this repo):** `.\sovereign_node_start.ps1` — starts Gateway (8080) and Dashboard (8082) in new windows. Spine (4000), Dashboard v1 (4200), Next.js (3031) and tunnel start from their own projects.

## Run locally

Serve the folder over HTTP (required for `config.json` and hash routing):

```bash
# From repo root
cd dashboard
python -m http.server 8082
# Or port 4200 (Dashboard v1):  python -m http.server 4200
```

- Open `http://localhost:8082` or `http://localhost:8082/index.html` (or `http://localhost:8082/#treasury` for the treasury section).
- **Port 4200:** Serve with `python -m http.server 4200` and open `http://localhost:4200/node.html` — `node.html` redirects to `index.html` so the same dashboard loads.

### Architecture diagram

- `architecture.html` — HTML wrapper that embeds `gateway-architecture.svg`.
- Open `http://localhost:8082/architecture.html` to view the live gateway/economic-engine layout.

## Deploy to a URL (Cloudflare Pages)

1. **Auth** (one-time):
   ```bash
   npx wrangler login
   ```

2. **Deploy** (from this repo root):
   ```bash
   npx wrangler pages deploy dashboard --project-name=bridge-dashboard
   ```

   First run may prompt to create the project. After deploy you get URLs like:
   - **https://master.bridge-dashboard-9p1.pages.dev** (alias)
   - **https://master.bridge-dashboard-9p1.pages.dev/#treasury** (treasury section)

3. **Production config**: Before deploying, edit `dashboard/config.json` and set `backend_url` to your production backend so the live dashboard can fetch agents. Ensure your backend and gateway allow CORS from your dashboard origin (see below).

## Next steps (production)

1. **Supaco domains**

   Recommended mapping:
   - **API**: `https://api.supaco.ai` → FastAPI/Worker gateway (exposes `/billing`, `/api/distribution/run`, `/api/usage/bump`, `/api/treasury/summary`, `/api/agents`, `/health`).
   - **Business UI**: `https://business.supaco.ai` → Cloudflare Pages project `bridge-dashboard` (this folder).
   - **Treasury UI**: `https://treasury.supaco.ai` → CNAME/redirect to `https://business.supaco.ai/#treasury` (via Cloudflare Page Rule/Redirect or Worker).

2. **Config**

   `dashboard/config.json` is already set for production:
   ```json
   {
     "gateway_url": "https://api.supaco.ai",
     "backend_url": "https://api.supaco.ai",
     "api_key": "client1",
     "price_per_tps": 0.20,
     "qr_target": "https://business.supaco.ai/public/"
   }
   ```

3. **CORS**

   Allow these origins on your gateway/backend (e.g. `CORS_ORIGINS`):
   - `https://business.supaco.ai`
   - `https://treasury.supaco.ai`
   - `https://master.bridge-dashboard-9p1.pages.dev` (Pages alias, optional).

4. **Edge Worker (bridge-ai-os-edge)**

   **Deployed:** `https://bridge-ai-os-edge.thebridgeaiagency.workers.dev`

   - **Code:** `edge/` — `wrangler.toml` (routes + `BACKEND_URL`) and `edge/src/index.js` (CORS, x-api-key, forward to backend).
   - **Backend:** `BACKEND_URL` in wrangler.toml is set to `https://gateway.bridge-ai-os.co.za` (not a Docker hostname); worker forwards requests there.
   - **Routes (wrangler.toml):** One `[[routes]]` per domain with `pattern = "host/*"` and `zone_name`. **api.supaco.ai is excluded** (Supa-Claw) to avoid loops. Included: supaco.ai, www.supaco.ai, supaco.io, supaco.co.za, supaco.team, supaco.tech, supaco.xyz, bridge-ai-os.com, bridge-ai-os.co.za, gateway.bridge-ai-os.co.za, bridge-ai-os.org, bridge-ai-os.tech, bridge-ai-os.xyz.
   - **Custom Domains (Dashboard):** Workers & Pages → **bridge-ai-os-edge** → **Triggers** → **Custom Domains** → Add **business.supaco.ai** and **treasury.supaco.ai**.
   - **CORS:** Worker adds `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, and `Access-Control-Allow-Headers` (including **x-api-key**) on all responses and on OPTIONS preflight.

   **Deploy:**
   ```bash
   cd edge
   npx wrangler deploy
   ```

   **Verify after deploy:** Call health on a routed domain and check CORS headers (preflight should return `Access-Control-Allow-Headers` with `x-api-key`):
   ```bash
   curl -I -X OPTIONS "https://gateway.bridge-ai-os.co.za/health" -H "Origin: https://business.supaco.ai" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: x-api-key"
   curl -s "https://gateway.bridge-ai-os.co.za/health"
   ```
   Or use `https://bridge-ai-os.co.za/health` if that domain is routed to the worker.

## DNS / custom domains conflict

If **Pages URL works** (`https://master.bridge-dashboard-9p1.pages.dev` → 200) but **custom domains** (`business.supaco.ai`, `treasury.supaco.ai`) show Active in Pages yet return 404 or wrong content:

- **Cause:** Those domains are already configured in **Supa-Claw** (Worker). Adding them to the Pages project creates a conflict.
- **Fix:** In Cloudflare Dashboard → **Pages** → **bridge-dashboard** → **Custom domains** → **Delete** `business.supaco.ai` and `treasury.supaco.ai`. Let Supa-Claw handle routing for those hostnames.
- **Use now:** `https://master.bridge-dashboard-9p1.pages.dev` is the working dashboard URL.

## One-step fix: DNS for business.supaco.ai

The Worker can be deployed and **supaco.ai** / **gateway.bridge-ai-os.co.za** can already hit it, but **business.supaco.ai** will not reach the Worker until DNS points it at the edge. Without this record, the dashboard shows **"Gateway stats error: Failed to fetch"** because polling never reaches the gateway.

**In Cloudflare Dashboard:**

1. **Cloudflare** → **supaco.ai** → **DNS**
2. **Create record:**
   - **Type:** CNAME  
   - **Name:** `business`  
   - **Target:** `bridge-ai-os-edge.thebridgeaiagency.workers.dev`  
   - **Proxy:** ON (orange cloud)  
   - **TTL:** Auto  
3. Save. Propagation is usually 10–30 seconds.

**Verify (PowerShell):**
```powershell
ipconfig /flushdns
Invoke-WebRequest https://business.supaco.ai/health -UseBasicParsing
```
Expected: `StatusCode : 200` and body like `{"status":"healthy","worker":"bridge-ai-os-edge"}`.

**Optional — treasury.supaco.ai:** Add a second CNAME if you want treasury to hit the Worker (same target, Name: `treasury`), or use a redirect rule. The Worker then 301s treasury → business.supaco.ai/#treasury.

**Network topology once DNS is set:**

```
business.supaco.ai
supaco.ai
gateway.bridge-ai-os.co.za
        ↓
Cloudflare Worker (bridge-ai-os-edge)
        ↓
Bridge AI OS Gateway
        ↓
Spine / Bridge / LLM services
```

## Still required in Cloudflare Dashboard

Worker is deployed with routes in **wrangler.toml**. These steps must be done manually:

**1. Attach Worker** (see above): Add **business.supaco.ai** and **treasury.supaco.ai** as Custom Domains on **bridge-ai-os-edge**.

**2. DNS CNAMEs** (Cloudflare → supaco.ai → DNS → Add). **business.supaco.ai** (required for dashboard to stop "Failed to fetch"):

| Name     | Type  | Target                                              | Proxy  |
|----------|-------|-----------------------------------------------------|--------|
| `business` | CNAME | `bridge-ai-os-edge.thebridgeaiagency.workers.dev` | ON (orange) |
| `treasury`  | CNAME | (same as above, optional)                         | ON     |

Other domains (app, bridge-ai-os.tech) as needed:

| Record | Type | Target |
|--------|------|--------|
| `app` | CNAME | `bridge-ai-4dy369xk5-thebridgeaiagency-1199s-projects.vercel.app` |
| (bridge-ai-os.tech zone) | CNAME | `bridge-ai-os.com` |

**3. Remove from Pages** (avoid conflicts):

- Pages → **bridge-dashboard** → **Custom domains**
- Remove **business.supaco.ai** and **treasury.supaco.ai** (Worker will serve them)

## Test checklist (Supaco)

| Check | URL | Expected |
|-------|-----|----------|
| API health | `https://api.supaco.ai/health` | JSON `{"status":"healthy",...}` |
| API billing | `https://api.supaco.ai/billing` (with `x-api-key: client1`) | JSON `summary`, `by_endpoint`, `per_agent` |
| Business UI | `https://business.supaco.ai/` | Dashboard (same as Pages app) |
| Treasury | `https://treasury.supaco.ai/` | Redirect to `business.supaco.ai/#treasury` or same app |
| Pages alias | `https://master.bridge-dashboard-9p1.pages.dev/` | Dashboard; uses `config.json` → api.supaco.ai |
