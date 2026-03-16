// frontend/src/revenue.js
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';

export function initRevenue() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'revenue-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `
    <h4 style="margin:4px 0">Revenue Engines</h4>
    <div id="revenue-status">Loading...</div>
    <div id="mouse-earnings" style="margin-top:6px;font-size:11px;color:#7bd;display:none">
      🖱 Mouse Activity: <span id="mouse-earned">0.00</span> BRDG earned · <span id="mouse-active">0</span>/<span id="mouse-per-task">12</span> moves
    </div>`;
  container.appendChild(panel);

  async function update() {
    try {
      const status = await fetchJson(`${API_BASE}/api/revenue/status`);
      const u = (v) => (v != null ? Number(v).toFixed(2) : '0');
      document.getElementById('revenue-status').innerHTML =
        `Balance: ${u(status.balance)} BRDG · Distributed: ${u(status.distributed)}<br>` +
        `UBI: ${u(status.ubi)} · Treasury: ${u(status.treasury)} · Ops: ${u(status.ops)} · Founder: ${u(status.founder)}`;
    } catch (err) {
      if (!window._revenueErr) { window._revenueErr = true; console.warn('Revenue API unavailable'); }
      document.getElementById('revenue-status').textContent = 'Unavailable';
    }
  }

  async function updateMouse() {
    try {
      const data = await fetchJson(`${API_BASE}/api/sensors/mouse`);
      const session = data.session || {};
      const earned = Number(session.total_earned || 0);
      const active = Number(session.active_count || 0);
      const el = document.getElementById('mouse-earnings');
      if (el) {
        el.style.display = (data.mouse || earned > 0) ? 'block' : 'none';
        const earnedEl = document.getElementById('mouse-earned');
        const activeEl = document.getElementById('mouse-active');
        if (earnedEl) earnedEl.textContent = earned.toFixed(2);
        if (activeEl) activeEl.textContent = active;
      }
    } catch { /* sensor not active */ }
  }

  update();
  updateMouse();
  setInterval(() => setTimeout(update, 0), 30000);
  setInterval(() => setTimeout(updateMouse, 0), 6000);
}

export default initRevenue;
