# Bridge AI OS — Diagrams

Diagrams (draw.io / mxGraph) for Bridge AI OS. Open `.drawio.xml` files in [draw.io](https://app.diagrams.net/) or in VS Code with the Draw.io extension.

---

## Digital Ecosystem Evolution

- **digital-ecosystem-evolution.drawio.xml** — Layers: Cosmic Processes → Infrastructure → Data Flows → Twin Agents → Marketplace Economy → AI Evolution → Digital Civilization. Includes flows: Planet Formation, Stable Foundation, Resource Distribution, Perception & Decision, Economic Interaction, Intelligence Emergence, Feedback Loop; Twin Perception/Decision/Simulation/Evolution; UBI, Task Allocation, Trading, Value Creation; Lineage, Trait Selection, Digital Ancestry, Intelligence Growth.

If you have the diagram as **URL-encoded** paste (e.g. from a draw.io share link starting with `%3CmxGraphModel%3E`):

1. Save the encoded string to **docs/diagrams/encoded_diagram.txt** (no other content).
2. Run:  
   `.\scripts\import-drawio-from-encoded.ps1`
3. Open **docs/diagrams/digital-ecosystem-evolution.drawio.xml** in draw.io.

---

## Sync and wiki

- **Twins + wiki sync:** `.\scripts\sync-twins-wiki.ps1` — writes `data/twin-registry.json`, `docs/WIKI-VERSIONS.md`, `docs/twin-wiki.html`. Does not modify this `docs/diagrams/` folder.
- **System diagram prompts:** See **docs/PROMPT-SYSTEM-DIAGRAM.md** for copy-paste prompts to generate other system diagrams (Bridge API, Redis, Worker, etc.).
