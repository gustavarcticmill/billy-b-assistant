# Phase 1: Core Integration - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire wake word detection into the session lifecycle so saying the wake word triggers a conversation session identically to a button press. Harden session resilience (playback_done_event, dead websocket detection, double-stop prevention), Home Assistant resilience (timeout, availability caching), and config validation. Fix any merge breakages discovered during integration.

</domain>

<decisions>
## Implementation Decisions

### Trigger refactoring
- **D-01:** Create a dedicated trigger module (`core/trigger.py`) with `trigger_session_start(source)` and `trigger_session_stop(source)` as the session lifecycle abstraction. Both `on_button()` in button.py and the wake word detection callback import from this module.
- **D-02:** Wake word initialization and callback wiring happens in `start_loop()` after `audio.detect_devices()`. The detection callback calls `trigger_session_start("wake_word")`.
- **D-03:** `button.is_pressed` guard only applies to the hardware source. Wake word and ui-test sources skip it entirely (WAKE-07).
- **D-04:** Global debounce — any trigger source resets a single 0.5s debounce timer. A wake word detection within 0.5s of a button press (or vice versa) is ignored.

### Mic handoff timing
- **D-05:** Call `notify_session_state(True)` to close the wake word stream, then wait a short configurable delay (~50-100ms) before the session opens its mic. Handles ALSA release timing on Pi.
- **D-06:** Immediate resume — call `notify_session_state(False)` in the session finally block right away. Rely on the controller's built-in 2.0s `cooldown_seconds` to prevent self-triggering from Billy's own audio.
- **D-07:** If the wake word stream fails to reopen after a session, log a warning, wait 500ms, retry once. If still fails, disable wake word and log error. Button press continues to work.

### Config validation
- **D-08:** Validation happens in `config.py` at load time using range-checked helpers (extend `_float_env` and add `_int_env` with min/max parameters). Catches issues at startup.
- **D-09:** Validate only the values listed in CONF-01: MIC_TIMEOUT_SECONDS (1-300), FLASK_PORT (1-65535), thresholds non-negative, WAKE_WORD_SENSITIVITY (0.0-1.0), CHUNK_MS (10-200). Invalid values log a warning and fall back to defaults.

### Merge breakage handling
- **D-10:** Fix-as-found during integration — catalogue breakages as they're encountered while wiring up wake word and implementing resilience fixes.
- **D-11:** Fix everything found regardless of whether it's strictly in Phase 1 scope. Quick fixes and larger issues both get resolved immediately to ensure a working state.

### Claude's Discretion
- Exact structure of `core/trigger.py` internals (class vs functions, lock strategy)
- The precise ALSA delay value within the 50-100ms range
- Session resilience fix implementations (SRES-01, SRES-02, SRES-03) — the requirements are specific enough
- HA resilience implementations (HARE-01, HARE-02) — timeout value and caching TTL
- Wake-up sound playback integration with wake word trigger (same as button per WAKE-06)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/REQUIREMENTS.md` — WAKE-01 through WAKE-09 (wake word integration), SRES-01 through SRES-03 (session resilience), HARE-01/HARE-02 (HA resilience), CONF-01/CONF-02 (config validation), FIX-01 (merge breakages)
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, dependency chain
- `.planning/PROJECT.md` — Constraints: don't modify hotword.py, preserve upstream architecture, follow existing patterns

### Known issues
- `.planning/codebase/CONCERNS.md` — Session shutdown race conditions (partially fixed), gpiozero button hold thread race, bare global state management

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/hotword.py` — Full `WakeWordController` with `notify_session_state()`, `set_detection_callback()`, `get_status()`, `set_parameters()`, event queue. Module-level singleton `controller` already instantiated.
- `core/config.py` — All wake word config vars already present (WAKE_WORD_ENABLED, SENSITIVITY, THRESHOLD, ENDPOINT, ACCESS_KEY). `_float_env()` helper exists for type-safe float loading.
- `core/audio.py` — `playback_done_event` (threading.Event), `play_random_wake_up_clip()`, `ensure_playback_worker_started()`, `stop_playback()`.

### Established Patterns
- Thread-based session management: `on_button()` spawns a daemon thread running `asyncio.run(session_instance.start())`
- Lock-based concurrency: `_session_start_lock` prevents concurrent session starts
- Mock support: `MockButton` class for non-hardware environments
- Global state: `is_active`, `session_thread`, `interrupt_event`, `session_instance` module-level variables in button.py

### Integration Points
- `button.py:start_loop()` — Where wake word init and callback wiring will go (after audio.detect_devices)
- `button.py:on_button()` — Logic to extract into trigger module
- `button.py:run_session()` finally block — Where `notify_session_state(False)` will go for mic resume
- `hotword.controller` — Module-level singleton to wire detection callback onto
- `audio.play_random_wake_up_clip()` — SRES-01 fix target (must set playback_done_event even when no clips found)
- `ha.send_conversation_prompt()` — HARE-01 fix target (needs explicit timeout)
- `ha.ha_available()` — HARE-02 fix target (needs cached availability with TTL)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-core-integration*
*Context gathered: 2026-03-23*
