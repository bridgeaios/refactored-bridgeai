// frontend/src/api.js
// Safe fetch helper – avoids parsing HTML as JSON when API returns 404/error page
export async function fetchJson(url, opts = {}) {
  const r = await fetch(url, opts);
  const ct = (r.headers.get('content-type') || '').toLowerCase();
  const isJson = ct.includes('application/json') || ct.includes('text/json');
  if (!r.ok || !isJson) {
    throw new Error('API unavailable');
  }
  return r.json();
}
