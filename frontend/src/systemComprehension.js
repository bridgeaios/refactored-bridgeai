/**
 * Bridge_System_Comprehension — Frontend client
 * Structural mapping, operational model, role awareness, alignment filter.
 */
import { API_BASE } from './config.js';

const BASE = `${API_BASE}/api/system/comprehension`;

/**
 * Fetch full system map: mission, architecture, economic engine, roles, governance, revenue.
 */
export async function getSystemMap() {
  try {
    const res = await fetch(`${BASE}`);
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[systemComprehension] getSystemMap failed:', e);
    return null;
  }
}

/**
 * Explain The Bridge at Level 1 (simple), 2 (operational), or 3 (strategic).
 */
export async function explainSystem(level = 1) {
  try {
    const res = await fetch(`${BASE}/explain?level=${level}`);
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[systemComprehension] explain failed:', e);
    return null;
  }
}

/**
 * Get operational model: Input → Processing → Output → Feedback → Reinforcement.
 */
export async function getOperationalModel() {
  try {
    const res = await fetch(`${BASE}/operational-model`);
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[systemComprehension] operationalModel failed:', e);
    return null;
  }
}

/**
 * Get role awareness: twin function, authority boundaries, decision constraints.
 */
export async function getRoleAwareness() {
  try {
    const res = await fetch(`${BASE}/role-awareness`);
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[systemComprehension] roleAwareness failed:', e);
    return null;
  }
}

/**
 * Check if action is aligned with mission. Returns { aligned, reason, confidence, clarification_needed }.
 */
export async function checkAlignment(action, context = {}) {
  try {
    const res = await fetch(`${BASE}/check-alignment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, context }),
    });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[systemComprehension] checkAlignment failed:', e);
    return null;
  }
}

/**
 * Skill definition.
 */
export async function getSkillDefinition() {
  try {
    const res = await fetch(`${BASE}/skill`);
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[systemComprehension] skill failed:', e);
    return null;
  }
}

export function initSystemComprehension() {
  window.getSystemMap = getSystemMap;
  window.explainSystem = (level) => explainSystem(level);
  window.checkAlignment = checkAlignment;

  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'system-comprehension-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;font-size:12px;';
  panel.innerHTML = `
    <h4 style="margin:4px 0">System Comprehension</h4>
    <button class="sys-btn" data-level="1">Explain (Simple)</button>
    <button class="sys-btn" data-level="2">Explain (Operational)</button>
    <button class="sys-btn" data-level="3">Explain (Strategic)</button>
    <div id="sys-result" style="margin-top:6px;font-size:11px;color:#8ac;max-height:80px;overflow:auto;"></div>
  `;
  container.appendChild(panel);

  const resultEl = document.getElementById('sys-result');
  const runAsync = (fn) => () => { setTimeout(fn, 0); };
  panel.querySelectorAll('.sys-btn').forEach(btn => {
    btn.onclick = runAsync(async () => {
      const level = parseInt(btn.getAttribute('data-level'), 10);
      resultEl.textContent = 'Loading...';
      const data = await explainSystem(level);
      resultEl.textContent = data?.text || (data ? JSON.stringify(data) : 'Unavailable');
    });
  });
}
