# Bridge Live Wall — Agent Definitions

Agents are first-class Spec Kit scenarios that orchestrate deterministic scripts, health checks, and telemetry. This file defines the SVG build orchestrator and related agents.

## Spec Kit Setup (one-time)

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify check
cd E:\BridgeAI\BridgeLiveWall
specify init --here --ai claude
```

Then run a full build via the agent path:

```powershell
pwsh -ExecutionPolicy Bypass -File "E:\A\run-svg-build.ps1"
```

---

## Agent: svg-build-orchestrator

- **Scope:** Maintain and run SVG-based system build for Bridge Live Wall.
- **Inputs:** repo state, Merkle root, config/bridge-wall.config.json, Taurus path, backend health.
- **Outputs:** Built SVG assets, updated logs, updated Merkle root, monetization telemetry events.

### Core Scenarios

#### 1. `/svg_build/full`
- Run `schedule-svg-build.ps1` → `run-svg-build.ps1`
- Validate backend health at `http://localhost:8000/api/health`
- Validate frontend at `http://localhost:3020` (default) or `http://localhost:3010`
- **3010 fix:** If root returns "cannot get", set `BRIDGE_FRONTEND_URL=http://localhost:3010` and `BRIDGE_FRONTEND_CHECK_PATH=/executive-dashboard.html`
- Write summary to `E:\A\logs\svg-build-*.log`

#### 2. `/svg_build/delta`
- Use `index.json` + Merkle root to compute delta
- Only rebuild changed SVGs (future enhancement)

### Tool: `run_svg_build`
- **Command:** `pwsh -ExecutionPolicy Bypass -File "E:\A\run-svg-build.ps1"`
- **Preconditions:** Backend health OK, Taurus path resolved, Omni CLI scan done (or explicitly skipped as non-blocking)

### Telemetry & Monetization
On successful SVG build, the agent MUST emit a `svg_build_completed` telemetry event to `POST /api/telemetry/events`, which the backend uses for billing and reputation.

---

## Agent: taurus-dashboard
- **Scope:** Taurus Showcase (port 4202) displays SVG build status.
- **Inputs:** `/api/live/map` (includes `svg_build` when present)
- **Requirement:** Taurus MUST show latest SVG build status, Merkle root, and last 5 builds from `E:\A\logs`.

---

## Paths (canonical)
- **Taurus core:** `C:\Users\supas\bridge-ai-os\taurus`
- **Bridge Live Wall:** `E:\BridgeAI\BridgeLiveWall`
- **SVG build root:** `E:\A`
- **Omni CLI:** Not present on this host — non-blocking for Bridge Live Wall deploy; required only for future multi-host orchestration.
