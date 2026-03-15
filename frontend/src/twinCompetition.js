/**
 * Twins Competition — Auto-add tasks, allocate to twins, leaderboard.
 * Twins compete to build the most and get more done for the Bridge.
 */
import { fetchJson } from './api.js';
import { API_BASE } from './config.js';

export function initTwinCompetition() {
  const container = document.getElementById('side-panel') || document.body;
  const panel = document.createElement('div');
  panel.id = 'twin-competition-panel';
  panel.style.cssText = 'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #333;';
  panel.innerHTML = `
    <h4>🏆 Twins Competition</h4>
    <p style="font-size:11px;color:#888;margin-bottom:6px">Twins use auto DEX, follow buy/sell signals, compete to build the most</p>
    <button id="twin-auto-add" style="margin-bottom:4px">Auto-add Task</button>
    <label style="font-size:11px;display:block;margin-bottom:8px"><input type="checkbox" id="twin-auto-add-toggle"> Auto-add every 60s</label>
    <div id="twin-leaderboard" style="margin-bottom:8px;font-size:12px"></div>
    <div id="twin-allocate-section">
      <strong>Allocate to twin:</strong>
      <div id="twin-allocate-list" style="margin-top:4px;font-size:11px"></div>
    </div>
    <div id="twin-in-progress-section" style="margin-top:8px">
      <strong>In progress (Complete):</strong>
      <div id="twin-in-progress-list" style="margin-top:4px;font-size:11px"></div>
    </div>
    <div id="twin-teach-section" style="margin-top:8px;padding-top:8px;border-top:1px solid #333">
      <strong>📚 Twin teaches twin:</strong>
      <div id="twin-teach-controls" style="margin-top:4px;font-size:11px"></div>
    </div>
  `;
  container.appendChild(panel);

  const autoAddBtn = document.getElementById('twin-auto-add');
  const leaderboardEl = document.getElementById('twin-leaderboard');
  const allocateListEl = document.getElementById('twin-allocate-list');
  const inProgressListEl = document.getElementById('twin-in-progress-list');
  const teachControlsEl = document.getElementById('twin-teach-controls');

  async function updateLeaderboard() {
    try {
      const lb = await fetchJson(`${API_BASE}/api/twins/leaderboard`);
      leaderboardEl.innerHTML = (Array.isArray(lb) ? lb : []).map((t, i) =>
        `<div style="margin:2px 0">#${t.rank} <strong>${t.name}</strong> — ${t.completed} done, ${t.trades_executed || 0} DEX trades, ${(t.total_score || 0) + (t.dex_pnl || 0)} BRDG</div>`
      ).join('') || '<div style="color:#864">No twins yet</div>';
    } catch (e) {
      leaderboardEl.innerHTML = '<div style="color:#864">Leaderboard unavailable</div>';
    }
  }

  window.addEventListener('twins-leaderboard-update', () => setTimeout(updateLeaderboard, 0));

  async function updateAllocateList() {
    try {
      const [tasks, twins] = await Promise.all([
        fetchJson(`${API_BASE}/api/marketplace/tasks`),
        fetchJson(`${API_BASE}/api/twins`),
      ]);
      const taskList = Array.isArray(tasks) ? tasks : [];
      const twinList = Array.isArray(twins) ? twins : [];
      if (taskList.length === 0) {
        allocateListEl.innerHTML = '<div style="color:#864">No open tasks. Auto-add some!</div>';
        return;
      }
      allocateListEl.innerHTML = taskList.map(t =>
        `<div style="margin:4px 0;padding:4px;background:#222;border-radius:4px">
          <span>${t.desc} (${t.reward} BRDG)</span>
          <div style="margin-top:4px">
            ${twinList.map(tw => `<button class="twin-alloc-btn" data-task="${t.id}" data-twin="${tw.id}" style="margin-right:4px;font-size:10px">→ ${tw.name}</button>`).join('')}
          </div>
        </div>`
      ).join('');
      allocateListEl.querySelectorAll('.twin-alloc-btn').forEach(btn => {
        btn.onclick = async () => {
          const taskId = btn.getAttribute('data-task');
          const twinId = btn.getAttribute('data-twin');
          try {
            await fetch(`${API_BASE}/api/twins/allocate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ task_id: parseInt(taskId, 10), twin_id: twinId }),
            });
            updateAllocateList();
            updateLeaderboard();
            window.dispatchEvent(new CustomEvent('marketplace-update'));
          } catch (err) {
            console.error('Allocate failed', err);
          }
        };
      });
    } catch (e) {
      allocateListEl.innerHTML = '<div style="color:#864">Unable to load</div>';
    }
  }

  let autoAddInterval = null;
  document.getElementById('twin-auto-add-toggle')?.addEventListener('change', (e) => {
    if (autoAddInterval) clearInterval(autoAddInterval);
    if (e.target.checked) {
      autoAddInterval = setInterval(async () => {
        try {
          await fetch(`${API_BASE}/api/twins/auto-add`, { method: 'POST' });
          updateAllocateList();
          window.dispatchEvent(new CustomEvent('marketplace-update'));
        } catch (_) {}
      }, 60000);
    }
  });

  autoAddBtn.onclick = async () => {
    autoAddBtn.disabled = true;
    try {
      await fetch(`${API_BASE}/api/twins/auto-add`, { method: 'POST' });
      updateAllocateList();
      window.dispatchEvent(new CustomEvent('marketplace-update'));
    } catch (err) {
      console.error('Auto-add failed', err);
    }
    autoAddBtn.disabled = false;
  };

  async function updateInProgress() {
    try {
      const tasks = await fetchJson(`${API_BASE}/api/marketplace/tasks?status=in_progress`);
      const list = Array.isArray(tasks) ? tasks : [];
      inProgressListEl.innerHTML = list.length === 0
        ? '<div style="color:#864">None</div>'
        : list.map(t => {
            const twin = (t.acceptor || '').replace(/^twin:/, '') || '?';
            return `<div style="margin:4px 0;padding:4px;background:#223;border-radius:4px">
              <span>${t.desc} → ${twin}</span>
              <button class="twin-complete-btn" data-id="${t.id}" style="margin-left:6px;font-size:10px">Complete</button>
            </div>`;
          }).join('');
      inProgressListEl.querySelectorAll('.twin-complete-btn').forEach(btn => {
        btn.onclick = async () => {
          try {
            await fetch(`${API_BASE}/api/marketplace/complete`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ task_id: parseInt(btn.getAttribute('data-id'), 10) }),
            });
            updateInProgress();
            updateLeaderboard();
            updateAllocateList();
            window.dispatchEvent(new CustomEvent('marketplace-update'));
          } catch (err) {
            console.error('Complete failed', err);
          }
        };
      });
    } catch (e) {
      inProgressListEl.innerHTML = '<div style="color:#864">Unable to load</div>';
    }
  }

  async function updateTeachControls() {
    try {
      const twins = await fetchJson(`${API_BASE}/api/twins`);
      const list = Array.isArray(twins) ? twins : [];
      const teachers = list.filter(t => (t.skills_learned || []).some(s => s.verified));
      if (teachers.length === 0) {
        teachControlsEl.innerHTML = '<div style="color:#864">No twins with verified skills yet. Complete tasks first.</div>';
        return;
      }
      teachControlsEl.innerHTML = `
        <select id="twin-teach-teacher" style="margin-right:4px;font-size:10px">
          <option value="">Teacher</option>
          ${teachers.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
        </select>
        <select id="twin-teach-student" style="margin-right:4px;font-size:10px">
          <option value="">Student</option>
          ${list.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
        </select>
        <select id="twin-teach-skill" style="margin-right:4px;font-size:10px;min-width:140px">
          <option value="">Skill</option>
        </select>
        <button id="twin-teach-btn" style="font-size:10px">Teach</button>
      `;
      const teacherSel = document.getElementById('twin-teach-teacher');
      const studentSel = document.getElementById('twin-teach-student');
      const skillSel = document.getElementById('twin-teach-skill');
      teacherSel.addEventListener('change', () => {
        const t = list.find(tw => tw.id === teacherSel.value);
        const verified = (t?.skills_learned || []).filter(s => s.verified);
        skillSel.innerHTML = '<option value="">Skill</option>' + verified.map(s => `<option value="${s.name}">${s.name}</option>`).join('');
      });
      document.getElementById('twin-teach-btn').onclick = async () => {
        const teacherId = teacherSel.value;
        const studentId = studentSel.value;
        const skillName = skillSel.value;
        if (!teacherId || !studentId || !skillName || teacherId === studentId) {
          alert('Pick different teacher and student, and a skill.');
          return;
        }
        try {
          const res = await fetch(`${API_BASE}/api/twins/teach`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ teacher_id: teacherId, student_id: studentId, skill_name: skillName }),
          });
          const data = await res.json();
          if (res.ok) {
            updateLeaderboard();
            updateTeachControls();
            window.dispatchEvent(new CustomEvent('twins-leaderboard-update'));
          } else {
            alert(data.detail || 'Teach failed');
          }
        } catch (err) {
          console.error('Teach failed', err);
          alert('Teach failed');
        }
      };
    } catch (e) {
      teachControlsEl.innerHTML = '<div style="color:#864">Unable to load</div>';
    }
  }

  updateLeaderboard();
  updateAllocateList();
  updateInProgress();
  updateTeachControls();
  setInterval(() => setTimeout(updateLeaderboard, 0), 8000);
  setInterval(() => setTimeout(updateAllocateList, 0), 10000);
  setInterval(() => setTimeout(updateInProgress, 0), 8000);
  setInterval(() => setTimeout(updateTeachControls, 0), 12000);
}
