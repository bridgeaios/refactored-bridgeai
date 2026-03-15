# All Keys Needed — From the Digital Twin

The Digital Twin key list is the **single source of truth** in this file; the same list is applied in the backend (`TWIN_ENV_KEY_CHECKS`), audit (`$keyChecks`), **.env.example**, and **apply-keys.ps1**.

Set keys in **E:\AOE\.env**, **E:\AOE\v1\.env**, or this repo’s **`.env`**.

---

## Critical (required for full audit / production)

| Variable | Label | Purpose |
|----------|--------|---------|
| `OPENAI_API_KEY` | OpenAI | OpenAI API |
| `HF_TOKEN` | Hugging Face | Hugging Face token |
| `HUGGING_FACE_API_KEY` | Hugging Face (alt) | Hugging Face API key (alternate) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Account | Cloudflare account ID |
| `JWT_SECRET` | JWT Secret | JWT signing secret |
| `JWT_SECRET_KEY` | JWT Secret Key | JWT secret (alternate name) |

*At least one of `JWT_SECRET` or `JWT_SECRET_KEY` must be set and non-placeholder for JWT to pass.*

---

## Optional

| Variable | Label | Purpose |
|----------|--------|---------|
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile | Turnstile CAPTCHA |
| `ELEVENLABS_API_KEY` | ElevenLabs | ElevenLabs TTS |
| `ANTHROPIC_API_KEY` | Anthropic | Anthropic API |
| `SMTP_PASSWORD` | SMTP | SMTP auth |
| `PAYPAL_CLIENT_ID` | PayPal | PayPal integration |
| `DISCORD_BOT_TOKEN` | Discord Bot | Discord bot |
| `R2_BUCKET_NAME` | Cloudflare R2 Bucket | R2 storage bucket name (optional; reduces audit rec when Cloudflare Account is set) |

---

## Other (not env keys)

- **AWS:** `~/.aws/credentials` (file must exist).
- **Ports:** 3000 (dashboard), 7777 (installer), 8000 (Bridge API).

---

## How to “ask the Digital Twin” for key status

- **API:** `GET http://localhost:8000/api/twin/env-keys`  
  Returns for each key: `key`, `label`, `critical`, `status` (`configured` | `missing` | `placeholder`). **No secret values are ever returned.**
- **Dashboard:** Open the **Twin** panel; the “Env API keys” section shows the same status.

---

## Search and apply (implement)

**Where these keys are used in the repo:**

| Location | Purpose |
|----------|---------|
| `backend/app/routes/api.py` | `TWIN_ENV_KEY_CHECKS` — GET /api/twin/env-keys |
| `backend/app/main.py` | Loads `.env` from repo, then E:\AOE\.env |
| `audit-wall.ps1` | `$keyChecks` — audit and wallpaper |
| `.env.example` | Template; copy to `.env` and fill |

**Apply steps:**

1. **Copy template (repo):**  
   `Copy-Item .env.example .env`  
   Then edit `.env` and set real values for each key.

2. **Or use E:\AOE (digital twin):**  
   Copy `.env.example` to `E:\AOE\.env` and fill there. Audit and backend read that path.  
   **To inject E:\AOE keys into the repo .env:** run `.\inject-env-from-aoe.ps1` — reads `E:\AOE\.env` (or `E:\AOE\v1\.env`) and merges into this repo’s `.env`.

3. **Verify:**  
   - Run `.\audit-wall.ps1` (without `BRIDGE_AUDIT_DEV`) to see critical/ok.  
   - Or call `GET http://localhost:8000/api/twin/env-keys` or open the Twin panel.

4. **Refresh wallpaper:**  
   `.\update.ps1` (uses `BRIDGE_AUDIT_DEV=1` by default for “all complete” until keys are set).

After adding keys, run `.\audit-wall.ps1` and `.\update.ps1` to refresh the wallpaper (or use `BRIDGE_AUDIT_DEV=1` for "all complete" until keys are set).

---

## How to use it

```powershell
# 1. Apply template (creates .env from .env.example if missing)
.\apply-keys.ps1

# 2. Edit .env and add your real keys

# 3. Verify (Twin API or audit)
# GET http://localhost:8000/api/twin/env-keys
# or: .\audit-wall.ps1

# 4. Refresh wallpaper
.\update.ps1
```
