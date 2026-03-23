# Requirements: Billy B Assistant — Wake Word Reintegration & Stabilization

**Defined:** 2026-03-24
**Core Value:** The fish responds to voice — both button press and hands-free wake word activation — routing queries intelligently between Claude and Home Assistant.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Wake Word Integration

- [x] **WAKE-01**: Wake word detection triggers a conversation session identically to a button press (via `trigger_session_start("wake_word")`)
- [x] **WAKE-02**: `trigger_session_stop(source)` cleanly stops sessions from any source (hardware, wake_word, ui-test)
- [x] **WAKE-03**: `on_button()` delegates to `trigger_session_start("hardware")` and `trigger_session_stop("hardware")` instead of inline logic
- [x] **WAKE-04**: Wake word controller receives `notify_session_state(True/False)` on session start and end to pause/resume mic listening
- [x] **WAKE-05**: Wake word controller is initialized in `start_loop()` with config parameters and detection callback
- [x] **WAKE-06**: Audio feedback (wake-up sound) plays when wake word is detected, same as button press
- [x] **WAKE-07**: `button.is_pressed` guard does not block wake-word-sourced triggers
- [x] **WAKE-08**: Debounce logic works per-source (0.5s) preventing duplicate triggers
- [x] **WAKE-09**: Session cleanup/finally block calls `notify_session_state(False)` to re-enable wake word listening

### Wake Word Web Routes

- [ ] **WWEB-01**: `GET /wake-word/status` returns JSON with wake word controller status (or fallback if unavailable)
- [ ] **WWEB-02**: `GET /wake-word/events` drains and returns up to 50 events from the controller event queue
- [ ] **WWEB-03**: `POST /wake-word/runtime-config` accepts enabled, sensitivity, threshold, endpoint, access key and updates controller
- [ ] **WWEB-04**: `POST /wake-word/test` accepts simulate/stop actions, calls trigger_session_start/stop("ui-test")
- [ ] **WWEB-05**: `POST /wake-word/calibrate` records audio via sounddevice, computes RMS metrics for ambient and phrase modes
- [ ] **WWEB-06**: `POST /wake-word/calibrate/apply` persists threshold/sensitivity to .env and updates runtime config
- [ ] **WWEB-07**: Wake word blueprint registered in Flask app factory following existing blueprint pattern

### Wake Word UI

- [ ] **WWUI-01**: Enable/disable toggle with listener status badge (Listening/Disabled/Paused/Error/Unavailable)
- [ ] **WWUI-02**: Porcupine endpoint path and access key input fields
- [ ] **WWUI-03**: Sensitivity slider (0.0-1.0, step 0.05) and RMS threshold input
- [ ] **WWUI-04**: Simulate Detection / Stop Session / Refresh Status buttons
- [ ] **WWUI-05**: Event stream display showing last 50 events (scrollable)
- [ ] **WWUI-06**: Calibration wizard: Measure Background -> Record Wake Phrase -> Apply Suggestions
- [ ] **WWUI-07**: Calibration results grid showing ambient noise RMS, peak, suggested threshold, and wake phrase peak RMS
- [ ] **WWUI-08**: "Apply Suggestions" button with threshold display and "persist to .env" checkbox
- [ ] **WWUI-09**: Panel is collapsible, visually consistent with Audio Settings / MQTT / HA sections
- [ ] **WWUI-10**: JS module follows IIFE pattern, calls `WakeWordPanel.init()` on DOMContentLoaded

### Settings Persistence

- [ ] **SETS-01**: Wake word config keys (WAKE_WORD_ENABLED, SENSITIVITY, THRESHOLD, ENDPOINT, PORCUPINE_ACCESS_KEY) saved to .env on form submit
- [ ] **SETS-02**: Wake word keys added to CONFIG_KEYS in system routes so main settings save includes them

### Session Resilience

- [x] **SRES-01**: `play_random_wake_up_clip()` sets `playback_done_event` even when no clips found, preventing mic start deadlock
- [x] **SRES-02**: Dead websocket detected after repeated send timeouts, triggers session teardown instead of silent failure
- [x] **SRES-03**: Mic timeout checker verifies session isn't already stopping before calling `stop_session()`, preventing double-stop race condition

### Home Assistant Resilience

- [x] **HARE-01**: `send_conversation_prompt()` has explicit timeout (5 seconds) preventing indefinite hangs
- [x] **HARE-02**: HA availability cached with TTL — fail fast if HA known to be down instead of blocking session

### Config Validation

- [x] **CONF-01**: Numeric config values validated for sane ranges (MIC_TIMEOUT_SECONDS 1-300, FLASK_PORT 1-65535, thresholds non-negative)
- [x] **CONF-02**: Invalid config values log a warning and fall back to sensible defaults instead of silently misbehaving

### Merge Breakage Fixes

- [x] **FIX-01**: Investigate and fix any other issues caused by upstream merge (to be catalogued during implementation)

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Enhanced Wake Word

- **EWAK-01**: Provider failover — if primary AI provider is down, fall back to secondary instead of failing session
- **EWAK-02**: Per-environment sensitivity profiles (save calibration for kitchen vs bedroom)
- **EWAK-03**: Custom .ppn wake word model upload via web UI
- **EWAK-04**: Animatronic acknowledgment movement pattern on wake word detection
- **EWAK-05**: Porcupine v3 -> v4 upgrade with keyword re-training
- **EWAK-06**: Dual-mode detection display (Porcupine vs RMS mode-specific tuning)

### System Improvements

- **SIMP-01**: Atomic profile writes with backup (prevent memory corruption data loss)
- **SIMP-02**: MQTT reconnection hardening (prevent zombie reconnect threads)
- **SIMP-03**: Config hot-reload that actually updates live module state

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud-based wake word | Destroys privacy, adds latency, violates local-first principle |
| Multiple simultaneous wake words | Increases false acceptance rate, Porcupine free tier limits keywords |
| Continuous conversation mode | Session model already handles multi-turn; always-open-mic causes phantom triggers |
| Speaker identification | Existing `identify_user` conversational tool is more reliable on Pi |
| Wake word during playback | Echo cancellation infeasible on Pi hardware |
| OpenWakeWord engine | Already removed (commit 53a0cb4), Porcupine proven on Pi |
| Modifying core/hotword.py | Works as-is, only integration points needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WAKE-01 | Phase 1 | Complete |
| WAKE-02 | Phase 1 | Complete |
| WAKE-03 | Phase 1 | Complete |
| WAKE-04 | Phase 1 | Complete |
| WAKE-05 | Phase 1 | Complete |
| WAKE-06 | Phase 1 | Complete |
| WAKE-07 | Phase 1 | Complete |
| WAKE-08 | Phase 1 | Complete |
| WAKE-09 | Phase 1 | Complete |
| SRES-01 | Phase 1 | Complete |
| SRES-02 | Phase 1 | Complete |
| SRES-03 | Phase 1 | Complete |
| HARE-01 | Phase 1 | Complete |
| HARE-02 | Phase 1 | Complete |
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| FIX-01 | Phase 1 | Complete |
| WWEB-01 | Phase 2 | Pending |
| WWEB-02 | Phase 2 | Pending |
| WWEB-03 | Phase 2 | Pending |
| WWEB-04 | Phase 2 | Pending |
| WWEB-05 | Phase 2 | Pending |
| WWEB-06 | Phase 2 | Pending |
| WWEB-07 | Phase 2 | Pending |
| SETS-01 | Phase 2 | Pending |
| SETS-02 | Phase 2 | Pending |
| WWUI-01 | Phase 3 | Pending |
| WWUI-02 | Phase 3 | Pending |
| WWUI-03 | Phase 3 | Pending |
| WWUI-04 | Phase 3 | Pending |
| WWUI-05 | Phase 3 | Pending |
| WWUI-06 | Phase 3 | Pending |
| WWUI-07 | Phase 3 | Pending |
| WWUI-08 | Phase 3 | Pending |
| WWUI-09 | Phase 3 | Pending |
| WWUI-10 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after roadmap creation*
