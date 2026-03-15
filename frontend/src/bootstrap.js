import { Renderer } from './renderer.js';
import { EmotionEngine } from './emotionEngine.js';
import { Voice } from './voice.js';
import { LipSync } from './lipsync.js';
import { Terminal } from './terminal.js';
import { MissionBoard } from './missionBoard.js';
import { SkillsPanel } from './skillsPanel.js';

const WS_URL = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/global';
const ws = new WebSocket(WS_URL);
ws.addEventListener('open', ()=> ws.send(JSON.stringify({type:'hello', client_id:crypto.randomUUID()})));

const renderer = new Renderer(document.getElementById('app'));
const emotion = new EmotionEngine(ws);
const voice = new Voice(ws, emotion);
const lipsync = new LipSync(renderer, ws, emotion);
const terminal = new Terminal(document.getElementById('terminal'), ws, emotion);
const mission = new MissionBoard(document.getElementById('mission'), ws);
const skills = new SkillsPanel(document.getElementById('skills'), ws, mission, emotion);

// light startup voice demonstration (transparent about being AI)
terminal.write({role:'system',text:'Bridge AI OS initialized — identity: AI system (transparent)'});

export { renderer, emotion, voice, lipsync, terminal, mission, skills };
