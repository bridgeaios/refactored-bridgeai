/**
 * Determinator Boot Agent — localhost:4201
 * RBAC-driven HRE: serve login page, authenticate, redirect to next actionable interface.
 * Deterministic, auditable. No entropy in critical path.
 * Configure: DETERMINATOR_NEXT_URL (default http://localhost:8000), PORT=4201.
 */
const http = require('http');
const url = require('url');

const PORT = parseInt(process.env.PORT || '4201', 10);
const NEXT_URL = process.env.DETERMINATOR_NEXT_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3020';

const RBAC_LOGIN_HTML = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Determinator HRE — RBAC Login</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0a0c12; color: #8fc; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .box { background: rgba(0,0,0,0.85); padding: 2rem; border-radius: 8px; border: 1px solid #333; max-width: 360px; }
    h1 { font-size: 1rem; text-transform: uppercase; color: #6af; margin-top: 0; }
    input { width: 100%; padding: 8px 12px; margin: 8px 0; background: #111; border: 1px solid #333; color: #cf8; box-sizing: border-box; }
    button { width: 100%; padding: 10px; margin-top: 12px; background: #2a6; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
    button:hover { background: #3a7; }
    .footer { font-size: 11px; color: #666; margin-top: 16px; }
  </style>
</head>
<body>
  <div class="box">
    <h1>Determinator — Human Runtime Environment</h1>
    <p>RBAC login. Authenticate to continue to the next actionable interface.</p>
    <form method="post" action="/auth">
      <input type="text" name="user" placeholder="User" required autocomplete="username">
      <input type="password" name="pass" placeholder="Password" required autocomplete="current-password">
      <button type="submit">Sign in</button>
    </form>
    <p class="footer">Port 4201 · Traceable · Contract-grade</p>
    <p class="footer"><a href="/system-map.html" style="color:#6af;">System Map</a> — all systems linked & orchestrated</p>
  </div>
</body>
</html>
`;

const server = http.createServer((req, res) => {
  const path = url.parse(req.url, true).pathname;

  if (path === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, service: 'determinator-boot-agent', port: PORT }));
    return;
  }

  if (path === '/auth' && req.method === 'POST') {
    let body = '';
    req.on('data', (ch) => { body += ch; });
    req.on('end', () => {
      // Stub: accept any user/pass and redirect. Replace with real RBAC (Bridge Auth, SIWE, or Google).
      const params = new URLSearchParams(body);
      const user = params.get('user') || '';
      res.writeHead(302, {
        'Location': NEXT_URL,
        'Set-Cookie': `determinator_user=${encodeURIComponent(user)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400`
      });
      res.end();
    });
    return;
  }

  if (path === '/' || path === '/login') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(RBAC_LOGIN_HTML);
    return;
  }

  if (path === '/digital-twin-console.html') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Digital Twin Console — Bridge AI OS</title>
  <meta http-equiv="refresh" content="0;url=${FRONTEND_URL}/">
  <style>
    body { font-family: system-ui, sans-serif; background: #0a0c12; color: #8fc; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .box { background: rgba(0,0,0,0.85); padding: 2rem; border-radius: 8px; border: 1px solid #333; max-width: 400px; text-align: center; }
    h1 { font-size: 1.1rem; color: #6af; margin-top: 0; }
    a { display: inline-block; margin-top: 1rem; padding: 12px 24px; background: #2a6; color: #fff; text-decoration: none; border-radius: 6px; font-weight: 600; }
    a:hover { background: #3a7; }
    .footer { font-size: 11px; color: #666; margin-top: 16px; }
  </style>
</head>
<body>
  <div class="box">
    <h1>Digital Twin Console</h1>
    <p>Opening Bridge AI OS Digital Twin…</p>
    <a href="${FRONTEND_URL}/">Open Digital Twin at ${FRONTEND_URL}</a>
    <p class="footer">Port 4201 → Frontend ${FRONTEND_URL}</p>
  </div>
</body>
</html>`);
    return;
  }

  if (path === '/system-map.html') {
    const API_BASE = NEXT_URL.replace(/\/$/, '');
    const systemMapHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>System Map — Bridge AI OS · All systems linked & orchestrated</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: #0a0c12; color: #e2e8f0; margin: 0; padding: 20px; min-height: 100vh; }
    h1 { color: #38bdf8; font-size: 1.5rem; margin-bottom: 4px; }
    .sub { color: #94a3b8; font-size: 0.9rem; margin-bottom: 8px; }
    .registry-link { font-size: 0.8rem; margin-bottom: 20px; }
    .registry-link a { color: #7dd3fc; text-decoration: none; }
    .registry-link a:hover { text-decoration: underline; }
    .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .toolbar button { padding: 8px 16px; background: #0ea5e9; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.85rem; }
    .toolbar button:hover { background: #38bdf8; }
    .toolbar button.sec { background: #1e40af; }
    .toolbar button.sec:hover { background: #2563eb; }
    #summary { color: #94a3b8; font-size: 0.85rem; margin-bottom: 16px; padding: 10px 14px; background: rgba(15,23,42,0.8); border-radius: 8px; border: 1px solid #1e293b; }
    .section-label { color: #475569; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 24px 0 10px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
    .card { background: rgba(15,23,42,0.9); border: 1px solid #1e293b; border-radius: 10px; padding: 14px 16px; transition: border-color 0.2s; }
    .card.online { border-color: #166534; }
    .card.offline { border-color: #7f1d1d; }
    .card.seeded { border-color: #1e3a5f; }
    .card h3 { margin: 0 0 4px; font-size: 0.95rem; color: #fbbf24; }
    .card .type { font-size: 0.72rem; color: #475569; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
    .card .status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .dot.online { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
    .dot.offline { background: #f87171; }
    .dot.seeded { background: #60a5fa; }
    .dot.checking { background: #94a3b8; }
    .card .status-text { font-size: 0.8rem; color: #94a3b8; }
    .card .caps { font-size: 0.72rem; color: #475569; margin-bottom: 10px; line-height: 1.4; }
    .card .actions { display: flex; gap: 6px; flex-wrap: wrap; }
    .card a { display: inline-block; padding: 5px 10px; background: #1e3a5f; color: #7dd3fc; text-decoration: none; border-radius: 5px; font-size: 0.8rem; }
    .card a:hover { background: #2563eb; color: #fff; }
    .card .port-badge { float: right; font-size: 0.7rem; color: #475569; padding: 2px 6px; background: #0f172a; border-radius: 4px; margin-left: 4px; }
    .sync-section { margin-top: 36px; padding: 20px; background: rgba(15,23,42,0.9); border: 1px solid #1e293b; border-radius: 12px; }
    .sync-section h2 { color: #38bdf8; font-size: 1rem; margin: 0 0 10px; }
    .sync-section p { color: #94a3b8; font-size: 0.85rem; margin-bottom: 10px; }
    .sync-section ul { margin: 0; padding-left: 18px; }
    .sync-section li { margin-bottom: 8px; color: #94a3b8; font-size: 0.85rem; }
    .sync-section a { color: #7dd3fc; text-decoration: none; }
    .sync-section a:hover { text-decoration: underline; }
    .error-box { padding: 12px 16px; background: rgba(127,29,29,0.3); border: 1px solid #7f1d1d; border-radius: 8px; color: #f87171; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>System Map</h1>
  <p class="sub">All systems linked, orchestrated, funneled. Live registry from Bridge API.</p>
  <p class="registry-link">Source of truth: <a href="${API_BASE}/api/projects" target="_blank">${API_BASE}/api/projects</a> &nbsp;|&nbsp; <a href="${API_BASE}/docs" target="_blank">API Docs</a></p>

  <div class="toolbar">
    <button onclick="refreshAll()">&#8635; Refresh all</button>
    <button class="sec" onclick="window.open('${API_BASE}/api/projects','_blank')">View registry JSON</button>
    <button class="sec" onclick="window.open('https://drive.google.com/file/d/1aebwruTyIYZYe8fkOn8R9njOtcL82z0c/view?usp=sharing','_blank')">&#128194; Google Drive diagram</button>
    <button class="sec" onclick="window.open('https://app.diagrams.net/','_blank')">&#9741; Draw.io</button>
  </div>

  <div id="summary">Loading registry…</div>
  <div id="systems"></div>

  <section class="sync-section" aria-label="Sync live with Google and Draw.io">
    <h2>&#128279; Sync live with Google &amp; Draw.io</h2>
    <p>This map pulls live data from the project registry. The same ecosystem is mirrored in Google Drive and Draw.io diagrams.</p>
    <ul>
      <li><a href="https://drive.google.com/file/d/1aebwruTyIYZYe8fkOn8R9njOtcL82z0c/view?usp=sharing" target="_blank" rel="noopener">Google Drive — Digital Ecosystem Evolution</a> — shared diagram, view/edit with team.</li>
      <li><a href="https://app.diagrams.net/" target="_blank" rel="noopener">Draw.io</a> — use <strong>File &rarr; Open from &rarr; Google Drive</strong> to open the Drive diagram, or open <code>docs/diagrams/system-map.drawio.xml</code> from repo.</li>
      <li><strong>Repo:</strong> <code>docs/diagrams/</code> — BRIDGE.DRAWIO, system-map.drawio.xml. Open in VS Code (Draw.io ext) or app.diagrams.net.</li>
    </ul>
  </section>

  <script>
    const API_BASE = ${JSON.stringify(API_BASE)};
    const FRONTEND_URL = ${JSON.stringify(FRONTEND_URL)};

    // Frontend sub-pages not in the registry but always shown
    const FRONTEND_PAGES = [
      { id: 'gateway',   name: 'Gateway',            url: FRONTEND_URL + '/gateway/' },
      { id: 'join',      name: 'Join as Agent',       url: FRONTEND_URL + '/join.html' },
      { id: 'agents',    name: 'Agents & Twins',      url: FRONTEND_URL + '/agents.html' },
      { id: 'dashboard', name: 'Executive Dashboard', url: FRONTEND_URL + '/executive-dashboard.html' },
      { id: '50apps',    name: '50 Applications',     url: FRONTEND_URL + '/50-applications.html' },
      { id: 'docs',      name: 'Docs & Wiki',         url: FRONTEND_URL + '/docs.html' },
    ];

    // Extra services known locally but may not be in registry yet
    const EXTRA = [
      { id: 'api-production', label: 'Bridge API (Production)', type: 'api', baseUrl: 'https://api.bridge-ai-os.tech', health: '/health' },
      { id: 'nextjs-app',     label: 'Next.js App',             type: 'frontend', baseUrl: 'http://localhost:3032', health: null },
      { id: 'console-sync',   label: 'Console Sync',            type: 'service',  baseUrl: 'http://localhost:3022', health: null },
    ];

    async function checkHealth(baseUrl, healthPath) {
      if (!healthPath) return 'seeded';
      try {
        const r = await fetch(baseUrl + healthPath, { cache: 'no-store', signal: AbortSignal.timeout(3000) });
        return r.ok ? 'online' : 'offline';
      } catch (_) { return 'offline'; }
    }

    function renderCard(p, status) {
      const dot = '<span class="dot ' + status + '"></span>';
      const statusLabel = { online: 'Online', offline: 'Offline', seeded: 'Registered', checking: 'Checking…' }[status] || status;
      const port = p.port ? '<span class="port-badge">:' + p.port + '</span>' : '';
      const caps = (p.capabilities && p.capabilities.length) ? '<div class="caps">' + p.capabilities.slice(0,4).join(' · ') + '</div>' : '';
      const openUrl = p.baseUrl || p.apiUrl || '';
      const openBtn = openUrl ? '<a href="' + openUrl + '" target="_blank" rel="noopener">Open</a>' : '';
      return '<div class="card ' + status + '">'
        + '<h3>' + p.label + port + '</h3>'
        + '<div class="type">' + (p.type || '') + '</div>'
        + '<div class="status-row">' + dot + '<span class="status-text">' + statusLabel + '</span></div>'
        + caps
        + '<div class="actions">' + openBtn + '</div>'
        + '</div>';
    }

    async function refreshAll() {
      const summaryEl = document.getElementById('summary');
      const systemsEl = document.getElementById('systems');
      summaryEl.textContent = 'Fetching registry from ' + API_BASE + '/api/projects …';

      // Fetch registry
      let projects = [];
      let registryOk = false;
      try {
        const r = await fetch(API_BASE + '/api/projects', { cache: 'no-store', signal: AbortSignal.timeout(5000) });
        if (r.ok) {
          const d = await r.json();
          projects = d.projects || [];
          registryOk = true;
        }
      } catch (_) {}

      if (!registryOk) {
        summaryEl.innerHTML = '<span style="color:#f87171">&#9888; Bridge API offline — cannot load registry. Start with .\\\\launch-full-stack.ps1</span>';
        systemsEl.innerHTML = '<div class="error-box">Bridge API not reachable at ' + API_BASE + '. Run the boot script and refresh.</div>';
        return;
      }

      // Add extras not already in registry
      const registeredIds = new Set(projects.map(p => p.id));
      for (const e of EXTRA) {
        if (!registeredIds.has(e.id)) projects.push(e);
      }

      // Check health for all in parallel
      const statuses = await Promise.all(projects.map(p => checkHealth(p.baseUrl || p.apiUrl || '', p.health || null)));

      // Determinator is always online (serving this page)
      const detIdx = projects.findIndex(p => p.id === 'determinator');
      if (detIdx >= 0) statuses[detIdx] = 'online';

      // Split into sections
      const registered   = projects.filter((p, i) => statuses[i] === 'online' || statuses[i] === 'offline');
      const seeded       = projects.filter((p, i) => statuses[i] === 'seeded');
      const statusMap    = Object.fromEntries(projects.map((p, i) => [p.id, statuses[i]]));

      let html = '';

      if (registered.length) {
        html += '<p class="section-label">Registered services (' + registered.length + ')</p><div class="grid">';
        html += registered.map(p => renderCard(p, statusMap[p.id])).join('');
        html += '</div>';
      }

      if (FRONTEND_PAGES.length) {
        html += '<p class="section-label">Frontend pages</p><div class="grid">';
        html += FRONTEND_PAGES.map(p => '<div class="card seeded"><h3>' + p.name + '</h3><div class="actions"><a href="' + p.url + '" target="_blank">Open</a></div></div>').join('');
        html += '</div>';
      }

      if (seeded.length) {
        html += '<p class="section-label">Known (not yet running)</p><div class="grid">';
        html += seeded.map(p => renderCard(p, 'seeded')).join('');
        html += '</div>';
      }

      systemsEl.innerHTML = html;

      const onlineCount = statuses.filter(s => s === 'online').length;
      const offlineCount = statuses.filter(s => s === 'offline').length;
      summaryEl.innerHTML = '<strong style="color:#4ade80">' + onlineCount + ' online</strong>'
        + (offlineCount ? ' &nbsp;|&nbsp; <strong style="color:#f87171">' + offlineCount + ' offline</strong>' : '')
        + ' &nbsp;|&nbsp; ' + projects.length + ' total in registry'
        + ' &nbsp;|&nbsp; <a href="' + API_BASE + '/api/projects" target="_blank" style="color:#7dd3fc">view registry</a>'
        + ' &nbsp;|&nbsp; <span style="color:#475569">last refreshed ' + new Date().toLocaleTimeString() + '</span>';
    }

    refreshAll();
    // Auto-refresh every 30s
    setInterval(refreshAll, 30000);
  </script>
</body>
</html>`;
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(systemMapHtml);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Determinator Boot Agent listening on http://localhost:${PORT}`);
  console.log(`RBAC login: http://localhost:${PORT}/`);
  console.log(`Next interface after auth: ${NEXT_URL}`);
});
