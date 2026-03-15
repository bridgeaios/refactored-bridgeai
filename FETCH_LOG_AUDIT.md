# fetch_log.json Audit Report

## Issues Found & Fixed

### 1. **Invalid Format (CRITICAL)**
- **Problem**: File had `.json` extension but contained JavaScript `fetch()` statements, not parseable JSON.
- **Fix**: Converted to valid JSON array: `[{ url, method, headers, body }, ...]`

### 2. **Syntax Artifacts**
- **Problem**: Each block ended with `}); ;` (redundant semicolons from DevTools "Copy as fetch").
- **Fix**: Normalized to proper JSON structure.

### 3. **Audit Summary**

| Metric           | Value |
|------------------|-------|
| Total entries    | 95    |
| Unique URLs      | 5     |
| App requests     | 92    |
| Extension reqs   | 3     |

**URLs observed:**
- `http://localhost:3010/api/health` — health checks (majority; consider throttling)
- `http://localhost:3010/models/HumanFace.glb` — 3D model
- `http://localhost:3010/models/RobotExpressive.glb` — 3D model
- `https://dl.polyhaven.org/.../studio_small_03_1k.hdr` — HDR env map
- `chrome-extension://...` — browser extension (excluded from app count)

### 4. **Recommendations**
- **Health poll throttling**: 90+ `/api/health` calls — consider 30s interval (see `checkBackendApi` in BridgeTwinV3).
- **Backup**: Original preserved as `fetch_log.json.bak`.

## How to Re-Fix

```bash
node scripts/fix-fetch-log.js
```

Run after re-exporting "Copy as fetch" from DevTools Network tab.
