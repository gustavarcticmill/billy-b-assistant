# Project Research Summary

**Project:** Billy B Assistant — Wake Word Reintegration
**Domain:** On-device wake word detection on Raspberry Pi voice assistant (animatronic fish)
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

This is a focused integration milestone, not a greenfield build. The wake word detection engine (`core/hotword.py`) is already written and production-ready — it runs Picovoice Porcupine (v3) with an RMS amplitude fallback, exposes a clean callback/event-queue interface, and handles microphone stream lifecycle internally. The gap is wiring: the engine is not connected to the session lifecycle in `button.py`, has no web UI surface, and its settings are not persistable through the dashboard. Everything needed already exists in the codebase; the work is integration, not invention.

The recommended approach is a strict layered build: first extract a source-agnostic `trigger_session_start()` abstraction from `button.py` so both button and wake word can start sessions identically, then wire the detection callback, then build web routes on top, then add UI. This order is dictated by hard component dependencies — you cannot build UI routes before the backend integration exists, and you cannot safely wire the callback before the session trigger abstraction is in place. Skipping the abstraction step and patching the wake word callback directly into `on_button()` logic is the most common failure mode in this type of integration and must be avoided.

The dominant risk is microphone resource contention. The Pi has one USB microphone and both the wake word detector and the session recording code open audio streams. If `notify_session_state(True)` is not called before a session starts, both streams race for the hardware device, causing silent failures or `PortAudioError`. A secondary risk is self-triggering: if the wake word listener resumes before audio playback finishes, Billy's own voice can re-trigger a new session. Both are handled by patterns already present in `WakeWordController` — they just need to be called correctly from the session lifecycle.

## Key Findings

### Recommended Stack

No new dependencies are needed. The existing `requirements.txt` covers everything: `pvporcupine` (v3.0.x — pin `<4.0.0` to protect keyword model compatibility), `sounddevice` (audio stream), `scipy` (resampling), `numpy <2`, `Flask 3.1.x` (app factory + blueprints), and `python-dotenv` (config persistence). The web event streaming approach is native Flask SSE (Response with `text/event-stream` MIME type, reading from `WakeWordController._event_queue`) — no Redis, no WebSocket competition, no additional libraries.

**Core technologies:**
- `pvporcupine 3.0.x`: on-device wake word detection — pin `<4.0.0`; v4 engine may break existing `.ppn` keyword files
- `sounddevice`: audio input stream — already in use; callback-based `sd.InputStream` that `WakeWordController` depends on
- `scipy.signal.resample`: mic rate to Porcupine's required 16kHz — already wired; performance risk on Pi 3 (see Pitfalls)
- `Flask 3.1.x` + native SSE: web dashboard and event streaming — blueprint pattern already established in codebase
- `python-dotenv`: settings persistence — already manages all config; wake word settings use `dotenv.set_key()` for write-back
- `threading` (stdlib): wake word listener runs in background daemon thread — already the pattern in `hotword.py`

### Expected Features

The feature set is well-defined by the existing codebase surface area. All P1 (must-have) features are low-to-medium complexity because the underlying logic already exists — the gap is wiring and UI exposure.

**Must have (table stakes) — P1:**
- `trigger_session_start(source)` abstraction in `button.py` — without this, wake word cannot start sessions without duplicating critical lifecycle logic
- Wake word detection callback wired to `trigger_session_start("wake_word")` — the actual hands-free activation
- `notify_session_state(True/False)` called on session start/end — prevents mic contention (single most important call)
- Enable/disable toggle with `.env` persistence — users cannot SSH to configure a consumer device
- Status badge in web UI — users need immediate visibility into whether wake word is active or errored
- Sensitivity and threshold fields in settings form — required for any environment-specific tuning

**Should have (differentiators) — P2:**
- Dedicated wake word blueprint (`/wakeword/` routes) with SSE event stream — enables real-time UI
- Real-time audio level meter via SSE — only differentiating calibration tool among DIY assistants
- Calibration wizard (ambient measurement + voice measurement + auto-threshold) — dramatically reduces setup friction
- Event log panel — visibility into detection history and false trigger rate
- Custom `.ppn` model upload via web UI — eliminates SCP for model updates
- Porcupine access key validation before save — prevents silent configuration failures
- Animatronic acknowledgment movement on wake word detection — unique to this project's physical embodiment

**Defer (v2+):**
- Per-environment sensitivity profiles (kitchen/bedroom saved configs)
- Detection analytics and false trigger rate tracking over time
- Voice-prompted recalibration ("Billy, recalibrate your hearing")
- Dual wake word model support

### Architecture Approach

The architecture is a layered integration on top of the existing singleton `WakeWordController`. The controller is self-contained with a clean callback interface (`set_detection_callback`), thread-safe event queue (`get_event_queue`), and mic handoff protocol (`notify_session_state`). The integration pattern is: button.py owns the session lifecycle and wires the callback at startup; hotword.py never imports from button.py (strictly one-directional dependency); web routes read controller state via `get_status()` and stream events via `get_event_queue()`; the web UI consumes events via `EventSource` (native browser SSE). Do not modify `core/hotword.py` — all integration happens outside it through its existing public interface.

**Major components:**
1. **Session Trigger Abstraction** (`core/button.py` refactor) — source-agnostic `trigger_session_start/stop()` functions; all trigger sources (button, wake word, MQTT, UI test) call this single entry point
2. **WakeWordController** (`core/hotword.py` — existing, do not modify) — continuous mic monitoring, Porcupine/RMS detection, event queue, mic stream lifecycle
3. **Wake Word Blueprint** (`webconfig/app/routes/wakeword.py` — new) — HTTP endpoints for status, enable/disable, configure, SSE stream, test trigger; follows existing blueprint pattern
4. **Wake Word UI Panel** (`webconfig/templates/` — new partial) — enable/disable toggle, status badge, RMS meter, calibration controls; JavaScript IIFE following existing front-end pattern
5. **Settings Persistence** (integrated into web routes) — atomic `.env` write-back + immediate `set_parameters()` call for zero-restart config changes

### Critical Pitfalls

1. **Microphone stream contention** — both the wake word detector and session audio open `sd.InputStream` on the same USB mic. Prevention: call `controller.notify_session_state(True)` before session starts and `notify_session_state(False)` in the session `finally` block. Add 50-100ms delay after stopping wake word stream to allow ALSA to release the device handle. Validate on target Pi hardware in Phase 1 before any UI work.

2. **Self-triggering feedback loop** — if `notify_session_state(False)` is called as soon as the AI session closes but before audio playback finishes, Billy's own voice can re-trigger wake word detection. Prevention: gate the re-enable on `playback_done_event.is_set() AND playback_queue.empty()`. The existing `is_billy_speaking()` check in `button.py` provides this logic but must be wired into the wake word resume path.

3. **Threading deadlock on session lock** — the wake word callback arrives on a daemon thread spawned by `hotword.py`; if it tries to acquire `_session_start_lock` while a concurrent session stop also holds related locks, deadlock is possible. Prevention: the `trigger_session_start(source)` abstraction handles this correctly by using `blocking=False` lock acquisition with the existing recovery logic. The wake word callback must call through this abstraction, never directly into session globals.

4. **Silent Porcupine initialization failure** — invalid access key, wrong-architecture `.ppn` file, or expired free-tier key causes `WakeWordController` to set `enabled=False` silently. Button still works, so users assume the system is fine. Prevention: startup health check, logger-based error reporting (replace `print()` in hotword.py), and a red status badge when `enabled=True` but `running=False` with `last_error` populated.

5. **Blueprint import order initializes controller with empty config** — if Flask app factory imports the wake word blueprint before `load_dotenv()` runs, the module-level `controller = WakeWordController()` reads empty config values. Prevention: ensure `load_dotenv()` runs before any `core` module imports in the app factory; alternatively, lazy-import the controller inside route handlers.

## Implications for Roadmap

Based on research, the architecture and pitfall analysis converge on the same 5-phase build order. The ordering is non-negotiable — hard component dependencies enforce it.

### Phase 1: Session Trigger Abstraction and Core Integration

**Rationale:** Everything depends on this. The `trigger_session_start/stop()` abstraction is the foundation that allows multiple trigger sources to share one session lifecycle safely. Pitfalls 1, 2, and 3 (mic contention, self-triggering, threading deadlock) are all Phase 1 concerns that must be validated before building UI on top of a broken backend.

**Delivers:** Hands-free wake word activation working end-to-end. Both button press and wake word trigger sessions identically. Session ends cleanly without mic contention or self-triggering.

**Addresses:** `trigger_session_start` abstraction, wake word callback wiring, `notify_session_state` on session start/end, playback-complete gate before wake word resume.

**Avoids:** Mic stream contention (Pitfall 1), self-triggering feedback loop (Pitfall 3), threading deadlock (Pitfall 2), sample rate mismatch on target hardware (Pitfall 5 — validate during this phase).

**Must validate on target Pi hardware** — not a concern on developer machines.

### Phase 2: Wake Word Web Routes Blueprint

**Rationale:** Backend integration must be proven before adding a web control layer. The blueprint gives the UI something reliable to talk to. Blueprint import order (Pitfall 6) must be addressed here during registration. The status endpoint is also the primary defense against silent Porcupine failures (Pitfall 4).

**Delivers:** `/wakeword/status`, `/wakeword/events` (SSE), `/wakeword/enable`, `/wakeword/disable`, `/wakeword/configure`, `/wakeword/test` endpoints. Porcupine error states visible via status API.

**Uses:** Native Flask SSE (no new dependencies), `WakeWordController.get_status()`, `get_event_queue()`, `set_parameters()`.

**Implements:** Wake Word Blueprint component; wires into Flask app factory following existing blueprint pattern.

**Avoids:** Silent Porcupine failure (Pitfall 4 — status endpoint exposes error details), blueprint import order bug (Pitfall 6).

### Phase 3: Wake Word UI Panel

**Rationale:** Needs Phase 2 endpoints to exist. The UI is a consumer of the web API layer, not a driver of it. Real-time meter and status badge consume the SSE stream.

**Delivers:** Enable/disable toggle (takes effect immediately via `set_parameters()`), status badge (shows listening/stopped/error states), RMS audio level meter, detection event log panel.

**Implements:** Wake Word UI Panel component (Jinja2 partial + JavaScript IIFE following existing front-end pattern). Uses browser-native `EventSource` API.

**Avoids:** UX pitfall of no visual feedback during calibration, no indication of Porcupine vs. RMS fallback mode.

### Phase 4: Settings Persistence

**Rationale:** Runtime config (`set_parameters()`) works without `.env` write-back, so persistence is non-critical for functionality. Deferring it allows Phase 3 to be validated without the complexity of atomic file writes. Pitfall 7 (`.env` persistence race) is isolated to this phase.

**Delivers:** Wake word settings (enabled, sensitivity, threshold, access key, endpoint) survive reboot. Atomic `.env` write (write-then-rename pattern). Porcupine access key validation before save.

**Avoids:** `.env` persistence race condition (Pitfall 7 — atomic write-then-rename), key truncation on concurrent saves.

### Phase 5: Enhanced UX and Differentiators

**Rationale:** Built on stable Phase 1-4 foundation. These features improve user experience and setup success rate but do not affect core functionality.

**Delivers:** Calibration wizard (guided ambient + voice measurement, auto-threshold suggestion), custom `.ppn` model upload via web UI, animatronic acknowledgment movement pattern on wake word detection.

**Implements:** Calibration wizard (requires real-time meter from Phase 3), custom model upload (independent, simple file save), motor control hook for wake-word acknowledgment.

### Phase Ordering Rationale

- **Phases 1 before 2-5:** No web layer is trustworthy until the backend integration is validated end-to-end on real Pi hardware. Mic contention and self-triggering are non-obvious and will be missed in development environments.
- **Phase 2 before 3:** UI routes require HTTP endpoints to exist; SSE meter requires the SSE endpoint.
- **Phase 4 after 3:** Persistence is additive to a working UI; tackling it before UI is validated adds complexity for no functional gain.
- **Phase 5 last:** Calibration wizard depends on the audio meter (Phase 3); animatronic hook is polish, not foundation.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Mic handoff timing on specific Pi hardware models (Pi 3 vs Pi 4 vs Pi 5 ALSA behavior differences); sample rate support on the specific USB mic in use. Validate `notify_session_state` timing in integration tests.
- **Phase 4:** Atomic `.env` write pattern — verify `os.rename()` is atomic on the target filesystem (ext4 on Pi SD card: yes; exFAT if external drive: no).

Phases with standard patterns (skip deep research):
- **Phase 2:** Flask blueprint registration is a well-established pattern in this codebase; SSE streaming is documented and the pattern is explicit in STACK.md.
- **Phase 3:** Browser `EventSource` API is well-documented and stable; the IIFE JavaScript pattern is already established in the project.
- **Phase 5:** Calibration wizard is a straightforward composition of Phase 3 meter events; custom file upload is a standard Flask route.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct codebase analysis plus official Picovoice and Flask docs; no new dependencies needed |
| Features | HIGH | Features are tightly scoped to existing codebase surface area; minimal speculation required |
| Architecture | HIGH | Based on direct code reading of `core/hotword.py` and `core/button.py`; integration surface is explicit and documented |
| Pitfalls | HIGH | Combination of direct code analysis, documented project history (openWakeWord removal), and Picovoice GitHub issue tracking |

**Overall confidence:** HIGH

### Gaps to Address

- **Pi hardware mic behavior:** ALSA device-release timing after `sd.InputStream.stop()` varies by Pi model and USB hub configuration. The 50-100ms delay recommendation is a heuristic — validate empirically on the actual Pi unit during Phase 1.
- **Porcupine free-tier key lifecycle:** The free tier allows 3 devices with no stated key expiry, but community reports suggest keys can be invalidated. The Phase 2 status endpoint and Phase 3 badge are the mitigation; no architectural change needed.
- **`.ppn` file architecture matching:** The project has a working `.ppn` file for the current Pi. If the Pi is upgraded (e.g., Pi 4 to Pi 5), the keyword file must be regenerated. This is a deployment concern, not a code concern — document it.
- **`button.py` refactoring scope:** The `on_button()` function is described as 200+ lines of interleaved logic. The exact refactoring surface should be scoped carefully in Phase 1 planning to avoid breaking the existing button path.

## Sources

### Primary (HIGH confidence)
- `core/hotword.py` — WakeWordController implementation, integration API surface (direct code analysis)
- `core/button.py` — session lifecycle management, trigger refactoring target (direct code analysis)
- `webconfig/app/__init__.py`, `webconfig/app/routes/` — Flask app factory and blueprint patterns (direct code analysis)
- `core/config.py` — wake word configuration variables and dotenv loading (direct code analysis)
- [Picovoice Porcupine Documentation](https://picovoice.ai/docs/porcupine/) — Python SDK, access key, `.ppn` file requirements
- [pvporcupine on PyPI](https://pypi.org/project/pvporcupine/) — version history, v3 vs v4 differences
- [Flask on PyPI](https://pypi.org/project/Flask/) — 3.1.3 current stable
- [Flask native SSE pattern](https://maxhalford.github.io/blog/flask-sse-no-deps/) — SSE without dependencies

### Secondary (MEDIUM confidence)
- [Porcupine GitHub releases](https://github.com/Picovoice/porcupine/releases) — v4.0 engine change notes; keyword model compatibility not explicitly documented
- [PyAudio/Porcupine stream conflict (GitHub issue #88)](https://github.com/Picovoice/Porcupine/issues/88) — mic contention pattern on Pi
- [Porcupine Input Overflow (GitHub issue #10)](https://github.com/Picovoice/Porcupine/issues/10) — FFT resampling performance on Pi 3
- `.planning/codebase/CONCERNS.md` — documented tech debt (global state in button.py, .env write atomicity)

### Tertiary (LOW confidence)
- [Porcupine Raspberry Pi 5 support (GitHub issue #1183)](https://github.com/Picovoice/porcupine/issues/1183) — Pi 5 `.ppn` compatibility; may require fresh model generation
- [sounddevice + pyaudio conflict on Pi (Raspberry Pi Forums)](https://forums.raspberrypi.com/viewtopic.php?t=280156) — ALSA device release timing heuristics

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
