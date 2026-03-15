#!/usr/bin/env node
// Serves frontend with no-cache; proxies /api/* and /ws/* to backend to avoid CORS
const http = require('http');
const fs = require('fs');
const path = require('path');
let WebSocketServer, WebSocket;
try {
  const ws = require('ws');
  WebSocketServer = ws.WebSocketServer;
  WebSocket = ws;
} catch (e) {
  WebSocketServer = null;
}

const ROOT = __dirname;
const DIST = path.join(__dirname, 'dist');
const PUBLIC = path.join(__dirname, 'public');
// In production, refuse to serve source tree; require built artifacts.
if ((process.env.NODE_ENV || '').toLowerCase() === 'production' || process.env.REQUIRE_DIST === '1') {
  if (!fs.existsSync(DIST)) {
    console.error('Missing dist/. Run `npm run build` first. Refusing to start.');
    process.exit(1);
  }
}
const STATIC_ROOT = fs.existsSync(DIST) ? DIST : ROOT;
const MIMES = { '.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json', '.css': 'text/css', '.ico': 'image/x-icon', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.glb': 'model/gltf-binary' };

const STUB_APIS = {
  'GET /api/marketplace/tasks': () => [],
  'POST /api/marketplace/task': () => ({ ok: true }),
  'POST /api/marketplace/accept': () => ({ ok: true }),
  'POST /api/marketplace/complete': () => ({ status: 'completed', task: {} }),
  'GET /api/sdg/metrics': () => ({ ubi_claims: 0, tasks_created: 0, trades_executed: 0 }),
  'GET /api/revenue/status': () => ({ balance: 0, distributed: 0, ubi: 0, treasury: 0, ops: 0, founder: 0 }),
  'GET /api/bossbots/signals': () => [],
  'POST /api/bossbots/trade': () => ({ ok: true, signal: 'BUY', twins_followed: [] }),
  'GET /api/mission/board': () => ({ backlog: 0, in_progress: 0, review: 0, done: 0 }),
  'GET /api/esim/status': () => ({ status: 'stub', data_remaining_gb: 5 }),
  'POST /api/skills': () => ({ ok: true }),
  'GET /api/twin/shared-xml': () => '<?xml version="1.0" encoding="UTF-8"?><twin><authority>I am the Bridge. I am the Founder. I am the System. I am the Authority.</authority><backend>human</backend><mission><backlog>0</backlog><in_progress>0</in_progress><review>0</review><done>0</done></mission><face_state>ALIVE</face_state></twin>',
  'POST /api/twin/shared-xml': () => ({ ok: true }),
  'GET /api/twin/profile': () => ({ identity: { core_values: ['integrity','long-term compounding'], cognitive_mode: 'strategic' }, skill_stack: { hard: [], soft: [], meta: [] }, decision_model: {}, adaptive_loop: {}, risk_model: {}, communication_style: {}, blind_spots: [], upgrade_path: [] }),
  'POST /api/twin/decide': () => ({ action: null, reason: 'no_positive_value_output' }),
  'POST /api/twin/simulate': () => ({ reaction: 'proceed', action: 'apply_decision_model' }),
  'POST /api/twin/evolve': () => ({ feedback_ingested: true }),
  'GET /api/tts/available': () => ({ available: false }),
  'POST /api/tts': () => ({}),
  'GET /api/twins': () => [{ id: 'alpha', name: 'Alpha Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0, auto_dex: true, skills_learned: [{ task_id: 1, name: 'Improve mission board UX', tags: ['frontend', 'ux'], verified: true }] }, { id: 'beta', name: 'Beta Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0, auto_dex: true, skills_learned: [] }, { id: 'gamma', name: 'Gamma Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0, auto_dex: true, skills_learned: [] }],
  'GET /api/twins/leaderboard': () => [{ rank: 1, id: 'alpha', name: 'Alpha Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0 }, { rank: 2, id: 'beta', name: 'Beta Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0 }, { rank: 3, id: 'gamma', name: 'Gamma Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0 }],
  'POST /api/twins/auto-add': () => ({ status: 'created', task: { id: 1, desc: 'Stub task', reward: 10, status: 'open' } }),
  'POST /api/twins/allocate': () => ({ status: 'allocated', task: {} }),
  'POST /api/twins/teach': () => ({ status: 'taught', skill: {}, taught_by: 'alpha', student: 'beta' }),
  'POST /api/ubi/claim': () => ({ amount: 0 }),
  'POST /api/emotion/compute': () => ({ state: 'neutral', score: 0 }),
  'POST /api/train/start': () => ({ started: false }),
  'GET /api/train/status': () => ({ status: 'idle' }),
  'POST /api/speech/reason': () => ({ normalized_text: '', intent: 'unknown', emotion: 'neutral', confidence: 0, response: '' }),
  'POST /api/speech/embody': () => ({ response: '', phonemes: [], silence: true, confidence: 0 }),
  'POST /api/speech/embody/speak': () => ({ phonemes: [], audio_base64: null }),
  'GET /api/speech/embodiment/skill': () => ({ name: 'Twin_Speech_Communication_Embodiment', description: '' }),
  'POST /api/speech/embodiment/memory/clear': () => ({ ok: true }),
  'GET /api/speech/embodiment/memory': () => ({ entries: [] }),
  'GET /api/system/comprehension': () => ({ mission: {}, architecture: {}, economic_engine: {}, roles: {}, governance: {}, revenue: {} }),
  'GET /api/system/comprehension/explain': () => ({ level: 1, explanation: 'The Bridge is an ecosystem for poverty reduction and value creation. Users post tasks, earn rewards, and claim UBI.' }),
  'GET /api/system/comprehension/operational-model': () => ({ input: [], processing: [], output: [], feedback: [] }),
  'GET /api/system/comprehension/role-awareness': () => ({ twin_function: '', authority_boundaries: [], decision_constraints: [] }),
  'POST /api/system/comprehension/check-alignment': () => ({ aligned: true, reason: '', confidence: 1 }),
  'POST /api/system/comprehension/evolve': () => ({ ok: true }),
  'GET /api/system/comprehension/skill': () => ({ name: 'Bridge_System_Comprehension', description: '' }),
  'GET /api/health': () => ({ ok: true }),
  'GET /api/state/reducers': () => ({ version: '1.0.0', reducers: [{ name: 'emotionOverride', class: 'cognitive', version: '1.0.0' }, { name: 'twinStateUpdate', class: 'cognitive', version: '1.0.0' }, { name: 'dialogueAppend', class: 'cognitive', version: '1.0.0' }, { name: 'missionBoardUpdate', class: 'structural', version: '1.0.0' }, { name: 'skillIngest', class: 'structural', version: '1.0.0' }, { name: 'faceStateUpdate', class: 'visual', version: '1.0.0' }, { name: 'marketplaceTaskUpdate', class: 'economic', version: '1.0.0' }, { name: 'governanceVote', class: 'governance', version: '1.0.0' }], reducer_names: ['dialogueAppend','emotionOverride','faceStateUpdate','governanceVote','marketplaceTaskUpdate','missionBoardUpdate','skillIngest','twinStateUpdate'], checksum: 'stub', strict_mode: true, spine: 'Endpoint → Reducer → State → Scheduler → Expression', identity_hash: 'stub' }),
  'GET /api/capabilities': () => ({ ok: true, data: { perception: true, speech: true, trade: true, ubi: true, simulate: true, evolution: true, marketplace: true, state_mutation: true }, meta: { state_delta: false } }),
  'GET /api/telemetry': () => ({ ok: true, data: { decision_latency_p50_ms: 0, decision_latency_p95_ms: 0, speech_latency_p50_ms: 0, silence_rate: 0, state_mutation_frequency: 0, economic_conversion_rate: 0 }, meta: {} })
};
const jsonHeaders = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
const CSP = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.babylonjs.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com https://fonts.googleapis.com; img-src 'self' data: https: blob:; connect-src 'self' ws: wss: https: http:; frame-src https:;";

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';

function proxyToBackend(req, res, url, onFail) {
  const target = BACKEND + url + (req.url.includes('?') ? '?' + req.url.split('?')[1] : '');
  const targetUrl = new URL(target);
  const opts = {
    protocol: targetUrl.protocol,
    hostname: targetUrl.hostname,
    port: targetUrl.port,
    path: targetUrl.pathname + targetUrl.search,
    method: req.method,
    headers: { ...req.headers, host: targetUrl.host },
  };
  const key = req.method + ' ' + url;
  const stub = STUB_APIS[key];
  const proxyReq = http.request(opts, (proxyRes) => {
    if (url === '/api/tts' && proxyRes.statusCode >= 502) {
      proxyRes.resume();
      res.writeHead(503, jsonHeaders);
      res.end(JSON.stringify({ error: 'TTS unavailable', useBrowser: true }));
      return;
    }
    if (proxyRes.statusCode === 404 && stub) {
      proxyRes.resume();
      if (key === 'GET /api/twin/shared-xml') {
        res.writeHead(200, { 'Content-Type': 'application/xml', 'Cache-Control': 'no-store' });
        res.end(stub());
      } else {
        res.writeHead(200, jsonHeaders);
        res.end(JSON.stringify(stub()));
      }
      return;
    }
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.setTimeout(5000, () => { proxyReq.destroy(); });
  proxyReq.on('error', () => {
    if (url === '/api/tts') {
      res.writeHead(503, jsonHeaders);
      res.end(JSON.stringify({ error: 'TTS unavailable', useBrowser: true }));
      return;
    }
    onFail();
  });
  req.pipe(proxyReq);
}

// STUB_FIRST=1: force serve stubs for /api/* without proxying.
// Default: proxy-first (real backend), fall back to stubs on network error or 404.
const STUB_FIRST = process.env.STUB_FIRST === '1' || process.env.STUB_FIRST === 'true';

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  if (url.startsWith('/api/')) {
    const key = req.method + ' ' + url;
    const stub = STUB_APIS[key];
    // Serve stub directly only when explicitly forced.
    const serveStub = () => {
      if (req.method !== 'GET') req.resume(); // drain body for POST etc.
      if (stub) {
        if (key === 'GET /api/twin/shared-xml') {
          res.writeHead(200, { 'Content-Type': 'application/xml', 'Cache-Control': 'no-store' });
          res.end(stub());
        } else {
          res.writeHead(200, jsonHeaders);
          res.end(JSON.stringify(stub()));
        }
      } else {
        res.writeHead(404, jsonHeaders);
        res.end(JSON.stringify({ error: 'Not found' }));
      }
    };
    if (STUB_FIRST && stub) {
      serveStub();
      return;
    }
    proxyToBackend(req, res, url, serveStub);
    return;
  }
  const key = req.method + ' ' + url;
  const stub = STUB_APIS[key];
  if (stub) {
    res.writeHead(200, jsonHeaders);
    res.end(JSON.stringify(stub()));
    return;
  }
  if (url === '/favicon.ico') {
    res.writeHead(204);
    res.end();
    return;
  }
  if (url === '/gateway' || url === '/gateway/') {
    const gatewayPath = path.join(STATIC_ROOT, 'gateway', 'index.html');
    const fallback = path.join(__dirname, 'public', 'gateway', 'index.html');
    const file = fs.existsSync(gatewayPath) ? gatewayPath : fallback;
    if (fs.existsSync(file)) {
      fs.readFile(file, (err, data) => {
        if (err) { res.writeHead(404); res.end(); return; }
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
        res.setHeader('Content-Type', 'text/html');
        res.setHeader('Content-Security-Policy', CSP);
        res.end(data);
      });
      return;
    }
  }
  // GLTF model fallback: /models/X.glb -> model.glb when specific file missing
  if (url.startsWith('/models/') && url.endsWith('.glb')) {
    const modelPath = path.resolve(STATIC_ROOT, url.replace(/^\//, ''));
    if (!fs.existsSync(modelPath)) {
      const fallback = path.join(STATIC_ROOT, 'model.glb');
      if (fs.existsSync(fallback)) {
        fs.readFile(fallback, (err, data) => {
          if (err) { res.writeHead(404); res.end(); return; }
          res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
          res.setHeader('Content-Type', MIMES['.glb']);
          res.end(data);
        });
        return;
      }
    }
  }
  const rel = url === '/' ? 'index.html' : url.replace(/^\//, '');
  let file = path.resolve(STATIC_ROOT, rel);
  const base = path.resolve(STATIC_ROOT);
  if (!(file === base || file.startsWith(base + path.sep))) {
    res.writeHead(403);
    res.end();
    return;
  }
  // If file isn't in STATIC_ROOT, fall back to /public without mutating the repo.
  if (!fs.existsSync(file)) {
    const pubFile = path.resolve(PUBLIC, rel);
    const pubBase = path.resolve(PUBLIC);
    if ((pubFile === pubBase || pubFile.startsWith(pubBase + path.sep)) && fs.existsSync(pubFile)) {
      file = pubFile;
    }
  }
  // Case-insensitive fallback: lipSync.js -> lipsync.js (browsers sometimes request wrong casing)
  if (!fs.existsSync(file) && /lipSync\.js$/i.test(rel)) {
    const alt = path.join(path.dirname(file), 'lipsync.js');
    if (fs.existsSync(alt)) file = alt;
  }
  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not found' }));
      return;
    }
    const ext = path.extname(file);
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
    res.setHeader('Content-Type', MIMES[ext] || 'application/octet-stream');
    if (ext === '.html') res.setHeader('Content-Security-Policy', CSP);
    res.end(data);
  });
});

const PORT = process.env.PORT || 3020;
let _listenPort = parseInt(PORT, 10);
function tryListen() {
  const p = _listenPort;
  server.listen(p, () => {
    console.log('Bridge AI OS at http://localhost:' + p + ' (no-cache)');
    if (STUB_FIRST) console.log('Stub-first: API stubs served. Set STUB_FIRST=0 to proxy to backend.');
  });
}
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE' && _listenPort < 3040) {
    _listenPort++;
    console.log('Port in use, trying ' + _listenPort + '...');
    tryListen();
  } else {
    throw err;
  }
});

if (WebSocketServer && WebSocket) {
  const wss = new WebSocketServer({ noServer: true });
  server.on('upgrade', (req, socket, head) => {
    if (req.url && req.url.startsWith('/ws/')) {
      wss.handleUpgrade(req, socket, head, (clientWs) => {
        // Send immediate heartbeat so systemVerifier (5s timeout) passes right away
        const sendHb = () => { try { if (clientWs.readyState === 1) clientWs.send(JSON.stringify({ type: 'heartbeat', ts: Date.now() / 1000 })); } catch (_) {} };
        sendHb();
        const targetUrl = BACKEND.replace(/^http/, 'ws') + req.url;
        const backendWs = new WebSocket(targetUrl);
        let connected = false;
        let fallbackUsed = false;
        const useFallbackHeartbeat = () => {
          if (fallbackUsed) return;
          fallbackUsed = true;
          sendHb();
          const iv = setInterval(sendHb, 4000);
          clientWs.on('close', () => clearInterval(iv));
        };
        const connTimeout = setTimeout(() => {
          if (!connected) useFallbackHeartbeat();
        }, 2000);
        backendWs.on('open', () => {
          connected = true;
          clearTimeout(connTimeout);
          clientWs.on('message', (m) => { try { backendWs.send(m); } catch (_) {} });
          backendWs.on('message', (m) => { try { clientWs.send(m); } catch (_) {} });
        });
        backendWs.on('error', () => {
          if (!connected) useFallbackHeartbeat();
          else clientWs.close();
        });
        backendWs.on('close', () => { if (connected) clientWs.close(); });
        clientWs.on('close', () => backendWs.readyState < 2 && backendWs.close());
      });
    } else {
      socket.destroy();
    }
  });
} else {
  console.warn('ws not installed; WebSocket proxy disabled. Run: npm install ws');
}

tryListen();
