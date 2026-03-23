import { initRenderer } from './babylonRenderer.js';
import { runSystemCheck } from './systemVerifier.js';
import { initLipSync } from './lipsync.js';
import { initVoice } from './voice.js';
import { initSpeechEmbodiment } from './speechEmbodiment.js';
import { initTerminal } from './terminal.js';
import { initMissionBoard } from './missionBoard.js';
import { initFounderTodo } from './founderTodo.js';
import { initSkillsPanel } from './skillsPanel.js';
import { initARVR } from './arvr.js';
import { initGeolocation } from './geolocation.js';
import { initEsim } from './esim.js';
import { initWallet } from './wallet.js';
import { initMarketplace } from './marketplace.js';
import { initUbi } from './ubi.js';
import { initSdg } from './sdg.js';
import { initRevenue } from './revenue.js';
import { initBossBots } from './bossbots.js';
import { initTwinSharedXml } from './twinSharedXml.js';
import { initCognitiveTwin } from './cognitiveTwin.js';
import { initTwinPanel } from './twinPanel.js';
import { initTwinCompetition } from './twinCompetition.js';
import { initSystemComprehension } from './systemComprehension.js';
import { initTabs } from './tabs.js';
import { initControlPanel } from './controlPanel.js';

const loadingEl = document.getElementById('loading');
const canvas = document.getElementById('renderCanvas');

if (!canvas) {
    if (loadingEl) loadingEl.innerHTML = 'Missing canvas element.';
    throw new Error('renderCanvas not found');
}
if (typeof BABYLON === 'undefined') {
    if (loadingEl) loadingEl.innerHTML = 'Babylon.js failed to load. Check network.';
    throw new Error('BABYLON not loaded');
}

const engine = new BABYLON.Engine(canvas, true, {
    preserveDrawingBuffer: true,
    stencil: true,
    disableWebGL2Support: false,
    powerPreference: 'high-performance'
});

let scene;
let lastFps = 60;

(async () => {
    let faceState = 'OFFLINE';
    try {
        const check = await runSystemCheck();
        if (check.overall) faceState = 'ALIVE';
        else if (check.apiStatus && !check.wsStatus) faceState = 'DEGRADED';
        else faceState = 'OFFLINE';
    } catch (e) {
        console.error('System check failed:', e);
        faceState = 'OFFLINE';
    }

    try {
        scene = await initRenderer(engine, canvas, { faceState });
        if (loadingEl) loadingEl.style.display = 'none';
    } catch (e) {
        console.error('initRenderer failed:', e);
        if (loadingEl) {
            loadingEl.innerHTML = 'Failed to load 3D. Check console.';
            loadingEl.style.color = '#f88';
        }
        throw e;
    }

    try { initLipSync(scene); } catch (e) { console.warn('initLipSync:', e); }
    try { initVoice(); } catch (e) { console.warn('initVoice:', e); }
    try { initSpeechEmbodiment(scene); } catch (e) { console.warn('initSpeechEmbodiment:', e); }
    try { initTabs(); } catch (e) { console.warn('initTabs:', e); }
    try { initControlPanel(); } catch (e) { console.warn('initControlPanel:', e); }
    try { initTerminal(); } catch (e) { console.warn('initTerminal:', e); }
    try { initMissionBoard(); } catch (e) { console.warn('initMissionBoard:', e); }
    try { initFounderTodo(); } catch (e) { console.warn('initFounderTodo:', e); }
    try { initSkillsPanel(); } catch (e) { console.warn('initSkillsPanel:', e); }
    try { initARVR(); window.__babylonScene = scene; } catch (e) { console.warn('initARVR:', e); }
    try { initGeolocation(); } catch (e) { console.warn('initGeolocation:', e); }
    try { initEsim(); } catch (e) { console.warn('initEsim:', e); }
    try { initWallet(); } catch (e) { console.warn('initWallet:', e); }
    try { initMarketplace(); } catch (e) { console.warn('initMarketplace:', e); }
    try { initUbi(); } catch (e) { console.warn('initUbi:', e); }
    try { initSdg(); } catch (e) { console.warn('initSdg:', e); }
    try { initRevenue(); } catch (e) { console.warn('initRevenue:', e); }
    try { initBossBots(); } catch (e) { console.warn('initBossBots:', e); }
    try { initTwinSharedXml(); } catch (e) { console.warn('initTwinSharedXml:', e); }
    try { initCognitiveTwin(); } catch (e) { console.warn('initCognitiveTwin:', e); }
    try { initTwinPanel(); } catch (e) { console.warn('initTwinPanel:', e); }
    try { initTwinCompetition(); } catch (e) { console.warn('initTwinCompetition:', e); }
    try { initSystemComprehension(); } catch (e) { console.warn('initSystemComprehension:', e); }

    let _renderSkip = 0;
    engine.runRenderLoop(() => {
        _renderSkip++;
        if (_renderSkip % 2 !== 0) return;  // Cap at ~30fps to reduce rAF violations
        const fps = engine.getFps();
        if (fps < 30 && lastFps >= 30) engine.setHardwareScalingLevel(2.0);
        else if (fps > 50 && lastFps <= 50) engine.setHardwareScalingLevel(1.0);
        lastFps = fps;
        if (scene) scene.render();
    });

    window.addEventListener('resize', () => engine.resize());
    window.addEventListener('bridge:tab', (e) => {
        // When switching to the 3D tab, force a resize so the canvas fits.
        try {
            const tab = e?.detail?.tab;
            if (tab === 'twin') setTimeout(() => engine.resize(), 0);
        } catch (_) {}
    });
})();
