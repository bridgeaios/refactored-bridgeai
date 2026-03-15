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

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Determinator Boot Agent listening on http://localhost:${PORT}`);
  console.log(`RBAC login: http://localhost:${PORT}/`);
  console.log(`Next interface after auth: ${NEXT_URL}`);
});
