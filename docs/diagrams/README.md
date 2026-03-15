# Bridge AI OS — Diagrams

Diagrams (draw.io / mxGraph) for Bridge AI OS. Open `.drawio`, `.drawio.xml`, or `.dio` files in [draw.io](https://app.diagrams.net/) or in **VS Code** with the [Draw.io extension](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) (e.g. **New Draw.io Diagram** from command palette).

---

## BRIDGE.DRAWIO and Digital Ecosystem

- **BRIDGE.DRAWIO** — Canonical Bridge AI OS architecture diagram. Edit in VS Code (hediet.vscode-drawio) or in [app.diagrams.net](https://app.diagrams.net/). Sync to [Google Drive](https://drive.google.com/drive) for team access (e.g. `digital ecosystem.drawio`).
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
