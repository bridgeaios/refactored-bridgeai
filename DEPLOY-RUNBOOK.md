# Bridge AI OS — Phase 6 Deployment Runbook

**Target:** `102.208.228.44` (Ubuntu 22.04.5 LTS)  
**Domain:** `bridge-ai-os.com`  
**Status:** Ready to execute — run steps in order

---

## Pre-flight Checklist

- [ ] `scripts/backup_before_merge.sh` run and backup verified
- [ ] `supaclaw-core.js` deployed (via `deploy-supaclaw.sh`)
- [ ] Neo4j password rotated (done 2026-04-05)
- [ ] `.env.unified` populated with all live credentials (no `<PLACEHOLDERS>`)
- [ ] DNS TTL for `bridge-ai-os.com` set to 300s (do this 24h ahead)
- [ ] Payment webhook sandbox test at Paystack/PayPal/PayFast dashboards

---

## Step 1 — Backup (on VPS)

```bash
ssh root@102.208.228.44
cd /var/www/bridgeai
bash backend/scripts/backup_before_merge.sh
# Confirm: backup tarball appears in ./backups/
ls -lh backups/
```

---

## Step 2 — Sync unified codebase to VPS

Run from **local machine** (`E:\BridgeAI\BridgeLiveWall\`):

```bash
rsync -avz --progress \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='.env' \
  ./ root@102.208.228.44:/var/www/bridgeai-unified/
```

---

## Step 3 — Upload .env.unified as production .env

```bash
scp E:/BridgeAI/BridgeLiveWall/.env.unified \
  root@102.208.228.44:/var/www/bridgeai-unified/.env
```

---

## Step 4 — Run database migration (on VPS)

```bash
ssh root@102.208.228.44
cd /var/www/bridgeai-unified

# Install Python deps if first deploy
pip install -r backend/requirements.txt

# Run unified schema migration (idempotent — safe to re-run)
python backend/scripts/init_unified_db.py

# Verify tables created
psql "$DATABASE_URL" -c "\dt" | wc -l
# Should report ~38 tables
```

---

## Step 5 — Start unified Docker stack

```bash
ssh root@102.208.228.44
cd /var/www/bridgeai-unified

# Pull latest images
docker compose -f docker-compose.unified.yml pull

# Start all services (detached)
docker compose -f docker-compose.unified.yml up -d

# Watch startup
docker compose -f docker-compose.unified.yml logs -f --tail=50
```

**Expected healthy services:**
```
caddy       — running
frontend    — running
backend     — running  (health: /api/health → 200)
auth        — running
state_loop  — running
svg_engine  — running
postgres    — healthy
redis       — healthy
neo4j       — started
prometheus  — running
grafana     — running
```

---

## Step 6 — Run endpoint smoke test

```bash
ssh root@102.208.228.44
cd /var/www/bridgeai-unified

pip install httpx rich

# Test against local backend (no DNS dependency yet)
BRIDGE_DEV_SECRET=<your-dev-secret> \
  python backend/scripts/test_all_endpoints.py http://localhost:8000

# All endpoints should return OK or 401 (auth-required without token)
# Zero 5XX or ERR — if any, fix before DNS switch
```

---

## Step 7 — Update payment webhook URLs

In each payment provider dashboard, update webhook URL to:

| Provider | Webhook URL |
|----------|-------------|
| Paystack | `https://api.bridge-ai-os.com/api/payments/webhook/paystack` |
| PayPal   | `https://api.bridge-ai-os.com/api/payments/webhook/paypal` |
| PayFast  | `https://api.bridge-ai-os.com/api/payments/webhook/payfast` |
| Crypto   | `https://api.bridge-ai-os.com/api/payments/webhook/crypto` |

> **Do this BEFORE flipping DNS** so webhooks work immediately after cutover.

---

## Step 8 — Update Clerk domain

1. Clerk Dashboard → Settings → Domains
2. Add `bridge-ai-os.com` as production domain
3. Update `VITE_CLERK_PUBLISHABLE_KEY` in `.env.unified` if key changes

---

## Step 9 — DNS cutover

At your DNS provider (Cloudflare recommended):

```
# A records
bridge-ai-os.com        A  102.208.228.44  TTL=300
*.bridge-ai-os.com      A  102.208.228.44  TTL=300

# Redirects from old domains (if not handled by Caddy)
ai-os.co.za             CNAME → bridge-ai-os.com
bridge-ai-os.co.za      CNAME → bridge-ai-os.com
```

Caddy handles the 301 redirects for old domains (already in Caddyfile).  
Auto-TLS fires within ~60 seconds of DNS propagation.

---

## Step 10 — Post-cutover smoke test

```bash
# Test via public domain (confirms Caddy + TLS + routing all working)
BRIDGE_DEV_SECRET=<your-dev-secret> \
  python backend/scripts/test_all_endpoints.py https://api.bridge-ai-os.com

# Test redirect from old domain
curl -I https://ai-os.co.za
# Expect: 301 → https://bridge-ai-os.com

# Test WebSocket
wscat -c wss://bridge-ai-os.com/ws/hub
# Expect: connection established, state stream messages
```

---

## Step 11 — Verify monitoring

```bash
# Grafana
open https://monitor.bridge-ai-os.com
# Login: admin / $GRAFANA_ADMIN_PASSWORD

# Prometheus targets (should all be UP)
curl http://localhost:9090/api/v1/targets | python3 -m json.tool | grep '"health"'
```

---

## Step 12 — 24h watch

```bash
# Stream all service logs
docker compose -f docker-compose.unified.yml logs -f

# PM2 processes (if any still on PM2)
pm2 list

# Supaclaw invariants
curl https://bridge-ai-os.com/api/core/invariants | python3 -m json.tool

# Treasury gate status (active after 1000 clean cycles)
curl -H "Authorization: Bearer <token>" \
  https://api.bridge-ai-os.com/api/treasury/status
```

---

## Rollback (if critical failure)

```bash
# 1. Revert DNS to old infrastructure (instant — 300s TTL)
# 2. Revert payment webhooks to old URLs
# 3. Old services still running — point DNS back to original IPs

# Old VPS services (do NOT stop until 7-day stability confirmed)
pm2 list  # shows old stack
```

---

## Post-Deployment Checklist (7 days)

- [ ] Zero 5XX errors in Grafana for 24h
- [ ] Payment webhooks receiving (check provider dashboards)
- [ ] Supaclaw treasury gate active (1000 clean cycles)
- [ ] Clerk auth working on new domain
- [ ] SIWE wallet login working
- [ ] Neo4j knowledge graph accessible
- [ ] Email sending via Brevo working
- [ ] All 21 React pages rendering
- [ ] Avatar 3D system loading in browser
- [ ] Archive old codebases (do NOT delete)
