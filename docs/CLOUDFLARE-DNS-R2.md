# Cloudflare: Worker, DNS, and R2 — Apply audit suggestions

This doc covers: **creating and deploying the Bridge API Worker**, **DNS** (api.bridge-ai-os.tech), and **R2_BUCKET_NAME** for storage.

---

## 1. Worker (API at api.bridge-ai-os.tech)

A Cloudflare Worker in **worker/** serves health and optional R2. Deploy it, then point DNS to it.

### Create R2 bucket first

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → **R2** → **Overview** → **Create bucket**.
2. Bucket name: **bridge-live-wall** (must match `bucket_name` in `worker/wrangler.toml`).
3. Create the bucket.

### Deploy the Worker

```powershell
cd E:\BridgeAI\BridgeLiveWall\worker
npm install
npx wrangler login
npx wrangler deploy
```

Use the same Cloudflare account as `CLOUDFLARE_ACCOUNT_ID` in your `.env`. After deploy you get a `*.workers.dev` URL.

### Set R2_BUCKET_NAME in .env

In repo **.env** or **E:\AOE\.env** (or **.env1** then run `.\apply-env1.ps1`):

```env
R2_BUCKET_NAME=bridge-live-wall
```

Then run `.\audit-wall.ps1`; the “Cloudflare: set R2_BUCKET_NAME for storage” recommendation will clear once the value is non-empty and non-placeholder.

---

## 2. DNS: api.bridge-ai-os.tech

Point the domain to your Worker so the audit shows “DNS api.bridge-ai-os.tech resolves”.

### Option A: Worker custom domain (recommended)

1. Dashboard → **Workers & Pages** → **bridge-live-wall-api** → **Settings** → **Domains**.
2. **Add custom domain** → enter **api.bridge-ai-os.tech**.
3. Cloudflare will add the DNS record for the zone that owns `bridge-ai-os.tech`.

### Option B: Manual DNS record

1. Dashboard → select zone **bridge-ai-os.tech** → **DNS** → **Records**.
2. Add record:
   - **Type:** `CNAME`
   - **Name:** `api`
   - **Target:** `bridge-live-wall-api.<your-subdomain>.workers.dev` (see Workers & Pages → your worker → overview for the workers.dev hostname).
   - **Proxy:** Proxied (orange cloud).
3. In **Workers & Pages** → **bridge-live-wall-api** → **Settings** → **Domains**, add **api.bridge-ai-os.tech** as a custom domain so the Worker receives the request.

After propagation, run `.\audit-wall.ps1` to confirm “DNS api.bridge-ai-os.tech resolves”.

---

## 3. R2_BUCKET_NAME (summary)

| Step | Action |
|------|--------|
| Create bucket | R2 → Create bucket → name **bridge-live-wall**. |
| Worker | Already bound in `worker/wrangler.toml` as `BUCKET`. |
| .env | Set `R2_BUCKET_NAME=bridge-live-wall` in `.env` or E:\AOE\.env. |

---

## 4. Start local services (optional)

To run the four recommended services locally (Bridge API 8000, bridge-backend 3001, bridge-auth 3030, frontend 3020):

```powershell
cd E:\BridgeAI\BridgeLiveWall
.\scripts\start-recommended-services.ps1
```

Each service starts in a minimized window only if its port is not already listening.

---

## Summary

| Item | Action |
|------|--------|
| **Worker** | `cd worker` → `npm install` → `npx wrangler login` → `npx wrangler deploy`. |
| **R2 bucket** | Create **bridge-live-wall** in R2; set `R2_BUCKET_NAME=bridge-live-wall` in `.env`. |
| **DNS** | Add custom domain **api.bridge-ai-os.tech** to the Worker (or add CNAME + Worker route). |
| **Start services** | `.\scripts\start-recommended-services.ps1` for local API, bridge-backend, auth, frontend. |

After all steps, re-run `.\audit-wall.ps1` to confirm recommendations are cleared.
