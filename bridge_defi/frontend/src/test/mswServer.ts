import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const server = setupServer(
  http.get('/api/treasury/status', () =>
    HttpResponse.json({ ok: true, balance: 1000, currency: 'BRIDGE' }),
  ),
  http.get('/api/treasury/summary', () => HttpResponse.json({ total: 2000, net: 1200 })),
  http.post('/api/treasury/collect', () => HttpResponse.json({ ok: true, collected: 100 })),
  http.get('/api/marketplace/open', () => HttpResponse.json([{ id: 'task-1', title: 'Write docs', value: 50 }])),
  http.post('/api/ubi/distribute', () => HttpResponse.json({ ok: true, distributed: 20 })),
  http.get('/api/econ/circuit-breaker', () => HttpResponse.json({ state: 'closed' })),
  http.get('/api/econ/weights', () =>
    HttpResponse.json({ ubi: 0.4, treasury: 0.3, ops: 0.2, founder: 0.1 }),
  ),
  http.get('/api/twins', () => HttpResponse.json([{ id: 'twin-1', name: 'Alpha' }])),
  http.get('/api/twins/leaderboard', () => HttpResponse.json([{ id: 'twin-1', score: 100 }])),
  http.get('/api/swarm/health', () => HttpResponse.json({ status: 'healthy' })),
  http.get('/api/live/map', () => HttpResponse.json({ nodes: [] })),
  http.get('/api/live/report', () => HttpResponse.json({ active: 1 })),
  http.get('/api/status', () => HttpResponse.json({ status: 'ok' })),
  http.get('/api/capabilities', () => HttpResponse.json({ features: [] })),
  http.get('/api/projects', () => HttpResponse.json([{ id: 'p1' }])),
  http.get('/api/audit/drift', () => HttpResponse.json({ drift: false })),
  http.get('/api/reputation/top', () => HttpResponse.json([{ id: 'agent-1', score: 10 }])),
  http.get('/api/user/settings', () => HttpResponse.json({ theme: 'dark', language: 'en' })),
  http.put('/api/user/settings', () => HttpResponse.json({ ok: true })),
);
