import { fetchJson } from './api.js';
import { API_BASE } from './config.js';
import { getParsedSharedXml, onSharedXmlUpdate } from './twinSharedXml.js';

export function initMissionBoard(){
    const board = document.getElementById('missionBoard');
    board.innerHTML = '<div style="font-weight:bold">Mission Board</div><div>Loading...</div>';
    function render(data) {
        const b = data.backlog ?? 0, i = data.in_progress ?? 0, r = data.review ?? 0, d = data.done ?? 0;
        board.innerHTML = `Backlog: ${b}<br>In Progress: ${i}<br>Review: ${r}<br>Done: ${d}`;
    }
    function updateBoard(){
        setTimeout(() => {
            fetchJson(`${API_BASE}/api/mission/board`)
                .then(data => render(data))
                .catch(() => {
                    const shared = getParsedSharedXml();
                    if (shared?.mission) render(shared.mission);
                    else board.innerHTML = 'Board unavailable';
                });
        }, 0);
    }
    onSharedXmlUpdate((_xml, parsed) => {
        if (parsed?.mission) render(parsed.mission);
    });
    updateBoard();
    setInterval(() => setTimeout(updateBoard, 0), 10000);
}
export class MissionBoard {
  constructor(el, ws){
    this.el = el; this.ws = ws; this.counts = {backlog:0,in_progress:0,review:0,done:0};
    this._render();
    this._poll();
  }

  async _poll(){
    try{
      const res = await fetch(`${API_BASE}/api/mission/board`);
      if(res.ok){ this.counts = await res.json(); this._render(); }
    }catch(e){ console.warn('mission poll failed', e); }
    setTimeout(()=>this._poll(),5000);
  }

  _render(){
    this.el.innerHTML = `<div style='font-weight:bold'>Mission Board</div>` +
      `<div>Backlog: ${this.counts.backlog}</div><div>In Progress: ${this.counts.in_progress}</div><div>Review: ${this.counts.review}</div><div>Done: ${this.counts.done}</div>`;
  }
}
