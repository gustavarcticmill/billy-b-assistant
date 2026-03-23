# Wake Word, Calibration & Mic Check Re-integration

## Context

This codebase was forked from `Thokoop/billy-b-assistant` and I had previously implemented wake word support, a calibration wizard, and wake word UI controls. The upstream repo was recently merged and their major refactor overwrote my custom code. The core wake word module (`core/hotword.py`) still exists and is untouched, but the integration points were lost. I need you to re-integrate everything into the new codebase structure.

The upstream refactored:
- `webconfig/server.py` from a monolithic file to a Flask app factory (`webconfig/app/__init__.py` with blueprints in `webconfig/app/routes/`)
- `webconfig/templates/index.html` from inline HTML to component-based Jinja2 includes
- `webconfig/static/js/config.js` was split into separate JS modules in `webconfig/static/js/`
- `core/button.py` was rewritten with MockButton support, logger, and different session management (no wake word)
- `core/session.py` was renamed to `core/session_manager.py` with a provider-based architecture

## What exists and works (DO NOT modify these unless necessary for integration)

- `core/hotword.py` -- Full `WakeWordController` with Porcupine + RMS fallback detection, event queue, `notify_session_state()`, `set_parameters()`, `get_status()`, `enable()`/`disable()`/`start()`/`stop()`
- `core/config.py` -- Already has all wake word config vars: `WAKE_WORD_ENABLED`, `WAKE_WORD_SENSITIVITY`, `WAKE_WORD_THRESHOLD`, `WAKE_WORD_ENDPOINT`, `WAKE_WORD_PORCUPINE_ACCESS_KEY`
- `webconfig/app/routes/audio.py` -- Already has mic check SSE routes (`/mic-check`, `/mic-check/stop`), mic gain, volume, speaker test, device info
- `webconfig/static/js/audio-panel.js` -- Already has mic check UI, mic bar, gain slider
- `webconfig/templates/components/settings-form.html` -- Already has audio settings section with mic check

## What needs to be re-implemented

### 1. Wake word integration in `core/button.py`

The current `button.py` (upstream version) has a monolithic `on_button()` function with all session logic inline. My previous version had a cleaner abstraction with `trigger_session_start(source)` and `trigger_session_stop(source)` that supported multiple trigger sources (hardware button, wake word, UI test).

**Re-add to `core/button.py`:**

a) Import the hotword controller:
```python
from .hotword import controller as wake_word_controller
```

b) Add a `trigger_session_start(source: str) -> bool` function that:
   - Accepts a source string ("hardware", "wake_word", "ui-test")
   - Has debounce logic per source (0.5s)
   - Checks if a session is already active, rejects if so
   - Calls `wake_word_controller.notify_session_state(True)` when starting
   - Starts the wake-up audio clip and session thread
   - Returns True if session was started

c) Add a `trigger_session_stop(source: str, *, reason=None, force=False) -> bool` function that:
   - Sets the interrupt event, stops playback
   - Stops the active session via `session_instance.stop_session()`
   - Returns True if stopped

d) Modify `on_button()` to delegate to `trigger_session_start("hardware")` and `trigger_session_stop("hardware")`

e) In `start_loop()`, after setting `button.when_pressed`, add wake word controller setup:
```python
wake_word_controller.set_parameters(
    enabled=config.WAKE_WORD_ENABLED,
    sensitivity=config.WAKE_WORD_SENSITIVITY,
    threshold=config.WAKE_WORD_THRESHOLD,
    endpoint=config.WAKE_WORD_ENDPOINT,
    porcupine_access_key=config.WAKE_WORD_PORCUPINE_ACCESS_KEY,
)
if config.WAKE_WORD_ENABLED:
    wake_word_controller.set_detection_callback(_handle_wake_word_trigger)
    wake_word_controller.enable()
    wake_word_controller.start()
else:
    wake_word_controller.set_detection_callback(None)
    wake_word_controller.disable()
    wake_word_controller.stop()
```

f) Add `_handle_wake_word_trigger(payload)` callback that calls `trigger_session_start("wake_word")`

g) Make sure `wake_word_controller.notify_session_state(False)` is called in the session cleanup/finally block.

**Important:** Preserve upstream's existing features: MockButton, logger usage, `_force_release_session_start_lock`, `_ensure_button_hold_thread`, `move_tail` startup animation, `FLAP_ON_BOOT`. Use the existing `logger` instead of `print()`. Use `session_manager.BillySession` (not the old `session.BillySession`). The current upstream button.py imports from `.session_manager` not `.session`.

### 2. Wake word web routes -- new blueprint `webconfig/app/routes/wake_word.py`

Create a new Flask blueprint following the same pattern as the other route files (see `webconfig/app/routes/audio.py` for reference).

**Routes to implement:**

a) `GET /wake-word/status` -- Returns JSON with wake word controller status. If controller is unavailable, return a fallback dict with config values. If available, call `wake_word_controller.get_status()`.

b) `GET /wake-word/events` -- Drains up to 50 events from `wake_word_controller.get_event_queue()`, serializes with `dataclasses.asdict()`, returns as JSON.

c) `POST /wake-word/runtime-config` -- Accepts JSON with optional keys: `enabled` (bool), `endpoint` (str), `sensitivity` (float), `threshold` (float), `porcupine_access_key` (str). Passes to `wake_word_controller.set_parameters()`. If `enabled` changes, calls `enable()/start()` or `disable()/stop()`.

d) `POST /wake-word/test` -- Accepts `{"action": "simulate"|"stop"}`. For "simulate", calls `button_controller.trigger_session_start("ui-test")`. For "stop", calls `button_controller.trigger_session_stop("ui-test", reason="wake-word-test", force=True)`.

e) `POST /wake-word/calibrate` -- Records audio using sounddevice, computes RMS metrics. Accepts JSON with `mode` ("ambient" or "phrase"), `duration` (float, clamped 1.5-12.0), optional `base_threshold`. Uses helper functions (see below). Thread-safe with a calibration lock.

f) `POST /wake-word/calibrate/apply` -- Accepts `threshold` and/or `sensitivity` values. Persists to `.env` if `persist=true`. Updates runtime config on wake_word_controller. Updates core_config values in memory.

**Calibration helper functions** (private to the module):

```python
def _resolve_input_device():
    """Find mic device index + info, preferring MIC_PREFERENCE."""

def _record_audio(duration_seconds: float) -> tuple[np.ndarray, int]:
    """Record audio from mic, return (samples_int16, samplerate)."""

def _compute_rms_metrics(samples: np.ndarray, samplerate: int) -> dict:
    """Compute RMS stats: average, median, p90, p95, peak, recommended_threshold."""

def _recommend_threshold(baseline: float, peak: float) -> float:
    """Calculate suggested threshold from baseline noise and peak levels."""
```

**Register the blueprint** in `webconfig/app/__init__.py`:
```python
from .routes.wake_word import bp as wake_word_bp
app.register_blueprint(wake_word_bp)
```

### 3. Wake Word UI panel -- new template component and JS module

a) Create `webconfig/templates/components/wake-word-panel.html` with:
   - Enable/disable toggle with label
   - Porcupine keyword file path input (`WAKE_WORD_ENDPOINT`)
   - Porcupine access key input (password field, `WAKE_WORD_PORCUPINE_ACCESS_KEY`)
   - Sensitivity slider (0.0-1.0, step 0.05)
   - RMS Threshold input (step 10)
   - Listener status section with badge (Listening/Disabled/Paused/Error/Unavailable), status detail text, last error display
   - Simulate Detection / Stop Session / Refresh buttons
   - Event stream display (scrollable pre/div showing last 50 events)
   - Calibration section:
     - "1. Measure Background" button
     - "2. Record Wake Phrase" button (disabled until ambient done)
     - Status text showing calibration progress
     - Results grid: Ambient (noise RMS, peak, suggested threshold) and Wake Phrase (peak RMS)
     - "Apply Suggestions" button with threshold display and "persist to .env" checkbox

b) Include the component in `webconfig/templates/components/settings-form.html` (or `settings-panel.html`), inside the settings form, as a collapsible section similar to the existing Audio Settings, MQTT, and Home Assistant sections.

c) Create `webconfig/static/js/wake-word-panel.js` implementing `WakeWordPanel` module with:
   - `init()` -- binds DOM elements, starts polling status every 5s and events every 3s
   - `fetchStatus()` -- fetches `/wake-word/status`, updates badge, toggle, detail text, error display
   - `fetchEvents()` -- fetches `/wake-word/events`, renders in event container
   - `onToggleChange()` -- sends runtime config update when toggle is clicked
   - `runCalibration(mode)` -- calls `/wake-word/calibrate`, updates summary display
   - `applyCalibration()` -- calls `/wake-word/calibrate/apply`
   - Input change handlers for sensitivity, threshold, endpoint, access key that send runtime updates

d) Include the JS file in `webconfig/templates/base.html` (check how other JS files are included) and call `WakeWordPanel.init()` in the DOMContentLoaded handler in `webconfig/static/js/init.js`.

### 4. Settings form integration

The wake word settings (`WAKE_WORD_ENABLED`, `WAKE_WORD_SENSITIVITY`, `WAKE_WORD_THRESHOLD`, `WAKE_WORD_ENDPOINT`, `WAKE_WORD_PORCUPINE_ACCESS_KEY`) need to be saved to `.env` when the main settings form is submitted. Check how the existing settings form save works in `webconfig/static/js/settings-form.js` and `webconfig/app/routes/system.py` (the `/save` route and `CONFIG_KEYS` list). Add the wake word keys to `CONFIG_KEYS` if they're not already there.

## Style guidelines

- Follow the existing code patterns exactly. Use `logger` (from `core.logger`) instead of `print()` in Python. Use the same Tailwind CSS classes as existing UI sections. Follow the same JS module pattern (IIFE returning public methods).
- Use the existing `showNotification()` function for user feedback in JS.
- Keep the wake word panel visually consistent with the Audio Settings, MQTT, and Home Assistant collapsible sections.
- The blueprint should import core modules the same way other blueprints do (see `from ..core_imports import core_config`).

## Verification

After implementing:
1. Run the Flask app and verify the web UI loads without errors
2. Check that the Wake Word section appears in settings and is collapsible
3. Verify `/wake-word/status` returns valid JSON
4. If on a system with a mic, test the calibration flow (Measure Background -> Record Phrase -> Apply)
5. Verify that saving settings persists wake word config to `.env`
6. Check that `core/button.py` starts the wake word listener when `WAKE_WORD_ENABLED=true`
