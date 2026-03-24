# Architecture Research

**Domain:** Wake word detection integration into voice assistant (Raspberry Pi)
**Researched:** 2026-03-24
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
                         TRIGGER SOURCES
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │  Hardware Button  │  │  Wake Word Det.  │  │  MQTT Command    │
  │  (core/button.py) │  │  (core/hotword)  │  │  (core/mqtt.py)  │
  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
           │                     │                      │
           └─────────────┬───────┘──────────────────────┘
                         ▼
              ┌─────────────────────┐
              │  Session Trigger    │
              │  Abstraction Layer  │    <-- MISSING, needs to be built
              │  (trigger_session)  │
              └─────────┬──────────┘
                        ▼
              ┌─────────────────────┐
              │  BillySession       │
              │  (session_manager)  │
              └─────────┬──────────┘
                        ▼
              ┌─────────────────────┐
              │  AI Provider        │
              │  (OpenAI / xAI)     │
              └─────────────────────┘

                      WEB LAYER
  ┌──────────────────────────────────────────────────────────────┐
  │  Flask App Factory (webconfig/app/)                          │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
  │  │ system   │ │ persona  │ │ audio    │ │ wakeword │ <-- NEW│
  │  │ bp       │ │ bp       │ │ bp       │ │ bp       │       │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
  │  ┌────────────────────────────────────────────────┐         │
  │  │  WebSocket (live logs + wake word SSE events)  │         │
  │  └────────────────────────────────────────────────┘         │
  └──────────────────────────────────────────────────────────────┘

              AUDIO RESOURCE (SHARED)
  ┌──────────────────────────────────────────┐
  │  Microphone (sounddevice InputStream)    │
  │                                          │
  │  Exclusive access:                       │
  │    - Wake word owns mic when IDLE        │
  │    - Session owns mic when ACTIVE        │
  │    - Handoff via notify_session_state()  │
  └──────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Location |
|-----------|----------------|----------|
| WakeWordController | Continuous mic monitoring, Porcupine/RMS detection, event publishing | `core/hotword.py` (exists, do not modify) |
| Session Trigger Abstraction | Unified entry point for starting/stopping sessions from any source | `core/button.py` (needs refactor) |
| Wake Word Blueprint | HTTP endpoints for status, config, test trigger, SSE event stream | `webconfig/app/routes/wakeword.py` (new) |
| Wake Word UI Panel | Dashboard widget for enable/disable, calibration, status badge | `webconfig/templates/` (new partial) |
| Settings Persistence | Save wake word config changes to .env file | Integrate with existing settings routes |
| BillySession | Voice conversation lifecycle orchestration | `core/session_manager.py` (exists) |

## Component Boundaries and Integration Surface

### The Core Problem: Trigger Coupling

Currently, `button.py` directly manages session lifecycle (globals: `is_active`, `session_thread`, `session_instance`, `interrupt_event`, `_session_start_lock`). The `on_button()` function is 200+ lines of interleaved trigger detection, session start, session interrupt, and cleanup logic. Wake word detection needs to call into the same session start/stop mechanism without duplicating this logic.

### Integration Surface Analysis

**WakeWordController (core/hotword.py) -- Already Built:**
- Exposes `set_detection_callback(callback)` -- the primary integration hook
- Exposes `notify_session_state(active: bool)` -- tells it to pause/resume mic listening
- Exposes `get_status() -> dict` -- for web routes to query
- Exposes `get_event_queue() -> Queue[WakeWordEvent]` -- for SSE streaming
- Exposes `set_parameters(...)` -- for runtime config changes from web UI
- Exposes `start()`, `stop()`, `enable()`, `disable()` -- lifecycle control
- Module-level singleton: `controller = WakeWordController()`

**button.py -- Needs Session Trigger Extraction:**
- The `on_button()` function handles both "start new session" and "interrupt active session"
- Wake word only needs to trigger "start new session" (no interrupt semantics)
- Session start logic (lines 232-304) should be extracted into a `trigger_session_start(source: str)` function
- Session stop logic should be extracted into `trigger_session_stop(source: str)` function
- The `on_button()` function then becomes: check debounce, check active, route to start or stop

**Web Layer -- New Blueprint Needed:**
- Pattern to follow: existing blueprints (e.g., `webconfig/app/routes/audio.py`)
- Endpoints: GET `/wakeword/status`, POST `/wakeword/enable`, POST `/wakeword/disable`, POST `/wakeword/test`, GET `/wakeword/events` (SSE), POST `/wakeword/calibrate`
- Blueprint registered in `webconfig/app/__init__.py` following existing pattern

## Data Flow

### Wake Word Detection Flow

```
[Mic Audio Stream]
      │
      ▼
[WakeWordController._audio_callback()]
      │
      ├── RMS calculation + meter event → event_queue
      │
      ├── Porcupine frame processing
      │   └── keyword detected? → _dispatch_detection()
      │
      └── RMS threshold detection
          └── streak met? → _dispatch_detection()
                  │
                  ▼
          [on_detect callback]  ← set via set_detection_callback()
                  │
                  ▼
          [trigger_session_start("wake_word")]
                  │
                  ├── Acquire _session_start_lock
                  ├── Play wake-up sound
                  ├── Create BillySession
                  ├── controller.notify_session_state(True)  ← PAUSES mic listening
                  └── Start session thread
                            │
                            ▼ (session ends)
                  controller.notify_session_state(False)  ← RESUMES mic listening
```

### Microphone Resource Handoff (Critical)

The microphone is a single physical resource. Both the wake word detector and the voice session need exclusive mic access. The WakeWordController already handles this via `notify_session_state()`:

```
IDLE STATE:
  WakeWordController owns InputStream → listening for wake word
      │
      ▼ (detection callback fires)

HANDOFF:
  notify_session_state(True) called
  → _sync_stream_state() closes wake word InputStream
  → BillySession opens its own audio stream
      │
      ▼ (session ends)

RETURN:
  notify_session_state(False) called
  → _sync_stream_state() reopens wake word InputStream
  → Back to IDLE STATE
```

This handoff is the single most important architectural concern. If both try to hold the mic simultaneously, one will fail with a device-busy error.

### Web Event Flow (SSE for UI)

```
[WakeWordController._event_queue]
      │
      ▼
[/wakeword/events SSE endpoint]
      │ (reads from queue, formats as SSE)
      ▼
[Browser EventSource]
      │
      ▼
[UI status badge, meter visualization, detection log]
```

### Settings Persistence Flow

```
[Web UI form change]
      │
      ▼
[POST /wakeword/configure]
      │
      ├── controller.set_parameters(...)  ← runtime update
      └── Write to .env file             ← persist for next boot
```

## Architectural Patterns

### Pattern 1: Trigger Source Abstraction

**What:** Extract session start/stop from `on_button()` into source-agnostic functions that any trigger source (button, wake word, MQTT, UI test button) can call.

**When to use:** Whenever a new trigger source needs to start a session.

**Trade-offs:** Adds a small indirection layer, but prevents code duplication and ensures consistent session lifecycle management across all trigger sources.

**Example:**
```python
# core/button.py - extracted trigger functions

def trigger_session_start(source: str = "button") -> bool:
    """Start a new voice session. Returns True if session started.

    Called by: on_button(), wake word callback, MQTT handler, web test button.
    """
    global is_active, session_thread, interrupt_event, session_instance

    if is_active:
        logger.warning(f"Session already active, ignoring {source} trigger")
        return False

    if not _session_start_lock.acquire(blocking=False):
        # ... existing recovery logic ...
        return False

    # ... existing session start logic (lines 271-298) ...
    logger.info(f"Session started via {source}", "🎤")
    return True


def trigger_session_stop(source: str = "button") -> None:
    """Stop the active session."""
    # ... existing session stop logic from on_button() ...


def on_button():
    """Button-specific handler: debounce + route to start or stop."""
    # ... debounce check ...
    if is_active:
        trigger_session_stop("button")
    else:
        trigger_session_start("button")
```

### Pattern 2: Callback Wiring at Startup

**What:** Wire the wake word detection callback to the session trigger during `start_loop()` initialization, keeping hotword.py completely decoupled from button.py.

**When to use:** At application startup, when all components are initialized.

**Example:**
```python
# core/button.py - in start_loop()

def start_loop():
    audio.detect_devices(debug=config.DEBUG_MODE)
    _ensure_button_hold_thread()

    # Wire wake word → session trigger
    if config.WAKE_WORD_ENABLED:
        from .hotword import controller as ww_controller
        ww_controller.set_detection_callback(
            lambda payload: trigger_session_start("wake_word")
        )
        ww_controller.start()
        logger.info("Wake word detection enabled", "👂")

    button.when_pressed = on_button
    # ... rest of loop ...
```

### Pattern 3: Session State Notification

**What:** After session start/stop, notify the WakeWordController so it can pause/resume mic listening. This prevents mic contention.

**When to use:** Every session transition.

**Example:**
```python
# Inside trigger_session_start, after session starts:
if config.WAKE_WORD_ENABLED:
    from .hotword import controller as ww_controller
    ww_controller.notify_session_state(True)

# Inside run_session() finally block:
if config.WAKE_WORD_ENABLED:
    from .hotword import controller as ww_controller
    ww_controller.notify_session_state(False)
```

### Pattern 4: Flask Blueprint for Wake Word Web API

**What:** Dedicated blueprint following the existing pattern (`bp = Blueprint("wakeword", __name__, url_prefix="/wakeword")`).

**When to use:** For all wake word web endpoints.

**Example:**
```python
# webconfig/app/routes/wakeword.py

from flask import Blueprint, Response, jsonify, request
from core.hotword import controller

bp = Blueprint("wakeword", __name__, url_prefix="/wakeword")

@bp.route("/status")
def status():
    return jsonify(controller.get_status())

@bp.route("/events")
def events():
    def stream():
        q = controller.get_event_queue()
        while True:
            try:
                event = q.get(timeout=30)
                yield f"data: {json.dumps(event.__dict__)}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    return Response(stream(), mimetype="text/event-stream")
```

## Anti-Patterns

### Anti-Pattern 1: Duplicating Session Logic in Wake Word Callback

**What people do:** Copy-paste the session start logic from `on_button()` into a wake word callback handler.
**Why it's wrong:** Two diverging copies of critical session lifecycle code. Bugs fixed in one path don't get fixed in the other. The locking, cleanup, and error handling are subtle and must be consistent.
**Do this instead:** Extract `trigger_session_start()` and have both button and wake word call it.

### Anti-Pattern 2: Opening Two Mic Streams Simultaneously

**What people do:** Let the wake word detector keep its mic stream open while the session opens another.
**Why it's wrong:** On Raspberry Pi with a single USB mic, only one process/stream can hold the device. The second open will fail with `PortAudioError` or produce silence.
**Do this instead:** Use `notify_session_state(True)` before session starts (which closes the wake word stream), and `notify_session_state(False)` after session ends (which reopens it). The WakeWordController already implements this correctly.

### Anti-Pattern 3: Polling for Wake Word Events in the Web Layer

**What people do:** Use setInterval + fetch to poll `/wakeword/status` every 500ms.
**Why it's wrong:** Wastes resources, adds latency, and misses rapid events. The WakeWordController already provides an event queue designed for streaming.
**Do this instead:** Use Server-Sent Events (SSE) with the event queue. The browser uses `EventSource` which auto-reconnects and is lightweight.

### Anti-Pattern 4: Modifying core/hotword.py

**What people do:** Add session management, button imports, or web route logic directly into hotword.py.
**Why it's wrong:** The module is deliberately self-contained with a clean callback interface. Adding dependencies on button.py or Flask creates circular imports and couples the detection engine to application lifecycle.
**Do this instead:** Use the existing callback and event queue interfaces. All integration happens outside hotword.py.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Direction | Notes |
|----------|---------------|-----------|-------|
| hotword.py -> button.py | Detection callback (set via `set_detection_callback`) | hotword fires, button receives | Callback runs in a daemon thread spawned by hotword |
| button.py -> hotword.py | `notify_session_state(bool)` | button calls hotword | Must be called on session start AND end (including error paths) |
| hotword.py -> web routes | `get_status()`, `get_event_queue()`, `set_parameters()` | web reads/writes hotword state | Thread-safe (uses RLock internally) |
| web routes -> .env file | Write config values | web persists to disk | Use existing .env write pattern from settings routes |
| web routes -> app factory | Blueprint registration | factory imports and registers | Follow exact pattern of existing blueprints |
| UI JS -> SSE endpoint | EventSource connection | browser opens, server pushes | Auto-reconnect built into EventSource API |

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Picovoice Porcupine | pvporcupine Python SDK, .ppn keyword file | Requires access key (env var), ARM-compatible, ~1% CPU on Pi |
| Microphone (USB) | sounddevice InputStream | Single-device constraint, exclusive access |

## Suggested Build Order

Dependencies between components dictate this order:

### Phase 1: Session Trigger Abstraction (Foundation)

**What:** Extract `trigger_session_start()` and `trigger_session_stop()` from `on_button()`.

**Why first:** Everything else depends on having a clean, source-agnostic way to start sessions. The wake word callback needs it. The web test button needs it. Without this, you're duplicating session lifecycle logic.

**Dependencies:** None (refactors existing code).

**Verification:** Button press still works identically after refactor.

### Phase 2: Wake Word Callback Wiring

**What:** Wire `WakeWordController.set_detection_callback()` to `trigger_session_start("wake_word")` in `start_loop()`. Add `notify_session_state()` calls to session start/end paths.

**Why second:** Depends on Phase 1's trigger abstraction. This is the core integration -- after this, wake word detection triggers sessions.

**Dependencies:** Phase 1.

**Verification:** Say wake word -> session starts. Session ends -> wake word resumes listening. Button still works.

### Phase 3: Wake Word Web Blueprint

**What:** Create `webconfig/app/routes/wakeword.py` with status, enable/disable, configure, test, and SSE events endpoints. Register in app factory.

**Why third:** The backend integration (Phases 1-2) must work before adding a web control layer on top.

**Dependencies:** Phase 1 (test trigger endpoint calls `trigger_session_start`), working hotword controller.

**Verification:** `/wakeword/status` returns correct state. `/wakeword/test` triggers a session.

### Phase 4: Wake Word UI Panel

**What:** Jinja2 template partial with enable/disable toggle, status badge, RMS meter visualization, calibration controls. JavaScript module following IIFE pattern.

**Why fourth:** Needs the web endpoints from Phase 3 to exist.

**Dependencies:** Phase 3.

**Verification:** UI shows live status, toggle works, meter updates via SSE.

### Phase 5: Settings Persistence

**What:** Save wake word config changes (enabled, sensitivity, threshold, access key) to `.env` file so they survive reboot.

**Why last:** Non-critical for functionality (runtime config via `set_parameters()` works without persistence). Can follow existing settings form patterns.

**Dependencies:** Phase 3 (web endpoint exists), existing .env write mechanism.

**Verification:** Change setting in UI, restart app, setting is retained.

## Scaling Considerations

Not applicable in the traditional sense (this is a single-device embedded system), but resource constraints on Raspberry Pi are the equivalent concern:

| Concern | Impact | Mitigation |
|---------|--------|------------|
| CPU usage from continuous mic monitoring | Porcupine uses ~1-3% CPU on Pi 4 | RMS fallback is even lighter; both are fine |
| Memory for audio buffers | ~50KB for Porcupine frame buffer | Negligible on Pi with 1-8GB RAM |
| Mic device contention | Fatal if two streams open | `notify_session_state()` handoff pattern (already built) |
| Event queue overflow | Queue capped at 256, auto-evicts oldest | Built into WakeWordController already |
| SSE connection lifetime | Long-lived HTTP connections | Use keepalive pings, EventSource auto-reconnects |

## Sources

- `core/hotword.py` -- existing WakeWordController implementation (primary source for integration API)
- `core/button.py` -- existing session lifecycle management (primary source for trigger refactoring)
- `webconfig/app/__init__.py` -- Flask app factory pattern (blueprint registration reference)
- `webconfig/app/routes/audio.py` -- existing blueprint pattern to follow
- `core/config.py` -- wake word configuration variables (WAKE_WORD_ENABLED, SENSITIVITY, THRESHOLD, ENDPOINT, PORCUPINE_ACCESS_KEY)
- Picovoice Porcupine documentation for pvporcupine API patterns (HIGH confidence, verified against actual usage in hotword.py)

---
*Architecture research for: Wake word integration into Billy B voice assistant*
*Researched: 2026-03-24*
