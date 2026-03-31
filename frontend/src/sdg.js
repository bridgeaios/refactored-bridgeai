// frontend/src/sdg.js
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';
import { escapeHtml } from './bridgeUi.js';

export function initSdg() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'sdg-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `
    <h4 style="margin:4px 0">UN SDG Metrics</h4>
    <div id="sdg-metrics">Loading...</div>
  `;
  container.appendChild(panel);

  async function updateMetrics() {
    try {
      const metrics = await fetchJson(`${API_BASE}/api/sdg/metrics`);
      document.getElementById('sdg-metrics').innerHTML = `SDG1 UBI Claims: ${metrics.ubi_claims}<br>SDG8 Tasks Created: ${metrics.tasks_created}<br>Trades Executed: ${metrics.trades_executed}`;
    } catch (err) {
      if (!window._sdgErr) { window._sdgErr = true; console.warn('SDG API unavailable'); }
      document.getElementById('sdg-metrics').textContent = 'Unavailable';
    }
  }

  updateMetrics();
  setInterval(() => setTimeout(updateMetrics, 0), 30000);
}

export default initSdg;
