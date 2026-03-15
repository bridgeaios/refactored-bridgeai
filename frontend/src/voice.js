import { API_BASE } from './config.js';

function map_emotion_to_voice_pitch(emotion) {
  const pitches = { neutral: 1.0, focused: 0.95, confident: 1.05, alert: 1.1, reflective: 0.9, concerned: 0.85 };
  return pitches[emotion] ?? 1.0;
}

function showTtsFallbackToast() {
  const toast = document.createElement('div');
  toast.textContent = 'Voice: using browser (add ELEVEN_API_KEY to backend for cloud TTS)';
  toast.style.cssText = 'position:fixed;bottom:200px;left:50%;transform:translateX(-50%);background:rgba(0,80,40,0.95);color:#8fc;padding:8px 16px;border-radius:6px;font-size:12px;z-index:9998;font-family:monospace;box-shadow:0 2px 8px rgba(0,0,0,0.4);';
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function getBestBrowserVoice() {
  const voices = speechSynthesis.getVoices();
  if (!voices.length) return null;
  const prefer = ['Google US English', 'Microsoft Zira', 'Samantha', 'Karen', 'Daniel', 'Victoria', 'en-US'];
  for (const p of prefer) {
    const v = voices.find(x => x.name?.includes(p));
    if (v) return v;
  }
  return voices.find(v => v.lang?.startsWith('en')) || voices[0];
}

async function speakWithBackend(text) {
  try {
    const r = await fetch(`${API_BASE}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.slice(0, 500) })
    });
    if (!r.ok) return false;  // 503/502 → fallback to browser TTS (no ELEVEN_API_KEY or backend down)
    const blob = await r.blob();
    if (typeof window.__playWithLipSync === 'function' && window.__lipSyncScene) {
      await window.__playWithLipSync(blob);
      return true;
    }
    const audio = new Audio(URL.createObjectURL(blob));
    await audio.play();
    audio.onended = () => URL.revokeObjectURL(audio.src);
    return true;
  } catch {
    return false;
  }
}

function speakWithBrowser(text, emotion = 'neutral') {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.pitch = map_emotion_to_voice_pitch(emotion);
  utterance.rate = 0.92;
  utterance.volume = 1;
  const voice = getBestBrowserVoice();
  if (voice) utterance.voice = voice;
  speechSynthesis.speak(utterance);
}

export function initVoice() {
  if (typeof speechSynthesis !== 'undefined') {
    speechSynthesis.getVoices();
    speechSynthesis.addEventListener('voiceschanged', () => speechSynthesis.getVoices());
  }

  window.speak = async (text, emotion = 'neutral') => {
    if (!text || typeof text !== 'string') return;
    try {
      const usedBackend = await speakWithBackend(text);
      if (!usedBackend && typeof speechSynthesis !== 'undefined') {
        if (!window.__ttsFallbackShown) {
          window.__ttsFallbackShown = true;
          showTtsFallbackToast();
        }
        speakWithBrowser(text, emotion);
      }
    } catch (e) {
      if (typeof speechSynthesis !== 'undefined') speakWithBrowser(text, emotion);
    }
  };
}

export class Voice {
  constructor(ws, emotion) {
    this.ws = ws;
    this.emotion = emotion;
    this.ctx = null;
    this.queue = [];
    ws.addEventListener('message', e => {
      try {
        const m = JSON.parse(e.data);
        if (m.type === 'tts_chunk') this._handleChunk(m.data);
      } catch (e) {}
    });
  }

  async _ensureCtx() {
    if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
  }

  async speak(text, voice = '21m00Tcm4TlvDq8ikWAM') {
    try {
      const r = await fetch(`${API_BASE}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice_id: voice })
      });
      if (r.ok) {
        const blob = await r.blob();
        if (typeof window.__playWithLipSync === 'function' && window.__lipSyncScene) {
          await window.__playWithLipSync(blob);
          return;
        }
        const audio = new Audio(URL.createObjectURL(blob));
        await audio.play();
        audio.onended = () => URL.revokeObjectURL(audio.src);
        return;
      }
    } catch (e) {}
    if (typeof speechSynthesis !== 'undefined') {
      if (!window.__ttsFallbackShown) {
        window.__ttsFallbackShown = true;
        showTtsFallbackToast();
      }
      const ut = new SpeechSynthesisUtterance(text);
      const pitch = 1 + (this.emotion?.state?.score || 0) * 0.05;
      ut.pitch = Math.max(0.6, Math.min(1.4, pitch));
      ut.rate = 0.92;
      const voiceOpt = getBestBrowserVoice();
      if (voiceOpt) ut.voice = voiceOpt;
      speechSynthesis.speak(ut);
    }
  }

  async _handleChunk(base64data) {
    try {
      const bytes = Uint8Array.from(atob(base64data), c => c.charCodeAt(0));
      await this._ensureCtx();
      const audioBuffer = await this.ctx.decodeAudioData(bytes.buffer.slice(0));
      const src = this.ctx.createBufferSource();
      src.buffer = audioBuffer;
      const semitone = (this.emotion?.state?.score || 0) * 2;
      src.playbackRate.value = Math.pow(2, semitone / 12);
      const gain = this.ctx.createGain();
      gain.gain.value = 1.0;
      src.connect(gain).connect(this.ctx.destination);
      src.start();
    } catch (e) {}
  }
}
