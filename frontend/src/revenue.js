// frontend/src/revenue.js
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';

export function initRevenue() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'revenue-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `<h4 style="margin:4px 0">Revenue Engines</h4><div id="revenue-status">Loading...</div>`;
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

  update();
  setInterval(() => setTimeout(update, 0), 30000);
}

export default initRevenue;
