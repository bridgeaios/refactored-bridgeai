/**
 * Digital Cognitive Twin — UI Panel
 * Displays Twin Profile, Env API keys status, Simulate, Evolve. Call on the Twin for key status (no secret values).
 */
import { fetchTwinProfile, getTwinProfile, decide, simulate, evolve } from './cognitiveTwin.js';
import { API_BASE } from './config.js';
import { escapeHtml } from './bridgeUi.js';

async function fetchTwinEnvKeys() {
  try {
    const res = await fetch(`${API_BASE}/api/twin/env-keys`);
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[twinPanel] env-keys fetch failed:', e);
    return null;
  }
}

function renderEnvKeysSection(keysData) {
  if (!keysData?.keys?.length) return '<div class="twin-section"><strong>Env keys</strong><div class="twin-list">—</div></div>';
  const lines = keysData.keys.map((k) => {
    const sym = k.status === 'configured' ? '✓' : (k.status === 'placeholder' ? '○' : '✗');
    const cls = k.status === 'configured' ? 'color:#8fc' : (k.critical ? 'color:#f88' : 'color:#888');
    return `<div style="${cls}">${sym} ${escapeHtml(k.label)} (${escapeHtml(k.key)}) — ${escapeHtml(k.status)}</div>`;
  });
  const sum = keysData.summary || {};
  return `
    <div class="twin-section">
      <strong>Env API keys</strong>
      <div class="twin-list" style="font-size:0.9em">${sum.configured ?? 0} configured, ${sum.criticalMissing ?? 0} critical missing</div>
      <div class="twin-keys-list">${lines.join('')}</div>
    </div>`;
}

export function initTwinPanel() {
  const panel = document.getElementById('twinPanel');
  if (!panel) return;

  panel.innerHTML = '<div style="font-weight:bold">Digital Twin</div><div class="twin-loading">Loading profile...</div>';

  async function renderProfile() {
    let profile = getTwinProfile();
    if (!profile) {
      profile = await fetchTwinProfile();
    }
    const keysData = await fetchTwinEnvKeys();

    if (!profile) {
      const loading = panel.querySelector('.twin-loading');
      if (loading) loading.textContent = 'Profile unavailable';
      if (keysData) {
        const keysHtml = renderEnvKeysSection(keysData);
        panel.innerHTML = '<div style="font-weight:bold">Digital Twin</div><div class="twin-profile">' + keysHtml + '</div>';
      }
      return;
    }

    const id = profile.identity || {};
    const skills = profile.skill_stack || {};
    const dm = profile.decision_model || {};

    const envKeysHtml = renderEnvKeysSection(keysData);

    const html = `
      <div class="twin-profile">
        <div class="twin-section">
          <strong>Identity</strong>
          <div>Mode: ${escapeHtml(id.cognitive_mode || '-')} · Horizon: ${escapeHtml(id.time_horizon_bias || '-')}</div>
          <div class="twin-values">${(id.core_values || []).slice(0, 3).map(v => escapeHtml(v)).join(', ')}</div>
        </div>
        <div class="twin-section">
          <strong>Skills</strong>
          <div>Hard: ${(skills.hard || []).length} · Soft: ${(skills.soft || []).length} · Meta: ${(skills.meta || []).length}</div>
          <div class="twin-skill">Effective: ${(skills.effective_skill ?? 0).toFixed(2)}</div>
        </div>
        <div class="twin-section">
          <strong>Decision</strong>
          <div>Silence threshold: ${dm.silence_threshold ?? 0} · Weights: ${Object.keys(dm.weights || {}).map(w => escapeHtml(w)).join(', ')}</div>
        </div>
        <div class="twin-section">
          <strong>Blind spots</strong>
          <div class="twin-list">${(profile.blind_spots || []).slice(0, 2).map(b => escapeHtml(b)).join(' · ') || 'None'}</div>
        </div>
        ${envKeysHtml}
        <div class="twin-actions">
          <button id="twin-simulate" class="twin-btn">Simulate</button>
          <button id="twin-decide" class="twin-btn">Decide</button>
          <button id="twin-evolve" class="twin-btn">Evolve</button>
          <button id="twin-refresh" class="twin-btn">↻</button>
        </div>
        <div id="twin-result" class="twin-result"></div>
      </div>
    `;

    const loading = panel.querySelector('.twin-loading');
    if (loading) {
      loading.outerHTML = html;
    } else {
      panel.innerHTML = '<div style="font-weight:bold">Digital Twin</div>' + html;
    }

    const resultEl = panel.querySelector('#twin-result');
    const showResult = (text, ok = true) => {
      if (!resultEl) return;
      resultEl.textContent = text;
      resultEl.style.color = ok ? '#8fc' : '#f88';
      resultEl.style.display = 'block';
      setTimeout(() => { resultEl.style.display = 'none'; }, 4000);
    };

    const runAsync = (fn) => () => { setTimeout(fn, 0); };

    panel.querySelector('#twin-simulate')?.addEventListener('click', runAsync(async () => {
      const scenario = { uncertainty: 0.8, pressure: 0.5, loss: 0.2, opportunity: 0.3 };
      const out = await simulate(scenario);
      showResult(out ? `${out.reaction} → ${out.action}` : 'Simulate failed', !!out);
    }));

    panel.querySelector('#twin-decide')?.addEventListener('click', runAsync(async () => {
      const payload = {
        environment: { context: 'demo' },
        goal_vector: [0.8, 0.7],
        constraints: ['ethical'],
        risk_threshold: 0.5,
        candidates: [
          { action_id: 'a1', expected_value: 0.9, ethical_compliance: 0.8, strategic_alignment: 0.7, long_term_compounding: 0.6 },
          { action_id: 'a2', expected_value: 0.5, ethical_compliance: 0.9, strategic_alignment: 0.6, long_term_compounding: 0.8 },
        ],
      };
      const out = await decide(payload);
      showResult(out ? `Action: ${out.action?.action_id} (rank ${out.action?.rank?.toFixed(2)})` : 'Silence (no positive value)', !!out);
    }));

    panel.querySelector('#twin-evolve')?.addEventListener('click', runAsync(async () => {
      const feedback = { event: 'user_feedback', note: 'Twin panel evolve test', timestamp: Date.now() };
      const out = await evolve(feedback);
      showResult(out?.feedback_ingested ? 'Evolution loop ingested' : 'Evolve failed', !!out?.feedback_ingested);
    }));

    panel.querySelector('#twin-refresh')?.addEventListener('click', runAsync(async () => {
      await fetchTwinProfile();
      renderProfile();
    }));
  }

  renderProfile();
}
