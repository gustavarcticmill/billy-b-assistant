# Phase 1: Core Integration - Research

**Researched:** 2026-03-23
**Domain:** Wake word integration, session lifecycle management, threading/concurrency, config validation, HA resilience
**Confidence:** HIGH

## Summary

Phase 1 wires the existing `core/hotword.py` WakeWordController into the session lifecycle so that saying the wake word triggers a conversation session identically to a hardware button press. The hotword module is already fully implemented with Porcupine support, event queue, session state notifications, and a detection callback mechanism -- it simply has no consumer wired up. The work is primarily integration plumbing: extracting the session-start/stop logic from button.py into a shared trigger module, wiring the hotword controller's detection callback, managing mic handoff (ALSA exclusive access between hotword stream and session mic stream), and adding defensive fixes for session resilience, HA timeouts, and config validation.

The codebase is a mature Python 3.11 application using threading for concurrency (daemon threads for sessions, MQTT, motor watchdog) with asyncio event loops inside session threads. The hotword controller runs its own `sd.InputStream` on the main thread's context, while sessions run `sd.InputStream` via MicManager in a session-spawned daemon thread. The core challenge is ALSA device exclusivity on Raspberry Pi: only one process/stream can hold the mic at a time, requiring careful close-then-open sequencing with timing delays.

**Primary recommendation:** Create `core/trigger.py` as the single entry point for session start/stop from any source (hardware, wake_word, ui-test). Extract the session-start logic from `button.py:on_button()` into this module, keeping button.py as a thin delegation layer. Wire `hotword.controller.set_detection_callback()` in `start_loop()` after `audio.detect_devices()`. Use `notify_session_state(True/False)` for mic handoff with a configurable delay (75ms default) before session mic opens.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Create a dedicated trigger module (`core/trigger.py`) with `trigger_session_start(source)` and `trigger_session_stop(source)` as the session lifecycle abstraction. Both `on_button()` in button.py and the wake word detection callback import from this module.
- **D-02:** Wake word initialization and callback wiring happens in `start_loop()` after `audio.detect_devices()`. The detection callback calls `trigger_session_start("wake_word")`.
- **D-03:** `button.is_pressed` guard only applies to the hardware source. Wake word and ui-test sources skip it entirely (WAKE-07).
- **D-04:** Global debounce -- any trigger source resets a single 0.5s debounce timer. A wake word detection within 0.5s of a button press (or vice versa) is ignored.
- **D-05:** Call `notify_session_state(True)` to close the wake word stream, then wait a short configurable delay (~50-100ms) before the session opens its mic. Handles ALSA release timing on Pi.
- **D-06:** Immediate resume -- call `notify_session_state(False)` in the session finally block right away. Rely on the controller's built-in 2.0s `cooldown_seconds` to prevent self-triggering from Billy's own audio.
- **D-07:** If the wake word stream fails to reopen after a session, log a warning, wait 500ms, retry once. If still fails, disable wake word and log error. Button press continues to work.
- **D-08:** Validation happens in `config.py` at load time using range-checked helpers (extend `_float_env` and add `_int_env` with min/max parameters). Catches issues at startup.
- **D-09:** Validate only the values listed in CONF-01: MIC_TIMEOUT_SECONDS (1-300), FLASK_PORT (1-65535), thresholds non-negative, WAKE_WORD_SENSITIVITY (0.0-1.0), CHUNK_MS (10-200). Invalid values log a warning and fall back to defaults.
- **D-10:** Fix-as-found during integration -- catalogue breakages as they're encountered while wiring up wake word and implementing resilience fixes.
- **D-11:** Fix everything found regardless of whether it's strictly in Phase 1 scope. Quick fixes and larger issues both get resolved immediately to ensure a working state.

### Claude's Discretion
- Exact structure of `core/trigger.py` internals (class vs functions, lock strategy)
- The precise ALSA delay value within the 50-100ms range
- Session resilience fix implementations (SRES-01, SRES-02, SRES-03) -- the requirements are specific enough
- HA resilience implementations (HARE-01, HARE-02) -- timeout value and caching TTL
- Wake-up sound playback integration with wake word trigger (same as button per WAKE-06)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WAKE-01 | Wake word detection triggers a conversation session identically to a button press | trigger.py module with `trigger_session_start("wake_word")` calling same session-start logic as button; hotword controller already has callback dispatch via `_dispatch_detection()` |
| WAKE-02 | `trigger_session_stop(source)` cleanly stops sessions from any source | Extract stop logic from button.py lines 124-187 into trigger.py; handle asyncio cross-thread coordination |
| WAKE-03 | `on_button()` delegates to `trigger_session_start("hardware")` and `trigger_session_stop("hardware")` | Refactor button.py to thin wrapper; keep MockButton and gpiozero-specific code in button.py |
| WAKE-04 | Wake word controller receives `notify_session_state(True/False)` on session start and end | hotword.py line 93-96 already implements this; call in trigger_session_start and session finally block |
| WAKE-05 | Wake word controller is initialized in `start_loop()` with config parameters and detection callback | hotword.controller singleton exists (line 442); call `set_detection_callback()` and `start()` in start_loop after detect_devices |
| WAKE-06 | Audio feedback (wake-up sound) plays when wake word is detected, same as button press | Reuse `audio.play_random_wake_up_clip()` in trigger_session_start regardless of source |
| WAKE-07 | `button.is_pressed` guard does not block wake-word-sourced triggers | D-03 decision: guard only applies to source="hardware"; trigger.py checks source before applying guard |
| WAKE-08 | Debounce logic works per-source (0.5s) preventing duplicate triggers | D-04 decision: single global debounce timer, 0.5s, any source resets it |
| WAKE-09 | Session cleanup/finally block calls `notify_session_state(False)` to re-enable wake word listening | Add to run_session() finally block in trigger.py; D-06: rely on controller's 2.0s cooldown for self-trigger prevention |
| SRES-01 | `play_random_wake_up_clip()` sets `playback_done_event` even when no clips found | audio.py line 387-389: currently returns None without setting event; add `playback_done_event.set()` before return |
| SRES-02 | Dead websocket detected after repeated send timeouts, triggers session teardown | Add timeout tracking in `_ws_send_json`; after N consecutive timeouts, call stop_session |
| SRES-03 | Mic timeout checker verifies session isn't already stopping before calling `stop_session()` | mic_manager_wrapper.py line 205: check `session._stopping` before calling `stop_session()` |
| HARE-01 | `send_conversation_prompt()` has explicit timeout (5 seconds) | ha.py: add `timeout=aiohttp.ClientTimeout(total=5)` to ClientSession constructor |
| HARE-02 | HA availability cached with TTL -- fail fast if HA known down | Add module-level cache dict with timestamp; skip API call if last failure within TTL |
| CONF-01 | Numeric config values validated for sane ranges | Extend config.py with `_int_env(key, default, min_val, max_val)` helper; apply to listed values |
| CONF-02 | Invalid config values log warning and fall back to defaults | `_float_env` already does this for floats; extend pattern to int and range-checked variants |
| FIX-01 | Investigate and fix merge breakages discovered during integration | Fix-as-found per D-10/D-11; document in plan verification |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pvporcupine | latest (in requirements.txt) | Wake word detection engine | Already chosen by project; Porcupine is the industry standard on-device wake word engine for Pi |
| sounddevice | latest | Audio I/O streams for mic and playback | Already in use throughout audio.py, mic.py, hotword.py |
| threading | stdlib | Daemon threads for sessions, locks for concurrency | Project pattern; asyncio used inside session threads |
| asyncio | stdlib | Event loop inside session threads | Project pattern for websocket-based AI provider communication |
| aiohttp | latest | Async HTTP client for HA API | Already in use in ha.py |
| gpiozero | 2.0.1 | GPIO button control | Installed and in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| time (stdlib) | - | Debounce timers, cooldown tracking | Global debounce in trigger.py |
| contextlib (stdlib) | - | `suppress(Exception)` for graceful cleanup | Session stop error handling |

### Alternatives Considered
None -- all decisions are locked. No new libraries needed; this phase uses only what's already in the project.

## Architecture Patterns

### Recommended Project Structure Changes
```
core/
├── trigger.py          # NEW: session lifecycle abstraction (start/stop from any source)
├── button.py           # MODIFIED: thin wrapper delegating to trigger.py
├── hotword.py          # UNCHANGED: wake word controller (must not modify)
├── config.py           # MODIFIED: add _int_env, range validation
├── audio.py            # MODIFIED: SRES-01 fix in play_random_wake_up_clip
├── ha.py               # MODIFIED: HARE-01/HARE-02 timeout and caching
├── session_manager.py  # MODIFIED: SRES-02 dead websocket detection
├── session/
│   └── mic_manager_wrapper.py  # MODIFIED: SRES-03 double-stop prevention
└── mic.py              # UNCHANGED
```

### Pattern 1: Trigger Abstraction Module
**What:** `core/trigger.py` provides `trigger_session_start(source: str)` and `trigger_session_stop(source: str)` as the single entry point for session lifecycle from any input source.
**When to use:** Any code that needs to start or stop a conversation session.
**Key design considerations:**
- Module-level globals for session state (mirrors current button.py pattern: `is_active`, `session_thread`, `interrupt_event`, `session_instance`, `_session_start_lock`)
- These globals move FROM button.py TO trigger.py
- button.py imports from trigger.py and becomes a thin wrapper
- The detection callback from hotword.py calls trigger.py directly
- Source parameter ("hardware", "wake_word", "ui-test") controls which guards apply

```python
# core/trigger.py - Skeleton structure
import asyncio
import contextlib
import threading
import time

from . import audio, config
from .logger import logger
from .movements import move_head
from .session_manager import BillySession

# Session globals (moved from button.py)
is_active = False
session_thread = None
interrupt_event = threading.Event()
session_instance: BillySession | None = None
_session_start_lock = threading.Lock()

# Global debounce (D-04)
_last_trigger_time = 0.0
_DEBOUNCE_SECONDS = 0.5

# ALSA handoff delay (D-05)
_MIC_HANDOFF_DELAY = 0.075  # 75ms, tunable within 50-100ms

def trigger_session_start(source: str) -> None:
    """Start a conversation session from any trigger source."""
    global is_active, session_thread, interrupt_event, session_instance
    global _last_trigger_time

    now = time.time()
    # D-04: Global debounce
    if now - _last_trigger_time < _DEBOUNCE_SECONDS:
        return
    _last_trigger_time = now

    # D-03: is_pressed guard only for hardware
    if source == "hardware":
        from . import button as _button_mod
        if not _button_mod.button.is_pressed:
            return

    # ... session start logic extracted from button.py on_button() ...

def trigger_session_stop(source: str) -> None:
    """Stop the current session from any trigger source."""
    # ... session stop logic extracted from button.py on_button() ...
```

### Pattern 2: Hotword Callback Wiring
**What:** In `start_loop()`, after `audio.detect_devices()`, initialize and wire the hotword controller.
**When to use:** Application startup only.

```python
# In button.py start_loop(), after audio.detect_devices():
from .hotword import controller as wake_word_controller

def _on_wake_word_detected(payload: dict) -> None:
    """Callback invoked by hotword controller on wake word detection."""
    logger.info(f"Wake word detected: {payload}", "🗣️")
    trigger_session_start("wake_word")

if config.WAKE_WORD_ENABLED:
    wake_word_controller.set_detection_callback(_on_wake_word_detected)
    wake_word_controller.start()
    logger.info("Wake word detection enabled and started", "👂")
```

### Pattern 3: Mic Handoff Sequence
**What:** Close hotword stream before session mic opens; resume after session ends.
**When to use:** Every session start/stop when wake word is enabled.

```
Session Start:
1. notify_session_state(True)     → hotword closes its sd.InputStream
2. time.sleep(0.075)              → ALSA releases device (D-05: 50-100ms)
3. Session thread spawns           → MicManager opens sd.InputStream
4. Session runs normally

Session End (finally block):
1. MicManager.stop()              → session's sd.InputStream closed
2. notify_session_state(False)    → hotword's _sync_stream_state() reopens
3. Controller's 2.0s cooldown     → prevents self-trigger from Billy's audio (D-06)
```

### Pattern 4: Config Validation at Load Time
**What:** Range-checked environment variable loading with warning + fallback.
**When to use:** All numeric config values listed in CONF-01.

```python
def _int_env(key: str, default: str, *, min_val: int | None = None, max_val: int | None = None) -> int:
    """Load integer env var with range validation."""
    value = os.getenv(key)
    if value is None:
        return int(default)
    try:
        result = int(value)
    except (TypeError, ValueError):
        logger.warning(f"Invalid integer for {key}={value!r}, falling back to {default}")
        return int(default)
    if min_val is not None and result < min_val:
        logger.warning(f"{key}={result} below minimum {min_val}, falling back to {default}")
        return int(default)
    if max_val is not None and result > max_val:
        logger.warning(f"{key}={result} above maximum {max_val}, falling back to {default}")
        return int(default)
    return result
```

### Anti-Patterns to Avoid
- **Modifying hotword.py:** The controller module must not be changed (project constraint). All integration happens through its public API: `set_detection_callback()`, `start()`, `stop()`, `notify_session_state()`, `get_status()`, `set_parameters()`.
- **Circular imports between trigger.py and button.py:** button.py imports from trigger.py, not the reverse. trigger.py should not import button.py at module level (use lazy imports inside functions if needed, e.g., for `button.is_pressed` check).
- **Holding the session start lock during ALSA delay:** The 75ms sleep for ALSA handoff should happen BEFORE acquiring `_session_start_lock`, not while holding it. Otherwise the lock blocks other triggers unnecessarily.
- **Using print() instead of logger:** Per project convention, all new code uses the `logger` singleton. Exception: hotword.py uses print() internally but that module is not being modified.
- **Blocking the hotword callback thread:** The hotword controller dispatches detection callbacks on a new daemon thread (hotword.py line 404-408). The callback must not block -- it should do minimal work and spawn the session thread quickly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wake word detection | Custom audio threshold detection | pvporcupine via existing hotword.py | Porcupine handles noise rejection, keyword matching, false positive reduction |
| Audio stream management | Custom ALSA bindings | sounddevice (already used) | Handles PortAudio/ALSA abstraction, device enumeration, stream lifecycle |
| Session start/stop concurrency | Ad-hoc flag checks | threading.Lock (existing `_session_start_lock`) | Prevents race conditions on concurrent trigger events |
| Debounce timing | Custom timer classes | Simple `time.time()` comparison | 0.5s debounce is a single float comparison, no need for timer objects |
| HA availability caching | Complex cache framework | Module-level dict with timestamp | Only one value to cache; stdlib time.time() comparison is sufficient |

**Key insight:** This phase is integration plumbing, not new feature development. Every component already exists -- the hotword controller, session management, audio streams, config loading. The work is wiring them together safely.

## Common Pitfalls

### Pitfall 1: ALSA Exclusive Access on Raspberry Pi
**What goes wrong:** Two `sd.InputStream` objects try to open the same ALSA device simultaneously, causing "Device or resource busy" errors.
**Why it happens:** The hotword controller's mic stream and the session's MicManager both target the same mic device. ALSA on Pi doesn't support concurrent access to the same capture device.
**How to avoid:** Always call `notify_session_state(True)` to close the hotword stream BEFORE the session's MicManager opens its stream. Add a configurable delay (75ms) between close and open to allow ALSA to fully release the device.
**Warning signs:** "Device unavailable", "PaErrorCode -9985", or "Device or resource busy" errors in logs during session start.

### Pitfall 2: Self-Triggering on Billy's Own Audio
**What goes wrong:** After a session ends and the hotword stream reopens, Billy's own wake-up sound or trailing audio triggers another wake word detection.
**Why it happens:** The speaker output bleeds into the microphone (no echo cancellation on Pi hardware). The hotword stream reopens while audio is still playing back.
**How to avoid:** D-06: Rely on the hotword controller's built-in `cooldown_seconds = 2.0` (hotword.py line 43). After `notify_session_state(False)` is called, the controller won't fire another detection for 2 seconds. This exceeds typical audio bleed duration.
**Warning signs:** Rapid session start-stop cycling after a session ends; logs showing "detected" events immediately after session cleanup.

### Pitfall 3: Deadlock on playback_done_event When No Clips Found
**What goes wrong:** `play_random_wake_up_clip()` returns None without setting `playback_done_event`. The session's `run_stream()` method (session_manager.py line 727-728) waits on `playback_done_event.wait()` forever, deadlocking the session.
**Why it happens:** audio.py lines 387-389: when no clips are found, the function returns early without calling `playback_done_event.set()`.
**How to avoid:** SRES-01: Add `playback_done_event.set()` before the `return None` on line 389.
**Warning signs:** Session hangs after button press or wake word detection; no mic input ever starts; "Mic waiting for wake-up sound to finish" logged but never resolved.

### Pitfall 4: Circular Import Between trigger.py and button.py
**What goes wrong:** trigger.py imports button.py (for `button.is_pressed` check) and button.py imports trigger.py (for delegation), causing ImportError.
**Why it happens:** Python's circular import resolution fails when both modules need each other at module level.
**How to avoid:** trigger.py should use a lazy/deferred import for `button.is_pressed` -- import inside the function body, not at module top. Alternatively, pass the is_pressed check as a callback during initialization rather than importing the module.
**Warning signs:** ImportError on application startup.

### Pitfall 5: Session Start Lock Not Released on Exception
**What goes wrong:** `_session_start_lock` remains acquired after an exception during session setup, blocking all future session starts.
**Why it happens:** button.py has complex exception handling (lines 232-304) with multiple paths where the lock might not be released.
**How to avoid:** Use try/finally consistently. The lock should be released either by the session thread's finally block (normal path) or by the exception handler in the setup code. The existing `_force_release_session_start_lock()` is a safety net but should not be relied on as primary mechanism.
**Warning signs:** "Session start already in progress" warnings when no session is active; "Session start lock busy while inactive; attempting recovery" log messages.

### Pitfall 6: Dead WebSocket Silent Failure
**What goes wrong:** The AI provider's websocket connection dies silently (network issue, server timeout), but the session keeps running with a dead connection. Mic audio is sent but never processed; no responses come back.
**Why it happens:** `_ws_send_json` catches TimeoutError and logs a warning but doesn't escalate. The session has no heartbeat mechanism.
**How to avoid:** SRES-02: Track consecutive send timeouts. After a threshold (e.g., 3 consecutive timeouts), trigger session teardown rather than continuing silently.
**Warning signs:** "Timed out acquiring ws_lock for send; dropping payload" appearing repeatedly in logs.

### Pitfall 7: Double-Stop Race Condition
**What goes wrong:** The mic timeout checker calls `stop_session()` at the same moment the button handler or websocket close triggers a stop, causing duplicate cleanup and potential crashes.
**Why it happens:** mic_manager_wrapper.py `timeout_checker()` (line 200-205) doesn't check if a stop is already in progress.
**How to avoid:** SRES-03: Check `session._stopping` before calling `stop_session()` in the timeout checker.
**Warning signs:** "Stopping session..." appearing twice in rapid succession in logs; RuntimeError from trying to release an already-released lock.

## Code Examples

### Example 1: trigger_session_start Core Logic
```python
# Source: Extracted from button.py on_button() lines 232-298
# Modified for multi-source support

def trigger_session_start(source: str) -> None:
    global is_active, session_thread, interrupt_event, session_instance
    global _last_trigger_time

    now = time.time()
    if now - _last_trigger_time < _DEBOUNCE_SECONDS:
        return
    _last_trigger_time = now

    # D-03: is_pressed guard only for hardware
    if source == "hardware":
        # Lazy import to avoid circular dependency
        from . import button as _btn
        if not _btn.button.is_pressed:
            return

    if is_active:
        # Delegate to stop logic (same as button press during active session)
        trigger_session_stop(source)
        return

    if not _session_start_lock.acquire(blocking=False):
        # ... recovery logic (same as current button.py) ...
        return

    try:
        # D-05: Notify hotword controller to release mic
        from .hotword import controller as _hw
        _hw.notify_session_state(True)
        time.sleep(_MIC_HANDOFF_DELAY)

        # ... previous session cleanup ...

        audio.ensure_playback_worker_started(config.CHUNK_MS)
        audio.playback_done_event.clear()
        threading.Thread(target=audio.play_random_wake_up_clip, daemon=True).start()
        is_active = True
        interrupt_event = threading.Event()
        logger.info(f"Session triggered by {source}. Listening...", "🎤")

        def run_session():
            global session_instance, is_active
            try:
                session_instance = BillySession(interrupt_event=interrupt_event)
                session_instance.last_activity[0] = time.time()
                asyncio.run(session_instance.start())
            except Exception as e:
                logger.error(f"Session error: {e}")
            finally:
                move_head("off")
                is_active = False
                session_instance = None
                # D-06: Resume wake word listening
                _hw.notify_session_state(False)
                logger.info("Waiting for trigger...", "🕐")
                with contextlib.suppress(Exception):
                    _session_start_lock.release()

        session_thread = threading.Thread(target=run_session, daemon=True)
        session_thread.start()
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        with contextlib.suppress(Exception):
            _session_start_lock.release()
```

### Example 2: SRES-01 Fix -- playback_done_event on No Clips
```python
# Source: audio.py play_random_wake_up_clip() -- fix for line 389
# Before:
#     if not clips:
#         print("...")
#         return None
# After:
    if not clips:
        logger.warning("No wake-up clips found in any directory.", "⚠️")
        playback_done_event.set()  # SRES-01: prevent mic start deadlock
        return None
```

### Example 3: HARE-01 -- HA Timeout
```python
# Source: ha.py send_conversation_prompt() -- add explicit timeout
async def send_conversation_prompt(prompt: str) -> str | None:
    if not ha_available():
        logger.warning("Home Assistant not configured.", "⚠️")
        return None

    url = f"{HA_HOST.rstrip('/')}/api/conversation/process"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"text": prompt, "language": HA_LANG}

    try:
        timeout = aiohttp.ClientTimeout(total=5)  # HARE-01: 5s timeout
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(url, headers=headers, json=payload) as resp,
        ):
            if resp.status == 200:
                data = await resp.json()
                return data.get("response", "")
            logger.warning(f"HA API returned HTTP {resp.status}", "⚠️")
            return None
    except asyncio.TimeoutError:
        logger.warning("HA conversation prompt timed out (5s)", "⏱️")
        _mark_ha_unavailable()
        return None
    except Exception as e:
        logger.error(f"Error reaching Home Assistant API: {e}", "❌")
        _mark_ha_unavailable()
        return None
```

### Example 4: HARE-02 -- HA Availability Cache
```python
# Source: ha.py -- add cached availability check
import time as _time

_ha_unavailable_until: float = 0.0
_HA_CACHE_TTL: float = 30.0  # seconds

def _mark_ha_unavailable() -> None:
    global _ha_unavailable_until
    _ha_unavailable_until = _time.time() + _HA_CACHE_TTL

def ha_available() -> bool:
    if not (HA_HOST and HA_TOKEN):
        return False
    if _time.time() < _ha_unavailable_until:
        return False
    return True
```

### Example 5: CONF-01/CONF-02 -- Range-Checked Config Helpers
```python
# Source: config.py -- extend validation helpers
def _int_env(
    key: str,
    default: str,
    *,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Load integer from environment with optional range validation."""
    value = os.getenv(key)
    if value is None:
        return int(default)
    try:
        result = int(value)
    except (TypeError, ValueError):
        print(
            f"⚠️ Invalid integer for {key}={value!r}, falling back to {default}",
            flush=True,
        )
        return int(default)
    if min_val is not None and result < min_val:
        print(
            f"⚠️ {key}={result} below minimum {min_val}, falling back to {default}",
            flush=True,
        )
        return int(default)
    if max_val is not None and result > max_val:
        print(
            f"⚠️ {key}={result} above maximum {max_val}, falling back to {default}",
            flush=True,
        )
        return int(default)
    return result


def _float_env_ranged(
    key: str,
    default: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
) -> float:
    """Load float from environment with optional range validation."""
    result = _float_env(key, default)
    default_val = float(default)
    if min_val is not None and result < min_val:
        print(
            f"⚠️ {key}={result} below minimum {min_val}, falling back to {default}",
            flush=True,
        )
        return default_val
    if max_val is not None and result > max_val:
        print(
            f"⚠️ {key}={result} above maximum {max_val}, falling back to {default}",
            flush=True,
        )
        return default_val
    return result

# Usage:
MIC_TIMEOUT_SECONDS = _int_env("MIC_TIMEOUT_SECONDS", "5", min_val=1, max_val=300)
FLASK_PORT = _int_env("FLASK_PORT", "80", min_val=1, max_val=65535)
CHUNK_MS = _int_env("CHUNK_MS", "40", min_val=10, max_val=200)
SILENCE_THRESHOLD = _float_env_ranged("SILENCE_THRESHOLD", "1000", min_val=0.0)
WAKE_WORD_SENSITIVITY = _float_env_ranged("WAKE_WORD_SENSITIVITY", "0.5", min_val=0.0, max_val=1.0)
WAKE_WORD_THRESHOLD = _float_env_ranged("WAKE_WORD_THRESHOLD", "2400", min_val=0.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Button-only session trigger (monolithic on_button) | Multi-source trigger abstraction (trigger.py) | This phase | Enables wake word, UI-test, future MQTT session triggers |
| No config validation | Range-checked env helpers with fallback | This phase | Prevents silent misconfiguration at startup |
| HA calls with no timeout | 5s timeout + availability cache | This phase | Prevents session hangs when HA is down |
| playback_done_event not set on empty clips | Always set on all paths | This phase | Prevents mic start deadlock |

## Open Questions

1. **Exact ALSA release timing on target Pi hardware**
   - What we know: ALSA typically releases within 10-50ms on Pi 4/5. The 50-100ms range from D-05 is conservative.
   - What's unclear: The exact hardware model and USB audio adapter in use may affect timing.
   - Recommendation: Default to 75ms. If issues occur, the value should be configurable via an env var (e.g., `WAKE_WORD_MIC_HANDOFF_DELAY_MS`). The planner should include a verification step that tests session start after wake word on the actual hardware.

2. **Merge breakages (FIX-01) scope**
   - What we know: D-10/D-11 say fix-as-found. The codebase CONCERNS.md lists known issues but no specific merge breakages are documented yet.
   - What's unclear: What specific breakages will be discovered during integration.
   - Recommendation: The plan should allocate time for discovery and include a "fix breakages found" task that allows flexible scope. Any breakages found should be documented in the verification step.

3. **SRES-02 dead websocket threshold**
   - What we know: `_ws_send_json` has a 2.0s timeout (session_manager.py line 175). Consecutive timeouts indicate a dead connection.
   - What's unclear: Optimal threshold for "dead" -- 2 consecutive? 3? What about transient network blips?
   - Recommendation: Use 3 consecutive timeouts as the threshold. This gives ~6 seconds of tolerance for transient issues while still detecting truly dead connections within 10 seconds. Reset the counter on any successful send.

## Project Constraints (from CLAUDE.md)

- **Platform**: Raspberry Pi (Linux/ARM) -- limited resources, must be efficient
- **Hardware module**: `core/hotword.py` must not be modified unless strictly necessary for integration
- **Existing code**: Must preserve upstream's refactored architecture (app factory, blueprints, modular JS)
- **Style**: Follow existing patterns -- use `logger` not `print()`, same coding conventions
- **Formatting**: ruff with 88 char line length, 4 space indent, `isort` profile
- **Pre-commit**: ruff lint + ruff format hooks
- **Error handling**: Broad `except Exception` is acceptable for operational robustness; use specific exceptions when recovery differs
- **Type hints**: Consistently applied to function signatures
- **Threading**: `threading.Thread()` for daemon threads, `threading.Lock()` for critical sections
- **Import style**: Absolute imports from `core/`: `from core.logger import logger`; relative in same package: `from . import config`
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
- **GSD Workflow**: All changes through GSD commands

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All code | Yes | 3.11.2 | -- |
| pvporcupine | Wake word detection | Not installed (system pip) | -- | RMS fallback in hotword.py (amplitude-based detection) |
| sounddevice | Audio I/O | Listed in requirements.txt | -- | No fallback (required for audio) |
| gpiozero | Button hardware | Yes | 2.0.1 | MockButton for non-hardware environments |
| aiohttp | HA integration | Listed in requirements.txt | -- | HA features disabled if unavailable |
| ruff | Pre-commit hooks | Configured in .pre-commit-config.yaml (v0.12.3) | -- | -- |

**Note on pvporcupine:** The package is not installed in the system Python on this development machine. However, it IS listed in `requirements.txt` and the code handles its absence gracefully (hotword.py lines 18-24: `_PORCUPINE_AVAILABLE = False` when import fails). The hotword controller will fall back to RMS-based detection if pvporcupine is unavailable. On the actual deployment Pi, pvporcupine should be installed with a valid access key.

**Missing dependencies with no fallback:**
- sounddevice must be available on the deployment target (required for all audio)

**Missing dependencies with fallback:**
- pvporcupine: falls back to RMS amplitude detection (less accurate but functional)

## Sources

### Primary (HIGH confidence)
- `core/hotword.py` source code (442 lines) -- full WakeWordController API surface, verified all public methods
- `core/button.py` source code (341 lines) -- current session lifecycle, on_button() logic, start_loop() structure
- `core/config.py` source code (271 lines) -- existing `_float_env` pattern, all config variables, validation gaps
- `core/audio.py` source code (734 lines) -- playback_done_event behavior, play_random_wake_up_clip() bug
- `core/ha.py` source code (36 lines) -- current send_conversation_prompt() without timeout
- `core/session_manager.py` source code (904 lines) -- session lifecycle, _ws_send_json timeout behavior
- `core/session/mic_manager_wrapper.py` source code (262 lines) -- timeout_checker stop_session call
- `core/session/state_machine.py` source code (327 lines) -- session state tracking
- `core/mic.py` source code (96 lines) -- MicManager sd.InputStream usage
- `.planning/codebase/CONCERNS.md` -- known bugs and fragile areas

### Secondary (MEDIUM confidence)
- aiohttp ClientTimeout documentation (well-established pattern, `aiohttp.ClientTimeout(total=N)`)
- ALSA device exclusivity behavior on Raspberry Pi (based on general Linux audio subsystem knowledge)

### Tertiary (LOW confidence)
- Exact ALSA release timing (50-100ms is heuristic; actual timing depends on hardware/driver)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies
- Architecture: HIGH -- trigger.py pattern directly follows existing button.py structure; all integration points verified in source code
- Pitfalls: HIGH -- all pitfalls identified from actual code analysis (line numbers referenced); ALSA timing is the one area with some uncertainty
- Config validation: HIGH -- extending existing `_float_env` pattern with same error handling approach
- Resilience fixes: HIGH -- each fix targets a specific, verified code location

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable; no external API changes expected)
