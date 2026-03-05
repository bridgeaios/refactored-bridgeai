function $(sel){return document.querySelector(sel)}
function now(){return new Date().toISOString().slice(11,19)}

function log(line, cls){
  const box = $('#log');
  if(!box) return;
  const p = document.createElement('p');
  if(cls) p.className = cls;
  p.textContent = `[${now()}] ${line}`;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function uuidv4(){
  if (crypto && crypto.randomUUID) return crypto.randomUUID();
  const a = crypto.getRandomValues(new Uint8Array(16));
  a[6] = (a[6] & 0x0f) | 0x40;
  a[8] = (a[8] & 0x3f) | 0x80;
  const h = [...a].map(b => b.toString(16).padStart(2,'0')).join('');
  return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}

async function loadConfig(relPath){
  const p = relPath || '../config.json';
  try{
    const r = await fetch(p, { cache: 'no-store' });
    if(!r.ok) throw new Error(`config HTTP ${r.status}`);
    const c = await r.json();
    return {
      gateway_url: (c.gateway_url || '').replace(/\/$/, ''),
      backend_url: (c.backend_url || '').replace(/\/$/, ''),
      api_key: c.api_key || '',
      price_per_tps: typeof c.price_per_tps === 'number' ? c.price_per_tps : 0.20,
      qr_target: c.qr_target || ''
    };
  }catch(e){
    log(`Config load failed: ${e.message}`, 'err');
    return null;
  }
}

async function postJSON(url, body, headers){
  const r = await fetch(url, {
    method: 'POST',
    headers: Object.assign({ 'Content-Type': 'application/json' }, headers || {}),
    body: JSON.stringify(body || {})
  });
  const text = await r.text();
  let data = null;
  try{ data = JSON.parse(text); }catch(_){}
  if(!r.ok){
    const msg = data && (data.detail || data.error) ? (data.detail || data.error) : text;
    throw new Error(`HTTP ${r.status}: ${msg}`);
  }
  return data ?? text;
}

async function getJSON(url, headers){
  const r = await fetch(url, { headers: headers || {} });
  const text = await r.text();
  let data = null;
  try{ data = JSON.parse(text); }catch(_){}
  if(!r.ok){
    const msg = data && (data.detail || data.error) ? (data.detail || data.error) : text;
    throw new Error(`HTTP ${r.status}: ${msg}`);
  }
  return data ?? text;
}

async function runDistribution(cfg, payload){
  const url = `${cfg.backend_url}/api/distribution/run`;
  const headers = { 'X-User-ID': payload.user_id || 'user-1' };
  const data = await postJSON(url, payload, headers);
  return data;
}

async function bumpUsage(cfg, endpoint, calls, tokens){
  const url = `${cfg.backend_url}/api/usage/bump`;
  return await postJSON(url, { endpoint, calls, tokens });
}

async function fetchBilling(cfg){
  const url = `${cfg.gateway_url}/billing`;
  return await getJSON(url, { 'x-api-key': cfg.api_key });
}

async function fetchTreasury(cfg){
  const url = `${cfg.backend_url}/api/treasury/summary`;
  return await getJSON(url);
}
