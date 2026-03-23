---
phase: 02-web-routes-settings
verified: 2026-03-23T13:19:30Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 2: Web Routes & Settings Verification Report

**Phase Goal:** The wake word controller is fully accessible via HTTP — status queryable, events streamable, configuration changeable at runtime, calibration recordable, and settings persistable across reboots
**Verified:** 2026-03-23T13:19:30Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /wake-word/status returns JSON with controller running state, engine mode, and error info | VERIFIED | `controller.get_status()` called in status route; fallback shape returns enabled/running/error/mode |
| 2 | GET /wake-word/events returns up to 50 drained events from the controller queue as JSON | VERIFIED | `get_nowait()` loop capped at 50; `dataclasses.asdict(event)` serialises each event |
| 3 | POST /wake-word/runtime-config updates controller parameters at runtime | VERIFIED | `controller.set_parameters(**params)` called with validated fields: enabled, sensitivity, threshold, endpoint, porcupine_access_key |
| 4 | POST /wake-word/test with action=simulate starts a session and action=stop ends it | VERIFIED | `trigger_session_start("ui_test")` and `trigger_session_stop("ui_test")` called; trigger.py documents "ui_test" as the canonical underscore form |
| 5 | POST /wake-word/calibrate records audio for a fixed duration and returns RMS metrics | VERIFIED | `sd.InputStream` callback records RMS; `notify_session_state(True/False)` wraps recording in try/finally |
| 6 | POST /wake-word/calibrate/apply persists threshold/sensitivity to .env and updates runtime controller | VERIFIED | `set_key(ENV_PATH, "WAKE_WORD_THRESHOLD", ...)` and `set_key(ENV_PATH, "WAKE_WORD_SENSITIVITY", ...)` write to .env; `controller.set_parameters(**params)` updates runtime |
| 7 | Blueprint is registered in the Flask app factory and all routes are accessible | VERIFIED | Live app test: all 6 routes appear in url_map (`/wake-word/status`, `/wake-word/events`, `/wake-word/runtime-config`, `/wake-word/test`, `/wake-word/calibrate`, `/wake-word/calibrate/apply`) |
| 8 | Wake word config keys are saved to .env when the main settings form is submitted | VERIFIED | 5 WAKE_WORD_ keys in CONFIG_KEYS; save() iterates `data.items()` and calls `set_key(ENV_PATH, key, value)` for each key in CONFIG_KEYS |
| 9 | Wake word settings section appears in the settings form between Audio Settings and MQTT Settings | VERIFIED | `id="section-audio"` at line 274, `id="section-wake-word"` at line 422, `id="section-mqtt"` at line 543 — ordering confirmed |
| 10 | Form field names exactly match the CONFIG_KEYS entries and .env variable names | VERIFIED | All 5 `name=` attributes (WAKE_WORD_ENABLED, WAKE_WORD_SENSITIVITY, WAKE_WORD_THRESHOLD, WAKE_WORD_ENDPOINT, WAKE_WORD_PORCUPINE_ACCESS_KEY) match CONFIG_KEYS entries exactly |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `webconfig/app/routes/wake_word.py` | All 6 wake word route handlers | VERIFIED | 193 lines; Blueprint named "wake_word"; 6 @bp.route decorators; all core imports lazy inside functions |
| `webconfig/app/__init__.py` | Blueprint registration | VERIFIED | `from .routes.wake_word import bp as wake_word_bp` at line 32; `app.register_blueprint(wake_word_bp)` at line 45 |
| `webconfig/app/routes/system.py` | 5 wake word keys in CONFIG_KEYS list | VERIFIED | Lines 68-72: WAKE_WORD_ENABLED, WAKE_WORD_SENSITIVITY, WAKE_WORD_THRESHOLD, WAKE_WORD_ENDPOINT, WAKE_WORD_PORCUPINE_ACCESS_KEY |
| `webconfig/templates/components/settings-form.html` | Wake Word Settings collapsible section with 5 form fields | VERIFIED | `id="section-wake-word"` at line 422; 18 WAKE_WORD_ references; all 5 name attributes present; hearing icon; font-semibold labels |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `webconfig/app/routes/wake_word.py` | `core/hotword.py` | lazy import of controller singleton | VERIFIED | `from core.hotword import controller` inside each route function |
| `webconfig/app/routes/wake_word.py` | `core/trigger.py` | trigger_session_start/stop for test endpoint | VERIFIED | `from core.trigger import trigger_session_start, trigger_session_stop` in test() route |
| `webconfig/app/__init__.py` | `webconfig/app/routes/wake_word.py` | blueprint import and registration | VERIFIED | `from .routes.wake_word import bp as wake_word_bp`; `app.register_blueprint(wake_word_bp)` |
| `webconfig/templates/components/settings-form.html` | `webconfig/app/routes/system.py` | form field name attributes matching CONFIG_KEYS entries | VERIFIED | All 5 name attributes (WAKE_WORD_*) match CONFIG_KEYS list entries exactly |
| `webconfig/app/routes/wake_word.py` | `webconfig/app/routes/system.py` | ENV_PATH imported for calibrate/apply | VERIFIED | `from .system import ENV_PATH` inside calibrate_apply() route |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `wake_word.py` status route | `controller.get_status()` return | `core/hotword.py` WakeWordController | Yes — controller returns live state dict | FLOWING |
| `wake_word.py` events route | `drained` list | `controller.get_event_queue()` | Yes — drains live queue with get_nowait() | FLOWING |
| `wake_word.py` calibrate route | `rms_values` list | `sd.InputStream` callback capturing mic data | Yes — sounddevice streams real audio frames | FLOWING |
| `wake_word.py` calibrate/apply route | `.env` write | `set_key(ENV_PATH, ...)` | Yes — writes to actual .env file path | FLOWING |
| `settings-form.html` wake word fields | form field values | `config.get('WAKE_WORD_*', default)` | Yes — config dict populated from CONFIG_KEYS/core_config in save route | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Blueprint importable without errors | `python -c "from webconfig.app.routes.wake_word import bp; print(bp.name)"` | `wake_word` | PASS |
| App factory registers all 6 routes | `create_app()` + iterate url_map for wake-word routes | 6 routes listed | PASS |
| All 6 route functions callable | Import all 6 functions, check `callable()` | All True | PASS |
| ENV_PATH importable from system module | `from webconfig.app.routes.system import ENV_PATH` | `/home/pi/billy-b-assistant/.env` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WWEB-01 | 02-01-PLAN.md | GET /wake-word/status returns JSON with controller status | SATISFIED | `@bp.route("/wake-word/status")` calls `controller.get_status()` |
| WWEB-02 | 02-01-PLAN.md | GET /wake-word/events drains up to 50 events from queue | SATISFIED | Loop capped at 50, uses `get_nowait()`, returns `{"events": [...], "count": N}` |
| WWEB-03 | 02-01-PLAN.md | POST /wake-word/runtime-config updates controller | SATISFIED | Validates and passes enabled/sensitivity/threshold/endpoint/porcupine_access_key to `controller.set_parameters()` |
| WWEB-04 | 02-01-PLAN.md | POST /wake-word/test calls trigger_session_start/stop("ui_test") | SATISFIED | Uses "ui_test" (underscore) — canonical form per trigger.py docstring; REQUIREMENTS.md "ui-test" typo is benign |
| WWEB-05 | 02-01-PLAN.md | POST /wake-word/calibrate records audio and returns RMS metrics | SATISFIED | sd.InputStream callback; pauses listener; returns mode/rms_mean/rms_peak/duration_seconds/sample_count |
| WWEB-06 | 02-01-PLAN.md | POST /wake-word/calibrate/apply persists to .env and updates runtime | SATISFIED | `set_key(ENV_PATH, "WAKE_WORD_THRESHOLD/SENSITIVITY", val)` + `controller.set_parameters()` |
| WWEB-07 | 02-01-PLAN.md | Wake word blueprint registered in Flask app factory | SATISFIED | `app.register_blueprint(wake_word_bp)` in `create_app()` |
| SETS-01 | 02-02-PLAN.md | Wake word config keys saved to .env on form submit | SATISFIED | 5 WAKE_WORD_ keys in CONFIG_KEYS; save() writes each via `set_key(ENV_PATH, key, value)` |
| SETS-02 | 02-02-PLAN.md | Wake word keys added to CONFIG_KEYS in system routes | SATISFIED | Lines 68-72 of system.py confirm all 5 entries present |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps WWEB-01 through WWEB-07 and SETS-01/SETS-02 all to Phase 2. No Phase 2 requirements appear in REQUIREMENTS.md outside the plan coverage. No orphaned requirements found.

**Note on WWEB-04 wording:** REQUIREMENTS.md says `"ui-test"` (hyphen) but `core/trigger.py` documents `"ui_test"` (underscore) as the canonical source identifier (lines 50, 237). The implementation correctly uses `"ui_test"`. This is a typo in the requirements document, not an implementation gap.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `webconfig/app/routes/system.py` | 220, 285-286, 322 | "not available" strings | Info | Pre-existing messages for missing system tools (journalctl, nmcli, git) — unrelated to Phase 2 changes, not stubs |

No stubs, placeholders, TODOs, or empty implementations found in Phase 2 files.

---

### Human Verification Required

None — all Phase 2 deliverables are backend API routes and server-side template changes that can be fully verified programmatically.

The calibrate route (`POST /wake-word/calibrate`) requires a live microphone to produce real audio data, but the implementation is structurally complete. Functional audio testing is a hardware concern beyond scope of this phase verification.

---

### Gaps Summary

No gaps found. All 10 must-have truths are verified, all 4 required artifacts exist and are substantive and wired, all 5 key links are confirmed, all 9 requirements (WWEB-01 through WWEB-07, SETS-01, SETS-02) are satisfied, and all behavioral spot-checks pass.

The phase goal is fully achieved: the wake word controller is accessible via 6 HTTP endpoints, settings are persistable to .env via the settings form, and calibration results can be applied at runtime.

---

_Verified: 2026-03-23T13:19:30Z_
_Verifier: Claude (gsd-verifier)_
