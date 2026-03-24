# Feature Research

**Domain:** Voice-activated animatronic assistant with wake word detection and smart home integration
**Researched:** 2026-03-24
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wake word activation | Hands-free is the entire point of a voice assistant; button-only defeats the purpose | MEDIUM | `core/hotword.py` exists with full `WakeWordController` (Porcupine + RMS fallback). Integration into `button.py` session lifecycle is the gap. |
| Session pause during wake word listening | Mic must stop wake word detection while a conversation session is active, or false triggers will interrupt responses | LOW | `notify_session_state(active)` already implemented in `WakeWordController`. Must be called from session start/stop in `button.py`. |
| Cooldown between detections | Prevents rapid-fire false triggers from echoed audio or ambient noise | LOW | Already implemented: `cooldown_seconds = 2.0` in `WakeWordController`. |
| Wake word enable/disable toggle | Users need to silence always-on listening without shutting down the whole system | LOW | `enable()`/`disable()` methods exist. Needs UI toggle in web dashboard and `.env` persistence. |
| Audio feedback on wake word detection | User needs confirmation the device heard the wake word (visual/audio cue) | LOW | Wake-up sound playback already exists via `audio.play_random_wake_up_clip()`. Must wire into wake word detection callback same as button press. |
| Web dashboard status indicator | User needs to see if wake word listening is active, errored, or disabled at a glance | LOW | `get_status()` returns full state dict. Needs a status badge component in the web UI header or settings panel. |
| Sensitivity/threshold configuration via UI | Users cannot be expected to SSH in and edit `.env` to tune detection sensitivity | MEDIUM | Config vars exist (`WAKE_WORD_SENSITIVITY`, `WAKE_WORD_THRESHOLD`). `set_parameters()` supports runtime changes. Needs settings form fields and `.env` write-back. |
| Graceful degradation when Porcupine unavailable | System must not crash if `pvporcupine` is missing or access key is invalid | LOW | Already handled: `_PORCUPINE_AVAILABLE` flag, error capture in `_prepare_engine()`, `_last_error` tracking. Just needs UI surfacing of error state. |
| Multiple trigger sources (button + wake word) | Both physical button and wake word must start sessions identically | MEDIUM | Core gap. `button.py` has `on_button()` hardcoded to physical button. Needs a `trigger_session_start()` abstraction callable from both button press and wake word callback. |
| MQTT remote trigger | Smart home automations should be able to trigger Billy (e.g., "when doorbell rings, have Billy announce") | LOW | MQTT `billy/command` topic already subscribed. Wake word events should publish to `billy/state` for HA awareness. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Real-time audio level meter in UI | Visual feedback during calibration lets users tune threshold without guesswork; most DIY assistants lack this | LOW | `WakeWordController` already emits `meter` events with RMS level every 250ms. Needs SSE endpoint and a simple meter bar in the UI. |
| Wake word calibration wizard | Guided step-by-step: "speak normally", "be quiet", auto-suggests threshold. Dramatically reduces setup friction | MEDIUM | Can be built on top of the meter event stream. Collect ambient RMS for 5s, collect speech RMS for 5s, set threshold between them. |
| Per-environment sensitivity profiles | Save calibration profiles for different rooms/noise conditions (e.g., "kitchen" vs "bedroom") | MEDIUM | Not currently supported. Would need profile storage and selection in UI. Defer to later. |
| Porcupine access key validation in UI | Test the access key before saving, show clear error if invalid or expired | LOW | Can attempt `pvporcupine.create()` with a test keyword and catch exceptions. Prevents frustrating "why won't it work" debugging. |
| Wake word event log/history | Shows recent detections, false triggers, errors in a scrollable log panel | LOW | Event queue already exists with full event typing. Just needs a UI panel that drains events via SSE. |
| Custom wake word model upload | Let users upload their own `.ppn` file through the web UI instead of SCP | LOW | File upload route + save to `wake-word-models/` directory. Simple but high-quality-of-life improvement. |
| Animatronic acknowledgment pattern | Fish does a distinctive head/tail movement on wake word detection (before speaking), creating a physical "I'm listening" cue unique to this project | LOW | Motor control already exists. Add a short movement pattern in the wake word callback before session starts. |
| Dual-mode detection display | Show whether Porcupine (keyword) or RMS (amplitude) mode is active, with mode-specific tuning options | LOW | `detector_mode` tracked in status. UI can conditionally show Porcupine-specific or RMS-specific settings. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Cloud-based wake word detection | "Better accuracy with cloud ML" | Destroys privacy, adds latency, requires internet for basic activation, violates the local-first principle of the project | Use Porcupine on-device. It runs efficiently on Raspberry Pi with sub-second detection and no cloud dependency. |
| Multiple simultaneous wake words | "Support Hey Billy AND OK Billy AND Billy" | Each additional keyword increases false acceptance rate multiplicatively. Porcupine free tier limits keywords. Confusing UX. | Pick one good wake word and tune sensitivity well. Custom `.ppn` models via Picovoice console. |
| Continuous conversation mode (no wake word between turns) | "I don't want to say the wake word every time" | The `conversation_state(expects_follow_up)` tool already handles multi-turn conversation within a session. Adding always-open-mic between sessions causes phantom triggers, privacy concerns, and high CPU usage on Pi. | Current design is correct: wake word or button starts a session, session handles follow-ups internally via VAD, session ends on timeout/silence. |
| Voice identification / speaker recognition | "Know who is talking without asking" | Requires significant compute (speaker embeddings), training data per user, unreliable in noisy/reverberant home environments, and the existing `identify_user` tool handles this conversationally | Keep the `identify_user` tool approach. User says "I'm Tom" and Billy remembers. Much more reliable than speaker ID on Pi hardware. |
| OpenWakeWord as alternative engine | "It's free and open source" | Billy already removed it (`53a0cb4 removed openwakeword` in git history). Likely removed due to accuracy or resource issues on the target hardware. Porcupine is proven on Pi. | Stick with Porcupine. It has better accuracy benchmarks (< 5% FRR at 1 FA per 10 hours) and runs efficiently on ARM. |
| Wake word works during active playback | "Billy should hear me even while talking" | Echo cancellation on Pi hardware is extremely difficult. The mic picks up speaker output, causing false detections or missed detections. Would need AEC hardware or DSP pipeline. | Current design pauses wake word during sessions (`notify_session_state`). Button press interrupts active sessions. This is the right pattern. |

## Feature Dependencies

```
Wake Word Integration (trigger_session_start abstraction)
    |-- requires --> Session lifecycle in button.py (existing)
    |-- requires --> WakeWordController callback wiring (existing module)
    |
    |-- enables --> Wake Word Web Routes (status, config, events)
    |                   |-- enables --> Wake Word UI Panel
    |                   |-- enables --> Real-time Audio Meter
    |                   |-- enables --> Calibration Wizard
    |                   |-- enables --> Event Log/History
    |
    |-- enables --> Settings Form Integration (.env persistence)
    |                   |-- enables --> Sensitivity/Threshold UI
    |                   |-- enables --> Porcupine Key Validation
    |
    |-- enables --> MQTT Wake Word State Publishing

Wake Word UI Panel
    |-- requires --> Wake Word Web Routes Blueprint
    |-- requires --> SSE Event Stream Endpoint

Calibration Wizard
    |-- requires --> Real-time Audio Meter
    |-- requires --> Wake Word Web Routes (parameter update endpoint)

Custom Wake Word Upload
    |-- requires --> Wake Word Web Routes (file upload endpoint)
    |-- independent of --> Calibration Wizard
```

### Dependency Notes

- **trigger_session_start requires session lifecycle:** The abstraction wraps existing `on_button()` session management. Without it, wake word detection fires but cannot start sessions.
- **Wake Word Web Routes requires integration:** No point building UI routes if the backend wake word controller is not wired into the session lifecycle.
- **Calibration Wizard requires Audio Meter:** The wizard needs real-time RMS readings to guide the user through threshold selection. Build the meter first, wizard second.
- **Custom Wake Word Upload is independent:** Can be built at any time since it just saves a `.ppn` file to disk and updates `WAKE_WORD_ENDPOINT`.

## MVP Definition

### Launch With (v1)

Minimum viable wake word reintegration -- what's needed for hands-free operation.

- [x] `trigger_session_start()` abstraction in `button.py` -- unifies button and wake word triggers
- [x] Wake word callback wiring -- `WakeWordController.set_detection_callback()` calls `trigger_session_start()`
- [x] Session state notification -- `notify_session_state(True/False)` called on session start/end to pause/resume listening
- [x] Wake word enable/disable in settings UI -- checkbox in existing settings form, persisted to `.env`
- [x] Status badge in web UI -- shows listening/stopped/error state
- [x] Basic sensitivity and threshold fields in settings form -- numeric inputs, saved to `.env`
- [x] End-to-end verification -- both button press and wake word trigger sessions correctly

### Add After Validation (v1.x)

Features to add once core wake word integration is working.

- [ ] Wake word web routes blueprint -- dedicated `/api/wakeword/` endpoints for status, events, config, test
- [ ] SSE event stream -- real-time wake word events pushed to browser
- [ ] Real-time audio level meter -- visual RMS bar in UI using SSE meter events
- [ ] Wake word event log panel -- scrollable history of detections and errors
- [ ] Calibration wizard -- guided threshold tuning with ambient/speech level measurement
- [ ] Porcupine access key validation -- test key before saving
- [ ] Custom `.ppn` model upload via web UI
- [ ] Animatronic acknowledgment pattern on wake word detection

### Future Consideration (v2+)

Features to defer until core is stable and validated.

- [ ] Per-environment sensitivity profiles -- save/load calibration per room
- [ ] Dual wake word model support -- e.g., different keywords for different users
- [ ] Wake word detection analytics -- false trigger rate tracking over time
- [ ] Voice-prompted recalibration -- "Billy, recalibrate your hearing"

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| trigger_session_start abstraction | HIGH | MEDIUM | P1 |
| Wake word callback wiring | HIGH | LOW | P1 |
| Session state notification | HIGH | LOW | P1 |
| Enable/disable toggle in UI | HIGH | LOW | P1 |
| Status badge | MEDIUM | LOW | P1 |
| Sensitivity/threshold in settings | HIGH | LOW | P1 |
| .env persistence for wake word settings | HIGH | LOW | P1 |
| Wake word routes blueprint | MEDIUM | MEDIUM | P2 |
| SSE event stream | MEDIUM | MEDIUM | P2 |
| Real-time audio meter | MEDIUM | LOW | P2 |
| Calibration wizard | HIGH | MEDIUM | P2 |
| Event log panel | LOW | LOW | P2 |
| Custom .ppn upload | MEDIUM | LOW | P2 |
| Animatronic acknowledgment | MEDIUM | LOW | P2 |
| Porcupine key validation | MEDIUM | LOW | P2 |
| Per-environment profiles | LOW | MEDIUM | P3 |
| Detection analytics | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have -- wake word does not work without these
- P2: Should have -- significantly improves usability and setup experience
- P3: Nice to have -- polish features for mature product

## Competitor Feature Analysis

| Feature | Amazon Echo / Alexa | Home Assistant Voice | Billy B Assistant (Target) |
|---------|---------------------|---------------------|---------------------------|
| Wake word detection | Cloud-trained, multi-word, AEC | openWakeWord (local) or cloud | Porcupine (local, on-device) |
| Trigger methods | Voice only | Voice, companion app | Voice + physical button + MQTT + web UI |
| Smart home control | Native, 10K+ device support | Native, Matter/Zigbee/Z-Wave | Via Home Assistant API/MQTT relay |
| Conversational AI | Limited to Alexa skills | Local LLM or cloud LLM | Claude/OpenAI Realtime API (cloud, high quality) |
| Physical embodiment | LED ring, no movement | None (speaker satellite) | Animatronic fish with synchronized mouth/tail |
| Persona/personality | Fixed corporate voice | Configurable TTS voice | Full persona system with personality traits, backstory, humor tuning |
| Privacy | Cloud-dependent | Fully local option | Wake word local, conversation cloud |
| Calibration UI | Automatic (cloud ML) | Basic sensitivity slider | Threshold tuning + calibration wizard (target) |
| User profiles | Voice-based recognition | Manual switch | Conversational identification + persistent memories |

## Sources

- [Home Assistant wake word approach](https://www.home-assistant.io/voice_control/about_wake_word/)
- [Picovoice Porcupine wake word documentation](https://picovoice.ai/docs/porcupine/)
- [Picovoice wake word benchmarking](https://picovoice.ai/blog/benchmarking-a-wake-word-detection-engine/)
- [Porcupine GitHub](https://github.com/Picovoice/porcupine)
- [Picovoice complete wake word guide](https://picovoice.ai/blog/complete-guide-to-wake-word/)
- [Rhasspy wake word documentation](https://rhasspy.readthedocs.io/en/latest/wake-word/)
- [Home Assistant AI roadmap 2025](https://www.home-assistant.io/blog/2025/05/09/roadmap-2025h1/)
- Codebase analysis: `core/hotword.py`, `core/button.py`, `core/config.py`, `webconfig/app/routes/`

---
*Feature research for: Voice-activated animatronic assistant wake word reintegration*
*Researched: 2026-03-24*
