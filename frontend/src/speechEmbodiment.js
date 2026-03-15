/**
 * Twin_Speech_Communication_Embodiment — Frontend Skill Client
 * Phoneme → Viseme → Facial Rig. Lip sync from time-aligned phonemes.
 * Embodied communicator. Not a talking mannequin.
 */
import { API_BASE } from './config.js';

// Viseme → expression (jawOpen, smile, frown) — matches backend viseme_to_expression
const VISEME_EXPRESSION = {
  AA: { jawOpen: 0.45, smile: 0.1, frown: 0 },
  EE: { jawOpen: 0.08, smile: 0.7, frown: 0 },
  OH: { jawOpen: 0.35, smile: 0.05, frown: 0 },
  FV: { jawOpen: 0.12, smile: 0.25, frown: 0.08 },
  BMP: { jawOpen: 0.02, smile: 0.1, frown: 0 },
  TH: { jawOpen: 0.18, smile: 0.15, frown: 0.05 },
  Rest: { jawOpen: 0.04, smile: 0.2, frown: 0 },
};

let _sceneRef = null;
let _rafId = null;
let _phonemeStart = 0;
let _phonemes = [];
let _visemeMap = null;
let _emotionExpr = null;
let _audioCtx = null;
let _onEnd = null;

function getCurrentViseme() {
  if (!_phonemes.length) return "Rest";
  const elapsed = (performance.now() - _phonemeStart);
  for (let i = 0; i < _phonemes.length; i++) {
    const p = _phonemes[i];
    if (elapsed >= p.start_ms && elapsed < p.end_ms) return p.viseme;
  }
  return "Rest";
}

function blendExpression(base, overlay, t) {
  if (!overlay) return base;
  return {
    jawOpen: (base.jawOpen ?? 0.04) * (1 - t) + (overlay.jawOpen ?? 0.04) * t,
    smile: (base.smile ?? 0.2) * (1 - t) + (overlay.smile ?? 0.2) * t,
    frown: (base.frown ?? 0) * (1 - t) + (overlay.frown ?? 0) * t,
  };
}

function driveVisemeLoop() {
  if (!_sceneRef?._faceState) {
    _rafId = null;
    return;
  }
  const viseme = getCurrentViseme();
  const map = _visemeMap || VISEME_EXPRESSION;
  const expr = map[viseme] || map.Rest;
  const blended = _emotionExpr ? blendExpression(expr, _emotionExpr, 0.3) : expr;
  _sceneRef._faceState.jawOpen = blended.jawOpen;
  _sceneRef._faceState.smile = blended.smile;
  _sceneRef._faceState.frown = blended.frown;
  _rafId = requestAnimationFrame(driveVisemeLoop);
}

function stopVisemeLoop() {
  if (_rafId != null) {
    cancelAnimationFrame(_rafId);
    _rafId = null;
  }
  if (_sceneRef?._faceState) {
    _sceneRef._faceState.jawOpen = undefined;
    _sceneRef._faceState.smile = undefined;
    _sceneRef._faceState.frown = undefined;
  }
}

function emotionToExpression(emotion) {
  const m = {
    neutral: { smile: 0.2, frown: 0 },
    positive: { smile: 0.5, frown: 0 },
    negative: { smile: 0.1, frown: 0.25 },
    urgent: { smile: 0.25, frown: 0.1 },
    reflective: { smile: 0.12, frown: 0.08 },
    focused: { smile: 0.15, frown: 0.05 },
  };
  return m[emotion] || m.neutral;
}

/**
 * Play audio from base64 and drive visemes from phoneme sequence.
 */
async function playWithVisemes(audioBase64, phonemes, visemeMap, emotion, scene) {
  if (!scene?._faceState) return;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) {
    if (window.speak && phonemes?.length) {
      window.speak(phonemes.map(() => " ").join("")); // fallback: no text to speak
    }
    return;
  }

  _sceneRef = scene;
  _phonemes = phonemes || [];
  _visemeMap = visemeMap || VISEME_EXPRESSION;
  _emotionExpr = emotion ? emotionToExpression(emotion) : null;
  _phonemeStart = performance.now();

  if (_phonemes.length) driveVisemeLoop();

  if (!audioBase64) {
    // No TTS (e.g. ELEVEN_API_KEY missing) — still drive visemes for duration
    const last = _phonemes[_phonemes.length - 1];
    const dur = last ? last.end_ms : 2000;
    await new Promise((r) => setTimeout(r, dur));
    stopVisemeLoop();
    _onEnd?.();
    return;
  }

  try {
    const bytes = Uint8Array.from(atob(audioBase64), (c) => c.charCodeAt(0));
    _audioCtx = _audioCtx || new Ctx();
    if (_audioCtx.state === "suspended") await _audioCtx.resume();
    const buf = await _audioCtx.decodeAudioData(bytes.buffer.slice(0));
    const src = _audioCtx.createBufferSource();
    src.buffer = buf;
    src.connect(_audioCtx.destination);
    await new Promise((resolve, reject) => {
      src.onended = () => {
        stopVisemeLoop();
        _onEnd?.();
        resolve();
      };
      src.onerror = reject;
      src.start(0);
    });
  } catch (e) {
    stopVisemeLoop();
    _onEnd?.();
    throw e;
  }
}

/**
 * Full embody pipeline: POST /speech/embody → play audio + drive visemes.
 */
export async function embodyAndSpeak(transcript, options = {}) {
  const { scene, context, audienceModel, onEnd } = options;
  _onEnd = onEnd;

  try {
    const r = await fetch(`${API_BASE}/api/speech/embody`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transcript: transcript || "",
        prompt: transcript,
        text: transcript,
        context: context || {},
        audience_model: audienceModel || {},
      }),
    });
    if (!r.ok) throw new Error(`Embody failed: ${r.status}`);
    const data = await r.json();

    if (data.silence || !data.response) {
      _onEnd?.();
      return { response: "", silence: true };
    }

    const sc = window.__lipSyncScene || scene;
    if (sc && data.audio_base64 && data.phonemes?.length) {
      await playWithVisemes(
        data.audio_base64,
        data.phonemes,
        data.viseme_map,
        data.emotion,
        sc
      );
    } else if (window.speak && data.response) {
      await window.speak(data.response, data.emotion);
      _onEnd?.();
    }

    if (data.execution_plan && window.handleExecutionPlan) {
      window.handleExecutionPlan(data.execution_plan);
    }

    return {
      response: data.response,
      emotion: data.emotion,
      phonemes: data.phonemes,
      silence: false,
    };
  } catch (e) {
    if (window.speak && transcript) window.speak(transcript);
    _onEnd?.();
    throw e;
  }
}

/**
 * Speak pre-generated text with viseme-driven lip sync.
 * Uses /speech/embody/speak for phonemes + audio (no language engine).
 */
export async function speakWithEmbodiment(text, options = {}) {
  if (!text || typeof text !== "string") return;
  const { scene, onEnd } = options;
  _onEnd = onEnd;

  try {
    const r = await fetch(`${API_BASE}/api/speech/embody/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 1000) }),
    });
    if (!r.ok) throw new Error(`Speak embody failed: ${r.status}`);
    const data = await r.json();

    const sc = window.__lipSyncScene || scene;
    if (sc && data.audio_base64 && data.phonemes?.length) {
      await playWithVisemes(
        data.audio_base64,
        data.phonemes,
        data.viseme_map,
        data.emotion || "neutral",
        sc
      );
    } else if (window.speak) {
      await window.speak(text, data.emotion || "neutral");
      _onEnd?.();
    }
    return { response: data.response, phonemes: data.phonemes };
  } catch (e) {
    if (window.speak) window.speak(text);
    _onEnd?.();
    throw e;
  }
}

/**
 * Speak with local visemes only (no backend). Fallback when API unavailable.
 */
export async function speakWithVisemes(text, phonemes, scene) {
  if (!text) return;
  const sc = window.__lipSyncScene || scene;
  if (sc && phonemes?.length) {
    _sceneRef = sc;
    _phonemes = phonemes;
    _visemeMap = VISEME_EXPRESSION;
    _emotionExpr = null;
    _phonemeStart = performance.now();
    driveVisemeLoop();
  }
  if (window.speak) await window.speak(text);
  stopVisemeLoop();
}

export async function getEmbodimentSkill() {
  const r = await fetch(`${API_BASE}/api/speech/embodiment/skill`);
  if (!r.ok) return null;
  return r.json();
}

export async function clearEmbodimentMemory() {
  const r = await fetch(`${API_BASE}/api/speech/embodiment/memory/clear`, { method: "POST" });
  return r.ok ? r.json() : null;
}

export async function getEmbodimentMemory() {
  const r = await fetch(`${API_BASE}/api/speech/embodiment/memory`);
  if (!r.ok) return { history: [] };
  const d = await r.json();
  return { history: d.history || [] };
}

/**
 * Init: wire embodyAndSpeak, register with terminal/voice flow.
 */
export function initSpeechEmbodiment(scene) {
  if (!scene?._faceState) return;

  window.embodyAndSpeak = (text, opts = {}) =>
    embodyAndSpeak(text, { ...opts, scene: opts.scene || scene });
  window.__speechEmbodimentScene = scene;

  // Wire speakWithEmbodiment for pre-generated text (e.g. from WebSocket)
  // Signature: (text, emotionOrOpts) — emotion string or options object
  window.speakWithEmbodiment = (text, emotionOrOpts) => {
    const opts = typeof emotionOrOpts === "string" ? { emotion: emotionOrOpts } : (emotionOrOpts || {});
    return speakWithEmbodiment(text, { ...opts, scene: opts.scene || scene });
  };
}
