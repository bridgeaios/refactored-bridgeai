/**
 * BRIDGE AI OS — Deterministic System Verification Layer
 * Confirms REST API, WebSocket, heartbeat, and mission board connectivity.
 * Environment-agnostic: localhost, Docker, production.
 */
import { API_BASE, WS_BASE } from './config.js';

const WS_HEARTBEAT_TIMEOUT_MS = 5000;

/**
 * Check REST API connectivity by fetching mission board.
 * @returns {Promise<boolean>} apiStatus
 */
async function checkApi(apiBase) {
  const url = `${apiBase}/api/mission/board`.replace(/\/+/g, '/');
  try {
    const res = await fetch(url);
    if (res.status !== 200) {
      console.error('[systemVerifier] API mission/board returned', res.status);
      return false;
    }
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    const isJson = ct.includes('application/json') || ct.includes('text/json');
    if (!isJson) {
      console.error('[systemVerifier] API mission/board did not return JSON');
      return false;
    }
    const data = await res.json();
    if (data === null || typeof data !== 'object') {
      console.error('[systemVerifier] API mission/board returned invalid JSON');
      return false;
    }
    return true;
  } catch (e) {
    console.error('[systemVerifier] API fetch failed:', e);
    return false;
  }
}

/**
 * Check WebSocket connectivity and heartbeat reception.
 * @returns {Promise<boolean>} wsStatus
 */
function checkWebSocket(wsBase) {
  return new Promise((resolve) => {
    let resolved = false;
    const wsUrl = `${wsBase}/ws/mission`.replace(/([^:]\/)\/+/g, '$1');
    let ws;

    const done = (ok) => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timer);
      try {
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
      } catch (_) {}
      resolve(ok);
    };

    const timer = setTimeout(() => {
      if (!resolved) {
        console.error('[systemVerifier] WebSocket heartbeat timeout (5s)');
        done(false);
      }
    }, WS_HEARTBEAT_TIMEOUT_MS);

    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      console.error('[systemVerifier] WebSocket creation failed:', e);
      done(false);
      return;
    }

    ws.onopen = () => {
      // Server may send heartbeat shortly after connect; wait for it
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && data.type === 'heartbeat') {
          done(true);
        }
      } catch (_) {}
    };

    ws.onerror = (e) => {
      if (!resolved) {
        console.error('[systemVerifier] WebSocket error:', e);
        done(false);
      }
    };

    ws.onclose = () => {
      if (!resolved) {
        console.error('[systemVerifier] WebSocket closed before heartbeat');
        done(false);
      }
    };
  });
}

/**
 * Run full system check: API + WebSocket + heartbeat.
 * @returns {Promise<{ apiStatus: boolean, wsStatus: boolean, overall: boolean }>}
 */
export async function runSystemCheck() {
  const apiBase = API_BASE || (typeof location !== 'undefined' ? '' : '');
  const wsBase = WS_BASE || (typeof location !== 'undefined'
    ? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
    : 'ws://localhost');

  const [apiStatus, wsStatus] = await Promise.all([
    checkApi(apiBase),
    checkWebSocket(wsBase),
  ]);

  const overall = apiStatus && wsStatus;

  console.log('=== SYSTEM CHECK ===');
  console.log('API:', apiStatus ? 'OK' : 'FAIL');
  console.log('WS:', wsStatus ? 'OK' : 'FAIL');
  console.log('OVERALL:', overall ? 'OK' : 'FAIL');

  return { apiStatus, wsStatus, overall };
}
