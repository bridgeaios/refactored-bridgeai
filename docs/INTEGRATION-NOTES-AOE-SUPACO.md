# Integration Notes — AOE / Supaco / Bridge alignment

Reference for keeping BridgeLiveWall in sync with AOE/Supaco planning and known issues.

---

## Port alignment

| Service | BridgeLiveWall config | AOE/planning note |
|---------|------------------------|-------------------|
| **Dashboard** | 3000 (optional) | **4201** in AOE STATE.md — Dashboard port corrected to 4201 (Determinator Boot Agent). Use 4201 when referring to “Dashboard” in integrated flows. |
| **Determinator Boot Agent** | 4201 | Same. |
| **Taurus** | 4202 | Same. |
| **Bridge API** | 8000 | Same. |
| **bridge_server.ps1** | — | Port **8082** (no conflict). |

---

## Known issues (from AOE CLAUDE.md / STATE.md)

- **Vercel CNAME** — not verified (Cloudflare 1016).
- **Workers** — edge worker + supaco-api worker need `wrangler deploy`.
- **DNS** — bridge-ai-os.tech missing some DNS records; add as needed in Cloudflare.
- **Spine** — in-memory only (no SQLite persistence).
- **Fund Management** — no idempotency keys yet.

Resolved in AOE: payment keys ✅, welcome email ✅, CORS ✅, bridge_server.ps1 port 8082 ✅, SPINE_ORIGIN ✅ (2026-03-07).

---

## Env vars

AOE planning uses ✅/⚠️ status per var. BridgeLiveWall keys (see STATUS-AND-CAPABILITIES.md, audit) — ensure shared vars (e.g. API base, auth URLs) match when integrating.

---

## Roadmap alignment

- **Phase 2** ✓ — complete (welcome email, etc.).
- **Phase 3** ✓ partial — source created, deploy still needed (workers).
- **Phase 5** ✓ — complete.

Use this when wiring Bridge ↔ Supaco ↔ Taurus so deploy and DNS assumptions stay consistent.

---

## Reference

- **BridgeLiveWall:** **CLAUDE.md** (project root) — system overview, domain map, port map, wired flow, config mismatches, known issues, env vars; aligned with config and System Map (4201). This doc (INTEGRATION-NOTES-AOE-SUPACO) aligns AOE planning with BridgeLiveWall.
- AOE project (external): CLAUDE.md (known issues, env vars), .planning/STATE.md (dashboard 4201, fixes log), .planning/ROADMAP.md (phase status).
- BridgeLiveWall: this doc, INTEGRATION-SUPAC-TAURUS-WIKI.md, config `integratedPlatforms`, AUDIT-FRONTEND-BACKEND-CLOUD.md, AUDIT-SYSTEM-MAP-4201.md.
