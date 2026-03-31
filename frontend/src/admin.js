/**
 * BRIDGE AI OS — Admin Key Management
 * Fetches current key status, allows setting keys, saves to backend .env
 */

const KEY_DEFINITIONS = [
  // ── AI / LLM ──
  {
    group: 'AI / LLM Providers',
    keys: [
      { env: 'ANTHROPIC_API_KEY', label: 'Anthropic (Claude)', desc: 'Powers core AI reasoning', url: 'https://console.anthropic.com/settings/keys', urlLabel: 'Get Key' },
      { env: 'OPENAI_API_KEY', label: 'OpenAI', desc: 'GPT models (if used)', url: 'https://platform.openai.com/api-keys', urlLabel: 'Get Key' },
      { env: 'OPENROUTER_API_KEY', label: 'OpenRouter', desc: 'Multi-model routing', url: 'https://openrouter.ai/keys', urlLabel: 'Get Key' },
      { env: 'OPENROUTER_API_KEY_2', label: 'OpenRouter (Secondary)', desc: 'Backup / high-volume key', url: 'https://openrouter.ai/keys', urlLabel: 'Get Key' },
      { env: 'HUGGING_FACE_API_KEY', label: 'Hugging Face', desc: 'Model inference & datasets', url: 'https://huggingface.co/settings/tokens', urlLabel: 'Get Token' },
      { env: 'ELEVENLABS_API_KEY', label: 'ElevenLabs', desc: 'Voice synthesis', url: 'https://elevenlabs.io/app/settings/api-keys', urlLabel: 'Get Key' },
    ],
  },
  // ── Auth & Identity ──
  {
    group: 'Auth & Identity',
    keys: [
      { env: 'GOOGLE_CLIENT_ID', label: 'Google OAuth Client ID', desc: 'Google sign-in', url: 'https://console.cloud.google.com/apis/credentials', urlLabel: 'Console' },
      { env: 'GOOGLE_CLIENT_SECRET', label: 'Google OAuth Secret', desc: 'Google sign-in secret', url: 'https://console.cloud.google.com/apis/credentials', urlLabel: 'Console' },
      { env: 'NEXTAUTH_SECRET', label: 'NextAuth Secret', desc: 'Session encryption (auto-generated)', generated: true },
      { env: 'JWT_SECRET', label: 'JWT Secret', desc: 'General JWT signing (auto-generated)', generated: true },
      { env: 'JWT_SECRET_KEY', label: 'JWT Secret Key', desc: 'Extended JWT signing (auto-generated)', generated: true },
      { env: 'BRIDGE_SIWE_JWT_SECRET', label: 'SIWE JWT Secret', desc: 'Web3 wallet auth signing (auto-generated)', generated: true },
      { env: 'BRIDGE_INTERNAL_SECRET', label: 'Internal Service Secret', desc: 'Service-to-service auth (auto-generated)', generated: true },
      { env: 'BRIDGE_ORCHESTRATOR_SECRET', label: 'Orchestrator Secret', desc: 'System-level orchestration auth (auto-generated)', generated: true },
    ],
  },
  // ── Payments ──
  {
    group: 'Payment Processors',
    keys: [
      { env: 'PAYPAL_CLIENT_ID', label: 'PayPal Client ID', desc: 'PayPal payments', url: 'https://developer.paypal.com/dashboard/applications/live', urlLabel: 'Dashboard' },
      { env: 'PAYPAL_CLIENT_SECRET', label: 'PayPal Client Secret', desc: 'PayPal API secret', url: 'https://developer.paypal.com/dashboard/applications/live', urlLabel: 'Dashboard' },
      { env: 'PAYSTACK_PUBLIC_KEY', label: 'Paystack Public Key', desc: 'Paystack payments (Africa)', url: 'https://dashboard.paystack.com/#/settings/developers', urlLabel: 'Dashboard' },
      { env: 'PAYSTACK_SECRET_KEY', label: 'Paystack Secret Key', desc: 'Paystack API secret', url: 'https://dashboard.paystack.com/#/settings/developers', urlLabel: 'Dashboard' },
      { env: 'PAYSTACK_WEBHOOK_SECRET', label: 'Paystack Webhook Secret', desc: 'Webhook signature verification', url: 'https://dashboard.paystack.com/#/settings/developers', urlLabel: 'Dashboard' },
    ],
  },
  // ── Email / Comms ──
  {
    group: 'Email & Communications',
    keys: [
      { env: 'RESEND_API_KEY', label: 'Resend', desc: 'Transactional email', url: 'https://resend.com/api-keys', urlLabel: 'Get Key' },
      { env: 'SMTP_PASSWORD', label: 'SMTP Password (Brevo)', desc: 'Brevo/Sendinblue SMTP relay', url: 'https://app.brevo.com/settings/keys/smtp', urlLabel: 'Get Key' },
      { env: 'DISCORD_BOT_TOKEN', label: 'Discord Bot Token', desc: 'Discord integration', url: 'https://discord.com/developers/applications', urlLabel: 'Dev Portal' },
    ],
  },
  // ── Infrastructure ──
  {
    group: 'Infrastructure',
    keys: [
      { env: 'CLOUDFLARE_ACCOUNT_ID', label: 'Cloudflare Account ID', desc: 'R2 storage & Workers', url: 'https://dash.cloudflare.com/', urlLabel: 'Dashboard' },
      { env: 'TURNSTILE_SECRET_KEY', label: 'Cloudflare Turnstile Secret', desc: 'Bot protection', url: 'https://dash.cloudflare.com/?to=/:account/turnstile', urlLabel: 'Dashboard' },
    ],
  },
];

const PLACEHOLDER_PATTERNS = ['ROTATE_ME', 'your_', 'REPLACE', 'change-me', 'placeholder', 'xxx', 'todo', 'fill_'];

function isPlaceholder(val) {
  if (!val) return false;
  const lower = val.toLowerCase();
  return PLACEHOLDER_PATTERNS.some(p => lower.includes(p.toLowerCase()));
}

function getStatus(val) {
  if (!val || val.trim() === '') return 'missing';
  if (isPlaceholder(val)) return 'placeholder';
  return 'set';
}

function getStatusLabel(status) {
  if (status === 'set') return 'Configured';
  if (status === 'placeholder') return 'Needs Key';
  return 'Missing';
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// Current key values from backend
let currentKeys = {};

async function loadKeys() {
  try {
    const res = await fetch('/admin/keys', {
      credentials: 'include',  // Include HttpOnly cookie
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 401 || res.status === 403) {
        throw new Error('Not authenticated. Please log in first.');
      }
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    currentKeys = data.data?.keys || data.keys || {};
  } catch (e) {
    currentKeys = {};
    showBanner('error', 'Could not load keys: ' + e.message);
  }
  render();
}

function render() {
  const groupsEl = document.getElementById('keyGroups');
  const statsEl = document.getElementById('stats');

  let totalKeys = 0;
  let setCount = 0;
  let placeholderCount = 0;
  let missingCount = 0;

  // Count stats
  KEY_DEFINITIONS.forEach(g => g.keys.forEach(k => {
    totalKeys++;
    const s = getStatus(currentKeys[k.env]);
    if (s === 'set') setCount++;
    else if (s === 'placeholder') placeholderCount++;
    else missingCount++;
  }));

  statsEl.innerHTML = `
    <div class="stat"><div class="num" style="color:var(--accent-green)">${setCount}</div><div class="label">Configured</div></div>
    <div class="stat"><div class="num" style="color:var(--accent-orange)">${placeholderCount}</div><div class="label">Needs Key</div></div>
    <div class="stat"><div class="num" style="color:var(--accent-red)">${missingCount}</div><div class="label">Missing</div></div>
    <div class="stat"><div class="num" style="color:var(--accent-cyan)">${totalKeys}</div><div class="label">Total</div></div>
  `;

  let html = '';
  KEY_DEFINITIONS.forEach(g => {
    html += `<div class="group"><div class="group-title">${escapeHtml(g.group)}</div>`;
    g.keys.forEach(k => {
      const val = currentKeys[k.env] || '';
      const status = getStatus(val);
      const statusLabel = getStatusLabel(status);
      // Mask the value for display (show first 8 chars + ...)
      const masked = val && !isPlaceholder(val) && val.length > 12
        ? val.slice(0, 8) + '...' + val.slice(-4)
        : '';

      html += `
        <div class="key-row" data-env="${escapeHtml(k.env)}">
          <div class="top">
            <div>
              <span class="name">${escapeHtml(k.env)}</span>
            </div>
            <span class="status ${status}">${statusLabel}</span>
          </div>
          <div class="desc">${escapeHtml(k.label)} &mdash; ${escapeHtml(k.desc)}</div>
          <div class="input-row">
            <input
              type="password"
              id="input-${k.env}"
              placeholder="${masked || 'Paste your key here...'}"
              data-env="${escapeHtml(k.env)}"
              autocomplete="off"
              spellcheck="false"
            >
            ${k.url ? `<a href="${escapeHtml(k.url)}" target="_blank" rel="noopener" class="link-btn">${escapeHtml(k.urlLabel || 'Get Key')} &#8599;</a>` : ''}
            ${k.generated ? `<button class="link-btn" onclick="generateKey('${k.env}')">Generate</button>` : ''}
          </div>
        </div>
      `;
    });
    html += '</div>';
  });

  groupsEl.innerHTML = html;

  // Toggle password visibility on focus
  groupsEl.querySelectorAll('input[type="password"]').forEach(inp => {
    inp.addEventListener('focus', () => { inp.type = 'text'; });
    inp.addEventListener('blur', () => {
      if (!inp.value) inp.type = 'password';
    });
  });
}

// Generate a random hex secret
window.generateKey = function(envName) {
  const bytes = new Uint8Array(envName.includes('SECRET_KEY') ? 64 : 32);
  crypto.getRandomValues(bytes);
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  const input = document.getElementById('input-' + envName);
  if (input) {
    input.value = hex;
    input.type = 'text';
  }
};

function showBanner(type, msg) {
  const el = document.getElementById('statusBanner');
  el.className = 'status-banner ' + type;
  el.textContent = msg;
  el.style.display = 'flex';
  setTimeout(() => { el.style.display = 'none'; }, 6000);
}

window.saveKeys = async function() {
  const btn = document.getElementById('saveBtn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  // Collect all non-empty inputs
  const updates = {};
  document.querySelectorAll('.key-row input').forEach(inp => {
    const val = inp.value.trim();
    if (val) {
      updates[inp.dataset.env] = val;
    }
  });

  if (Object.keys(updates).length === 0) {
    showBanner('error', 'No keys to save. Enter at least one key value.');
    btn.disabled = false;
    btn.textContent = 'Save All Keys';
    return;
  }

  try {
    const res = await fetch('/admin/keys', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',  // Include HttpOnly cookie
      body: JSON.stringify({ keys: updates }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 401 || res.status === 403) {
        throw new Error('Not authenticated. Please log in first.');
      }
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    const updated = data.data?.updated || data.updated || Object.keys(updates).length;
    showBanner('success', `Saved ${updated} keys. Restart backend for changes to take effect.`);
    // Refresh
    Object.assign(currentKeys, updates);
    render();
    // Clear inputs
    document.querySelectorAll('.key-row input').forEach(inp => { inp.value = ''; });
  } catch (e) {
    showBanner('error', 'Failed to save: ' + e.message);
  }

  btn.disabled = false;
  btn.textContent = 'Save All Keys';
};

// Init
loadKeys();
