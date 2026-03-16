// Bridge UI helpers — shared across panels
export function escapeHtml(s) {
  if (s == null) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

export function formatBrdg(v, decimals = 2) {
  return (v != null && !isNaN(Number(v))) ? Number(v).toFixed(decimals) : '0.00';
}

export function showToast(msg, type = 'info', durationMs = 3500) {
  const el = document.createElement('div');
  const bg = type === 'success' ? '#16a34a' : type === 'error' ? '#dc2626' : '#334155';
  el.style.cssText = `position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;padding:.75rem 1.25rem;border-radius:8px;background:${bg};color:#fff;font-size:.85rem;font-family:system-ui,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.25);`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), durationMs);
}
