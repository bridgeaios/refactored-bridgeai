# Twin_Speech_Communication_Embodiment

Drop-in skill module for functional speech embodiment. Not cosmetic chatter.

## Architecture

```
Communication_Output =
  (Language_Model_Response × Emotional_Modulation × Audience_Model)
  → TTS → Phoneme_Stream → Viseme_Driver → Facial_Rig
```

## Components

### 1. Language Engine
- **Inputs**: Intent, context state, emotional state, audience model
- **Process**: Semantically precise response, tone calibration, coherence validation
- **Output**: Clean text, emotion tag, prosody parameters
- **Backend**: `speech_reasoning` service

### 2. Voice Synthesis Layer
- Neural TTS (ElevenLabs when `ELEVEN_API_KEY` set)
- Adjustable pitch, tempo, intensity via prosody
- **Backend**: `voice_broker` (stream_tts)

### 3. Lip Sync & Facial Binding
- **Visemes**: AA, EE, OH, FV, BMP, TH, Rest
- Phoneme → viseme mapping (ARPAbet-style)
- Drives: jawOpen, smile, frown (compatible with `setExpression`)
- **Frontend**: `speechEmbodiment.js` viseme driver

### 4. Emotional Modulation
- **Voice**: pitch variance, speech speed, energy level
- **Face**: brow compression, eye aperture, lip tension (via emotion→expression)

### 5. Conversational Memory
- Dialogue history (last N turns)
- **API**: `GET /api/speech/embodiment/memory`, `POST /api/speech/embodiment/memory/clear`

### 6. Adaptive Feedback
- Confidence threshold → silence when no positive-value output
- Audience reaction signals (extensible)

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/speech/embody` | POST | Full pipeline: transcript → response + phonemes + audio |
| `/api/speech/embody/speak` | POST | Pre-generated text → phonemes + audio (no language engine) |
| `/api/speech/embodiment/skill` | GET | Skill definition |
| `/api/speech/embodiment/memory` | GET | Dialogue history |
| `/api/speech/embodiment/memory/clear` | POST | Clear memory |

## Frontend

```javascript
// Full pipeline (user prompt → twin response)
await embodyAndSpeak("tell me about yourself", { scene, onEnd });

// Pre-generated text (e.g. from WebSocket)
await speakWithEmbodiment("I am the Bridge.", { scene, emotion: "neutral" });

// Terminal uses speakWithEmbodiment when available (phoneme-driven lip sync)
```

## Viseme Mapping

| Viseme | jawOpen | smile | frown |
|--------|---------|-------|-------|
| AA | 0.45 | 0.1 | 0 |
| EE | 0.08 | 0.7 | 0 |
| OH | 0.35 | 0.05 | 0 |
| FV | 0.12 | 0.25 | 0.08 |
| BMP | 0.02 | 0.1 | 0 |
| TH | 0.18 | 0.15 | 0.05 |
| Rest | 0.04 | 0.2 | 0 |

## Requirements

- `ELEVEN_API_KEY` for neural TTS (falls back to browser `speechSynthesis` when unset)
- Babylon.js scene with `_faceState` (jawOpen, smile, frown)
