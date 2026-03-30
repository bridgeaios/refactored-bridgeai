/**
 * KeyForge — Client-side Deterministic Rotating Key Validator
 *
 * Mirrors the Python KeyForge system for cross-runtime compatibility.
 * Any node with the same master secret derives identical keys.
 *
 * Usage:
 *   const forge = new KeyForge(masterHex);
 *   const token = forge.issue('api-gateway');
 *   const result = forge.validate(token);
 */

const KEY_VERSION = 2;
const TOKEN_PREFIX = 'kf2.';
const EPOCH_DURATION_SEC = 600;  // 10 minutes
const DRIFT_TOLERANCE = 1;
const CHAIN_LOOKBACK = 3;
const MAX_TOKEN_AGE_SEC = EPOCH_DURATION_SEC * (DRIFT_TOLERANCE + 1) * 2;

// ── Crypto helpers (Web Crypto API) ────────────────────────────────

async function hmacSha256(keyBytes, msgBytes) {
  const cryptoKey = await crypto.subtle.importKey(
    'raw', keyBytes, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  );
  const sig = await crypto.subtle.sign('HMAC', cryptoKey, msgBytes);
  return new Uint8Array(sig);
}

async function sha256(data) {
  const hash = await crypto.subtle.digest('SHA-256', data);
  return new Uint8Array(hash);
}

async function sha512(data) {
  const hash = await crypto.subtle.digest('SHA-512', data);
  return new Uint8Array(hash);
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes) {
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}

function textToBytes(str) {
  return new TextEncoder().encode(str);
}

function concatBytes(...arrays) {
  const total = arrays.reduce((s, a) => s + a.length, 0);
  const result = new Uint8Array(total);
  let offset = 0;
  for (const arr of arrays) {
    result.set(arr, offset);
    offset += arr.length;
  }
  return result;
}

function padTo(bytes, len) {
  if (bytes.length >= len) return bytes.slice(0, len);
  const padded = new Uint8Array(len);
  padded.set(bytes);
  return padded;
}

function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

// ── Epoch ──────────────────────────────────────────────────────────

function currentEpoch(now) {
  return Math.floor((now || Date.now() / 1000) / EPOCH_DURATION_SEC);
}

function epochRange(center, tolerance = DRIFT_TOLERANCE) {
  const result = [];
  for (let i = center - tolerance; i <= center + tolerance; i++) {
    result.push(i);
  }
  return result;
}

// ── Key Derivation ─────────────────────────────────────────────────

async function deriveEpochKey(master, epoch) {
  return hmacSha256(master, textToBytes(`keyforge-epoch-${KEY_VERSION}-${epoch}`));
}

async function rollingEntropy(master, epoch) {
  let chain = new Uint8Array(0);
  for (let i = 0; i < CHAIN_LOOKBACK; i++) {
    const prev = epoch - i - 1;
    if (prev < 0) continue;
    const ek = await deriveEpochKey(master, prev);
    chain = concatBytes(chain, ek);
  }
  if (chain.length === 0) chain = new Uint8Array(32);
  return sha256(chain);
}

async function deriveKey(master, epoch, scope, keyId = 'default') {
  const epochKey = await deriveEpochKey(master, epoch);
  const entropy = await rollingEntropy(master, epoch);

  // Version: 2 bytes big-endian
  const versionBytes = new Uint8Array(2);
  new DataView(versionBytes.buffer).setUint16(0, KEY_VERSION);

  const scopeBytes = padTo(textToBytes(scope), 64);
  const keyIdBytes = padTo(textToBytes(keyId), 32);

  const msg = concatBytes(versionBytes, scopeBytes, keyIdBytes, entropy);
  return hmacSha256(epochKey, msg);
}

async function signPayload(master, epoch, scope, keyId, issuedAt) {
  const derived = await deriveKey(master, epoch, scope, keyId);
  const msg = textToBytes(`${KEY_VERSION}:${epoch}:${scope}:${keyId}:${issuedAt.toFixed(3)}`);
  const sig = await hmacSha256(derived, msg);
  return bytesToHex(sig);
}

// ── Token Serialization ────────────────────────────────────────────

function serializeToken(version, epoch, scope, keyId, issuedAt, signature) {
  const payload = JSON.stringify({ v: version, e: epoch, s: scope, k: keyId, t: issuedAt });
  const b64 = btoa(payload).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `${TOKEN_PREFIX}${b64}.${signature}`;
}

function deserializeToken(raw) {
  if (!raw.startsWith(TOKEN_PREFIX)) return null;
  const body = raw.slice(TOKEN_PREFIX.length);
  const dotIdx = body.lastIndexOf('.');
  if (dotIdx === -1) return null;
  const b64 = body.slice(0, dotIdx);
  const sig = body.slice(dotIdx + 1);
  try {
    const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
    const json_ = atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
    const p = JSON.parse(json_);
    return { version: p.v, epoch: p.e, scope: p.s, keyId: p.k || 'default', issuedAt: p.t, signature: sig };
  } catch {
    return null;
  }
}

// ── KeyForge Class ─────────────────────────────────────────────────

export class KeyForge {
  /**
   * @param {string} masterHex - Hex-encoded master secret (≥64 chars)
   */
  constructor(masterHex) {
    if (!masterHex || masterHex.length < 64) {
      throw new Error('KeyForge: master secret must be at least 64 hex chars');
    }
    this._master = hexToBytes(masterHex);
    this._activeKeys = new Set(['default']);
    this._revokedKeys = new Set();
    this._revokedScopes = new Set();
  }

  /**
   * Create from explicit secret string (hashed to master)
   */
  static async fromSecret(secret) {
    if (secret.length < 32) throw new Error('Secret must be at least 32 chars');
    const hash = await sha512(textToBytes(secret));
    return new KeyForge(bytesToHex(hash));
  }

  // Key management
  addKey(keyId) { this._activeKeys.add(keyId); }
  removeKey(keyId) { this._activeKeys.delete(keyId); this._revokedKeys.add(keyId); }
  revokeScope(scope) { this._revokedScopes.add(scope); }
  reinstateScope(scope) { this._revokedScopes.delete(scope); }

  isRevoked(keyId, scope) {
    return this._revokedKeys.has(keyId) || this._revokedScopes.has(scope);
  }

  /**
   * Issue a scoped token.
   * @param {string} scope
   * @param {object} [opts]
   * @param {string} [opts.keyId='default']
   * @param {number} [opts.now] - Override time (unix seconds)
   * @returns {Promise<string>} Serialized token
   */
  async issue(scope, { keyId = 'default', now } = {}) {
    if (!this._activeKeys.has(keyId)) throw new Error(`Key '${keyId}' is not active`);
    if (this.isRevoked(keyId, scope)) throw new Error(`Key or scope revoked`);

    const ts = now || Date.now() / 1000;
    const epoch = currentEpoch(ts);
    const sig = await signPayload(this._master, epoch, scope, keyId, ts);

    return serializeToken(KEY_VERSION, epoch, scope, keyId, ts, sig);
  }

  /**
   * Validate a token.
   * @param {string} rawToken
   * @param {object} [opts]
   * @param {string} [opts.requiredScope]
   * @param {number} [opts.now]
   * @returns {Promise<{valid: boolean, scope?: string, keyId?: string, epoch?: number, reason?: string}>}
   */
  async validate(rawToken, { requiredScope, now } = {}) {
    const token = deserializeToken(rawToken);
    if (!token) return { valid: false, reason: 'malformed_token' };
    if (token.version !== KEY_VERSION) return { valid: false, reason: `version_mismatch:${token.version}` };
    if (this.isRevoked(token.keyId, token.scope)) return { valid: false, reason: 'revoked' };

    const ts = now || Date.now() / 1000;
    const curEpoch = currentEpoch(ts);
    const validEpochs = epochRange(curEpoch);

    if (!validEpochs.includes(token.epoch)) {
      return { valid: false, reason: 'epoch_expired', epoch: token.epoch };
    }

    const age = ts - token.issuedAt;
    if (age > MAX_TOKEN_AGE_SEC || age < -60) {
      return { valid: false, reason: 'token_too_old' };
    }

    if (requiredScope && token.scope !== requiredScope) {
      return { valid: false, reason: `scope_mismatch:${token.scope}` };
    }

    const expectedSig = await signPayload(this._master, token.epoch, token.scope, token.keyId, token.issuedAt);
    if (!constantTimeEqual(expectedSig, token.signature)) {
      return { valid: false, reason: 'invalid_signature' };
    }

    return {
      valid: true,
      scope: token.scope,
      keyId: token.keyId,
      epoch: token.epoch,
      drift: token.epoch - curEpoch,
    };
  }

  /**
   * Merge revocation state from another node.
   */
  mergeState(state) {
    if (state.revoked_keys) state.revoked_keys.forEach(k => this._revokedKeys.add(k));
    if (state.revoked_scopes) state.revoked_scopes.forEach(s => this._revokedScopes.add(s));
    if (state.active_keys) {
      // Intersection — removals propagate
      const remote = new Set(state.active_keys);
      for (const k of this._activeKeys) {
        if (!remote.has(k)) this._activeKeys.delete(k);
      }
    }
  }

  status() {
    return {
      version: KEY_VERSION,
      epoch: currentEpoch(),
      activeKeys: [...this._activeKeys],
      revokedKeys: [...this._revokedKeys],
      revokedScopes: [...this._revokedScopes],
    };
  }
}
