# Founder TODO — Digital Twin Wallpaper

Live TODO list linked to the digital twin wallpaper. When objectives are met, the wallpaper updates on the next refresh.

## Files

| File | Purpose |
|------|---------|
| `founder-todo.json` | Source of truth. Objectives with id, title, status, completedAt. |
| `audit-wall.ps1` | Full audit: keys (OpenAI, Hugging Face, Cloudflare), AWS, DNS, ports. Writes audit-results.json. |
| `audit-results.json` | Audit output. Read by update.ps1 for Critical Recommendations. |
| `update.ps1` | Runs audit, reads founder-todo + phases + audit; renders twin_wall.png; applies wallpaper. |
| `mark-objective.ps1` | CLI: mark an objective complete. |
| `run-wallpaper-live.ps1` | Runs update.ps1 every 60s. Start at login for live wallpaper. |

## How to mark an objective complete

**CLI:**
```powershell
.\mark-objective.ps1 -Id "obj-1"
```

**API (backend on port 8000):**
```powershell
Invoke-RestMethod -Method PATCH -Uri "http://localhost:8000/api/founder-todo/obj-1/complete"
```

**Frontend:** Click "Complete" in the Founder Objectives panel (Digital Twin UI, port 3020).

## Audit (audit-wall.ps1)

Checks run automatically before each wallpaper update. Displays on wallpaper:

**Critical:** Missing keys, placeholder values, AWS credentials, JWT
**Recommendations:** Optional keys, ports not listening, DNS (api.bridge-ai-os.tech), Cloudflare R2

| Check | Source |
|-------|--------|
| **Critical:** OPENAI_API_KEY, HF_TOKEN, HUGGING_FACE_API_KEY, CLOUDFLARE_ACCOUNT_ID, JWT_SECRET, JWT_SECRET_KEY | E:\AOE\.env or repo `.env` |
| **Optional:** TURNSTILE_SECRET_KEY, ELEVENLABS_API_KEY, ANTHROPIC_API_KEY, SMTP_PASSWORD, PAYPAL_CLIENT_ID, DISCORD_BOT_TOKEN | E:\AOE\.env or repo `.env` |
| AWS credentials | ~/.aws/credentials |
| Ports 3000, 7777, 8000 | netstat |
| DNS api.bridge-ai-os.tech | Resolve-DnsName |

Full list and apply steps: **KEYS-REQUIRED.md**. Template: **.env.example**. Apply template: `.\apply-keys.ps1` (copies to `.env` and optionally `E:\AOE\.env`, `E:\AOE\v1\.env`).

## Flow

1. run-wallpaper-live.ps1 runs update.ps1 every 60s
2. update.ps1 runs audit-wall.ps1 → audit-results.json
3. update.ps1 reads founder-todo.json + phases.json + audit-results.json → draws twin_wall.png → applies wallpaper
4. Wallpaper reflects current state. Deterministic. No magic.
