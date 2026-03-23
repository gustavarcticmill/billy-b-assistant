# Phase 2: Web Routes & Settings - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

HTTP blueprint endpoints for wake word controller: status query, event drain, runtime config update, simulate/stop test, calibration recording with RMS metrics, calibration apply with .env persistence, and settings form integration. All routes under `/wake-word/` prefix.

</domain>

<decisions>
## Implementation Decisions

### Blueprint structure
- **D-01:** Single file `webconfig/app/routes/wake_word.py` with all 6 routes. Follows existing pattern (audio.py, system.py). Blueprint registered in `webconfig/app/__init__.py`.
- **D-02:** URL prefix `/wake-word/` as specified in requirements. Blueprint variable named `bp = Blueprint("wake_word", __name__)`.

### Calibration recording
- **D-03:** Synchronous recording with timeout — POST /wake-word/calibrate blocks for a fixed duration (e.g. 3s ambient, 3s phrase), computes RMS metrics, returns JSON when done. Matches existing mic check pattern in audio routes.
- **D-04:** Pause wake word listener during calibration — call `notify_session_state(True)` to free the mic, record, then resume with `notify_session_state(False)`. Same pattern as session handoff from Phase 1.

### Event delivery
- **D-05:** Polling only — GET /wake-word/events drains up to 50 events from the controller queue and returns JSON array. No SSE streaming in Phase 2. Phase 3 UI polls this endpoint on an interval.

### Settings integration
- **D-06:** Add wake word config keys (WAKE_WORD_ENABLED, WAKE_WORD_SENSITIVITY, WAKE_WORD_THRESHOLD, WAKE_WORD_ENDPOINT, PORCUPINE_ACCESS_KEY) to the existing `CONFIG_KEYS` list in `system.py`. They save alongside all other settings via the existing form submit endpoint.

### Claude's Discretion
- Exact recording durations for ambient vs phrase calibration modes
- RMS computation approach (rolling window, peak detection, etc.)
- JSON response shapes for each endpoint (must match what Phase 3 UI consumes)
- Error response format and HTTP status codes
- How runtime config update interacts with the controller's `set_parameters()` method

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/REQUIREMENTS.md` — WWEB-01 through WWEB-07 (wake word web routes), SETS-01/SETS-02 (settings persistence)
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, dependency on Phase 1
- `.planning/PROJECT.md` — Constraints: preserve upstream architecture, follow blueprint pattern

### Existing code patterns
- `webconfig/app/routes/audio.py` — Blueprint pattern, mic recording, RMS computation (reference implementation)
- `webconfig/app/routes/system.py` — CONFIG_KEYS list (lines 40-65), .env save flow via `set_key()`
- `webconfig/app/__init__.py` — Blueprint registration pattern
- `core/hotword.py` — WakeWordController public API: `get_status()`, `set_parameters()`, `get_event_queue()`, `notify_session_state()`
- `core/trigger.py` — `trigger_session_start("ui-test")` / `trigger_session_stop("ui-test")` for test endpoint

### UI design contract
- `.planning/phases/02-web-routes-settings/02-UI-SPEC.md` — Visual specs for settings form fields, API response shapes consumed by Phase 3 UI

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/hotword.controller` — Module-level singleton with `get_status()`, `set_parameters()`, `get_event_queue()`, `notify_session_state()`. Routes are thin wrappers around these.
- `core/trigger.trigger_session_start("ui-test")` / `trigger_session_stop("ui-test")` — For WWEB-04 test endpoint.
- `webconfig/app/routes/audio.py` — Mic check pattern with `sd.InputStream`, RMS queue, synchronous recording. Reference for calibration endpoint.
- `webconfig/app/core_imports.py` — Provides `core_config` access for reading current config values.
- `dotenv.set_key()` — Used in system.py for .env persistence. Reuse for WWEB-06 calibrate/apply.

### Established Patterns
- Blueprint with `bp = Blueprint("name", __name__)` and import in `__init__.py`
- `CONFIG_KEYS` list controls which .env keys get saved on form submit
- Routes return `jsonify()` responses with appropriate HTTP status codes
- `from ..core_imports import core_config` for accessing config values
- Error handling with try/except returning `jsonify({"error": message}), 500`

### Integration Points
- `webconfig/app/__init__.py` — Register new wake_word blueprint
- `webconfig/app/routes/system.py` CONFIG_KEYS — Add 5 wake word keys
- `core/hotword.controller` — All status/config/event routes wrap this singleton
- `core/trigger` — Test endpoint calls trigger_session_start/stop
- `core/audio` — Mic device index and rate info needed for calibration recording

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

*Phase: 02-web-routes-settings*
*Context gathered: 2026-03-23*
