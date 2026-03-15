// Same-origin: /api/* and /ws/* proxied by frontend server to backend:8081 (avoids CORS)
// Override: window.__API_BASE or window.__WS_BASE before script load if using direct backend
export const API_BASE = (typeof window !== 'undefined' && window.__API_BASE != null)
  ? String(window.__API_BASE) : '';
export const WS_BASE = (typeof window !== 'undefined' && window.__WS_BASE != null)
  ? String(window.__WS_BASE) : (typeof location !== 'undefined' ? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}` : '');
