# Data Flow

Client (browser) ↔ WebSocket (/ws/{channel}) ↔ WebSocket Hub ↔ Services

## Speech Pipeline (ASR → Reasoning → Response → TTS)

```
ASR transcript → SpeechReasoningService → response / execution_plan → TTS → stream
                       ↑
              Reasoning buffer: normalize, intent detection,
              emotion/urgency, confidence scoring (<0.65 → clarify)
```

- WebSocket accepts `prompt` or `transcript` — never executes raw speech directly
- SpeechReasoningService: filler removal, intent (command/inquiry/emotional/philosophical), confidence threshold 0.65
- Output: `{ normalized_text, intent, emotion, confidence, response, execution_plan? }`
- See `docs/SPEECH_COMMUNICATION_DIRECTIVE.md` for full spec

## Other Flows

- Client subscribes to channels: emotion, mission, terminal, tts, phoneme
- WebSocket Hub broadcasts JSON messages to subscribed clients
- EmotionService reads inputs (governance, mission, sentiment, health, pressure), computes deterministic state, appends to Redis (`emotion_history`) and broadcasts `state_update`
- VoiceBroker streams TTS from ElevenLabs or `LOCAL_TTS_URL`, forwards base64 chunks over WebSocket as `tts_chunk`
- Phoneme detector (optional) ingests audio frames and emits `phoneme` messages to clients
- MissionService persists board snapshots to Redis (`mission_board`) and serves `/api/mission/board`
