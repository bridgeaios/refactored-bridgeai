# Mobile Nav and Features

Quick reference for BridgeLiveWall mobile navigation and related features.

---

## Files

| File | Purpose |
|------|---------|
| `frontend/public/bridge-nav.js` | Hamburger menu logic |
| `frontend/public/mobile-friendly.css` | Responsive nav + touch targets |

---

## Pages with Mobile Nav

All use `bridge-nav`, `bridge-nav-toggle`, `bridge-nav-links`:

- CFO, Executive, Status, Agents
- Dashboards, BAN Live Wall, BAN Ops
- Control Plane, Corporate, Landing
- Docs, Settings, Join, Network Dashboard

---

## Usage

1. Add to `<nav>`: `class="bridge-nav"`
2. Add brand link: `class="bridge-nav-brand"`
3. Add toggle: `<button class="bridge-nav-toggle" aria-label="Toggle menu">☰</button>`
4. Wrap links: `<div class="bridge-nav-links"><ul>...</ul></div>`
5. Include scripts: `<script src="/bridge-nav.js"></script>`
6. Include styles: `<link rel="stylesheet" href="/mobile-friendly.css">`

---

## Breakpoints

- **≤768px**: Hamburger visible, links in collapsible panel
- **≥769px**: Full nav, hamburger hidden

---

## Touch Targets

`mobile-friendly.css` enforces 44px min height/width for buttons and nav links on coarse pointers.

---

## See Also

- [TECHNICAL-IMPLEMENTATION-SUMMARY.md](./TECHNICAL-IMPLEMENTATION-SUMMARY.md) — Full implementation details
- [SHARED-ARCHITECTURE.md](./SHARED-ARCHITECTURE.md) — DB, Spine, Revenue
