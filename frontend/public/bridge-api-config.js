/**
 * Bridge AI OS — Centralized API & Spine Config
 * All surfaces share: DB (MemoryStore/Redis), Spine (reducers), Revenue (Treasury).
 * Local + Cloud: switch via ?api=cloud or localStorage.bridge_api_mode
 */
(function () {
  const LOCAL = 'http://localhost:8000';
  const CLOUD = 'https://api.bridge-ai-os.tech';

  function getParam(name) {
    try {
      const m = new URLSearchParams(location.search || '');
      return m.get(name);
    } catch { return null; }
  }

  const urlMode = getParam('api') || getParam('bridge_api');
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('bridge_api_mode') : null;
  const mode = urlMode || stored || 'local';

  if (typeof localStorage !== 'undefined' && urlMode && urlMode !== stored) {
    localStorage.setItem('bridge_api_mode', urlMode);
  }

  const base = mode === 'cloud' ? CLOUD : LOCAL;
  const wsBase = mode === 'cloud' ? 'wss://api.bridge-ai-os.tech' : 'ws://localhost:8000';
  window.__API_BASE = base;
  window.__WS_BASE = wsBase;
  window.__BRIDGE_SPINE = true;
  window.__BRIDGE_REVENUE_CENTRAL = true;
  window.__BRIDGE_DB_SHARED = true;
  window.__BRIDGE_API_MODE = mode;
})();
