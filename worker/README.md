# Bridge Live Wall — Cloudflare Worker

Worker for **api.bridge-ai-os.tech** with health check and optional R2 binding. Use the same bucket name as `R2_BUCKET_NAME` in your `.env`.

## Prerequisites

- Node 18+
- Cloudflare account (same as `CLOUDFLARE_ACCOUNT_ID` in .env)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/): `npm i -g wrangler` or use `npx wrangler`

## 1. Create R2 bucket

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → **R2** → **Create bucket**.
2. Bucket name: **bridge-live-wall** (or match `bucket_name` in `wrangler.toml`).

## 2. Deploy Worker

```bash
cd worker
npm install
npx wrangler login
npx wrangler deploy
```

## 3. Set R2_BUCKET_NAME in .env

In repo `.env` or `E:\AOE\.env`:

```env
R2_BUCKET_NAME=bridge-live-wall
```

## 4. DNS (api.bridge-ai-os.tech)

1. Dashboard → **Workers & Pages** → **bridge-live-wall-api** → **Settings** → **Domains** → **Add custom domain**.
2. Enter **api.bridge-ai-os.tech** and add the route. Cloudflare will create the DNS record.

Or manually: **DNS** → Add **CNAME** `api` → target `bridge-live-wall-api.<your-subdomain>.workers.dev` (or use **Workers Route** in DNS for the zone).

## Endpoints

| Method | Path        | Description                    |
|--------|-------------|--------------------------------|
| GET    | `/`, `/health` | Health (for audit/DNS check) |
| GET    | `/r2/list`  | List R2 object keys (if binding present) |

## Audit

After deploy and DNS:

- Run `.\audit-wall.ps1`: "DNS api.bridge-ai-os.tech resolves" and "Cloudflare R2 Bucket OK" (once `R2_BUCKET_NAME` is set).
