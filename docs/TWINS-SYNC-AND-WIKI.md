# Digital Twins Sync and Wiki-Style Version Control

Stay synced with **all digital twins on this system**, with **display and access to all versions** and **wiki-type version control**. Versioned artifacts in **C:\Downloads** (and optional C:\Downloads root) are included.

---

## What gets synced

1. **From Bridge API (localhost:8000)**  
   - All twins: `GET /api/twins`  
   - Leaderboard: `GET /api/twins/leaderboard`  
   - State version: `GET /api/state/snapshot`  
   - Shared XML: `GET /api/twin/shared-xml`  
   - Env keys status: `GET /api/twin/env-keys`  

2. **From C:\Downloads (and C:\Downloads)**  
   - Files matching: `*bridge*`, `*living*`, `*twin*`, `*neural*`, `*.html`, `manifest.json`, `*.json`  
   - Each file is listed with name, last modified, size, and full path.

---

## How to sync

```powershell
.\scripts\sync-twins-wiki.ps1
```

- Writes **data/twin-registry.json** (full registry).  
- Writes **docs/WIKI-VERSIONS.md** (wiki-style version list).  
- Writes **docs/twin-wiki.html** (single-page viewer; open in browser for all versions and “Open” links to artifacts).

Run this whenever you want to refresh twins and versioned artifacts (e.g. after new Downloads or API changes).

---

## How to view and access all versions

| What | Where |
|------|--------|
| **Wiki-style version list** | **docs/WIKI-VERSIONS.md** |
| **Single-page viewer (all twins + all versions)** | **docs/twin-wiki.html** (open in browser) |
| **Machine-readable registry** | **data/twin-registry.json** |
| **From running backend** | **GET http://localhost:8000/api/wiki/registry** (returns registry when present) |

---

## Config (optional)

In **config/bridge-wall.config.json**, section **twinsSync**:

- **apiBaseUrl** — Bridge API base (default `http://localhost:8000`).  
- **downloadsPaths** — List of folders to scan (default: `C:\Users\%USERNAME%\Downloads`, `C:\Downloads`).  
- **versionedPatterns** — File name patterns to include.  
- **registryPath** — Where to write `twin-registry.json`.  
- **wikiPath** — Where to write `WIKI-VERSIONS.md`.

---

## Notes

- If the Bridge API is not running when you run the sync script, twin/leaderboard/state sections will show “API unreachable”; re-run sync when the API is up to fill them.  
- Downloads artifacts are always scanned and listed regardless of API.  
- **twin-wiki.html** embeds the registry so it works offline (e.g. opened from disk). “Open” links use `file://` to open the artifact in the default app.
