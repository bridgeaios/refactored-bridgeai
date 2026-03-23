/**
 * BRIDGE AI OS — Shell System v1.0
 * Canonical nav · footer · boot · status · sitemap
 *
 * Include in <head>:
 *   <script src="/bridge-shell.js"></script>
 *
 * Replaces any existing .bridge-nav innerHTML.
 * Appends canonical footer to <body>.
 * Pings API and shows live status dot.
 */
;(function () {
  'use strict';

  /* ─── Boot: ensure globals exist (bridge-api-config.js may run before or after) */
  if (typeof window.__API_BASE === 'undefined') window.__API_BASE = '';
  if (typeof window.__WS_BASE === 'undefined') window.__WS_BASE = '';

  /* ─── Page Registry ─────────────────────────────────────────────────────────── */
  var GROUPS = [
    { key: 'core',    label: 'Core',    glyph: '◈' },
    { key: 'ops',     label: 'Ops',     glyph: '⬡' },
    { key: 'finance', label: 'Finance', glyph: '◆' },
    { key: 'network', label: 'Network', glyph: '◉' },
    { key: 'system',  label: 'System',  glyph: '◫' },
    { key: 'defi',    label: 'DeFi',    glyph: '◧' }
  ];

  var PAGES = [
    /* Core */
    { path: '/',                           label: 'Digital Twin',    group: 'core',    desc: 'Main digital twin console & mission board',  icon: '◈' },
    { path: '/landing.html',               label: 'Landing',         group: 'core',    desc: 'Project overview & entry point',             icon: '▷' },
    { path: '/dashboards.html',            label: 'All Dashboards',  group: 'core',    desc: 'Unified dashboard hub',                      icon: '⊞' },
    { path: '/sitemap.html',               label: 'Site Index',      group: 'core',    desc: 'Full site map & page directory',             icon: '⊟' },
    /* Ops */
    { path: '/status.html',                label: 'System Status',   group: 'ops',     desc: 'Live API & service health',                  icon: '◎' },
    { path: '/executive-dashboard.html',   label: 'Executive',       group: 'ops',     desc: 'Revenue, treasury, mission KPIs',            icon: '◉' },
    { path: '/network-dashboard.html',     label: 'Network',         group: 'ops',     desc: 'Live topology, health, Merkle audit',        icon: '⬡' },
    { path: '/control-plane.html',         label: 'Control Plane',   group: 'ops',     desc: 'System control & CLI runner',                icon: '◇' },
    /* Finance */
    { path: '/cfo.html',                   label: 'CFO',             group: 'finance', desc: 'Treasury & financial controls',              icon: '◆' },
    { path: '/corporate.html',             label: 'Corporate',       group: 'finance', desc: 'Corporate surface & reporting',              icon: '▣' },
    /* Network */
    { path: '/agents.html',                label: 'Agents',          group: 'network', desc: 'Agents & digital twins registry',            icon: '◉' },
    { path: '/ban-live-wall.html',         label: 'BAN Live Wall',   group: 'network', desc: 'Bridge Autonomous Network live view',        icon: '▦' },
    { path: '/ban-ops-core.html',          label: 'BAN Ops Core',    group: 'network', desc: 'Mechanica & execution engine',               icon: '▤' },
    { path: '/digital-twin-console.html',  label: 'Twin Console',    group: 'network', desc: 'Digital twin console interface',             icon: '◑' },
    { path: '/gateway/',                   label: 'Gateway',         group: 'network', desc: 'Sovereign Web3 entry — SIWE + chain auth',   icon: '⬟' },
    /* System */
    { path: '/docs.html',                  label: 'Docs',            group: 'system',  desc: 'API reference & documentation',              icon: '▧' },
    { path: '/settings.html',              label: 'Settings',        group: 'system',  desc: 'System configuration',                       icon: '◫' },
    { path: '/join.html',                  label: 'Join Network',    group: 'system',  desc: 'Join as agent — QR onboarding',              icon: '◎' },
    { path: '/50-applications.html',       label: '50 Applications', group: 'system',  desc: '50-app autonomous deployment suite',         icon: '▤' },
    /* DeFi — external port */
    { path: 'http://localhost:5173/',          label: 'DeFi Dashboard', group: 'defi', desc: 'DeFi platform home',                         icon: '◈', external: true },
    { path: 'http://localhost:5173/lending',   label: 'Lending',        group: 'defi', desc: 'Borrow & lend assets',                       icon: '◆', external: true },
    { path: 'http://localhost:5173/staking',   label: 'Staking',        group: 'defi', desc: 'Stake & earn rewards',                       icon: '◇', external: true },
    { path: 'http://localhost:5173/dex',       label: 'DEX',            group: 'defi', desc: 'Decentralised exchange',                     icon: '⬡', external: true },
    { path: 'http://localhost:5173/treasury',  label: 'DeFi Treasury',  group: 'defi', desc: 'Protocol treasury',                         icon: '▣', external: true }
  ];

  /* ─── CSS (injected once) ───────────────────────────────────────────────────── */
  var SHELL_CSS = `
/* ── Bridge Shell: nav ─────────────────────────────────── */
.bshell-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 0;
  height: 56px;
  padding: 0 20px;
  background: rgba(0,0,0,0.92);
  border-bottom: 1px solid #2A2A2A;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 1px 0 rgba(255,0,51,0.12);
  font-family: Inter, system-ui, sans-serif;
  flex-shrink: 0;
}

/* brand */
.bshell-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
  margin-right: 20px;
  flex-shrink: 0;
}
.bshell-brand img { border-radius: 3px; }
.bshell-brand:hover { color: #FF1A4D; }

/* hamburger */
.bshell-hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 40px;
  height: 40px;
  background: none;
  border: 1px solid #2A2A2A;
  border-radius: 4px;
  cursor: pointer;
  padding: 8px;
  margin-left: auto;
  flex-shrink: 0;
}
.bshell-hamburger span {
  display: block;
  height: 2px;
  background: #A0A0A0;
  border-radius: 1px;
  transition: all 0.2s ease;
  transform-origin: center;
}
.bshell-hamburger.open span:nth-child(1) { transform: rotate(45deg) translate(5px, 5px); }
.bshell-hamburger.open span:nth-child(2) { opacity: 0; transform: scaleX(0); }
.bshell-hamburger.open span:nth-child(3) { transform: rotate(-45deg) translate(5px, -5px); }

/* nav body */
.bshell-nav-body {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}

/* group dropdowns */
.bshell-nav-groups {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
}

.bshell-dd-wrap {
  position: relative;
}

.bshell-dd-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 36px;
  padding: 0 12px;
  background: none;
  border: none;
  border-radius: 4px;
  color: #A0A0A0;
  font-size: 12px;
  font-family: inherit;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, background 0.15s;
}
.bshell-dd-btn:hover, .bshell-dd-btn.open { color: #fff; background: rgba(255,255,255,0.05); }
.bshell-dd-btn.active { color: #FF1A4D; }
.bshell-dd-icon { font-size: 11px; opacity: 0.7; }
.bshell-dd-caret { font-size: 9px; opacity: 0.5; transition: transform 0.15s; }
.bshell-dd-btn.open .bshell-dd-caret { transform: rotate(180deg); }

.bshell-dd-menu {
  display: none;
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 200px;
  background: #0A0A0A;
  border: 1px solid #2A2A2A;
  border-radius: 6px;
  padding: 6px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,0,51,0.1);
  z-index: 200;
  flex-direction: column;
}
.bshell-dd-menu.open { display: flex; }

.bshell-dd-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  color: #A0A0A0;
  font-size: 13px;
  text-decoration: none;
  transition: color 0.12s, background 0.12s;
  white-space: nowrap;
}
.bshell-dd-item:hover { color: #fff; background: rgba(255,255,255,0.06); }
.bshell-dd-item.active { color: #FF1A4D; background: rgba(255,0,51,0.08); }
.bshell-dd-item-icon { font-size: 11px; opacity: 0.6; flex-shrink: 0; }
.bshell-dd-item-desc { font-size: 11px; color: #555; display: none; }

/* nav actions */
.bshell-nav-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex-shrink: 0;
}

.bshell-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2A2A2A;
  flex-shrink: 0;
  cursor: default;
  transition: background 0.3s, box-shadow 0.3s;
}
.bshell-status-dot.alive   { background: #00FF88; box-shadow: 0 0 6px rgba(0,255,136,0.5); }
.bshell-status-dot.degraded{ background: #FFAA00; box-shadow: 0 0 6px rgba(255,170,0,0.5); }
.bshell-status-dot.offline { background: #FF0033; box-shadow: 0 0 6px rgba(255,0,51,0.5); }

.bshell-gateway-btn {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;
  background: #FF0033;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-decoration: none;
  cursor: pointer;
  transition: box-shadow 0.15s, filter 0.15s;
  flex-shrink: 0;
}
.bshell-gateway-btn:hover {
  box-shadow: 0 0 12px rgba(255,0,51,0.5), 0 0 24px rgba(255,0,51,0.2);
  filter: brightness(1.1);
}

/* ── Mobile nav ────────────────────────────────────────── */
@media (max-width: 800px) {
  .bshell-nav { height: 52px; padding: 0 16px; }
  .bshell-hamburger { display: flex; }
  .bshell-nav-body {
    display: none;
    position: fixed;
    top: 52px;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.97);
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    overflow-y: auto;
    padding: 16px;
    z-index: 999;
  }
  .bshell-nav-body.open { display: flex; }
  .bshell-nav-groups { flex-direction: column; align-items: stretch; gap: 4px; flex: none; }
  .bshell-dd-wrap { width: 100%; }
  .bshell-dd-btn {
    width: 100%;
    height: 48px;
    padding: 0 16px;
    justify-content: flex-start;
    font-size: 13px;
    border-bottom: 1px solid #1A1A1A;
  }
  .bshell-dd-caret { margin-left: auto; }
  .bshell-dd-menu {
    position: static;
    display: none;
    border: none;
    border-radius: 0;
    background: #0D0D0D;
    padding: 0 0 8px 24px;
    box-shadow: none;
    min-width: auto;
  }
  .bshell-dd-menu.open { display: flex; }
  .bshell-dd-item { height: 44px; font-size: 14px; border-bottom: 1px solid #1A1A1A; }
  .bshell-nav-actions { padding: 16px 0 8px; gap: 12px; justify-content: flex-start; }
  .bshell-gateway-btn { height: 40px; padding: 0 20px; font-size: 13px; }
}

/* ── Footer ────────────────────────────────────────────── */
.bshell-footer {
  background: #050505;
  border-top: 1px solid #1A1A1A;
  margin-top: 60px;
  font-family: Inter, system-ui, sans-serif;
}

.bshell-footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px 0;
}

.bshell-footer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 32px;
  padding-bottom: 32px;
  border-bottom: 1px solid #1A1A1A;
}

.bshell-footer-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bshell-footer-heading {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #FF1A4D;
  margin-bottom: 6px;
}

.bshell-footer-col a {
  font-size: 13px;
  color: #666;
  text-decoration: none;
  padding: 3px 0;
  transition: color 0.12s;
}
.bshell-footer-col a:hover { color: #fff; }

.bshell-footer-bottom {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 16px 0 20px;
}

.bshell-footer-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.bshell-footer-tagline {
  font-size: 12px;
  color: #444;
  letter-spacing: 0.05em;
}

.bshell-footer-links {
  display: flex;
  gap: 16px;
  margin-left: auto;
}

.bshell-footer-links a {
  font-size: 12px;
  color: #444;
  text-decoration: none;
  transition: color 0.12s;
}
.bshell-footer-links a:hover { color: #FF1A4D; }

@media (max-width: 600px) {
  .bshell-footer-grid { grid-template-columns: repeat(2, 1fr); gap: 20px; }
  .bshell-footer-bottom { flex-direction: column; align-items: flex-start; gap: 10px; }
  .bshell-footer-links { margin-left: 0; }
}

/* ── Sitemap page ──────────────────────────────────────── */
.bshell-sitemap-hero {
  text-align: center;
  padding: 60px 24px 40px;
  border-bottom: 1px solid #1A1A1A;
}
.bshell-sitemap-hero h1 {
  font-size: 36px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 12px 0 8px;
}
.bshell-sitemap-hero p {
  font-size: 15px;
  color: #666;
  max-width: 480px;
  margin: 0 auto;
}
.bshell-sitemap-section {
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 24px;
  border-bottom: 1px solid #111;
}
.bshell-sitemap-section-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.bshell-sitemap-section-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #FF1A4D;
}
.bshell-sitemap-section-divider {
  flex: 1;
  height: 1px;
  background: #1A1A1A;
}
.bshell-sitemap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.bshell-sitemap-card {
  display: block;
  background: #111;
  border: 1px solid #1E1E1E;
  border-radius: 6px;
  padding: 16px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.bshell-sitemap-card:hover {
  border-color: #FF0033;
  box-shadow: 0 0 12px rgba(255,0,51,0.15);
  transform: translateY(-1px);
}
.bshell-sitemap-card-icon {
  font-size: 18px;
  margin-bottom: 8px;
  color: #FF1A4D;
}
.bshell-sitemap-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}
.bshell-sitemap-card-path {
  font-family: "JetBrains Mono", monospace;
  font-size: 11px;
  color: #444;
  margin-bottom: 6px;
}
.bshell-sitemap-card-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
}
.bshell-sitemap-card-ext {
  display: inline-block;
  margin-top: 8px;
  font-size: 10px;
  color: #FF1A4D;
  border: 1px solid rgba(255,0,51,0.3);
  border-radius: 3px;
  padding: 1px 6px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
`;

  /* ─── Helpers ──────────────────────────────────────────────────────────────── */
  function currentPath() {
    var p = window.location.pathname;
    // normalise /gateway/ and /gateway/index.html to same key
    if (p.endsWith('/') && p.length > 1) return p;
    return p;
  }

  function isActive(page) {
    var cp = currentPath();
    if (page.external) return false;
    if (page.path === '/') return cp === '/' || cp === '/index.html';
    return cp === page.path ||
      cp.replace(/\.html$/, '') === page.path.replace(/\.html$/, '') ||
      cp.startsWith(page.path.replace(/index\.html$/, ''));
  }

  function groupPages(key) {
    return PAGES.filter(function (p) { return p.group === key; });
  }

  /* ─── Nav HTML ─────────────────────────────────────────────────────────────── */
  function buildNav() {
    var dropdowns = GROUPS.map(function (g) {
      var pages = groupPages(g.key);
      var hasActive = pages.some(isActive);

      var items = pages.map(function (p) {
        var act = isActive(p) ? ' active' : '';
        var ext = p.external ? ' ↗' : '';
        var target = p.external ? ' target="_blank" rel="noopener"' : '';
        return '<a href="' + p.path + '" class="bshell-dd-item' + act + '"' + target + '>' +
          '<span class="bshell-dd-item-icon">' + p.icon + '</span>' + p.label + ext +
          '</a>';
      }).join('');

      return '<div class="bshell-dd-wrap">' +
        '<button class="bshell-dd-btn' + (hasActive ? ' active' : '') + '" data-group="' + g.key + '">' +
        '<span class="bshell-dd-icon">' + g.glyph + '</span>' +
        g.label +
        '<span class="bshell-dd-caret">▾</span>' +
        '</button>' +
        '<div class="bshell-dd-menu" data-menu="' + g.key + '">' + items + '</div>' +
        '</div>';
    }).join('');

    return '<a href="/landing.html" class="bshell-brand">' +
      '<img src="/favicon.svg" alt="" width="24" height="24">' +
      '<span>Bridge AI OS</span>' +
      '</a>' +
      '<button class="bshell-hamburger" id="bshell-hamburger" aria-label="Menu">' +
      '<span></span><span></span><span></span>' +
      '</button>' +
      '<div class="bshell-nav-body" id="bshell-nav-body">' +
      '<div class="bshell-nav-groups">' + dropdowns + '</div>' +
      '<div class="bshell-nav-actions">' +
      '<span class="bshell-status-dot" id="bshell-api-dot" title="Checking API..."></span>' +
      '<a href="/gateway/" class="bshell-gateway-btn">Gateway</a>' +
      '</div>' +
      '</div>';
  }

  /* ─── Footer HTML ──────────────────────────────────────────────────────────── */
  function buildFooter() {
    var cols = GROUPS.map(function (g) {
      var pages = groupPages(g.key);
      var links = pages.map(function (p) {
        var ext = p.external ? ' target="_blank" rel="noopener"' : '';
        return '<a href="' + p.path + '"' + ext + '>' + p.label + '</a>';
      }).join('');

      return '<div class="bshell-footer-col">' +
        '<div class="bshell-footer-heading">' + g.glyph + ' ' + g.label + '</div>' +
        links +
        '</div>';
    }).join('');

    return '<div class="bshell-footer-inner">' +
      '<div class="bshell-footer-grid">' + cols + '</div>' +
      '<div class="bshell-footer-bottom">' +
      '<div class="bshell-footer-brand">' +
      '<img src="/favicon.svg" alt="" width="20" height="20">' +
      '<span>Bridge AI OS</span>' +
      '</div>' +
      '<div class="bshell-footer-tagline">Autonomous Systems · Real-World Execution</div>' +
      '<div class="bshell-footer-links">' +
      '<a href="/sitemap.html">Sitemap</a>' +
      '<a href="/status.html">Status</a>' +
      '<a href="/docs.html">Docs</a>' +
      '<a href="/gateway/">Gateway</a>' +
      '</div>' +
      '</div>' +
      '</div>';
  }

  /* ─── Inject CSS ───────────────────────────────────────────────────────────── */
  function injectCSS() {
    if (document.getElementById('bshell-css')) return;
    var style = document.createElement('style');
    style.id = 'bshell-css';
    style.textContent = SHELL_CSS;
    document.head.appendChild(style);
  }

  /* ─── Mount nav ────────────────────────────────────────────────────────────── */
  function mountNav() {
    var existing = document.querySelector('nav.bridge-nav, nav.bshell-nav');
    var nav;
    if (existing) {
      nav = existing;
      nav.className = 'bshell-nav bridge-nav';
    } else {
      nav = document.createElement('nav');
      nav.className = 'bshell-nav bridge-nav';
      document.body.insertBefore(nav, document.body.firstChild);
    }
    nav.innerHTML = buildNav();
    bindNav(nav);
  }

  function bindNav(nav) {
    /* hamburger */
    var hamburger = nav.querySelector('#bshell-hamburger');
    var navBody    = nav.querySelector('#bshell-nav-body');
    if (hamburger && navBody) {
      hamburger.addEventListener('click', function (e) {
        e.stopPropagation();
        navBody.classList.toggle('open');
        hamburger.classList.toggle('open');
      });
    }

    /* dropdown toggle */
    nav.querySelectorAll('.bshell-dd-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var key  = btn.getAttribute('data-group');
        var menu = nav.querySelector('.bshell-dd-menu[data-menu="' + key + '"]');
        var wasOpen = menu.classList.contains('open');
        /* close all */
        nav.querySelectorAll('.bshell-dd-menu').forEach(function (m) { m.classList.remove('open'); });
        nav.querySelectorAll('.bshell-dd-btn').forEach(function (b)  { b.classList.remove('open'); });
        if (!wasOpen) { menu.classList.add('open'); btn.classList.add('open'); }
      });
    });

    /* close on outside click */
    document.addEventListener('click', function () {
      nav.querySelectorAll('.bshell-dd-menu').forEach(function (m) { m.classList.remove('open'); });
      nav.querySelectorAll('.bshell-dd-btn').forEach(function (b)  { b.classList.remove('open'); });
      if (navBody) { navBody.classList.remove('open'); }
      if (hamburger) { hamburger.classList.remove('open'); }
    });
  }

  /* ─── Mount footer ─────────────────────────────────────────────────────────── */
  function mountFooter() {
    /* remove any existing bshell footer */
    var old = document.querySelector('footer.bshell-footer');
    if (old) old.remove();

    var footer = document.createElement('footer');
    footer.className = 'bshell-footer';
    footer.innerHTML = buildFooter();
    document.body.appendChild(footer);
  }

  /* ─── API status ───────────────────────────────────────────────────────────── */
  function pingStatus() {
    var dot = document.getElementById('bshell-api-dot');
    if (!dot) return;
    var ctrl;
    try { ctrl = new AbortController(); } catch (e) {}
    var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, 3500);

    fetch('/api/mission/board', ctrl ? { signal: ctrl.signal } : {})
      .then(function (r) {
        clearTimeout(timer);
        dot.className = 'bshell-status-dot ' + (r.ok ? 'alive' : 'degraded');
        dot.title = r.ok ? 'API Online' : 'API Degraded';
      })
      .catch(function () {
        clearTimeout(timer);
        dot.className = 'bshell-status-dot offline';
        dot.title = 'API Offline';
      });
  }

  /* ─── Main boot ────────────────────────────────────────────────────────────── */
  function boot() {
    injectCSS();
    mountNav();
    mountFooter();
    setTimeout(pingStatus, 400);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  /* ─── Expose sitemap data for sitemap.html ─────────────────────────────────── */
  window.__BRIDGE_SHELL = { PAGES: PAGES, GROUPS: GROUPS };

})();
