/**
 * Taurus — Gamification, Dev Support & Security Showcase (service on port 4202)
 * Serves a single-page showcase: gamification, dev support, security (SupaC/Taurus aligned).
 * GET /api/storage-sync: configurable storage from Google Drive / Sheet / local Excel (viewable).
 */
const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');
const PORT = parseInt(process.env.PORT || '4202', 10);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const STORAGE_SYNC_PATH = path.join(PROJECT_ROOT, 'data', 'storage-sync.json');

const SHOWCASE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Taurus — Gamification, Dev Support &amp; Security Showcase</title>
  <style>
    :root { --bg: #0a0c12; --panel: rgba(0,0,0,0.9); --accent: #6af; --ok: #8fc; --warn: #fa8; --border: #333; }
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: #ccc; margin: 0; padding: 24px; }
    h1 { font-size: 1.5rem; color: var(--accent); margin-top: 0; }
    h2 { font-size: 1rem; text-transform: uppercase; color: var(--accent); margin: 24px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
    .card ul { margin: 8px 0 0; padding-left: 20px; }
    .card li { margin: 4px 0; }
    a { color: var(--accent); }
    .badge { display: inline-block; background: var(--accent); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 6px; }
    .footer { margin-top: 32px; font-size: 11px; color: #666; }
  </style>
</head>
<body>
  <h1>Taurus — Gamification, Dev Support &amp; Security Showcase</h1>
  <p>Policy-aligned showcase service (SupaC, Taurus). Traceable, contract-grade.</p>

  <h2>Gamification</h2>
  <div class="grid">
    <div class="card">
      <span class="badge">Twins</span>
      <strong>Digital Twin &amp; Leaderboard</strong>
      <ul>
        <li><a href="http://localhost:8000/api/twins">GET /api/twins</a></li>
        <li><a href="http://localhost:8000/api/twins/leaderboard">GET /api/twins/leaderboard</a></li>
        <li>Allocate, teach, auto-add tasks</li>
      </ul>
    </div>
    <div class="card">
      <span class="badge">Mission</span>
      <strong>Mission Board &amp; Founder TODO</strong>
      <ul>
        <li><a href="http://localhost:8000/api/mission/board">GET /api/mission/board</a></li>
        <li><a href="http://localhost:8000/api/founder-todo">GET /api/founder-todo</a></li>
        <li>Backlog, in progress, review, done</li>
      </ul>
    </div>
    <div class="card">
      <span class="badge">Live</span>
      <strong>Live Map &amp; Report</strong>
      <ul>
        <li><a href="http://localhost:8000/api/live/map">GET /api/live/map</a></li>
        <li><a href="http://localhost:8000/api/live/report">GET /api/live/report</a></li>
        <li>Pboots, runbs, capabilities, sensors</li>
      </ul>
    </div>
  </div>

  <h2>Dev Support</h2>
  <div class="grid">
    <div class="card">
      <strong>Audit &amp; Apply</strong>
      <ul>
        <li><code>run-apply-audit.ps1</code> — Audit then apply keys/paths</li>
        <li><code>run-full-loop.ps1</code> — Install, boot, audit, verify, tests</li>
        <li><code>audit-wall.ps1</code> — Keys, ports, DNS, drives</li>
      </ul>
    </div>
    <div class="card">
      <strong>Stack &amp; Ports</strong>
      <ul>
        <li><code>launch-full-stack.ps1</code> — API, backend, auth, frontend</li>
        <li><code>scripts/port-handler.ps1 list</code> — Port status</li>
        <li>Bridge API 8000, Worker api.bridge-ai-os.tech</li>
      </ul>
    </div>
    <div class="card">
      <strong>Determinator &amp; Taurus</strong>
      <ul>
        <li><a href="http://localhost:4201">Boot Agent (4201)</a> — RBAC HRE</li>
        <li><code>determinator-finalize.ps1</code> — RUN VERSION, deployed</li>
        <li>Docs: DETERMINATOR-SYSTEM-SPEC.md, KIOSK-SHOWCASE-SYNC-GOOGLE-MCP.md</li>
      </ul>
    </div>
  </div>

  <h2>Security Showcase</h2>
  <div class="grid">
    <div class="card">
      <strong>SupaC &amp; Taurus</strong>
      <ul>
        <li>Policy frameworks (treaty-based governance)</li>
        <li>Black's Law Dictionary alignment</li>
        <li>Full auditability, enterprise safety</li>
      </ul>
    </div>
    <div class="card">
      <strong>Auditability</strong>
      <ul>
        <li>audit-results.json — OK / critical / recommendations</li>
        <li>State verify (Merkle, identity hash)</li>
        <li>Traceable, reversible, contract-grade actions</li>
      </ul>
    </div>
    <div class="card">
      <strong>Access &amp; Hardening</strong>
      <ul>
        <li>RBAC login — Determinator Boot Agent (4201)</li>
        <li>Bridge Auth (3030) — SIWE, JWT, sessions</li>
        <li>CSP, CORS, helmet; no destructive actions without guardrails</li>
      </ul>
    </div>
  </div>

  <h2>Storage — Configurable &amp; Viewable</h2>
  <div class="card">
    <p>Synced from Google Drive, new Google Sheet, or local Excel via <code>google-storage-sync.sh</code> / <code>google-storage-sync.ps1</code>. Data below from <code>data/storage-sync.json</code>.</p>
    <div id="storage-sync-meta" style="margin:8px 0;font-size:12px;color:#8fc;"></div>
    <pre id="storage-sync-preview" style="max-height:240px;overflow:auto;font-size:11px;background:#111;padding:8px;border-radius:4px;"></pre>
  </div>

  <p class="footer">Taurus Showcase service · Port ${PORT} · Bridge AI OS</p>
  <script>
    fetch('/api/storage-sync').then(r=>r.ok?r.json():{}).then(d=>{
      var meta=document.getElementById('storage-sync-meta');
      var pre=document.getElementById('storage-sync-preview');
      if(d&&d.source){ meta.textContent='Source: '+d.source+' · Synced: '+(d.syncedAt||'—'); pre.textContent=JSON.stringify(d,null,2); }
      else{ meta.textContent='No storage-sync data. Run google-storage-sync (Drive/Sheet/Excel).'; pre.textContent='{}'; }
    }).catch(function(){ document.getElementById('storage-sync-meta').textContent='Storage sync endpoint not available.'; });
  </script>
</body>
</html>
`;

const server = http.createServer((req, res) => {
  const reqPath = url.parse(req.url, true).pathname;
  if (reqPath === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, service: 'taurus-showcase', port: PORT }));
    return;
  }
  if (reqPath === '/api/storage-sync') {
    fs.readFile(STORAGE_SYNC_PATH, 'utf8', (err, data) => {
      if (err || !data) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ source: 'none', hint: 'Run google-storage-sync (Drive/Sheet/Excel)' }));
        return;
      }
      try {
        const parsed = JSON.parse(data);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(parsed));
      } catch (e) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ source: 'none', error: 'Invalid JSON in storage-sync.json' }));
      }
    });
    return;
  }
  if (reqPath === '/' || reqPath === '/showcase') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(SHOWCASE_HTML);
    return;
  }
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Taurus Showcase listening on http://localhost:${PORT}`);
  console.log(`Showcase: http://localhost:${PORT}/  Health: http://localhost:${PORT}/health`);
});
