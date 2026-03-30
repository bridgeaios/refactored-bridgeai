// frontend/src/marketplace.js
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';
import { signMessageEVM, signMessageSolana } from './wallet.js';

const LOCAL_KEY = 'bridge.marketplace.tasks.v1';
const PLEDGE_EVENTS_KEY = 'bridge.marketplace.pledges.v1';

function normWallet(w) {
  return String(w || '').trim().toLowerCase();
}

function newEventId() {
  try {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  } catch { /* ignore */ }
  return `evt_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

function animateAmount(el, from, to, duration = 900) {
  if (!el) return;
  const start = Number(from) || 0;
  const end = Number(to) || 0;
  if (!Number.isFinite(start) || !Number.isFinite(end)) return;
  if (el.__bridgeRaf) cancelAnimationFrame(el.__bridgeRaf);
  let startTs = null;
  const step = (ts) => {
    if (!startTs) startTs = ts;
    const t = Math.min(1, (ts - startTs) / duration);
    const v = start + (end - start) * easeOutCubic(t);
    el.textContent = v.toFixed(2);
    if (t < 1) el.__bridgeRaf = requestAnimationFrame(step);
  };
  el.__bridgeRaf = requestAnimationFrame(step);
}

function loadLocalTasks() {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveLocalTasks(tasks) {
  try { localStorage.setItem(LOCAL_KEY, JSON.stringify(tasks)); } catch { /* ignore */ }
}

function loadPledgeEvents() {
  try {
    const raw = localStorage.getItem(PLEDGE_EVENTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function savePledgeEvents(events) {
  try { localStorage.setItem(PLEDGE_EVENTS_KEY, JSON.stringify(events)); } catch { /* ignore */ }
}

function addPledgeEvent(evt) {
  const events = loadPledgeEvents();
  events.unshift(evt);
  // cap to avoid unbounded growth
  if (events.length > 2000) events.length = 2000;
  savePledgeEvents(events);
}

function sumPledgesByTask(events) {
  const sums = new Map();
  for (const e of Array.isArray(events) ? events : []) {
    if (e?.confirmed) continue; // avoid double-counting when backend reflects confirmed pledges
    const id = e?.task_id;
    const amt = Number(e?.amount);
    if (id == null || !Number.isFinite(amt)) continue;
    sums.set(String(id), (sums.get(String(id)) || 0) + amt);
  }
  return sums;
}

function markEventConfirmed(event_id) {
  if (!event_id) return;
  const events = loadPledgeEvents();
  let changed = false;
  for (const e of events) {
    if (e?.event_id === event_id && !e.confirmed) {
      e.confirmed = true;
      changed = true;
    }
  }
  if (changed) savePledgeEvents(events);
}

async function reconcileUnconfirmedPledges(limit = 25) {
  const events = loadPledgeEvents();
  const pending = (events || []).filter(e => e && !e.confirmed && e.event_id && e.task_id && e.wallet && Number(e.amount) > 0);
  if (!pending.length) return;
  let sent = 0;
  for (const e of pending) {
    if (sent >= limit) break;
    try {
      await fetch(`${API_BASE}/api/marketplace/pledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: e.task_id,
          wallet: normWallet(e.wallet),
          amount: Number(e.amount),
          event_id: e.event_id
        })
      });
      markEventConfirmed(e.event_id);
      sent += 1;
    } catch {
      // backend unavailable; stop and retry on next poll
      break;
    }
  }
}

function nowIso() {
  try { return new Date().toISOString(); } catch { return ''; }
}

function getWalletAddress() {
  // Try EVM first (MetaMask or other EVM wallet)
  const eth = window.__walletEVM || window.ethereum || window.web3?.currentProvider;
  if (eth) {
    // Handle MetaMask/injected provider
    if (eth?.isMetaMask || (Array.isArray(eth) && eth.find(p => p?.isMetaMask)) || 
        (Array.isArray(eth?.providers) && eth.providers.find(p => p?.isMetaMask))) {
      const provider = (() => {
        if (eth?.isMetaMask) return eth;
        if (Array.isArray(eth?.providers)) return eth.providers.find(p => p?.isMetaMask) || eth.providers[0] || null;
        if (Array.isArray(eth)) return eth.find(p => p?.isMetaMask) || eth[0] || null;
        return eth;
      })();
      if (provider?.selectedAddress) return provider.selectedAddress;
    }
    // Fallback for other EVM providers
    try {
      if (typeof eth.request === 'function') {
        const accounts = eth.request ? eth.request({ method: 'eth_accounts' }) : null;
        // Handle sync or promise
        if (accounts && typeof accounts.then === 'function') {
          // Promise case - we can't wait here, so return null and let caller handle async
          // But for simplicity, we'll try to get it synchronously if possible
          return null;
        } else if (accounts && Array.isArray(accounts) && accounts[0]) {
          return accounts[0];
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }
  
  // Try Solana (Phantom)
  if (window.phantom?.solana?.publicKey) {
    return window.phantom.solana.publicKey.toString();
  }
  if (window.solana?.publicKey?.toString?.()) {
    return window.solana.publicKey.toString();
  }
  
  return null;
}

const SDG_OPTIONS = [
  { id: 'SDG1', label: 'SDG1 No Poverty' },
  { id: 'SDG2', label: 'SDG2 Zero Hunger' },
  { id: 'SDG3', label: 'SDG3 Good Health' },
  { id: 'SDG4', label: 'SDG4 Quality Education' },
  { id: 'SDG5', label: 'SDG5 Gender Equality' },
  { id: 'SDG6', label: 'SDG6 Clean Water' },
  { id: 'SDG7', label: 'SDG7 Clean Energy' },
  { id: 'SDG8', label: 'SDG8 Decent Work' },
  { id: 'SDG9', label: 'SDG9 Industry/Innovation' },
  { id: 'SDG10', label: 'SDG10 Reduced Inequalities' },
  { id: 'SDG11', label: 'SDG11 Sustainable Cities' },
  { id: 'SDG12', label: 'SDG12 Responsible Consumption' },
  { id: 'SDG13', label: 'SDG13 Climate Action' },
  { id: 'SDG16', label: 'SDG16 Peace/Justice' },
  { id: 'SDG17', label: 'SDG17 Partnerships' }
];

export function initMarketplace() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'marketplace-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `
    <h4>Community Upliftment Marketplace</h4>
    <div style="display:flex; gap:6px; flex-wrap:wrap; margin:6px 0 8px 0;">
      <button data-tab="all" style="padding:4px 8px">All</button>
      <button data-tab="uplift" style="padding:4px 8px">Upliftment</button>
      <button data-tab="bounty" style="padding:4px 8px">Bounties</button>
      <span style="font-size:10px;color:#7aa; align-self:center;">Offline-safe (local tasks supported)</span>
    </div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; margin-bottom:8px;">
      <input data-field="desc" placeholder="Task / project description" style="grid-column: span 2;">
      <input data-field="reward" placeholder="Reward / pledge (BRDG)" inputmode="decimal">
      <select data-field="type">
        <option value="upliftment">Upliftment</option>
        <option value="bounty">Bounty</option>
        <option value="ops">Ops</option>
      </select>
      <select data-field="sdg" style="grid-column: span 2;">
        ${SDG_OPTIONS.map(o => `<option value="${o.id}">${o.label}</option>`).join('')}
      </select>
      <input data-field="location" placeholder="Location (optional)" style="grid-column: span 2;">
      <input data-field="beneficiaries" placeholder="Beneficiaries (optional)" inputmode="numeric">
      <input data-field="proof" placeholder="Proof required (optional)" style="grid-column: span 1;">
      <button data-action="post" style="grid-column: span 1;">Post</button>
    </div>
    <div style="display:flex; gap:6px; align-items:center; margin:0 0 6px 0;">
      <select data-field="filterSdg" style="max-width: 150px;">
        <option value="">All SDGs</option>
        ${SDG_OPTIONS.map(o => `<option value="${o.id}">${o.id}</option>`).join('')}
      </select>
      <input data-field="search" placeholder="Search..." style="flex:1; min-width: 90px;">
    </div>
    <ul data-role="list" style="margin-top:8px; max-height:220px; overflow:auto; padding-left:12px"></ul>
  `;
  container.appendChild(panel);

  const postBtn = panel.querySelector('[data-action="post"]');
  const list = panel.querySelector('[data-role="list"]');
  const inputDesc = panel.querySelector('[data-field="desc"]');
  const inputReward = panel.querySelector('[data-field="reward"]');
  const selectType = panel.querySelector('[data-field="type"]');
  const selectSdg = panel.querySelector('[data-field="sdg"]');
  const inputLocation = panel.querySelector('[data-field="location"]');
  const inputBeneficiaries = panel.querySelector('[data-field="beneficiaries"]');
  const inputProof = panel.querySelector('[data-field="proof"]');
  const filterSdg = panel.querySelector('[data-field="filterSdg"]');
  const search = panel.querySelector('[data-field="search"]');

  let activeTab = 'all';
  const lastPledgedTotals = new Map();

  panel.querySelectorAll('button[data-tab]').forEach(b => {
    b.addEventListener('click', () => {
      activeTab = b.getAttribute('data-tab') || 'all';
      panel.querySelectorAll('button[data-tab]').forEach(x => x.style.opacity = (x === b ? '1' : '0.65'));
      updateTasks();
    });
  });
  // set initial tab visual state
  panel.querySelector('button[data-tab="all"]')?.click?.();

  postBtn.onclick = async () => {
    const desc = inputDesc.value?.trim?.();
    const reward = inputReward.value?.trim?.();
    if (!desc || !reward) return alert('Provide description and reward');
    postBtn.disabled = true;
    try {
      const payload = {
        desc,
        reward,
        type: selectType.value,
        sdg: selectSdg.value,
        location: inputLocation.value?.trim?.() || '',
        beneficiaries: inputBeneficiaries.value?.trim?.() || '',
        proof: inputProof.value?.trim?.() || '',
        created_at: nowIso()
      };

      try {
        await fetch(`${API_BASE}/api/marketplace/task`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } catch (e) {
        // Offline/local fallback
        const local = loadLocalTasks();
        local.unshift({ id: `local-${Date.now()}`, status: 'open', ...payload, local: true });
        saveLocalTasks(local);
      }

      inputDesc.value = '';
      inputReward.value = '';
      inputLocation.value = '';
      inputBeneficiaries.value = '';
      inputProof.value = '';

      await updateTasks();
    } catch (err) {
      console.error('Post task failed', err);
      alert('Post failed');
    }
    postBtn.disabled = false;
  };

  function normalizeTask(t) {
    // Accept old shape {id, desc, reward}
    const type = (t?.type || 'bounty').toLowerCase();
    return {
      id: t?.id ?? `unknown-${Math.random().toString(16).slice(2)}`,
      desc: t?.desc ?? t?.description ?? '',
      reward: t?.reward ?? t?.pledge ?? '',
      type,
      sdg: t?.sdg || '',
      location: t?.location || '',
      beneficiaries: t?.beneficiaries || '',
      proof: t?.proof || '',
      proof_submitted: !!(t?.proof_submitted || t?.impact_verified || t?.verified),
      status: t?.status || 'open',
      pledged_total: Number(t?.pledged_total || 0),
      created_at: t?.created_at || '',
      local: !!t?.local
    };
  }

  function matchesFilters(t) {
    if (activeTab !== 'all' && t.type !== activeTab && !(activeTab === 'uplift' && t.type === 'upliftment')) return false;
    const sdgFilter = filterSdg.value || '';
    if (sdgFilter && (t.sdg || '') !== sdgFilter) return false;
    const q = (search.value || '').trim().toLowerCase();
    if (q) {
      const hay = `${t.desc} ${t.type} ${t.sdg} ${t.location}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  }

  async function updateTasks() {
    try {
      let tasks = [];
      const pledgeEvents = loadPledgeEvents();
      let remoteOk = false;
      let pledgeSums = sumPledgesByTask(pledgeEvents);
      try {
        const remote = await fetchJson(`${API_BASE}/api/marketplace/tasks`);
        tasks = Array.isArray(remote) ? remote.map(normalizeTask) : [];
        const local = loadLocalTasks().map(normalizeTask);
        // Merge local tasks on top (they're not in backend yet)
        tasks = [...local, ...tasks];
        remoteOk = true;
      } catch (e) {
        tasks = loadLocalTasks().map(normalizeTask);
      }

      if (remoteOk) {
        // Best-effort: reconcile offline pledges back to backend (idempotent via event_id).
        reconcileUnconfirmedPledges().catch(() => {});
      }

      // If backend is offline, include ALL local events (confirmed+unconfirmed) for UI continuity.
      if (!remoteOk) {
        const all = new Map();
        for (const e of Array.isArray(pledgeEvents) ? pledgeEvents : []) {
          const id = e?.task_id;
          const amt = Number(e?.amount);
          if (id == null || !Number.isFinite(amt)) continue;
          all.set(String(id), (all.get(String(id)) || 0) + amt);
        }
        pledgeSums = all;
      }

      // Apply local pledge overlay to tasks (unconfirmed only when backend is up).
      tasks = tasks.map(t => {
        const add = pledgeSums.get(String(t.id)) || 0;
        return add ? { ...t, pledged_total: Number(t.pledged_total || 0) + add } : t;
      });

      const filtered = tasks.filter(matchesFilters);

      list.innerHTML = filtered.map(t => {
        const meta = [
          t.type === 'upliftment' ? 'Upliftment' : (t.type === 'bounty' ? 'Bounty' : t.type),
          t.sdg ? t.sdg : null,
          t.location ? t.location : null,
          t.beneficiaries ? `${t.beneficiaries} beneficiaries` : null,
          t.local ? 'local' : null
        ].filter(Boolean).join(' · ');

        const pledgeLine = (t.type === 'upliftment')
          ? `<div style="font-size:11px;color:#7bd;margin-top:4px">
               Pledged: <span data-pledged-amount-for="${t.id}">${t.pledged_total.toFixed(2)}</span> BRDG
               ${t.proof_submitted ? '<span style="margin-left:6px;padding:2px 8px;border-radius:999px;background:#1f7a3a;color:#eafff2;border:1px solid rgba(120,255,170,0.35);font-size:10px;vertical-align:middle;">Verified</span>' : ''}
             </div>`
          : '';

        const actions = (t.type === 'upliftment')
          ? `<button data-pledge-id="${t.id}" style="margin-left:6px">Pledge</button>`
          : `<button data-accept-id="${t.id}" style="margin-left:6px">Accept</button>`;

        return `
          <li style="margin-bottom:8px">
            <div style="color:#cfe">${t.desc || '(no description)'}</div>
            <div style="font-size:11px;color:#8ab">${meta}</div>
            <div style="font-size:12px;color:#bdf;margin-top:4px">
              Target: ${t.reward || '—'} BRDG
              ${actions}
            </div>
            ${pledgeLine}
          </li>
        `;
      }).join('');

       // Accept (bounty) flow
       list.querySelectorAll('button[data-accept-id]').forEach(b => {
         b.onclick = async (e) => {
           const id = e.target.getAttribute('data-accept-id');
           const addr = getWalletAddress();
           if (!addr) return alert('Connect a wallet first');
           
           // Create a message to sign for the acceptance
           const message = `Accept task ${id}`;
           
           // Try to sign the message with the connected wallet
           let signature = null;
           let signedBy = addr;
           try {
             // Try EVM signing first
             if (window.__walletEVM || window.ethereum || window.web3?.currentProvider) {
               signature = await signMessageEVM(message, addr);
               signedBy = `${addr} (EVM)`;
             } else if (window.phantom?.solana?.publicKey || window.solana?.publicKey?.toString?.()) {
               // Try Solana signing
               signature = await signMessageSolana(message);
               signedBy = `${addr} (Solana)`;
             }
           } catch (signError) {
             console.warn('Wallet signing failed, proceeding without signature:', signError);
             // Continue without signature if wallet signing fails
           }
           
           try {
             await fetch(`${API_BASE}/api/marketplace/accept`, {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({ task_id: id, wallet: addr, signature, signedBy })
             });
             alert('Accepted and signed — complete the work and claim reward.');
           } catch {
             // local fallback: mark accepted
             const local = loadLocalTasks();
             const idx = local.findIndex(x => String(x.id) === String(id));
             if (idx >= 0) {
               local[idx].status = 'accepted';
               local[idx].accepted_by = addr;
               local[idx].signature = signature;
               local[idx].signedBy = signedBy;
               saveLocalTasks(local);
               alert('Accepted (local/offline).');
             } else {
               alert('Accept failed (offline).');
             }
           }
           await updateTasks();
         };
       });

   // Pledge (upliftment) flow
       list.querySelectorAll('button[data-pledge-id]').forEach(b => {
         b.onclick = async (e) => {
           const id = e.target.getAttribute('data-pledge-id');
           const addr = getWalletAddress();
           if (!addr) return alert('Connect a wallet first');
           const amountRaw = prompt('Pledge amount (BRDG):', '10');
           if (!amountRaw) return;
           const amount = Number(amountRaw);
           if (!Number.isFinite(amount) || amount <= 0) return alert('Enter a valid pledge amount.');
           const wallet = normWallet(addr);
           const event_id = newEventId();
           
           // Create a message to sign for the pledge
           const message = `Pledge ${amount} BRDG to task ${id}`;
           
           // Try to sign the message with the connected wallet
           let signature = null;
           let signedBy = wallet;
           try {
             // Try EVM signing first
             if (window.__walletEVM || window.ethereum || window.web3?.currentProvider) {
               signature = await signMessageEVM(message, addr);
               signedBy = `${wallet} (EVM)`;
             } else if (window.phantom?.solana?.publicKey || window.solana?.publicKey?.toString?.()) {
               // Try Solana signing
               signature = await signMessageSolana(message);
               signedBy = `${wallet} (Solana)`;
             }
           } catch (signError) {
             console.warn('Wallet signing failed, proceeding without signature:', signError);
             // Continue without signature if wallet signing fails
           }
           
           // Record locally first (offline-safe + instant leaderboard).
           addPledgeEvent({ event_id, task_id: id, wallet, amount, ts: Date.now(), confirmed: false, signature, signedBy });
           try {
             await fetch(`${API_BASE}/api/marketplace/pledge`, {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({ task_id: id, wallet, amount, event_id, signature, signedBy })
             });
             markEventConfirmed(event_id);
             alert('Pledge recorded and signed.');
           } catch {
             alert('Pledge recorded (local/offline).');
           }
           window.dispatchEvent(new CustomEvent('marketplace-update'));
           await updateTasks();
         };
       });

      // Animate upliftment pledged totals when they change.
      filtered.forEach(t => {
        if (t.type !== 'upliftment') return;
        const id = String(t.id);
        const selId = id.replaceAll('"', '\\"');
        const amountEl = list.querySelector(`[data-pledged-amount-for="${selId}"]`);
        if (!amountEl) return;
        const prev = lastPledgedTotals.has(id) ? lastPledgedTotals.get(id) : 0;
        const next = Number(t.pledged_total || 0) || 0;
        lastPledgedTotals.set(id, next);
        if (prev !== next) animateAmount(amountEl, prev, next);
        else amountEl.textContent = next.toFixed(2);
      });
    } catch (err) {
      if (!window._marketplaceErr) { window._marketplaceErr = true; console.warn('Marketplace API unavailable'); }
      list.innerHTML = '<li style="color:#864">Marketplace unavailable</li>';
    }
  }

  filterSdg.addEventListener('change', () => setTimeout(updateTasks, 0));
  search.addEventListener('input', () => setTimeout(updateTasks, 0));

  updateTasks();
  setInterval(() => setTimeout(updateTasks, 0), 15000);
  window.addEventListener('marketplace-update', () => setTimeout(updateTasks, 0));
}

export default initMarketplace;
