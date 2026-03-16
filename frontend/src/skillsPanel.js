import { API_BASE } from './config.js';

export function initSkillsPanel(){
    const panel = document.getElementById('skillsPanel');
    panel.innerHTML = `
        <h4 style="margin:0 0 6px 0;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#f59e0b;">Skills</h4>
        <div style="display:flex;gap:4px;margin-bottom:6px">
          <input id="skillInput" type="text" placeholder="Add skill..." style="flex:1;min-width:0">
          <button id="addSkill">+</button>
        </div>
        <ul id="skillsList" style="margin:0;padding-left:14px;max-height:120px;overflow-y:auto"></ul>
    `;
    const addButton = document.getElementById('addSkill');
    const input = document.getElementById('skillInput');
    const list = document.getElementById('skillsList');
    let skills = [];

    async function loadSkills() {
        try {
            const res = await fetch(`${API_BASE}/api/skills`);
            if (res.ok) {
                const data = await res.json();
                skills = (data.skills || []).map(s => s.name || String(s));
                updateList();
            }
        } catch (e) { console.warn('skills load failed', e); }
    }

    addButton.addEventListener('click', async () => {
        const skill = input.value.trim();
        if (!skill) return;
        skills.push(skill);
        updateList();
        input.value = '';
        try {
            await fetch(`${API_BASE}/api/skills`, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ name: skill, tags: [], description: '' })
            });
        } catch (e) { console.warn('skill post failed', e); }
    });

    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') addButton.click(); });

    function updateList(){
        list.innerHTML = skills.map(s => `<li style="margin-bottom:2px">${s}</li>`).join('');
    }

    loadSkills();
}
export class SkillsPanel {
  constructor(el, ws, mission, emotion){
    this.el = el; this.ws = ws; this.mission = mission; this.emotion = emotion;
    this._render();
  }

  _render(){
    this.el.innerHTML = `<div style='font-weight:bold'>Skills</div><div><input id='skill_name' placeholder='skill name' style='width:200px'/> <select id='skill_tag'><option>technical</option><option>governance</option><option>creative</option><option>strategic</option></select> <button id='add_skill'>Add</button></div><div id='skill_list'></div>`;
    this.el.querySelector('#add_skill').addEventListener('click', ()=> this.addSkill());
  }

  async addSkill(){
    const name = this.el.querySelector('#skill_name').value.trim();
    const tag = this.el.querySelector('#skill_tag').value;
    if(!name) return;
    const payload = {name, tags:[tag], description: ""};
    try{
      const res = await fetch('/api/skills',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});
      if(res.ok){ this._appendLocal(payload); this._increaseConfidence(); }
    }catch(e){ console.warn('save skill failed', e); }
  }

  _appendLocal(skill){
    const list = this.el.querySelector('#skill_list');
    const d = document.createElement('div'); d.textContent = `${skill.name} [${skill.tags.join(',')}]`; list.appendChild(d);
  }

  _increaseConfidence(){
    const cur = this.emotion.state.inputs || {};
    const newInputs = { ...cur, mission_progress: (cur.mission_progress||0) };
    // small confidence bump via local compute
    this.emotion.requestCompute(newInputs);
  }
}
