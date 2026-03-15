// frontend/src/ubi.js
// UBI Dashboard – claim periodic tokens (simple UI wired to backend)
import { API_BASE } from './config.js';
function _getEvmAddress() {
  try {
    const eth = window.__walletEVM || window.ethereum || window.web3?.currentProvider;
    const provider = Array.isArray(eth) ? eth[0] : eth;
    if (provider?.selectedAddress) return provider.selectedAddress;
    if (provider) return provider.request({ method: 'eth_accounts' }).then(a => a && a[0]);
  } catch (e) { /* ignore */ }
  return null;
}

export function initUbi() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'ubi-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `
    <h4 style="margin:4px 0">Universal Basic Income</h4>
    <button id="claim-ubi" style="padding:6px 10px;">Claim UBI</button>
    <div id="ubi-status" style="margin-top:8px; font-size:13px">Next claim: daily</div>
  `;
  container.appendChild(panel);

  const claimBtn = document.getElementById('claim-ubi');
  const status = document.getElementById('ubi-status');

  claimBtn.onclick = async () => {
    claimBtn.disabled = true;
    claimBtn.textContent = 'Claiming...';
    try {
      const addr = await _getEvmAddress() || (window.solana && window.solana.publicKey && window.solana.publicKey.toString());
      if (!addr) throw new Error('No wallet connected');
      const res = await fetch(`${API_BASE}/api/ubi/claim`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr }) });
      const data = await res.json();
      if (data.amount && data.amount > 0) {
        alert(`Claimed ${data.amount} BRDG`);
        status.textContent = `Last claim: ${new Date().toLocaleString()}`;
      } else {
        alert('No claim available (try later)');
      }
    } catch (err) {
      console.error('UBI claim failed', err);
      alert('Claim failed');
    }
    claimBtn.disabled = false;
    claimBtn.textContent = 'Claim UBI';
  };
}

export default initUbi;
