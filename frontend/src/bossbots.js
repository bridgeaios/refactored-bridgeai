// frontend/src/bossbots.js
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';

const ASSETS = ['BTC', 'ETH', 'BRDG', 'SOL'];

export function initBossBots() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'bossbots-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `
    <h4 style="margin:4px 0">Boss Bots Trading</h4>
    <p style="font-size:11px;color:#888;margin-bottom:6px">Twins use auto DEX and follow buy/sell signals</p>
    <button id="run-bot">Run Trade Signal</button>
    <label style="font-size:11px;display:block;margin-top:4px"><input type="checkbox" id="auto-dex-toggle"> Auto DEX: run signals every 45s</label>
    <div id="bot-signals" style="margin-top:8px"></div>
  `;
  container.appendChild(panel);

  let autoDexInterval = null;
  document.getElementById('auto-dex-toggle')?.addEventListener('change', (e) => {
    if (autoDexInterval) clearInterval(autoDexInterval);
    if (e.target.checked) {
      autoDexInterval = setInterval(async () => {
        try {
          const asset = ASSETS[Math.floor(Math.random() * ASSETS.length)];
          const res = await fetch(`${API_BASE}/api/bossbots/trade`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ asset }) });
          const data = res.ok ? await res.json() : {};
          if (data.twins_followed?.length) {
            window.dispatchEvent(new CustomEvent('twins-leaderboard-update'));
          }
          updateSignals();
        } catch (_) {}
      }, 45000);
    }
  });

  document.getElementById('run-bot').onclick = () => {
    setTimeout(async () => {
      try {
        // Check if wallet is connected before allowing trade
        const walletAddress = window.__walletEVM?.selectedAddress || 
                             (window.phantom?.solana?.publicKey?.toString()) ||
                             (window.solana?.publicKey?.toString?.());
        if (!walletAddress) {
          alert('Please connect a wallet first');
          return;
        }
        
        const asset = ASSETS[Math.floor(Math.random() * ASSETS.length)];
        const res = await fetch(`${API_BASE}/api/bossbots/trade`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ asset }) });
        const data = res.ok ? await res.json() : {};
        if (data.twins_followed?.length) {
          window.dispatchEvent(new CustomEvent('twins-leaderboard-update'));
        }
        await updateSignals();
      } catch (err) {
        console.error('Run bot failed', err);
        alert('Bot failed');
      }
    }, 0);
  };

  async function updateSignals() {
    try {
      const signals = await fetchJson(`${API_BASE}/api/bossbots/signals`);
      document.getElementById('bot-signals').innerHTML = (Array.isArray(signals) ? signals : []).map(s => `<div>${s.asset}: ${s.signal}</div>`).join('');
    } catch (err) {
      if (!window._bossbotsErr) { window._bossbotsErr = true; console.warn('BossBots API unavailable'); }
    }
  }

  updateSignals();
  setInterval(() => setTimeout(updateSignals, 0), 120000);
}

export default initBossBots;
