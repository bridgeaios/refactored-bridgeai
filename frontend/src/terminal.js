import { API_BASE, WS_BASE } from './config.js';

function map_emotion_to_color(emotion){
    const colors = {"neutral":"#FFFFFF","focused":"#00FF00","confident":"#FFFF00","alert":"#FF0000","reflective":"#0000FF","concerned":"#FF00FF"};
    return colors[emotion] ?? '#FFFFFF';
}

function topicBadgeStyle(topic) {
    const palette = {
        Commands: 'background:#2a6;color:#fff;',
        Questions: 'background:#36a;color:#fff;',
        Philosophy: 'background:#6a4;color:#fff;',
        Emotional: 'background:#a62;color:#fff;',
        Greeting: 'background:#48a;color:#fff;',
        Identity: 'background:#84a;color:#fff;',
        Help: 'background:#4a8;color:#fff;',
        General: 'background:#555;color:#ccc;',
    };
    return palette[topic] || 'background:#444;color:#aaa;';
}

function appendTopicBadge(parent, topic) {
    if (!topic || typeof topic !== 'string') return;
    const span = document.createElement('span');
    span.className = 'chat-topic';
    span.textContent = topic;
    span.style.cssText = `display:inline-block;margin-left:6px;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:600;${topicBadgeStyle(topic)}`;
    parent.appendChild(span);
}

export function initTerminal(){
    const terminal = document.getElementById('terminal');
    const ws = new WebSocket(`${WS_BASE}/ws/mission`);
    let lastUserMsgEl = null;

    async function apiGet(path) {
        try {
            const r = await fetch(`${API_BASE}${path}`);
            if (!r.ok) return { ok: false, status: r.status, data: null };
            return { ok: true, status: r.status, data: await r.json() };
        } catch (e) {
            return { ok: false, status: 0, data: { error: String(e) } };
        }
    }

    async function apiPost(path, body) {
        try {
            const r = await fetch(`${API_BASE}${path}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body || {}),
            });
            const data = await r.json().catch(() => null);
            return { ok: r.ok, status: r.status, data };
        } catch (e) {
            return { ok: false, status: 0, data: { error: String(e) } };
        }
    }

    function appendLine(text, { color = '#9effb8', topic = null } = {}) {
        const p = document.createElement('p');
        p.style.color = color;
        p.textContent = text;
        if (topic) appendTopicBadge(p, topic);
        terminal.insertBefore(p, terminal.querySelector('input'));
        terminal.scrollTop = terminal.scrollHeight;
        return p;
    }

    ws.onopen = () => console.log('WebSocket connected');
    ws.onmessage = (event) => {
        let data;
        try { data = JSON.parse(event.data); } catch { return; }
        if (data.type === 'heartbeat') return;
        const emotion = data.emotion_state || data.state || 'neutral';
        const topic = data.topic || data.reasoning?.topic;
        const text = data.response || data.message || (data.type === 'response' ? '' : JSON.stringify(data));
        // Defer heavy work so message handler returns quickly (avoids 'message' handler violation)
        const doWork = () => {
            if (text) {
                if (lastUserMsgEl && topic) {
                    appendTopicBadge(lastUserMsgEl, topic);
                    lastUserMsgEl = null;
                }
                const p = document.createElement('p');
                p.style.color = map_emotion_to_color(emotion);
                p.textContent = text;
                if (topic) appendTopicBadge(p, topic);
                terminal.insertBefore(p, terminal.querySelector('input'));
                terminal.scrollTop = terminal.scrollHeight;
                if (data.response) {
                    const speakFn = window.speakWithEmbodiment || window.speak;
                    if (speakFn) setTimeout(() => speakFn(data.response, emotion), 0);
                }
            }
            if (window.setExpression) {
                const face = { neutral: { smile: 0.2, frown: 0 }, focused: { smile: 0.15, frown: 0.05 }, confident: { smile: 0.6, frown: 0 }, alert: { smile: 0.3, frown: 0.1 }, reflective: { smile: 0.1, frown: 0.08 }, concerned: { smile: 0, frown: 0.35 } };
                window.setExpression(face[emotion] || face.neutral);
            }
        };
        if (typeof requestIdleCallback === 'function') {
            requestIdleCallback(() => requestAnimationFrame(doWork), { timeout: 100 });
        } else {
            requestAnimationFrame(doWork);
        }
    };
    ws.onerror = () => {
        if (!window._wsErrorLogged) {
            window._wsErrorLogged = true;
            console.warn(`Terminal: Backend WebSocket offline (${WS_BASE})`);
        }
    };
    ws.onclose = () => setTimeout(() => initTerminal(), 15000);

    terminal.innerHTML = '<p style="color:#8cf;">Bridge AI OS — I am the Bridge. I am the Authority. Twins share one XML.</p>';

    // Action bar: makes "missions / board / skills / UBI / CLI" explicit (no guessing).
    const actionBar = document.createElement('div');
    actionBar.style.cssText = 'margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;';

    const voiceBtn = document.createElement('button');
    voiceBtn.textContent = '🔊 Speak';
    voiceBtn.style.cssText = 'margin-left:8px;padding:6px 12px;background:#2a6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;';
    voiceBtn.onclick = () => {
        if (window.speak) window.speak('I am the Bridge. I am the Founder. I am the System. I am the Authority. The backend is human. How can I help you today?');
        else console.warn('Voice not ready');
    };
    actionBar.appendChild(voiceBtn);

    function mkBtn(label, onClick, css) {
        const b = document.createElement('button');
        b.textContent = label;
        b.type = 'button';
        b.style.cssText = css || 'padding:6px 10px;background:#111827;color:#e2e8f0;border:1px solid #334155;border-radius:8px;cursor:pointer;font-size:12px;';
        b.onclick = onClick;
        return b;
    }

    const btnMissions = mkBtn('Missions', () => {
        try {
            window.dispatchEvent(new CustomEvent('bridge:tab', { detail: { tab: 'missions' } }));
        } catch (_) {}
        appendLine('Opened Missions tab.', { color: '#8cf', topic: 'Commands' });
    });
    const btnBoard = mkBtn('Fetch board', async () => {
        appendLine('Fetching mission board…', { color: '#cfe', topic: 'Commands' });
        const r = await apiGet('/api/mission/board');
        if (!r.ok) return appendLine(`Mission board unavailable (${r.status})`, { color: '#f88', topic: 'System' });
        appendLine(`Mission board: backlog=${r.data.backlog} in_progress=${r.data.in_progress} review=${r.data.review} done=${r.data.done}`, { color: '#9effb8', topic: 'General' });
    });
    const btnSkills = mkBtn('List skills', async () => {
        appendLine('Fetching skills…', { color: '#cfe', topic: 'Commands' });
        const r = await apiGet('/api/skills');
        if (!r.ok) return appendLine(`Skills unavailable (${r.status})`, { color: '#f88', topic: 'System' });
        const count = r.data.count ?? (Array.isArray(r.data.skills) ? r.data.skills.length : 0);
        appendLine(`Skills: ${count}`, { color: '#9effb8', topic: 'General' });
    });
    const btnClaim = mkBtn('Claim UBI', async () => {
        const address = prompt('Enter wallet address for UBI claim');
        if (!address) return;
        appendLine(`Claiming UBI for ${address}…`, { color: '#cfe', topic: 'Commands' });
        const r = await apiPost('/api/ubi/claim', { address });
        if (!r.ok) return appendLine(`UBI claim failed (${r.status}): ${(r.data && (r.data.detail || r.data.error)) || 'unknown'}`, { color: '#f88', topic: 'System' });
        const amt = (r.data && (r.data.amount || r.data.amt || r.data.payout || r.data.paid)) ?? r.data;
        appendLine(`UBI claim result: ${JSON.stringify(amt)}`, { color: '#9effb8', topic: 'General' });
    }, 'padding:6px 10px;background:#1f2937;color:#e2e8f0;border:1px solid #14b8a6;border-radius:8px;cursor:pointer;font-size:12px;');

    const btnRunAudit = mkBtn('Run audit', async () => {
        const s = await apiGet('/api/cli/status');
        if (!s.ok || !s.data?.enabled) return appendLine('CLI runner is locked. Open Status → Smart Debug to enable.', { color: '#fb923c', topic: 'System' });
        const r = await apiPost('/api/cli/enqueue', { cmd_id: 'audit:wall', args: [] });
        if (!r.ok) return appendLine(`Queue failed (${r.status})`, { color: '#f88', topic: 'System' });
        appendLine(`Queued audit job: ${r.data?.job?.id || 'ok'}`, { color: '#8cf', topic: 'Commands' });
    });

    actionBar.appendChild(btnMissions);
    actionBar.appendChild(btnBoard);
    actionBar.appendChild(btnSkills);
    actionBar.appendChild(btnClaim);
    actionBar.appendChild(btnRunAudit);
    terminal.appendChild(actionBar);

    const input = document.createElement('input');
    input.id = 'terminal-prompt';
    input.name = 'terminal-prompt';
    input.type = 'text';
    input.placeholder = 'Enter prompt...';
    input.style.cssText = 'width:90%;padding:8px;margin-top:8px;background:#111;color:#cf8;border:1px solid #333;';
    terminal.appendChild(input);

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter'){
            const prompt = input.value.trim();
            if (!prompt) return;
            const p = document.createElement('p');
            p.style.color = '#cfe';
            p.textContent = `You: ${prompt}`;
            terminal.insertBefore(p, input);
            lastUserMsgEl = p;
            ws.send(JSON.stringify({ prompt }));
            input.value = '';
            terminal.scrollTop = terminal.scrollHeight;
        }
    });
}
export class Terminal {
  constructor(el, ws, emotion){
    this.el = el; this.ws = ws; this.emotion = emotion; this.buffer = [];
    ws.addEventListener('open', ()=>{});
    ws.addEventListener('message', e=>{ try{ const m = JSON.parse(e.data); if(m.type==='terminal_stream'){ this.write(m.payload); } }catch(e){} });
  }

  write(obj){
    const line = document.createElement('div');
    const color = obj.emotion_color || (obj.role==='system' ? '#9be' : (obj.role==='ai' ? '#8ef' : '#cfe'));
    line.style.color = color;
    line.textContent = (obj.role?('['+obj.role+'] '):'') + obj.text;
    this.el.appendChild(line);
    this.el.scrollTop = this.el.scrollHeight;
  }

  send(prompt){
    const id = crypto.randomUUID();
    this.write({role:'user', text:prompt});
    try{ this.ws.send(JSON.stringify({type:'prompt', id, prompt})); }
    catch(e){ this.write({role:'system', text:'Failed to send — offline', emotion_color:'#f88'}); }
  }
}
