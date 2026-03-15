// Founder TODO — linked to digital twin wallpaper. Live updates when objectives met.
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';

const DEFAULT_TODO = {
  version: 1,
  updatedAt: null,
  objectives: [
    { id: 'obj-1', title: 'Ship Phase 4 - Frontend Control Surface', status: 'pending', completedAt: null },
    { id: 'obj-2', title: 'Stabilize Bridge Live Wall integration', status: 'pending', completedAt: null },
    { id: 'obj-3', title: 'AWS credentials configured', status: 'pending', completedAt: null },
    { id: 'obj-4', title: 'Skills pipeline composable', status: 'pending', completedAt: null },
    { id: 'obj-5', title: 'Dashboard + Installer live (3000/7777)', status: 'complete', completedAt: null }
  ]
};

export function initFounderTodo() {
  const el = document.getElementById('founderTodo');
  if (!el) return;

  function render(data) {
    const objs = data?.objectives ?? [];
    const done = objs.filter(o => o.status === 'complete').length;
    const total = objs.length;
    el.innerHTML = `
      <h4>Founder Objectives</h4>
      <div style="margin-bottom:6px;font-size:11px;color:#8af;">${done}/${total} complete → Wallpaper updates live</div>
      ${objs.map(o => `
        <div style="margin:4px 0;display:flex;align-items:center;gap:6px;">
          <span style="color:${o.status === 'complete' ? '#8f8' : '#666'}">
            ${o.status === 'complete' ? '[OK]' : '[ ]'}
          </span>
          <span style="flex:1;${o.status === 'complete' ? 'text-decoration:line-through;color:#999' : ''}">${o.title}</span>
          ${o.status === 'pending' ? `<button class="btn-complete" data-id="${o.id}" style="font-size:10px;padding:2px 6px;cursor:pointer;background:#2a4;color:#fff;border:none;border-radius:4px;">Complete</button>` : ''}
        </div>
      `).join('')}
    `;
    el.querySelectorAll('.btn-complete').forEach(btn => {
      btn.addEventListener('click', () => completeObjective(btn.dataset.id));
    });
  }

  async function completeObjective(id) {
    try {
      const r = await fetch(`${API_BASE}/api/founder-todo/${id}/complete`, { method: 'PATCH' });
      if (!r.ok) throw new Error(await r.text());
      await load();
    } catch (e) {
      console.warn('mark complete failed:', e);
    }
  }

  async function load() {
    try {
      const data = await fetchJson(`${API_BASE}/api/founder-todo`);
      render(data);
    } catch (e) {
      render(DEFAULT_TODO);
    }
  }

  load();
  setInterval(load, 15000);
}
