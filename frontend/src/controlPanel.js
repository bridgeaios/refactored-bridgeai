import { API_BASE } from './config.js';

async function jget(path) {
  try {
    const r = await fetch(`${API_BASE}${path}`);
    if (!r.ok) return null;
    return await r.json();
  } catch (_) {
    return null;
  }
}

async function jpost(path, body) {
  try {
    const r = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const data = await r.json().catch(() => null);
    return { ok: r.ok, status: r.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { error: String(e) } };
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = (s == null ? '' : String(s));
  return d.innerHTML;
}

export function initControlPanel() {
  const root = document.getElementById('control-actions');
  if (!root) return;

  const kpi = document.getElementById('control-kpis');
  const historyEl = document.getElementById('cli-history');

  async function refreshKpis() {
    const [health, treas, cli] = await Promise.all([
      jget('/api/swarm/health'),
      jget('/api/treasury/status'),
      jget('/api/cli/status'),
    ]);

    if (kpi) {
      const buckets = treas?.buckets || {};
      const ok = health?.ok ? 'LIVE' : 'DEGRADED';
      kpi.innerHTML =
        `<div class="kpi"><div class="k">Swarm</div><div class="v">${esc(ok)} · ${(health?.health_score ?? '—')}</div></div>` +
        `<div class="kpi"><div class="k">Treasury</div><div class="v">total ${(treas?.total_collected_brdg ?? 0).toFixed?.(2) ?? esc(treas?.total_collected_brdg ?? '0')}</div></div>` +
        `<div class="kpi"><div class="k">UBI</div><div class="v">${esc((buckets.ubi ?? 0).toFixed?.(2) ?? buckets.ubi ?? 0)}</div></div>` +
        `<div class="kpi"><div class="k">CLI</div><div class="v">${cli?.enabled ? 'ENABLED' : 'LOCKED'}</div></div>`;
    }
  }

  async function refreshCliHistory() {
    const h = await jget('/api/cli/history?limit=10');
    if (!historyEl) return;
    const items = Array.isArray(h?.items) ? h.items : [];
    if (!items.length) {
      historyEl.innerHTML = `<div class="muted">No CLI jobs yet.</div>`;
      return;
    }
    historyEl.innerHTML = items.map(it => {
      const status = String(it.status || '');
      const cls = status === 'done' ? 'tag ok' : (status === 'failed' ? 'tag bad' : 'tag warn');
      const out = (it.stdout || '') + ((it.stderr && String(it.stderr).trim()) ? `\n--- stderr ---\n${it.stderr}` : '');
      return `
        <div class="cli-item">
          <div class="cli-head">
            <div class="cli-title">${esc(it.cmd_id)} <span class="muted">(${esc(it.id)})</span></div>
            <div class="${cls}">${esc(status)}</div>
          </div>
          <pre class="cli-out">${esc(out).slice(0, 8000)}</pre>
        </div>
      `;
    }).join('');
  }

  async function enqueue(cmd_id, args = []) {
    const res = await jpost('/api/cli/enqueue', { cmd_id, args });
    if (!res.ok) {
      const detail = res.data?.detail || res.data?.error || `enqueue failed (${res.status})`;
      alert(String(detail));
      return;
    }
    await refreshCliHistory();
  }

  root.querySelectorAll('[data-cmd]').forEach(btn => {
    btn.addEventListener('click', () => {
      const cmd = btn.getAttribute('data-cmd');
      if (cmd === 'echo') enqueue('echo', ['hello from control']);
      else enqueue(cmd, []);
    });
  });

  document.getElementById('control-refresh')?.addEventListener('click', async () => {
    await refreshKpis();
    await refreshCliHistory();
  });

  refreshKpis();
  refreshCliHistory();
  setInterval(refreshKpis, 8000);
  setInterval(refreshCliHistory, 12000);
}

