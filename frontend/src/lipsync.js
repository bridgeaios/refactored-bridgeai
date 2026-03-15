/**
 * Lip-sync: Audio-driven jaw/mouth from TTS and speechSynthesis.
 * - TTS blob: Web Audio API + AnalyserNode → RMS → jawOpen
 * - speechSynthesis: Timer-based mouth animation when speaking
 */
let _audioCtx = null;
let _analyser = null;
let _rafId = null;
let _sceneRef = null;

function ensureAudioContext() {
  if (_audioCtx) return _audioCtx;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  _audioCtx = new Ctx();
  _analyser = _audioCtx.createAnalyser();
  _analyser.fftSize = 256;
  _analyser.smoothingTimeConstant = 0.7;
  _analyser.connect(_audioCtx.destination);
  return _audioCtx;
}

function getRMS() {
  if (!_analyser) return 0;
  const data = new Uint8Array(_analyser.frequencyBinCount);
  _analyser.getByteTimeDomainData(data);
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    const v = (data[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / data.length);
}

function driveLipSyncLoop(minJaw = 0.04, maxJaw = 0.5) {
  if (!_sceneRef?._faceState) return;
  const rms = getRMS();
  const smoothed = Math.min(1, rms * 4);
  const jawOpen = minJaw + smoothed * (maxJaw - minJaw);
  _sceneRef._faceState.jawOpen = jawOpen;
  _sceneRef._faceState.smile = 0.15 + smoothed * 0.2;
  _rafId = requestAnimationFrame(() => driveLipSyncLoop(minJaw, maxJaw));
}

function stopLipSyncLoop() {
  if (_rafId != null) {
    cancelAnimationFrame(_rafId);
    _rafId = null;
  }
  if (_sceneRef?._faceState) {
    _sceneRef._faceState.jawOpen = undefined;
    _sceneRef._faceState.smile = undefined;
  }
}

/**
 * Play audio blob through Web Audio API and drive lip-sync from RMS.
 * Returns a Promise that resolves when playback ends.
 */
export async function playBlobWithLipSync(blob, scene) {
  if (!scene?._faceState) return Promise.reject(new Error('No face state'));
  const ctx = ensureAudioContext();
  if (!ctx) return Promise.reject(new Error('No AudioContext'));

  try {
    const arrayBuf = await blob.arrayBuffer();
    const audioBuf = await ctx.decodeAudioData(arrayBuf);
    const src = ctx.createBufferSource();
    src.buffer = audioBuf;
    src.connect(_analyser);
    if (ctx.state === 'suspended') await ctx.resume();

    _sceneRef = scene;
    driveLipSyncLoop(0.06, 0.55);

    return new Promise((resolve) => {
      src.onended = () => {
        stopLipSyncLoop();
        resolve();
      };
      src.start(0);
    });
  } catch (e) {
    stopLipSyncLoop();
    throw e;
  }
}

/**
 * Simulated lip-sync for speechSynthesis (no audio capture).
 * Syllable-like mouth open/close based on elapsed time.
 */
function driveSpeechSynthesisLipSync() {
  if (!_sceneRef?._faceState || !window.speechSynthesis?.speaking) {
    stopLipSyncLoop();
    return;
  }
  const t = performance.now() * 0.004;
  const cycle = Math.sin(t) * 0.5 + 0.5;
  _sceneRef._faceState.jawOpen = 0.06 + cycle * 0.35;
  _sceneRef._faceState.smile = 0.2;
  _rafId = requestAnimationFrame(driveSpeechSynthesisLipSync);
}

function onSpeechStart(scene) {
  _sceneRef = scene;
  driveSpeechSynthesisLipSync();
}

function onSpeechEnd() {
  stopLipSyncLoop();
}

export function initLipSync(scene) {
  if (!scene?._faceState) return;

  window.__playWithLipSync = (blob) => playBlobWithLipSync(blob, scene);
  window.__lipSyncScene = scene;

  if (typeof speechSynthesis !== 'undefined') {
    const origSpeak = speechSynthesis.speak.bind(speechSynthesis);
    speechSynthesis.speak = function (utterance) {
      utterance.addEventListener('start', () => onSpeechStart(scene), { once: true });
      utterance.addEventListener('end', onSpeechEnd, { once: true });
      utterance.addEventListener('error', onSpeechEnd, { once: true });
      origSpeak(utterance);
    };
  }
}
