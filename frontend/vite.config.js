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
  '/api/telemetry': { ok: true, data: { decision_latency_p50_ms: 0, speech_latency_p50_ms: 0, silence_rate: 0, state_mutation_frequency: 0, economic_conversion_rate: 0 }, meta: {} }
};

const CSP =
  "default-src 'self'; " +
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.babylonjs.com; " +
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; " +
  "font-src 'self' data: https://fonts.gstatic.com https://fonts.googleapis.com; " +
  "img-src 'self' data: https: blob:; " +
  "connect-src 'self' ws: wss: https: http:; " +
  "frame-src https:;";

export default {
  server: {
    port: 3020,
    headers: { 'Content-Security-Policy': CSP },
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true }
    }
  },
  plugins: [{
    configureServer(server) {
      // Run stub middleware FIRST (before proxy) so /api/* stubs are served when backend is down
      const stubMiddleware = (req, res, next) => {
        const path = req.url?.split('?')[0];
        const key = req.method + ' ' + path;
        let stub = (key === 'POST /api/marketplace/task' || key === 'POST /api/marketplace/accept' || key === 'POST /api/bossbots/trade')
          ? { ok: true }
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
