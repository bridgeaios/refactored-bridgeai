/**
 * Digital Cognitive Twin — Frontend client
 * Fetches Twin Profile, Decision Engine, Behavioral Simulation, Evolution Loop.
 */
import { API_BASE } from './config.js';

const PROFILE_URL = `${API_BASE}/api/twin/profile`;
const DECIDE_URL = `${API_BASE}/api/twin/decide`;
const SIMULATE_URL = `${API_BASE}/api/twin/simulate`;
const EVOLVE_URL = `${API_BASE}/api/twin/evolve`;

let _cachedProfile = null;

/**
 * Fetch Twin Profile (Identity, Skill Stack, Decision Model, etc.)
 * @returns {Promise<object|null>}
 */
export async function fetchTwinProfile() {
  try {
    const res = await fetch(PROFILE_URL);
    if (!res.ok) return _cachedProfile;
    const data = await res.json();
    _cachedProfile = data;
    return data;
  } catch (e) {
    console.warn('[cognitiveTwin] profile fetch failed:', e);
    return _cachedProfile;
  }
}

/**
 * Get cached Twin Profile.
 */
export function getTwinProfile() {
  return _cachedProfile;
}

/**
 * Decision engine. Returns ranked action or null (silence).
 * @param {object} payload - { environment, goal_vector, constraints, risk_threshold, candidates }
 * @returns {Promise<object|null>}
 */
export async function decide(payload) {
  try {
    const res = await fetch(DECIDE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const inner = data.data ?? data;  // normalized { ok, data, meta } or legacy
    return inner.action === null ? null : inner;
  } catch (e) {
    console.warn('[cognitiveTwin] decide failed:', e);
    return null;
  }
}

/**
 * Behavioral simulation under stress.
 * @param {object} scenario - { uncertainty, pressure, loss, opportunity }
 * @returns {Promise<object|null>}
 */
export async function simulate(scenario) {
  try {
    const res = await fetch(SIMULATE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scenario),
    });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[cognitiveTwin] simulate failed:', e);
    return null;
  }
}

/**
 * Evolution loop — ingest feedback.
 * @param {object} feedback
 * @returns {Promise<object|null>}
 */
export async function evolve(feedback) {
  try {
    const res = await fetch(EVOLVE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedback),
    });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    console.warn('[cognitiveTwin] evolve failed:', e);
    return null;
  }
}

/**
 * Initialize — fetch profile on load.
 */
export function initCognitiveTwin() {
  fetchTwinProfile();
}
