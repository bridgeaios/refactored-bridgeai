// frontend/src/api.js
// Safe fetch helper – avoids parsing HTML as JSON when API returns 404/error page.
// Provides structured error with HTTP status + retries for transient failures (429/503).

const _RETRY_STATUSES = new Set([429, 503, 504]);
const _DEFAULT_RETRIES = 2;
const _BASE_DELAY_MS = 400;

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function _sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function fetchJson(url, opts = {}, _attempt = 0) {
  let r;
  try {
    r = await fetch(url, opts);
  } catch (networkErr) {
    throw new ApiError(`Network error: ${networkErr.message}`, 0, null);
  }

  const ct = (r.headers.get('content-type') || '').toLowerCase();
  const isJson = ct.includes('application/json') || ct.includes('text/json');

  if (!r.ok) {
    // Retry transient errors with exponential back-off
    if (_RETRY_STATUSES.has(r.status) && _attempt < _DEFAULT_RETRIES) {
      await _sleep(_BASE_DELAY_MS * 2 ** _attempt);
      return fetchJson(url, opts, _attempt + 1);
    }
    let detail = `HTTP ${r.status}`;
    if (isJson) {
      try {
        const errBody = await r.json();
        detail = errBody?.detail || errBody?.error || errBody?.message || detail;
      } catch (_) { /* ignore */ }
    }
    throw new ApiError(detail, r.status, null);
  }

  if (!isJson) {
    throw new ApiError('API returned non-JSON response', r.status, null);
  }

  return r.json();
}
