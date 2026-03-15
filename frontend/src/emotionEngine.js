export class EmotionEngine {
  constructor(ws){
    this.ws = ws;
    this.state = {state:'neutral',score:0,inputs:{}};
    this.W = { governance:0.28, mission_progress:0.24, conversation_sentiment:0.22, system_health:0.18, task_pressure:0.08 };
    ws.addEventListener('message', e=>{
      try{ const m = JSON.parse(e.data); if(m.type==='state_update'){ this.state = m.payload; } }catch(e){}
    });
  }

  localCompute(inputs){
    let s=0;
    s += this.W.governance * (inputs.governance_score||0);
    s += this.W.mission_progress * ((inputs.mission_progress||0)*2 -1);
    s += this.W.conversation_sentiment * (inputs.conversation_sentiment||0);
    s += this.W.system_health * ((inputs.system_health||0)*2 -1);
    s += this.W.task_pressure * (1 - 2*(inputs.task_pressure||0));
    const STATES = ['neutral','focused','concerned','confident','alert','reflective'];
    let idx = Math.max(0, Math.min(STATES.length-1, Math.floor(((s+1)/2)*(STATES.length-1))));
    return {state:STATES[idx], score:s, inputs};
  }

  async requestCompute(inputs){
    this.state = this.localCompute(inputs);
    try{
      this.ws.send(JSON.stringify({type:'compute_emotion', inputs}));
    }catch(e){}
    return this.state;
  }
}
