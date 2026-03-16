# Integrated Platform — Bridge · Supac · Taurus · Wiki

All share **Digital Twins** and a single twin registry. Fully integrated system.

---

## Overview

| Platform | Role | Digital twin link |
|----------|------|--------------------|
| **Bridge AI OS** | Core API, frontend, gateway, reducers, state | `GET /api/twins`, `/api/twin/*`, `data/twin-registry.json` |
| **Wiki** | Versioned artifacts, C:\\Downloads scan, docs | `GET /api/wiki/registry`, `scripts/sync-twins-wiki.ps1` |
| **Taurus** | Gamification, dev support, showcase (port 4202) | Same registry; path: `C:\Users\supas\Videos\MM\M TAURUS` |
| **Supaco** | Observatory build | Same registry; path: `C:\Users\supas\Videos\supaco\supaco_observatory_build (1)` |

---

## Config (bridge-wall.config.json)

- **integratedPlatforms** — `bridge`, `wiki`, `taurus`, `supaco` with labels, URLs/paths, and `shareTwins: true` where applicable.
- **twinsSync** — `registryPath`, `wikiPath`, `endpoints` for twins, leaderboard, live report, wiki registry.

---

## QR scan to join as agent

- **Gateway:** `/gateway/` — “Scan to join as agent” card with QR code encoding the gateway URL. Scan → open gateway → connect wallet (SIWE) → join decentralized platform.
- **Join page:** `/join.html` — Dedicated page with QR and links to Gateway, Agents, Wiki, Digital Twin.
- **Flow:** QR → open URL → Gateway (wallet + SIWE) → Enter Digital Twin or Agents. All platforms use the same twin registry and state.

---

## Endpoints (Bridge API) used by all

- `GET /api/twins` — list twins  
- `GET /api/twins/leaderboard` — leaderboard  
- `GET /api/twin/shared-xml` — shared twin XML  
- `GET /api/wiki/registry` — twin registry (after sync-twins-wiki)  
- `GET /api/live/report` — live report (polity, governance, value_deltas)  
- `GET /api/human` — Human API (telemetry, mission, objectives)

---

## Sync and paths

- **Twin registry:** `data/twin-registry.json` (Bridge repo). Wiki sync script updates it from C:\\Downloads and repo.
- **Taurus path:** `C:\Users\supas\Videos\MM\M TAURUS` (config only; run Taurus from that path if needed).
- **Supaco path:** `C:\Users\supas\Videos\supaco\supaco_observatory_build (1)` (config only; run Supaco from that path if needed).

Ensure all three (Bridge, Taurus, Supaco) point to the same Bridge API base URL so they share the same twins and state.

---

## Cross-project alignment (AOE / Supaco)

For known issues, env vars, dashboard port (4201), workers, and DNS alignment with AOE/Supaco planning, see **INTEGRATION-NOTES-AOE-SUPACO.md**.
