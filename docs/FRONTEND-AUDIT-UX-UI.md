# Frontend Audit — UX & UI

**Date:** 2026-03-15  
**Scope:** Bridge AI OS frontend (Vite + Babylon.js, `frontend/`)

---

## 1. Executive summary

| Area | Status | Notes |
|------|--------|--------|
| **Structure & entry** | OK | Single-page app, clear entry (main.js → bootstrap of 20+ modules) |
| **Visual design** | OK | Dark theme, consistent palette (#8fc, #cf8, #6af, #05070d) |
| **Responsiveness** | Partial | Fixed side-panel (240px), terminal (180px); no breakpoints |
| **Accessibility** | Weak | No ARIA, minimal semantics, no keyboard nav, no focus management |
| **Error & loading** | Partial | Loading screen and fallbacks in places; many failures only in console |
| **Feature visibility** | Gaps | Twin panel, wallet, competition, marketplace, etc. partially or not in main layout |

---

## 2. Architecture & structure

### 2.1 Entry and layout

- **Entry:** `index.html` → `/src/main.js` (module). Babylon.js loaded from CDN; canvas `#renderCanvas` full viewport.
- **Layout (inline in index):**
  - `#loading` — full-screen loading (hidden after renderer init).
  - `#renderCanvas` — 100% × 100vh (3D scene).
  - `#terminal` — fixed bottom-left, height 180px, right margin 260px (so not under side-panel).
  - `#side-panel` — fixed top-right, width 240px, max-height calc(100vh - 220px); contains:
    - `#missionBoard`
    - `#founderTodo`
    - `#skillsPanel`

### 2.2 Modules initialized from main.js

Initialization order: system check → renderer (with face state ALIVE/DEGRADED/OFFLINE) → lip sync, voice, speech embodiment, terminal, mission board, founder todo, skills panel, AR/VR, geolocation, ESIM, wallet, marketplace, UBI, SDG, revenue, BossBots, twin shared XML, cognitive twin, **twin panel**, twin competition, system comprehension.

Many of these inject or look for their own DOM nodes:

- **Wallet** (`wallet.js`): appends `#wallet-status` to `#side-panel` or `document.body` — **visible**.
- **Twin panel** (`twinPanel.js`): looks for `#twinPanel` — **not present in index.html**, so **twin panel never mounts** in the default app.
- **Twin competition, marketplace, UBI, SDG, revenue, BossBots, system comprehension**: each looks for its own container (e.g. by id). If those ids are not in the DOM, those UIs are no-ops.

So the **default view** only shows: 3D scene, terminal, mission board, founder todo, skills panel, and wallet (injected). Other features exist in code but are not surfaced unless the HTML is extended.

---

## 3. UX flows

### 3.1 On load

1. Full-screen “Loading Digital Twin...” with Bridge logo.
2. System verifier runs (API + WebSocket). Result drives face state: ALIVE / DEGRADED / OFFLINE (wireframe or tint if not ALIVE).
3. Renderer initializes (MetaHuman-style avatar, high-fidelity skin, eyes, body). Loading div is hidden.
4. Terminal and side-panel modules init; mission board and founder todo poll API (or show “Board unavailable” / default TODO on failure).

**UX note:** If API/WS fail, user sees DEGRADED/OFFLINE avatar and “Board unavailable” in mission board; no prominent “Backend offline” banner or retry CTA.

### 3.2 Terminal (chat / voice)

- WebSocket to `/ws/mission`. Messages rendered with emotion-based color and optional topic badges.
- Input: single text field; Enter sends. “🔊 Speak” button triggers a canned voice line.
- **Gaps:** No loading indicator while waiting for response; no explicit “connection lost” message in UI (only console); no focus trap or keyboard shortcut list.

### 3.3 Mission board

- Polls `/api/mission/board` every 10s; shows Backlog / In Progress / Review / Done counts.
- Fallback: if API fails, uses shared XML mission if available; otherwise “Board unavailable”.
- **UX:** Read-only; no deep link to tasks or filters.

### 3.4 Founder TODO

- Lists objectives; “Complete” button calls `PATCH /api/founder-todo/{id}/complete`.
- Poll every 15s. On load/error falls back to `DEFAULT_TODO` (no user-visible error).
- **UX:** Clear progress (done/total); completion is one-click but no undo or confirmation.

### 3.5 Skills panel

- Add skill: text input + “Add” → POST `/api/skills`. Local list updated; “Edit” buttons in list have no handler (dead UI).
- **UX:** No validation message; no loading state; edit is not implemented.

### 3.6 Wallet

- “Connect EVM” / “Connect Solana” with hint text and links to MetaMask/Phantom.
- On connect, shows address and balance in `#wallet-info`.
- **UX:** Pending state (“Please wait for MetaMask…”) and extension-invalidated errors handled; good for a minimal wallet strip.

### 3.7 Twin panel (when mounted)

- Would show identity, skills, decision model, env keys, Simulate / Decide / Evolve / Refresh and result area.
- **Not in default layout:** `#twinPanel` is missing, so this flow is unavailable unless the app HTML is changed.

---

## 4. UI & visual design

### 4.1 Strengths

- **Palette:** Dark background (#05070d, #0a0c12), accent greens (#8fc, #cf8, #2a4), blue (#6af), red for errors (#f88). Consistent across panels and terminal.
- **Typography:** Monospace for terminal; small caps for panel headings (11px uppercase); readable hierarchy.
- **Layout:** Clear separation: canvas (main focus), terminal (dialogue), side-panel (status and actions). Background pattern (bridge-connector.svg) adds identity without clutter.
- **CSP:** Strict Content-Security-Policy in HTML and Vite; script/style/font/connect sources are explicit.

### 4.2 Weaknesses

- **Fixed dimensions:** Side-panel 240px, terminal 180px height. No media queries or fluid layout; small screens will feel cramped.
- **Inline styles:** Heavy use of inline `style=` and `.style` in JS; no shared design tokens or CSS variables (except in a few places). Theming or layout changes would require edits in many files.
- **No design system:** Buttons and inputs redefined per module (e.g. founderTodo “Complete”, terminal “Speak”, wallet “Connect EVM”). Slight inconsistencies in padding, radius, font size.
- **3D and 2D:** Canvas is not labeled for assistive tech; no text alternative for the scene state (ALIVE/DEGRADED/OFFLINE) beyond visual change.

---

## 5. Accessibility (a11y)

### 5.1 Current state

- **Semantics:** Almost no ARIA (`aria-*`, `role=`). One `data-role="list"` in marketplace; a couple of `<label>` in twin competition and BossBots. No landmarks (banner, main, complementary).
- **Keyboard:** No documented tab order or shortcuts; terminal input is focusable, other controls depend on default tab order. No skip link or focus trap in modals (none present).
- **Focus:** No explicit focus management after actions (e.g. after “Complete” or “Add skill”); focus not moved to result or status.
- **Screen readers:** Loading image has `alt="Bridge"`. Canvas has no `aria-label` or live region for “avatar state” or “scene”. Side-panel and terminal are plain divs; dynamic updates (mission counts, chat lines) are not announced (no `aria-live`).
- **Color:** Emotion and status use color only (e.g. terminal message color); no icons or text redundancy for “confident” vs “alert” etc. for color-blind users.

### 5.2 Recommendations

1. Add `aria-label` to canvas (e.g. “3D digital twin avatar”) and a live region for face/connection state.
2. Use `role="region"` and `aria-label` for side-panel and terminal; `aria-live="polite"` for mission board, founder TODO, and terminal messages.
3. Ensure all buttons and inputs have visible focus style and that tab order is logical.
4. Add a small “Connection: ALIVE | DEGRADED | OFFLINE” text near the canvas for both sighted and screen-reader users.
5. Avoid relying on color alone for emotion/status; add text or icon where possible.

---

## 6. Error handling & resilience

### 6.1 What’s in place

- **System verifier:** API + WebSocket check at startup; face state (ALIVE/DEGRADED/OFFLINE) drives avatar appearance.
- **Mission board:** Fallback to shared XML or “Board unavailable” on fetch failure.
- **Founder TODO:** Fallback to `DEFAULT_TODO` on fetch failure.
- **API helper:** `fetchJson` in `api.js` checks Content-Type and throws on non-JSON or !ok.
- **Vite stubs:** When backend is down, dev server can serve stub JSON for many `/api/*` routes so the app doesn’t fully break.
- **Terminal:** WebSocket reconnect after 15s on close; errors logged to console with a one-time “Backend WebSocket offline” warning.

### 6.2 Gaps

- No global “Backend offline” or “Reconnecting…” banner.
- Many `catch` blocks only `console.warn`; user sees no toast or inline error (e.g. “Complete” or “Add skill” failure).
- Twin panel result area shows success/error for 4s then hides; no way to re-open last result.
- No retry CTAs for failed fetches (e.g. “Retry” on mission board).

---

## 7. Performance & technical

- **Render loop:** Throttled to ~30fps (every 2nd frame) to reduce rAF pressure; hardware scaling adjusts (2.0 vs 1.0) based on FPS.
- **Babylon:** High-performance preference; preserveDrawingBuffer and stencil for effects.
- **Polling:** Mission board 10s, founder TODO 15s; no exponential backoff on failure.
- **Bundle:** Vite + ES modules; Babylon loaded from CDN (duplicated with package dependency). Consider single source (CDN or npm) to avoid version drift.

---

## 8. Recommendations summary

| Priority | Recommendation |
|----------|----------------|
| **High** | Add `#twinPanel` (and optionally other feature containers) to `index.html` or a single “control surface” layout so Twin panel and other features are visible. |
| **High** | Add a global connection/status strip or banner (e.g. “API offline” / “Reconnecting”) and optional retry for mission board and critical API calls. |
| **High** | Improve accessibility: ARIA for canvas and live regions, landmarks, focus styles, and non-color cues for status/emotion. |
| **Medium** | Replace or supplement inline styles with CSS variables (e.g. `--bg-panel`, `--accent`) and a small shared stylesheet for buttons/inputs. |
| **Medium** | Add responsive breakpoints: collapse or relocate side-panel and terminal on narrow viewports (e.g. drawer or bottom sheet). |
| **Medium** | Surface errors to the user (toast or inline) for founder-todo complete, skill add, and other mutations; keep console for detail. |
| **Low** | Implement “Edit” in skills list or remove the button to avoid dead UI. |
| **Low** | Unify Babylon source (CDN vs npm) and document expected version. |

---

## 9. Files referenced

- **Entry / layout:** `frontend/index.html`, `frontend/src/main.js`
- **Config / API:** `frontend/src/config.js`, `frontend/src/api.js`
- **UI modules:** `frontend/src/missionBoard.js`, `frontend/src/founderTodo.js`, `frontend/src/skillsPanel.js`, `frontend/src/terminal.js`, `frontend/src/wallet.js`, `frontend/src/twinPanel.js`
- **3D:** `frontend/src/babylonRenderer.js`, `frontend/src/skinSystem.js`, `frontend/src/bodyBuilder.js`, `frontend/src/eyeBuilder.js`
- **System:** `frontend/src/systemVerifier.js`
- **Build:** `frontend/vite.config.js`, `frontend/package.json`

---

**Conclusion:** The frontend delivers a coherent “Digital Twin” experience with 3D avatar, terminal, mission board, founder TODO, skills, and wallet. The main gaps are: (1) several features (Twin panel, etc.) not wired into the default layout, (2) weak accessibility and (3) limited user-visible error handling and connection status. Addressing the high-priority items above would materially improve UX and UI completeness.
