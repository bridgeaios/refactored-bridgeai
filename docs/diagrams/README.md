# Bridge AI OS — Diagrams

Diagrams (draw.io / mxGraph) for Bridge AI OS. Open `.drawio`, `.drawio.xml`, or `.dio` files in [draw.io](https://app.diagrams.net/) or in **VS Code** with the [Draw.io extension](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) (e.g. **New Draw.io Diagram** from command palette).

---

## System Map — sync live with Google & Draw.io

- **System Map (live):** [http://localhost:4201/system-map.html](http://localhost:4201/system-map.html) — Determinator Boot Agent; lists and links all systems (Determinator, Bridge API, Frontend, Gateway, Join, Agents, Dashboard, Docs, 50 Apps, Taurus, Console 3022, Production API) with live status. **Sync:** same map is reflected in Google Drive and Draw.io; open the shared diagram in [Google Drive](https://drive.google.com/file/d/1aebwruTyIYZYe8fkOn8R9njOtcL82z0c/view?usp=sharing) or in [app.diagrams.net](https://app.diagrams.net/) (File → Open from → Google Drive), or edit **system-map.drawio.xml** in this folder and re-upload to Drive to keep in sync.
- **system-map.drawio.xml** — Draw.io diagram of the same systems as the 4201 System Map; open in VS Code (Draw.io extension) or in app.diagrams.net. Edit here and optionally sync to Google Drive for team access.

---

## BRIDGE.DRAWIO and Digital Ecosystem

- **BRIDGE.DRAWIO** — Canonical Bridge AI OS architecture diagram. Edit in VS Code (hediet.vscode-drawio) or in [app.diagrams.net](https://app.diagrams.net/). Sync to [Google Drive](https://drive.google.com/drive) for team access.
- **Digital ecosystem diagram (shared):** [Google Drive — Digital Ecosystem Evolution](https://drive.google.com/file/d/1aebwruTyIYZYe8fkOn8R9njOtcL82z0c/view?usp=sharing) — open in draw.io or download to edit locally, then re-upload to Drive.
- **Four-layer self-expanding architecture:** Infrastructure → Data flows → Twin agents → Marketplace economy → AI evolution → Digital civilization. See **docs/SELF-EXPANDING-AI-NETWORK.md** and **docs/GLOBAL-TWIN-SWARM-ARCHITECTURE.md**.

---

## Digital Ecosystem Evolution (XML import)

- **digital-ecosystem-evolution.drawio.xml** — Same layers and flows (Cosmic Processes → … → Digital Civilization; Twin Perception/Decision/Simulation/Evolution; UBI, Task Allocation, Trading, Value Creation; Lineage, Trait Selection, Digital Ancestry, Intelligence Growth).

If you have the diagram as **URL-encoded** paste (e.g. from a draw.io share link starting with `%3CmxGraphModel%3E`):

1. Save the encoded string to **docs/diagrams/encoded_diagram.txt** (no other content).
2. Run:  
   `.\scripts\import-drawio-from-encoded.ps1`
3. Open **docs/diagrams/digital-ecosystem-evolution.drawio.xml** in draw.io.

---

## Sync and wiki

- **Twins + wiki sync:** `.\scripts\sync-twins-wiki.ps1` — writes `data/twin-registry.json`, `docs/WIKI-VERSIONS.md`, `docs/twin-wiki.html`. Does not modify this `docs/diagrams/` folder.
- **System diagram prompts:** See **docs/PROMPT-SYSTEM-DIAGRAM.md** for copy-paste prompts (Bridge API, Redis, Worker, global swarm, etc.).
