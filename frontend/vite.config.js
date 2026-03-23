import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Vite config – adds stub API routes when using npm run dev (avoids 404 when backend down)
const STUBS = {
  '/api/marketplace/tasks': [],
  '/api/sdg/metrics': { ubi_claims: 0, tasks_created: 0, trades_executed: 0 },
  '/api/revenue/status': { balance: 0, distributed: 0, ubi: 0, treasury: 0, ops: 0, founder: 0 },
  '/api/bossbots/signals': [],
  '/api/mission/board': { backlog: 0, in_progress: 0, review: 0, done: 0 },
  '/api/founder-todo': { version: 1, updatedAt: null, objectives: [{ id: 'obj-1', title: 'Ship Phase 4', status: 'pending', completedAt: null }, { id: 'obj-5', title: 'Dashboard + Installer live', status: 'complete', completedAt: null }] },
  '/api/esim/status': { status: 'stub', data_remaining_gb: 5 },
  '/api/twin/profile': { identity: { core_values: ['integrity', 'long-term compounding'], cognitive_mode: 'strategic' }, skill_stack: { hard: [], soft: [], meta: [] }, decision_model: {}, adaptive_loop: {}, risk_model: {}, communication_style: {}, blind_spots: [], upgrade_path: [] },
  '/api/twin/shared-xml': () => '<?xml version="1.0" encoding="UTF-8"?><twin><authority>I am the Bridge. I am the Founder. I am the System. I am the Authority.</authority><backend>human</backend><mission><backlog>0</backlog><in_progress>0</in_progress><review>0</review><done>0</done></mission><face_state>ALIVE</face_state></twin>',
  '/api/twins': [{ id: 'alpha', name: 'Alpha Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0, auto_dex: true, skills_learned: [] }, { id: 'beta', name: 'Beta Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0, auto_dex: true, skills_learned: [] }, { id: 'gamma', name: 'Gamma Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0, auto_dex: true, skills_learned: [] }],
  '/api/twins/leaderboard': [{ rank: 1, id: 'alpha', name: 'Alpha Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0 }, { rank: 2, id: 'beta', name: 'Beta Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0 }, { rank: 3, id: 'gamma', name: 'Gamma Twin', completed: 0, in_progress: 0, total_score: 0, trades_executed: 0, dex_pnl: 0 }],
  '/api/health': { ok: true },
  '/api/system/comprehension': { mission: {}, architecture: {}, economic_engine: {}, roles: {}, governance: {}, revenue: {} },
  '/api/system/comprehension/explain': { level: 1, explanation: 'The Bridge is an ecosystem for poverty reduction and value creation.' },
  '/api/state/reducers': { version: '1.0.0', reducer_names: ['dialogueAppend','emotionOverride','faceStateUpdate','governanceVote','marketplaceTaskUpdate','missionBoardUpdate','skillIngest','twinStateUpdate'], strict_mode: true, spine: 'Endpoint → Reducer → State → Scheduler → Expression', identity_hash: 'stub' },
  '/api/capabilities': { ok: true, data: { perception: true, speech: true, trade: true, ubi: true, simulate: true, evolution: true, marketplace: true, state_mutation: true }, meta: { state_delta: false } },
  '/api/telemetry': { ok: true, data: { decision_latency_p50_ms: 0, speech_latency_p50_ms: 0, silence_rate: 0, state_mutation_frequency: 0, economic_conversion_rate: 0 }, meta: {} },
  '/api/replication/status': { ok: true, last_run_ts: null, open_tasks: 0, twin_count: 0, rules_evaluated: 0, twins_created: 0 },
  '/api/replication/nodes': { ok: true, nodes: [] },
  '/api/reputation/top': { ok: true, agents: [{ agent_id: 'alpha', completed: 0, failed: 0, success_rate: 1, average_cost: 0, latency_ms: 0, quality_score: 1, score: 0.85 }] },
  '/api/swarm/health': { ok: true, health_score: 0.92, components: { queue_latency_ms: 120, worker_utilization: 0.55, task_profitability: 0.003, agent_failure_rate: 0.002 } },
  '/api/demand/pump': { ok: true, created: 5, skipped: 0, open_tasks: 50, target_backlog: 50 },
  '/api/skills': { ok: true, skills: [], count: 0 },
  '/api/projects': { ok: true, count: 0, projects: [] },
  '/api/sensors/mouse': { ok: true, mouse: null, session: { active_count: 0, total_earned: 0 } },
  '/api/sensors/wifi': { ok: true, wifi: null },
  '/api/twin/env-keys': { keys: [], summary: { configured: 0, criticalMissing: 0 } },
  '/api/cli/status': { ok: true, enabled: false, mode: 'disabled', observed_env: { ENV: null, NODE_ENV: null, BRIDGE_ALLOW_CLI_RUNNER: null } },
  '/api/cli/history': { ok: true, count: 0, items: [] },
  '/api/cli/queue/next': { ok: true, job: null },
  '/api/speech/embodiment/memory': { ok: true, memories: [], count: 0 },
  '/api/speech/embodiment/skill': { ok: true, skill: null },
  '/api/treasury/status': { ok: true, total_collected_brdg: 0, total_tx: 0, buckets: { ubi: 0, treasury: 0, ops: 0, founder: 0 }, by_project: {}, by_method: {}, by_currency: {}, last_tx_ts: null },
  '/api/treasury/ledger': { ok: true, count: 0, entries: [] },
  '/api/treasury/rails': { ok: true, rails: [], split: { ubi: '40%', treasury: '30%', ops: '20%', founder: '10%' } },
  '/health': { status: 'ok', service: 'bridge-live-wall', port: 8000 },
  '/api/health/extended': { ok: true, status: 'ok', checks: {} },
  '/api/ubi/claim': { amount: 0, detail: 'Backend offline — stub response' },
  '/api/ubi/distribute': { amount: 0, detail: 'Backend offline — stub response' },
  '/api/services': () => ({
    services: 'Dashboard:3000=offline, Bridge API:8000=offline, Frontend:3020=online, Determinator:4201=offline, Taurus:4202=offline',
    timestamp: new Date().toISOString(),
  }),
  '/api/human': () => ({
    ok: true,
    timestamp: new Date().toISOString(),
    telemetry: { decision_latency_p50_ms: 0, speech_latency_p50_ms: 0, silence_rate: 0, state_mutation_frequency: 0, economic_conversion_rate: 0 },
    mission_board: { backlog: 0, in_progress: 0, review: 0, done: 0 },
    objectives: [],
    identity_hash: 'stub',
    spine: 'Endpoint → Reducer → State → Scheduler → Expression',
    services: [],
    live_report_at: new Date().toISOString(),
  }),
  '/api/live/map': () => ({
    ok: true,
    ts: Date.now() / 1000,
    state_version: 1,
    state_hash: 'stub',
    twins: [],
    leaderboard: [],
    capabilities: {},
    telemetry: {},
    services: [],
    sensors: { wifi: null, mouse: null },
    svg_build: null,
  }),
  '/api/telemetry/events/svg-build': { ok: true, svg_build: null },
  '/api/svg-build/history': { ok: true, builds: [] },
  '/api/live/report': () => ({
    ok: true,
    report_at: new Date().toISOString(),
    live_display: true,
    twins: [],
    leaderboard: [],
    capabilities: {},
    telemetry: {},
    sensors: { wifi: null, mouse: null },
    polity: {
      spine: 'Endpoint → Reducer → State → Scheduler → Expression',
      identity_hash: 'stub',
      reducer_names: ['dialogueAppend', 'emotionOverride', 'faceStateUpdate', 'governanceVote', 'marketplaceTaskUpdate', 'missionBoardUpdate', 'skillIngest', 'twinStateUpdate'],
    },
    governance: { score: 0 },
    value_deltas: { balance: 0, distributed: 0, ubi: 0, treasury: 0, ops: 0, founder: 0 },
  }),
};

// In-memory stub for PUT /api/user/settings when backend is down (shared per dev server)
let stubUserSettings = {};

// Track backend availability — recheck every 10s
let _backendAlive = false;
let _backendLastCheck = 0;
async function _isBackendAlive() {
  const now = Date.now();
  if (now - _backendLastCheck < 10000) return _backendAlive;
  _backendLastCheck = now;
  try {
    const r = await fetch('http://localhost:8000/api/health', { signal: AbortSignal.timeout(1500) });
    _backendAlive = r.ok;
  } catch {
    _backendAlive = false;
  }
  return _backendAlive;
}
// Warm up immediately
_isBackendAlive();


const CSP =
  "default-src 'self'; " +
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.babylonjs.com https://cdn.tailwindcss.com https://cdn.jsdelivr.net; " +
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; " +
  "font-src 'self' data: https://fonts.gstatic.com https://fonts.googleapis.com; " +
  "img-src 'self' data: https: blob:; " +
  "connect-src 'self' ws: wss: https: http:; " +
  "frame-src https:;";

// Multi-page: use named object entries (array input is not valid for Vite rollupOptions.input).
const projectRoot = process.cwd();
export default {
  build: {
    rollupOptions: {
      input: {
        main: join(projectRoot, 'index.html'),
        apps: join(projectRoot, '50-applications.html'),
      },
    },
  },
  server: {
    port: 3020,
    headers: { 'Content-Security-Policy': CSP },
    proxy: {
      '/api': { target: process.env.BRIDGE_API_URL || 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: (process.env.BRIDGE_WS_URL || 'ws://localhost:8000'), ws: true }
    }
  },
  plugins: [{
    configureServer(server) {
      // Run stub middleware FIRST (before proxy) so /api/* stubs are served when backend is down.
      // Skip stubs entirely when backend is reachable — let the proxy serve real data.
      const stubMiddleware = (req, res, next) => {
        // Always pass through WebSocket upgrades
        if (req.headers.upgrade === 'websocket') return next();
        // Pass through to real backend if it's alive (async check — use cached value)
        if (_backendAlive && req.url?.startsWith('/api')) return next();

        const path = req.url?.split('?')[0];
        const key = req.method + ' ' + path;
        if (path === '/api/user/settings') {
          res.setHeader('Content-Type', 'application/json');
          if (req.method === 'GET') {
            res.end(JSON.stringify({ ok: true, settings: stubUserSettings }));
          } else if (req.method === 'PUT') {
            let body = '';
            req.on('data', (ch) => { body += ch; });
            req.on('end', () => {
              try {
                const payload = body ? JSON.parse(body) : {};
                stubUserSettings = payload.settings && typeof payload.settings === 'object' ? payload.settings : (typeof payload === 'object' ? payload : {});
              } catch (_) {}
              res.end(JSON.stringify({ ok: true, settings: stubUserSettings }));
            });
          } else {
            res.statusCode = 405;
            res.end(JSON.stringify({ error: 'Method not allowed' }));
          }
          return;
        }
        let stub = (key === 'POST /api/marketplace/task' || key === 'POST /api/marketplace/accept' || key === 'POST /api/bossbots/trade'
            || key === 'POST /api/marketplace/complete' || key === 'POST /api/marketplace/pledge'
            || key === 'POST /api/twin/decide' || key === 'POST /api/twin/evolve' || key === 'POST /api/twin/simulate'
            || key === 'POST /api/twins/allocate' || key === 'POST /api/twins/teach'
            || key === 'POST /api/speech/embody' || key === 'POST /api/speech/embody/speak'
            || key === 'POST /api/cli/enqueue')
          ? { ok: true, detail: 'Backend offline — stub response' }
          : (key === 'POST /api/twins/auto-add' ? { status: 'created', task: { id: 1, desc: 'Stub task', reward: 10, status: 'open' } } : STUBS[path]);
        if (stub) {
          if (path === '/api/twin/shared-xml' && req.method === 'GET') {
            res.setHeader('Content-Type', 'application/xml');
            res.setHeader('Cache-Control', 'no-store');
            res.end(typeof stub === 'function' ? stub() : stub);
          } else {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify(typeof stub === 'function' ? stub() : stub));
          }
          return;
        }
        if (path?.startsWith('/models/') && path.endsWith('.glb')) {
          const publicDir = join(process.cwd(), 'public');
          const modelPath = join(publicDir, path.replace(/^\//, ''));
          if (!existsSync(modelPath)) {
            const fallback = join(publicDir, 'model.glb');
            if (existsSync(fallback)) {
              res.setHeader('Content-Type', 'model/gltf-binary');
              res.setHeader('Cache-Control', 'no-store');
              res.end(readFileSync(fallback));
              return;
            }
          }
        }
        next();
      };
      server.middlewares.stack.unshift({ route: '', handle: stubMiddleware });
    }
  }]
};
