/**
 * Shared XML — Twins share a canonical XML document.
 * Fetches from /api/twin/shared-xml, parses for mission/face_state, syncs periodically.
 */
import { API_BASE } from './config.js';

const SHARED_XML_URL = `${API_BASE}/api/twin/shared-xml`;
const SYNC_INTERVAL_MS = 8000;

let _cachedXml = null;
let _parsedDoc = null;
let _listeners = new Set();

/**
 * Fetch shared XML from backend.
 * @returns {Promise<string|null>}
 */
export async function fetchSharedXml() {
  try {
    const res = await fetch(SHARED_XML_URL);
    if (!res.ok) return _cachedXml;
    const xml = await res.text();
    _cachedXml = xml;
    _parsedDoc = parseXml(xml);
    _listeners.forEach(fn => fn(_cachedXml, _parsedDoc));
    return xml;
  } catch (e) {
    console.warn('[twinSharedXml] fetch failed:', e);
    return _cachedXml;
  }
}

/**
 * POST shared XML to backend (all Twins will see it).
 * @param {string} xml
 * @returns {Promise<boolean>}
 */
export async function setSharedXml(xml) {
  try {
    const res = await fetch(SHARED_XML_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/xml' },
      body: xml,
    });
    if (!res.ok) return false;
    _cachedXml = xml;
    _parsedDoc = parseXml(xml);
    _listeners.forEach(fn => fn(_cachedXml, _parsedDoc));
    return true;
  } catch (e) {
    console.warn('[twinSharedXml] set failed:', e);
    return false;
  }
}

/**
 * Parse XML string to a simple object (mission counts, face_state).
 * @param {string} xml
 * @returns {{ mission?: object, face_state?: string } | null}
 */
function parseXml(xml) {
  if (!xml || typeof xml !== 'string') return null;
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'application/xml');
    const parseErr = doc.querySelector('parsererror');
    if (parseErr) return null;

    const mission = {};
    const missionEl = doc.querySelector('mission');
    if (missionEl) {
      ['backlog', 'in_progress', 'review', 'done'].forEach(k => {
        const el = missionEl.querySelector(k);
        mission[k] = el ? parseInt(el.textContent || '0', 10) : 0;
      });
    }

    const faceStateEl = doc.querySelector('face_state');
    const face_state = faceStateEl ? faceStateEl.textContent?.trim() || 'ALIVE' : 'ALIVE';

    const authorityEl = doc.querySelector('authority');
    const authority = authorityEl ? authorityEl.textContent?.trim() : null;

    const backendEl = doc.querySelector('backend');
    const backend = backendEl ? backendEl.textContent?.trim() : null;

    return {
      mission: Object.keys(mission).length ? mission : undefined,
      face_state,
      authority: authority || 'I am the Bridge. I am the Founder. I am the System. I am the Authority.',
      backend: backend || 'human',
    };
  } catch (_) {
    return null;
  }
}

/**
 * Get parsed shared XML (mission, face_state).
 * @returns {{ mission?: object, face_state?: string } | null}
 */
export function getParsedSharedXml() {
  return _parsedDoc;
}

/**
 * Get raw shared XML string.
 */
export function getRawSharedXml() {
  return _cachedXml;
}

/**
 * Subscribe to shared XML updates.
 * @param {(xml: string, parsed: object) => void} fn
 * @returns {() => void} unsubscribe
 */
export function onSharedXmlUpdate(fn) {
  _listeners.add(fn);
  if (_cachedXml) fn(_cachedXml, _parsedDoc);
  return () => _listeners.delete(fn);
}

/**
 * Initialize shared XML sync — fetches on load and polls.
 * setInterval only schedules; work runs async to avoid handler violation.
 */
export function initTwinSharedXml() {
  const schedule = () => setTimeout(() => fetchSharedXml(), 0);
  schedule();
  setInterval(schedule, SYNC_INTERVAL_MS);
}
