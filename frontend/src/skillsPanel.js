import { API_BASE } from './config.js';

export function initSkillsPanel(){
    const panel = document.getElementById('skillsPanel');
    panel.innerHTML = `
        <input id="skillInput" type="text" placeholder="Add skill...">
        <button id="addSkill">Add</button>
        <ul id="skillsList"></ul>
    `;
    const addButton = document.getElementById('addSkill');
    const input = document.getElementById('skillInput');
    const list = document.getElementById('skillsList');
    let skills = [];
    addButton.addEventListener('click', () => {
        const skill = input.value.trim();
        if (!skill) return;
        skills.push(skill);
        updateList();
        input.value = '';
        setTimeout(async () => {
            try { await fetch(`${API_BASE}/api/skills`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name: skill, tags: [], description: '' }) }); }
            catch (e) { console.warn('skill post failed', e); }
        }, 0);
    });
    function updateList(){
        list.innerHTML = skills.map(s => `<li>${s} <button class="edit">Edit</button></li>`).join('');
    }
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
