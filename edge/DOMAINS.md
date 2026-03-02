# DOMAIN ALLOCATION - BRIDGE AI OS

## PRIMARY (API KEY HOLDER)

| Domain | Type | Purpose | Status |
|--------|------|---------|--------|
| **supaco.ai** | PRIMARY | API + Command layer | ✅ OWNED |

All other domains route through supaco.ai for authentication.

---

## COMMAND LAYER (supaco.ai variants)

| Domain | Type | Purpose | Status |
|--------|------|---------|--------|
| **supaco.ai** | PRIMARY | Main API + Landing | ✅ OWNED |
| supaco.io | ALIAS | Marketing / Landing | ✅ OWNED |
| supaco.co.za | ALIAS | SA variant | ✅ OWNED |
| supaco.team | ALIAS | Brand protection | ✅ OWNED |
| supaco.tech | ALIAS | Brand protection | ✅ OWNED |
| supaco.xyz | ALIAS | Brand protection | ✅ OWNED |

---

## ECONOMIC PLATFORM

| Domain | Type | Purpose | Status |
|--------|------|---------|--------|
| **bridge-ai-os.com** | PRIMARY | Economic platform | ✅ OWNED |
| bridge-ai-os.co.za | ALIAS | SA variant | ✅ OWNED |
| bridge-ai-os.org | ALIAS | Brand protection | ✅ OWNED |
| bridge-ai-os.tech | ALIAS | Brand protection | ✅ OWNED |
| bridge-ai-os.xyz | ALIAS | Brand protection | ✅ OWNED |

---

## TREASURY

| Domain | Type | Purpose | Access |
|--------|------|---------|--------|
| **ai-os.co.za** | TREASURY | Internal financial ops | Zero Trust |

---

## ROUTING MATRIX

```
supaco.ai/*              → API / Auth (JWT)
supaco.io/*              → Landing → supaco.ai
bridge-ai-os.com/*       → Economic Engine
ai-os.co.za/internal/*  → Treasury (admin only)
```

---

## ACTION REQUIRED

1. Add all domains to Cloudflare
2. Point nameservers to Cloudflare
3. Deploy bridge-edge Worker
4. Set JWT_SECRET / JWT_PUBLIC_KEY
5. Enable Logpush to R2

---

*Updated: 2026-03-02*
