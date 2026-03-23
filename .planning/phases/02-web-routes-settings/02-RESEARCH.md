# Phase 2: Web Routes & Settings - Research

**Researched:** 2026-03-23
**Domain:** Flask blueprint routes, sounddevice audio recording, .env persistence
**Confidence:** HIGH

## Summary

Phase 2 adds a single Flask blueprint (`wake_word.py`) with 6 route handlers that wrap the existing `WakeWordController` singleton, plus integrates 5 wake word config keys into the existing settings save flow. The codebase already contains every building block needed -- the blueprint registration pattern (6 existing blueprints in `__init__.py`), the mic recording + RMS computation pattern (`audio.py` mic-check), the `.env` persistence pattern (`system.py` save + `set_key()`), and the session trigger abstraction (`core/trigger.py`). No new libraries are required.

The research focus is on: (1) the exact existing patterns to replicate for each route, (2) the `WakeWordController` public API surface and its data structures, (3) the calibration recording approach using `sounddevice` with mic handoff coordination, and (4) the CONFIG_KEYS integration for settings persistence.

**Primary recommendation:** Build all routes as thin wrappers around `core.hotword.controller` methods. Use the existing `audio.py` mic-check pattern for calibration recording. Add wake word keys to CONFIG_KEYS in system.py. Register the blueprint in `__init__.py` following the exact pattern of the other 6 blueprints.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single file `webconfig/app/routes/wake_word.py` with all 6 routes. Follows existing pattern (audio.py, system.py). Blueprint registered in `webconfig/app/__init__.py`.
- **D-02:** URL prefix `/wake-word/` as specified in requirements. Blueprint variable named `bp = Blueprint("wake_word", __name__)`.
- **D-03:** Synchronous recording with timeout -- POST /wake-word/calibrate blocks for a fixed duration (e.g. 3s ambient, 3s phrase), computes RMS metrics, returns JSON when done. Matches existing mic check pattern in audio routes.
- **D-04:** Pause wake word listener during calibration -- call `notify_session_state(True)` to free the mic, record, then resume with `notify_session_state(False)`. Same pattern as session handoff from Phase 1.
- **D-05:** Polling only -- GET /wake-word/events drains up to 50 events from the controller queue and returns JSON array. No SSE streaming in Phase 2. Phase 3 UI polls this endpoint on an interval.
- **D-06:** Add wake word config keys (WAKE_WORD_ENABLED, WAKE_WORD_SENSITIVITY, WAKE_WORD_THRESHOLD, WAKE_WORD_ENDPOINT, PORCUPINE_ACCESS_KEY) to the existing `CONFIG_KEYS` list in `system.py`. They save alongside all other settings via the existing form submit endpoint.

### Claude's Discretion
- Exact recording durations for ambient vs phrase calibration modes
- RMS computation approach (rolling window, peak detection, etc.)
- JSON response shapes for each endpoint (must match what Phase 3 UI consumes)
- Error response format and HTTP status codes
- How runtime config update interacts with the controller's `set_parameters()` method

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WWEB-01 | `GET /wake-word/status` returns JSON with controller status | `controller.get_status()` returns exact dict; route is a thin wrapper with fallback for missing controller |
| WWEB-02 | `GET /wake-word/events` drains up to 50 events from queue | `controller.get_event_queue()` returns `queue.Queue[WakeWordEvent]`; drain with `get_nowait()` loop, serialize WakeWordEvent dataclass fields |
| WWEB-03 | `POST /wake-word/runtime-config` updates controller parameters | `controller.set_parameters()` accepts keyword args: enabled, sensitivity, threshold, endpoint, porcupine_access_key |
| WWEB-04 | `POST /wake-word/test` triggers simulate/stop actions | `trigger_session_start("ui-test")` and `trigger_session_stop("ui-test")` from `core.trigger` |
| WWEB-05 | `POST /wake-word/calibrate` records audio and computes RMS metrics | sounddevice `sd.InputStream` with callback, numpy RMS computation -- matches `audio.py` mic-check pattern |
| WWEB-06 | `POST /wake-word/calibrate/apply` persists threshold/sensitivity to .env | `dotenv.set_key(ENV_PATH, key, value, quote_mode='never')` then `controller.set_parameters()` |
| WWEB-07 | Wake word blueprint registered in Flask app factory | Add `from .routes.wake_word import bp as wake_word_bp` and `app.register_blueprint(wake_word_bp)` in `__init__.py` |
| SETS-01 | Wake word config keys saved to .env on form submit | Add 5 keys to CONFIG_KEYS list in system.py |
| SETS-02 | Wake word keys added to CONFIG_KEYS in system routes | Same as SETS-01 -- the CONFIG_KEYS list controls what the `/save` endpoint persists |
</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.3 | Web framework, Blueprint, jsonify, request | Already in use across all routes |
| sounddevice | 0.5.5 | Mic audio capture for calibration recording | Already used in audio.py mic-check and hotword.py |
| numpy | 1.26.4 | RMS computation from audio samples | Already used in audio.py and hotword.py |
| python-dotenv | (installed) | `set_key()` for .env persistence | Already used in system.py save route |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses (stdlib) | n/a | WakeWordEvent is already a dataclass | Serializing events to JSON |
| queue (stdlib) | n/a | Thread-safe event queue | Draining events in WWEB-02 |
| json (stdlib) | n/a | JSON serialization | Response formatting |
| time (stdlib) | n/a | Timestamps, recording duration | Calibration timing |

**Installation:** None required. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
webconfig/app/routes/
    wake_word.py          # NEW: All 6 wake word routes (WWEB-01 through WWEB-06)
webconfig/app/
    __init__.py           # MODIFIED: Register wake_word blueprint
webconfig/app/routes/
    system.py             # MODIFIED: Add 5 keys to CONFIG_KEYS list
webconfig/templates/components/
    settings-form.html    # MODIFIED: Add wake word settings section between audio and MQTT
```

### Pattern 1: Blueprint Registration (replicate exactly)
**What:** Every route module defines `bp = Blueprint(...)` and is imported + registered in `create_app()`.
**When to use:** Always -- this is the only route registration pattern in the codebase.
**Example:**
```python
# Source: webconfig/app/__init__.py lines 26-46
from .routes.wake_word import bp as wake_word_bp
# ... existing registrations ...
app.register_blueprint(wake_word_bp)
```

### Pattern 2: Route Module Structure (replicate audio.py)
**What:** Each route file imports Flask utilities, defines `bp`, imports `core_config` via relative import, and defines route functions that return `jsonify()`.
**Example:**
```python
# Source: webconfig/app/routes/audio.py pattern
from flask import Blueprint, jsonify, request
from ..core_imports import core_config

bp = Blueprint("wake_word", __name__)

@bp.route("/wake-word/status")
def status():
    # ...
    return jsonify({...})
```

### Pattern 3: Error Response Pattern
**What:** All routes use try/except returning `jsonify({"error": message}), HTTP_STATUS`.
**Example:**
```python
# Source: webconfig/app/routes/audio.py lines 339-341
except Exception as e:
    yield f"data: {json.dumps({'error': str(e)})}\n\n"
# Source: webconfig/app/routes/system.py line 433
return jsonify({"status": "error", "error": str(e)}), 500
```

### Pattern 4: .env Persistence via set_key
**What:** The save route iterates CONFIG_KEYS, writing each to .env via `set_key()`.
**Example:**
```python
# Source: webconfig/app/routes/system.py lines 497-511
from dotenv import find_dotenv, set_key

ENV_PATH = find_dotenv(usecwd=True)

def save():
    data = request.json
    for key, value in data.items():
        if key in CONFIG_KEYS:
            set_key(ENV_PATH, key, value, quote_mode='never')
    return jsonify({"status": "ok"})
```

### Pattern 5: Mic Recording for Calibration (replicate audio.py mic-check)
**What:** Open a `sd.InputStream` with a callback that computes RMS and pushes to a queue. Read from queue for a fixed duration.
**Example:**
```python
# Source: webconfig/app/routes/audio.py lines 89-93, 321-342
def audio_callback(indata, frames, time_info, status):
    rms = float(np.sqrt(np.mean(np.square(indata))))
    rms_queue.put(rms)

# For calibration: collect RMS values for N seconds, compute stats
```

### Anti-Patterns to Avoid
- **Importing controller at module level without try/except:** The controller may fail to initialize on systems without audio hardware. Always wrap `from core.hotword import controller` in a try/except with a fallback status.
- **Blocking the wake word stream during calibration without releasing it:** Must call `controller.notify_session_state(True)` before opening the mic for calibration, then `notify_session_state(False)` after. Both operations need to happen in a finally block.
- **Using SSE for events in Phase 2:** Decision D-05 explicitly locks to polling-only. SSE is Phase 3 scope if at all.
- **Adding form fields with `name` attributes that don't match CONFIG_KEYS:** The save flow uses exact key matching. The `name` attribute on form inputs must exactly match the CONFIG_KEYS entry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .env file writing | Custom file parser | `dotenv.set_key(path, key, value, quote_mode='never')` | Handles escaping, creates file if missing, preserves other keys |
| Audio capture | Custom ALSA/PortAudio bindings | `sounddevice.InputStream` with callback | Already working in codebase, handles device selection |
| RMS computation | Manual sample iteration | `numpy.sqrt(numpy.mean(numpy.square(data)))` | One-liner, handles edge cases, matches existing pattern |
| Event queue | Custom ring buffer | `queue.Queue(maxsize=256)` | Already used by WakeWordController, thread-safe, bounded |
| Config key management | Custom config system | CONFIG_KEYS list + existing save route | Adding keys to the list is all that's needed |

**Key insight:** Every building block exists in the codebase. Phase 2 routes are thin orchestration wrappers -- no new algorithms or data structures needed.

## Common Pitfalls

### Pitfall 1: Mic Contention During Calibration
**What goes wrong:** Opening a `sd.InputStream` for calibration while the wake word controller already has one open causes ALSA device busy errors.
**Why it happens:** ALSA doesn't support multiple readers on the same capture device.
**How to avoid:** Call `controller.notify_session_state(True)` before opening the calibration stream. This calls `_close_stream()` internally, releasing the mic. After calibration, call `notify_session_state(False)` in a `finally` block to re-enable wake word listening.
**Warning signs:** `sounddevice.PortAudioError: Error opening InputStream: Device unavailable`

### Pitfall 2: WakeWordEvent Serialization
**What goes wrong:** `WakeWordEvent` is a dataclass but not directly JSON-serializable (has `float | None` fields, `dict | None` payload).
**Why it happens:** `jsonify()` can't serialize dataclass instances directly.
**How to avoid:** Convert each `WakeWordEvent` to a dict using `dataclasses.asdict()` or manual dict construction. The dataclass fields are: `timestamp` (float), `kind` (str), `level` (float|None), `threshold` (float|None), `message` (str|None), `payload` (dict|None).
**Warning signs:** `TypeError: Object of type WakeWordEvent is not JSON serializable`

### Pitfall 3: CONFIG_KEYS Naming Mismatch
**What goes wrong:** The .env key names, the `core.config` attribute names, the `CONFIG_KEYS` entries, and the HTML form `name` attributes must all align for the save flow to work.
**Why it happens:** The existing pattern uses identical strings everywhere. The wake word keys in `core.config` use `WAKE_WORD_` prefix (e.g., `WAKE_WORD_ENABLED`) and the env vars match. But `PORCUPINE_ACCESS_KEY` in the CONTEXT.md shorthand is actually `WAKE_WORD_PORCUPINE_ACCESS_KEY` in config.py. Also note config.py falls back to `PICOVOICE_ACCESS_KEY` env var.
**How to avoid:** Use the exact env var names from `core/config.py` lines 277-284: `WAKE_WORD_ENABLED`, `WAKE_WORD_SENSITIVITY`, `WAKE_WORD_THRESHOLD`, `WAKE_WORD_ENDPOINT`, `WAKE_WORD_PORCUPINE_ACCESS_KEY`. The config attribute `WAKE_WORD_PORCUPINE_ACCESS_KEY` reads from env var `WAKE_WORD_PORCUPINE_ACCESS_KEY` (with fallback to `PICOVOICE_ACCESS_KEY`).
**Warning signs:** Settings form saves but values don't appear on reload.

### Pitfall 4: Calibration Without Mic Device Initialization
**What goes wrong:** `core.audio.MIC_DEVICE_INDEX` may be `None` if the webconfig server starts before `main.py` (which calls `detect_devices()`).
**Why it happens:** The webconfig server runs as a separate systemd service (`billy-webconfig.service`) from the main app (`billy.service`). The web server doesn't call `audio.detect_devices()`.
**How to avoid:** In the calibration route, check if `audio.MIC_DEVICE_INDEX` is None and call `audio.detect_devices()` if needed, or return an error explaining that audio devices haven't been detected yet. The existing audio.py routes rely on `sd.InputStream()` with default device (no explicit device= parameter), which uses sounddevice's default. For calibration, doing the same (no explicit device) is safest.
**Warning signs:** `None` passed as device index causing cryptic sounddevice errors.

### Pitfall 5: Queue Drain Race Condition
**What goes wrong:** Events continue to arrive while draining the queue, potentially causing the drain loop to run indefinitely.
**Why it happens:** The wake word controller's audio callback continuously publishes events (especially "meter" events every 250ms).
**How to avoid:** Use `get_nowait()` in a loop with a hard cap (50 events as specified in D-05). Don't use `get()` with timeout which would block. Break after 50 events regardless.
**Warning signs:** Endpoint takes seconds to respond or returns huge event arrays.

### Pitfall 6: Blueprint URL Prefix
**What goes wrong:** Routes defined with `/wake-word/...` path in decorators may conflict with a `url_prefix` on the blueprint, resulting in `/wake-word/wake-word/...` double-prefix URLs.
**Why it happens:** Flask allows prefix on both the blueprint and individual routes.
**How to avoid:** Use either `url_prefix="/wake-word"` on the Blueprint constructor with relative paths in decorators (e.g., `@bp.route("/status")`), OR use absolute paths in decorators with no url_prefix. Looking at the existing code: `audio.py` uses absolute paths like `@bp.route("/wakeup")`, `@bp.route("/mic-check")` with no url_prefix on Blueprint. `system.py` uses `@bp.route("/")`, `@bp.route("/save")` etc. **Follow the existing pattern: no url_prefix, absolute paths in decorators.**
**Warning signs:** 404 errors on routes that should exist.

## Code Examples

### WWEB-01: Status Route
```python
# Verified pattern from controller.get_status() - core/hotword.py lines 129-145
@bp.route("/wake-word/status")
def status():
    try:
        from core.hotword import controller
        return jsonify(controller.get_status())
    except Exception as e:
        return jsonify({
            "enabled": False,
            "running": False,
            "error": str(e),
            "mode": "unavailable",
        })
```

### WWEB-02: Events Drain Route
```python
# Verified from WakeWordEvent dataclass - core/hotword.py lines 31-37
import dataclasses
import queue as queue_module

@bp.route("/wake-word/events")
def events():
    try:
        from core.hotword import controller
        eq = controller.get_event_queue()
        drained = []
        for _ in range(50):
            try:
                event = eq.get_nowait()
                drained.append(dataclasses.asdict(event))
            except queue_module.Empty:
                break
        return jsonify({"events": drained, "count": len(drained)})
    except Exception as e:
        return jsonify({"events": [], "count": 0, "error": str(e)})
```

### WWEB-03: Runtime Config Update
```python
# Verified from set_parameters() signature - core/hotword.py lines 98-127
@bp.route("/wake-word/runtime-config", methods=["POST"])
def runtime_config():
    data = request.get_json() or {}
    try:
        from core.hotword import controller
        params = {}
        if "enabled" in data:
            params["enabled"] = str(data["enabled"]).lower() in ("true", "1", "yes")
        if "sensitivity" in data:
            params["sensitivity"] = float(data["sensitivity"])
        if "threshold" in data:
            params["threshold"] = float(data["threshold"])
        if "endpoint" in data:
            params["endpoint"] = str(data["endpoint"])
        if "porcupine_access_key" in data:
            params["porcupine_access_key"] = str(data["porcupine_access_key"])
        controller.set_parameters(**params)
        return jsonify({"status": "ok", "applied": list(params.keys())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### WWEB-04: Test Simulate/Stop
```python
# Verified from trigger module - core/trigger.py lines 46, 233
@bp.route("/wake-word/test", methods=["POST"])
def test():
    data = request.get_json() or {}
    action = data.get("action", "simulate")
    try:
        from core.trigger import trigger_session_start, trigger_session_stop
        if action == "simulate":
            trigger_session_start("ui-test")
            return jsonify({"status": "ok", "action": "simulate"})
        elif action == "stop":
            trigger_session_stop("ui-test")
            return jsonify({"status": "ok", "action": "stop"})
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### WWEB-05: Calibration Recording
```python
# Verified from audio.py mic-check pattern - lines 89-93, 321-342
# and hotword.py notify_session_state - line 93-96
import time
import numpy as np
import sounddevice as sd

@bp.route("/wake-word/calibrate", methods=["POST"])
def calibrate():
    data = request.get_json() or {}
    mode = data.get("mode", "ambient")  # "ambient" or "phrase"
    duration = 3  # seconds

    try:
        from core.hotword import controller
        # Pause wake word listener to free the mic
        controller.notify_session_state(True)
        try:
            rms_values = []
            def callback(indata, frames, time_info, status):
                rms = float(np.sqrt(np.mean(np.square(indata))))
                rms_values.append(rms)

            with sd.InputStream(callback=callback):
                time.sleep(duration)

            if not rms_values:
                return jsonify({"error": "No audio data captured"}), 500

            rms_mean = float(np.mean(rms_values))
            rms_peak = float(np.max(rms_values))
            suggested_threshold = round(rms_peak * 1.5) if mode == "ambient" else None

            result = {
                "mode": mode,
                "rms_mean": round(rms_mean, 1),
                "rms_peak": round(rms_peak, 1),
                "duration_seconds": duration,
            }
            if suggested_threshold is not None:
                result["suggested_threshold"] = suggested_threshold

            return jsonify(result)
        finally:
            # Always resume wake word listener
            controller.notify_session_state(False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### WWEB-06: Calibration Apply
```python
# Verified from system.py save pattern - lines 12, 497-511
from dotenv import find_dotenv, set_key

ENV_PATH = find_dotenv(usecwd=True)
if not ENV_PATH:
    import os
    ENV_PATH = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        ".env",
    )

@bp.route("/wake-word/calibrate/apply", methods=["POST"])
def calibrate_apply():
    data = request.get_json() or {}
    try:
        from core.hotword import controller
        applied = {}
        if "threshold" in data:
            val = str(data["threshold"])
            set_key(ENV_PATH, "WAKE_WORD_THRESHOLD", val, quote_mode='never')
            applied["threshold"] = val
        if "sensitivity" in data:
            val = str(data["sensitivity"])
            set_key(ENV_PATH, "WAKE_WORD_SENSITIVITY", val, quote_mode='never')
            applied["sensitivity"] = val
        # Also update runtime controller
        params = {}
        if "threshold" in data:
            params["threshold"] = float(data["threshold"])
        if "sensitivity" in data:
            params["sensitivity"] = float(data["sensitivity"])
        if params:
            controller.set_parameters(**params)
        return jsonify({"status": "ok", "applied": applied})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### SETS-01/SETS-02: CONFIG_KEYS Addition
```python
# Source: webconfig/app/routes/system.py lines 40-68
# Add these 5 keys to the CONFIG_KEYS list:
CONFIG_KEYS = [
    # ... existing 27 keys ...
    "WAKE_WORD_ENABLED",
    "WAKE_WORD_SENSITIVITY",
    "WAKE_WORD_THRESHOLD",
    "WAKE_WORD_ENDPOINT",
    "WAKE_WORD_PORCUPINE_ACCESS_KEY",
]
```

### WWEB-07: Blueprint Registration
```python
# Source: webconfig/app/__init__.py lines 26-46
from .routes.wake_word import bp as wake_word_bp
# In create_app():
app.register_blueprint(wake_word_bp)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OpenWakeWord engine | Porcupine (pvporcupine) | Commit 53a0cb4 | Only Porcupine engine supported; RMS fallback mode exists |
| `PICOVOICE_ACCESS_KEY` env var | `WAKE_WORD_PORCUPINE_ACCESS_KEY` (with fallback to `PICOVOICE_ACCESS_KEY`) | Phase 1 | Config.py reads both env vars; new code should use `WAKE_WORD_PORCUPINE_ACCESS_KEY` |
| Inline button session logic | `core/trigger.py` abstraction | Phase 1 | All session start/stop goes through trigger module |

## Project Constraints (from CLAUDE.md)

- **Platform**: Raspberry Pi (Linux/ARM) -- limited resources, must not add heavy dependencies
- **Existing code**: Must preserve upstream's refactored architecture (app factory, blueprints, modular JS)
- **Hardware module**: core/hotword.py must not be modified unless strictly necessary for integration
- **Style**: Follow existing patterns -- use `logger` not `print()`, same Tailwind classes, IIFE JS module pattern, blueprint pattern for routes
- **Ruff**: Line length 88 chars, 4-space indent, preserve existing quote style
- **Type hints**: Applied consistently to function signatures
- **Error handling**: Broad `except Exception as e:` with `jsonify({"error": str(e)}), 500` return pattern

## Open Questions

1. **Calibration recording device selection**
   - What we know: `audio.py` mic-check uses `sd.InputStream(callback=...)` with no explicit device (defaults to system default). `hotword.py` uses `audio.MIC_DEVICE_INDEX` explicitly. The webconfig server runs as a separate process from main.py.
   - What's unclear: Whether the system default mic is always the correct one for calibration.
   - Recommendation: Use no explicit device (system default), matching the existing mic-check pattern. If users report issues, a later phase can add device selection.

2. **Calibration suggested threshold formula**
   - What we know: D-03 says compute RMS metrics and return suggested values. UI-SPEC says return `suggested_threshold`.
   - What's unclear: The exact formula for computing a suggested threshold from ambient RMS measurements.
   - Recommendation: For ambient mode, use `rms_peak * 1.5` (50% above peak ambient noise). For phrase mode, return `rms_peak` as the suggested sensitivity reference. These are starting points the user can adjust.

3. **ENV_PATH in wake_word.py**
   - What we know: system.py computes `ENV_PATH = find_dotenv(usecwd=True)` with a fallback. The calibrate/apply route needs the same path.
   - What's unclear: Whether to duplicate the `ENV_PATH` logic or import it from system.py.
   - Recommendation: Import `ENV_PATH` from the system route module (`from .system import ENV_PATH`) or compute it identically. Importing avoids duplication.

## Sources

### Primary (HIGH confidence)
- `webconfig/app/routes/audio.py` -- Blueprint pattern, mic recording, RMS computation (reference implementation)
- `webconfig/app/routes/system.py` -- CONFIG_KEYS list (lines 40-68), .env save flow via `set_key()` (line 504), ENV_PATH computation (lines 34-39)
- `webconfig/app/__init__.py` -- Blueprint registration pattern (lines 26-46)
- `core/hotword.py` -- WakeWordController API: `get_status()` (lines 129-145), `set_parameters()` (lines 98-127), `get_event_queue()` (line 147), `notify_session_state()` (lines 93-96), `WakeWordEvent` dataclass (lines 31-37)
- `core/trigger.py` -- `trigger_session_start("ui-test")` (line 46), `trigger_session_stop("ui-test")` (line 233)
- `core/config.py` -- Wake word config vars (lines 277-284), exact env var names

### Secondary (MEDIUM confidence)
- `.planning/phases/02-web-routes-settings/02-UI-SPEC.md` -- API response shapes (Phase 3 consumer contract), form field inventory
- `webconfig/templates/components/settings-form.html` -- Section insertion point between `section-audio` (line 274) and `section-mqtt` (line 422)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and in use, versions verified on the running system
- Architecture: HIGH -- every pattern has been verified against the actual codebase files with line numbers
- Pitfalls: HIGH -- all pitfalls identified from real code analysis (ALSA contention, dataclass serialization, CONFIG_KEYS naming, device initialization, queue drain, URL prefix)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- all findings based on current codebase, no external API changes expected)
