# Pitfalls Research

**Domain:** Wake word detection reintegration on Raspberry Pi voice assistant (animatronic fish)
**Researched:** 2026-03-24
**Confidence:** HIGH (based on codebase analysis + documented community issues)

## Critical Pitfalls

### Pitfall 1: Microphone Stream Contention Between Wake Word and Session Audio

**What goes wrong:**
The wake word detector (`core/hotword.py`) opens its own `sd.InputStream` on the same USB microphone that `core/audio.py` uses for session recording. On Raspberry Pi, most USB microphones are exclusive-access -- only one stream can hold the device at a time. If the wake word stream is not cleanly stopped before the session opens its own stream, one of them gets `PortAudioError: Device unavailable` or silent frames. Worse, on some ALSA configurations the second open silently succeeds but captures silence.

**Why it happens:**
The WakeWordController uses `notify_session_state(active=True)` to pause listening, but `button.py` currently has no code calling this method. Without explicit session-state notification, both streams race for the hardware device. The existing `_sync_stream_state` logic is correct in isolation -- it closes the stream when `_session_active` is True -- but nobody triggers it.

**How to avoid:**
1. In the session trigger callback (the function wired to `on_detect`), call `controller.notify_session_state(True)` **before** starting the session thread and `controller.notify_session_state(False)` in the session thread's `finally` block (same place `is_active = False` is set).
2. Add a short sleep (50-100ms) after stopping the wake word stream to allow ALSA to release the device handle before the session opens its stream.
3. Verify with `sd.query_devices()` that `MIC_DEVICE_INDEX` matches between both modules -- the wake word controller uses `audio_mod.MIC_DEVICE_INDEX` which could be `None` if `detect_devices()` has not been called yet.

**Warning signs:**
- `PortAudioError` or `OSError: [Errno -9985] Device unavailable` in logs when session starts after wake word trigger.
- Session works fine from button press but silently fails (no mic input) when triggered by wake word.
- Intermittent: works sometimes depending on timing of stream close vs. open.

**Phase to address:**
Phase 1 (Core Integration) -- this is the single most important integration point. Must be validated before any UI work.

---

### Pitfall 2: Threading Deadlock Between Session Lock and Wake Word Callback

**What goes wrong:**
The wake word detection callback (`_dispatch_detection`) spawns a new daemon thread to invoke the callback. If that callback tries to acquire `_session_start_lock` (which it must, to start a session via the same path as `on_button`), and a session stop is concurrently trying to release the lock while also calling `notify_session_state`, the system deadlocks. The `_session_start_lock` in `button.py` is a non-reentrant `threading.Lock()`, and the wake word controller uses a `threading.RLock()` -- mixing lock types across the boundary creates ordering hazards.

**Why it happens:**
`button.py` was written for a single trigger source (hardware button). The lock acquisition, global state mutation (`is_active`, `session_thread`, `session_instance`), and cleanup logic all assume the caller is the button callback on a gpiozero thread. A wake word callback arrives on a different thread with different timing guarantees.

**How to avoid:**
1. Create a `trigger_session_start(source: str)` abstraction in `button.py` that both `on_button` and the wake word callback call. This function should handle lock acquisition identically regardless of source.
2. The wake word callback should NOT directly start a session. It should set a flag or enqueue an event, and the main loop (or a dedicated trigger-dispatch thread) should process it. This serializes all trigger sources.
3. Add timeout to `_session_start_lock.acquire()` in the wake word path (the button path already uses `blocking=False`).

**Warning signs:**
- System freezes after wake word detection -- no response, no logs, button press also stops working.
- Log shows "Session start already in progress" when no session is running.
- The `_force_release_session_start_lock` recovery fires frequently.

**Phase to address:**
Phase 1 (Core Integration) -- the `trigger_session_start/stop` abstraction is a stated project requirement and directly prevents this pitfall.

---

### Pitfall 3: Wake Word Triggers During Audio Playback (Self-Triggering)

**What goes wrong:**
When Billy speaks (plays audio through the speaker), sound leaks back into the microphone. If the wake word stream is still active or restarts too quickly after a session ends, Porcupine can detect the wake word in Billy's own speech, or the RMS fallback triggers on playback volume. This creates a feedback loop: session ends, wake word triggers, new session starts, Billy speaks, wake word triggers again.

**Why it happens:**
The `notify_session_state(False)` call re-enables listening. If called as soon as the AI session closes but before audio playback finishes (the playback worker runs on a separate thread with its own queue), the wake word listener resumes while Billy is still talking. The `is_billy_speaking()` function in `button.py` checks `playback_done_event` and `playback_queue`, but this check is not wired into the wake word resume path.

**How to avoid:**
1. Do not call `notify_session_state(False)` until `playback_done_event.is_set()` AND `playback_queue.empty()`. Wait for audio playback to fully complete.
2. Use the existing 2-second `cooldown_seconds` on the WakeWordController, but verify it is sufficient. With Porcupine (not RMS), the cooldown may need to be longer since Porcupine detections are more reliable and could trigger on echoed wake words.
3. Consider adding a post-session cooldown of 1-2 seconds in the session cleanup before re-enabling wake word detection.

**Warning signs:**
- Billy starts a new session immediately after finishing speaking.
- Rapid session start/stop cycling in logs.
- Problem worsens in quiet rooms with hard surfaces (more echo).

**Phase to address:**
Phase 1 (Core Integration) -- must be handled in the session lifecycle, not deferred to UI tuning.

---

### Pitfall 4: Porcupine Access Key and .ppn File Misconfiguration Silently Disables Wake Word

**What goes wrong:**
When Porcupine initialization fails (invalid access key, missing .ppn file, expired key, wrong architecture .ppn), the WakeWordController catches the exception, sets `self.enabled = False`, and logs a warning -- but there is no persistent UI indicator or startup check that alerts the user. The system appears to work (button still functions) but wake word is silently dead. The user has no way to know until they try to use it.

**Why it happens:**
The `_open_stream` method has a broad `except Exception` that sets `enabled = False` and prints to stdout (not logger). The Picovoice free tier limits custom wake words to 3 per 30-day window, and access keys can expire or hit rate limits. The `.ppn` file must match the Pi's architecture (ARM Cortex-A53 for Pi 3, Cortex-A72 for Pi 4, Cortex-A76 for Pi 5).

**How to avoid:**
1. Add a startup health check that validates: (a) pvporcupine is importable, (b) access key is non-empty, (c) .ppn file exists at `WAKE_WORD_ENDPOINT` path, (d) Porcupine can be instantiated. Report results to the web UI status badge.
2. The wake word web routes blueprint should expose `/wake-word/status` that returns `get_status()` including `last_error`. The UI should show a red badge when `enabled=True` but `running=False` (configured but failed).
3. Log Porcupine initialization failures with `logger.error()`, not `print()`.

**Warning signs:**
- `get_status()` shows `enabled: false` and `last_error` is non-null even though the user thinks wake word is on.
- Works after fresh deploy but stops after key expiry / .ppn regeneration cycle.
- Works on dev machine (x86) but fails on Pi (ARM) due to architecture mismatch in .ppn file.

**Phase to address:**
Phase 2 (Web Routes & Status) -- the status endpoint and UI badge are the primary defense. Phase 1 should add logger-based error reporting.

---

### Pitfall 5: Sample Rate Mismatch Between Microphone and Porcupine Engine

**What goes wrong:**
Porcupine requires exactly 16kHz mono int16 audio. The USB microphone on the Pi might natively support 44.1kHz or 48kHz. The WakeWordController already handles resampling via `scipy.signal.resample`, but this resampling happens in the audio callback (real-time thread). On a Raspberry Pi 3 or Zero, the CPU cost of `resample()` per audio chunk can cause buffer overruns, which sounddevice reports as `InputOverflow` status warnings. Dropped frames mean missed wake words.

**Why it happens:**
`scipy.signal.resample` uses FFT-based resampling which is CPU-intensive. The audio callback runs on a high-priority thread and must complete within the chunk duration (~30ms at default CHUNK_MS). On a Pi 3 (1.2GHz quad-core Cortex-A53), this is tight. The `_process_porcupine` method also accumulates a buffer and processes frames in a while loop, which can compound latency.

**How to avoid:**
1. Force the `sd.InputStream` to open at 16kHz directly if the hardware supports it (most USB mics do). Set `samplerate=16000` explicitly in `_open_stream` rather than using the audio module's detected rate, which may be set for session recording at 24kHz.
2. If 16kHz is not supported, use `scipy.signal.decimate` (integer downsample, much cheaper than `resample`) or a simple averaging decimation for the common 48kHz-to-16kHz (factor of 3) case.
3. Monitor `InputOverflow` events -- the controller already publishes `stream_warning` events for these. If they appear frequently, the resampling is too slow.

**Warning signs:**
- Frequent `[callback flags: input overflow]` in debug logs or `stream_warning` events.
- Wake word detection works on desktop/laptop but misses on Pi.
- High CPU usage (>30% single core) when wake word is listening but idle.

**Phase to address:**
Phase 1 (Core Integration) -- validate audio pipeline performance on target Pi hardware before building UI.

---

### Pitfall 6: Flask Blueprint Registration Order Breaks Wake Word Routes

**What goes wrong:**
The upstream refactor moved to Flask app factory with blueprints. If the wake word blueprint is registered but references the global `controller` singleton from `core/hotword.py` at import time, and the app factory initializes before `core/config.py` loads `.env` values, the controller initializes with default (empty/disabled) config. The blueprint then exposes a controller that can never work because its access key and endpoint were empty at construction time.

**Why it happens:**
`core/hotword.py` line 442 creates `controller = WakeWordController()` at module level. This reads `config.WAKE_WORD_ENABLED`, `config.WAKE_WORD_PORCUPINE_ACCESS_KEY`, etc. at import time. If the Flask app factory imports the wake word routes blueprint, which imports `controller`, and `.env` has not been loaded via `dotenv` yet, all config values are defaults. The controller's `set_parameters()` method can update these later, but only if explicitly called.

**How to avoid:**
1. Ensure `load_dotenv()` runs before any imports of `core` modules. In `main.py` this already happens (lines 11-28 per CONCERNS.md), but the Flask app factory (`webconfig/app/__init__.py`) must also ensure `.env` is loaded before importing blueprints that touch `core`.
2. Alternatively, make the wake word blueprint lazy-load the controller -- import it inside route handlers, not at blueprint module level.
3. Add an assertion in the wake word blueprint registration that verifies `config.WAKE_WORD_PORCUPINE_ACCESS_KEY` is populated when `config.WAKE_WORD_ENABLED` is True.

**Warning signs:**
- Wake word works from `main.py` but not when accessed through the Flask web UI.
- `get_status()` shows `porcupine_access_key_present: false` even though `.env` has the key.
- Different behavior between `python main.py` and `flask run`.

**Phase to address:**
Phase 2 (Web Routes Blueprint) -- must be handled during blueprint creation and registration.

---

### Pitfall 7: .env Persistence Race When Saving Wake Word Settings from Web UI

**What goes wrong:**
The web UI settings form will need to persist wake word config (enabled, sensitivity, threshold, access key, endpoint) back to `.env`. If two settings saves happen in quick succession, or a settings save coincides with the system reading `.env` on startup, the file can be partially written. The existing profile/persona save routes already have this problem (noted in CONCERNS.md: "No Transaction/Atomicity for Profile Switches").

**Why it happens:**
Python's `dotenv` library reads `.env` line by line. If the web route writes the file while another thread reads it, you get partial values. There is no file locking on `.env` writes in the existing codebase. The wake word settings are particularly dangerous because an incomplete `WAKE_WORD_PORCUPINE_ACCESS_KEY` will cause Porcupine initialization to fail with a confusing error.

**How to avoid:**
1. Use atomic file writes: write to `.env.tmp`, then `os.rename('.env.tmp', '.env')`. Rename is atomic on Linux/ext4.
2. After writing, call `controller.set_parameters()` directly rather than relying on a config reload. The controller already supports runtime parameter updates.
3. Add a file lock (e.g., `fcntl.flock`) around `.env` reads and writes if multiple processes or threads access it.

**Warning signs:**
- Garbled or truncated values in `.env` after saving settings.
- Wake word stops working after changing an unrelated setting in the web UI.
- Porcupine initialization error with "invalid access key" when the key was correct.

**Phase to address:**
Phase 3 (Settings Persistence) -- the `.env` write mechanism must be atomic.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `print()` instead of `logger` in hotword.py | Quick debug output | Inconsistent log levels, can't filter wake word logs from UI | Never -- hotword.py uses `print()` in 5 places; should be logger |
| Global `controller` singleton at module level | Simple access from anywhere | Import-order-dependent initialization, hard to test | Acceptable for now, but wrap access in a getter function |
| RMS fallback detection with fixed threshold | Works without Porcupine license | Very high false positive rate in noisy environments; no way to distinguish wake word from cough | Only during development/testing without Porcupine key |
| Bare global state in button.py (`is_active`, `session_thread`, etc.) | Simple state tracking | Race conditions with multiple trigger sources, noted in CONCERNS.md | Never for multi-source triggers -- encapsulate in a class |
| Spawning daemon threads for detection callbacks | Non-blocking callback dispatch | Orphaned threads on shutdown, no backpressure | Acceptable if callbacks are fast and idempotent |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Porcupine + sounddevice | Opening stream at mic's native rate then resampling in callback | Open stream at 16kHz directly; most USB mics support it |
| Wake word + button.py session lifecycle | Calling `on_button()` directly from wake word callback | Create a `trigger_session_start(source)` abstraction; do not simulate button press |
| Wake word + Flask SSE/WebSocket | Polling `event_queue` in a blocking loop inside a Flask route | Use a background thread that drains the queue and pushes to connected SSE clients via `queue.Queue` per client |
| .env persistence + runtime config | Writing .env then restarting the process to pick up changes | Write .env for persistence, then call `controller.set_parameters()` for immediate effect |
| Porcupine .ppn files + git | Committing binary .ppn files to the repo | Add *.ppn to .gitignore; document how to generate/download them; store path in .env |
| gpiozero button + wake word trigger | Assuming `button.is_pressed` check works for non-button triggers | The `is_pressed` check on line 121 of button.py must be skipped or made source-aware for wake word triggers |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| FFT resampling in audio callback | InputOverflow warnings, missed wake words | Use integer decimation or open stream at target rate | Pi 3 and below; Pi 4 handles it |
| Porcupine buffer accumulation | Growing memory, latency spike after silence | Cap buffer size, discard old frames if buffer exceeds 2x frame_length | Long idle periods with background noise |
| Event queue maxsize=256 with no consumer | Queue fills silently, events dropped | Wire up a consumer (SSE endpoint or logger) before enabling wake word | Always, if no consumer is registered |
| DEBUG_MODE logging in audio callback | 4+ print statements per second per callback invocation | Disable DEBUG_MODE in production; use log-level gating | Immediately in production; fills SD card logs |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing Porcupine access key via `/wake-word/status` endpoint | Key leak allows unauthorized Picovoice API usage | Return `porcupine_access_key_present: bool` not the actual key (already done correctly in `get_status()`) |
| Storing access key in .env without file permissions | Any local user can read the key | Set `.env` to 600 permissions; add to deployment docs |
| Wake word calibration endpoint without auth | Anyone on the network can disable/reconfigure wake word | Add basic auth or IP allowlisting to Flask routes (existing pattern if any) |
| .ppn file serving via Flask static | Custom wake word model file accessible to network | Ensure .ppn files are outside `webconfig/static/`; do not serve via Flask |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visual/audio feedback when wake word is detected | User says wake word, nothing happens for 1-2 seconds, says it again causing double trigger | Play a brief acknowledgment sound (like Alexa's "bloop") immediately on detection, before session starts |
| Calibration wizard requires knowledge of RMS values | Non-technical user cannot set sensitivity | Provide a "speak now" calibration mode that auto-sets threshold based on measured ambient + voice levels |
| Wake word toggle in settings requires page reload to take effect | User enables wake word, nothing happens until they figure out to reload | Use the `set_parameters()` API for immediate effect; update UI state via SSE |
| No indication whether Porcupine or RMS fallback is active | User thinks they have keyword detection but they have amplitude detection | Show detector mode ("Porcupine" vs "Volume Fallback") prominently in the UI status badge |

## "Looks Done But Isn't" Checklist

- [ ] **Wake word triggers session:** Often missing `notify_session_state()` call -- verify wake word stream actually stops before session mic opens
- [ ] **Settings persistence:** Often missing atomic write -- verify .env survives power loss during save (write-then-rename)
- [ ] **Blueprint registration:** Often missing import-order guard -- verify wake word controller reads correct config when imported by Flask app factory
- [ ] **UI status badge:** Often missing error state display -- verify badge shows red when `enabled=true` but `running=false` with `last_error` populated
- [ ] **Session end cleanup:** Often missing playback-complete wait -- verify wake word does not re-enable until `playback_done_event.is_set()`
- [ ] **Mock mode:** Often missing wake word in mock -- verify wake word can be tested without GPIO (MOCKFISH mode should still allow wake word testing)
- [ ] **Button.is_pressed guard:** Often blocks wake word triggers -- verify `on_button()` or replacement does not check `button.is_pressed` when source is wake word

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Mic stream contention | LOW | Stop session, call `controller.stop()` then `controller.start()` to reset stream state |
| Session lock deadlock | MEDIUM | Call `_force_release_session_start_lock()` -- already exists. Add watchdog timer to auto-release after 30s |
| Self-triggering loop | LOW | `controller.disable()` stops the loop immediately. Increase cooldown_seconds. Add max-retrigger-count within time window |
| Porcupine key expiration | MEDIUM | System falls back to no wake word (button still works). User must regenerate key at console.picovoice.ai and update .env |
| .env corruption | MEDIUM | Restore from `.env.backup` (create backup before every write). Re-run settings wizard |
| Sample rate mismatch | LOW | Change `_open_stream` to force 16kHz. Restart wake word service |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Mic stream contention | Phase 1 (Core Integration) | End-to-end test: wake word triggers session, mic captures audio, session ends cleanly |
| Threading deadlock | Phase 1 (Core Integration) | Stress test: rapid wake word detections during session start/stop |
| Self-triggering | Phase 1 (Core Integration) | Test: session ends with playback, wake word does not re-trigger within 3 seconds |
| Silent Porcupine failure | Phase 2 (Web Routes & Status) | Status endpoint returns error details; UI shows failure state |
| Sample rate mismatch | Phase 1 (Core Integration) | Verify on target Pi hardware; check for InputOverflow in logs |
| Blueprint import order | Phase 2 (Web Routes Blueprint) | Test: `flask run` initializes wake word with correct access key |
| .env persistence race | Phase 3 (Settings & Persistence) | Test: save settings from two browser tabs simultaneously; verify .env integrity |

## Sources

- Codebase analysis: `core/hotword.py`, `core/button.py`, `core/audio.py`, `core/config.py` (direct code review)
- `.planning/codebase/CONCERNS.md` (documented tech debt and fragile areas)
- [Picovoice Porcupine Documentation](https://picovoice.ai/docs/porcupine/)
- [Porcupine Raspberry Pi Quick Start](https://picovoice.ai/docs/quick-start/porcupine-raspberrypi/)
- [Picovoice Free Tier Announcement](https://picovoice.ai/blog/introducing-picovoices-free-tier/)
- [PyAudio/Porcupine stream conflict (GitHub issue #88)](https://github.com/Picovoice/Porcupine/issues/88)
- [Porcupine Input Overflow (GitHub issue #10)](https://github.com/Picovoice/Porcupine/issues/10)
- [Porcupine Raspberry Pi 5 support (GitHub issue #1183)](https://github.com/Picovoice/porcupine/issues/1183)
- [sounddevice + pyaudio conflict on Pi (Raspberry Pi Forums)](https://forums.raspberrypi.com/viewtopic.php?t=280156)
- [Porcupine systemd service issues (Raspberry Pi Forums)](https://forums.raspberrypi.com/viewtopic.php?t=388995)
- [Home Assistant wake word architecture](https://www.home-assistant.io/voice_control/about_wake_word/)

---
*Pitfalls research for: Wake word reintegration on Raspberry Pi voice assistant*
*Researched: 2026-03-24*
