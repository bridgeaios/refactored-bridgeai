# DOMAIN ALLOCATION - BRIDGE AI OS

## AUTHORITY ZONES

| Domain | Type | Purpose | Access |
|--------|------|---------|--------|
| **bridge-ai-os.com** | PRIMARY | Main economic platform | Public |
| bridge-ai-os.co.za | ALIAS | SA variant | Public |
| bridge-ai-os.org | ALIAS | Brand protection | Public |
| bridge-ai-os.tech | ALIAS | Brand protection | Public |
| bridge-ai-os.xyz | ALIAS | Brand protection | Public |

## COMMAND LAYER

| Domain | Type | Purpose | Access |
|--------|------|---------|--------|
| **supaco.io** | PRIMARY | Command / Landing | Public |
| supaco.ai | ALIAS | Short form | Public |
| supaco.co.za | ALIAS | SA variant | Public |
| supaco.team | ALIAS | Brand protection | Public |
| supaco.tech | ALIAS | Brand protection | Public |
| supaco.xyz | ALIAS | Brand protection | Public |

## TREASURY

| Domain | Type | Purpose | Access |
|--------|------|---------|--------|
| **ai-os.co.za** | TREASURY | Internal financial ops | Zero Trust |

---

## ROUTING LOGIC

```
User → Cloudflare DNS → bridge-edge Worker → Route Decision

bridge-ai-os.com/*     → /api/* (economic)
supaco.io/*            → Landing / Dashboard
ai-os.co.za/internal/* → Treasury (admin only, Zero Trust)
```

---

## ACQUISITION STATUS

| Domain | Status | Action |
|--------|--------|--------|
| bridge-ai-os.com | ❌ NEEDS BUY | Purchase |
| supaco.io | ❌ NEEDS BUY | Purchase |
| ai-os.co.za | ❌ NEEDS BUY | Purchase |
| supaco.ai | ❌ NEEDS BUY | Purchase |
| *.co.za variants | ❌ NEEDS BUY | Purchase |
| .org/.tech/.xyz | ❌ NEEDS BUY | Purchase |

---

## CERTIFICATES

All domains will use Cloudflare-managed SSL (Full Strict).

---

*Generated: 2026-03-02*
