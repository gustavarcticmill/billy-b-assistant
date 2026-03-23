---
phase: 02-web-routes-settings
plan: 01
subsystem: api
tags: [flask, blueprint, wake-word, calibration, sounddevice, dotenv]

# Dependency graph
requires:
  - phase: 01-core-integration
    provides: "core/hotword.py WakeWordController, core/trigger.py session lifecycle"
provides:
  - "Wake word HTTP API: status, events, runtime-config, test, calibrate, calibrate/apply"
  - "Blueprint registered in Flask app factory"
affects: [02-web-routes-settings, 03-ui-panel]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Lazy core imports inside route functions for hardware isolation"]

key-files:
  created:
    - webconfig/app/routes/wake_word.py
  modified:
    - webconfig/app/__init__.py

key-decisions:
  - "ENV_PATH imported from .system module to avoid duplicating dotenv path logic"
  - "All core imports (hotword, trigger) are lazy inside route functions to prevent import errors when webconfig runs standalone"
  - "No url_prefix on blueprint -- follows existing pattern of absolute paths in route decorators"

patterns-established:
  - "Lazy core imports: hardware-dependent modules imported inside route functions with try/except"
  - "Calibration mic handoff: notify_session_state(True) before recording, notify_session_state(False) in finally block"

requirements-completed: [WWEB-01, WWEB-02, WWEB-03, WWEB-04, WWEB-05, WWEB-06, WWEB-07]

# Metrics
duration: 2min
completed: 2026-03-23
---

# Phase 2 Plan 1: Wake Word Routes Summary

**Flask blueprint with 6 wake word route handlers (status, events, runtime-config, test, calibrate, calibrate/apply) registered in app factory**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T13:11:07Z
- **Completed:** 2026-03-23T13:13:57Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created wake word blueprint with all 6 route handlers covering WWEB-01 through WWEB-06
- Registered blueprint in Flask app factory (WWEB-07)
- All core module imports are lazy inside route functions to prevent import errors on non-hardware environments

## Task Commits

Each task was committed atomically:

1. **Task 1: Create wake word blueprint with all 6 route handlers** - `26812c3` (feat)
2. **Task 2: Register wake word blueprint in Flask app factory** - `fa4e60a` (feat)

## Files Created/Modified
- `webconfig/app/routes/wake_word.py` - All 6 wake word route handlers (status, events, runtime-config, test, calibrate, calibrate/apply)
- `webconfig/app/__init__.py` - Added wake_word_bp import and registration

## Decisions Made
- ENV_PATH imported from .system module rather than duplicating the dotenv path discovery logic
- All core module imports (hotword.controller, trigger) are lazy inside route functions -- prevents import errors when webconfig runs without hardware
- No url_prefix on blueprint, consistent with all existing blueprints using absolute paths in route decorators
- Events endpoint caps at 50 items using get_nowait() to prevent blocking
- Calibration route pauses wake word listener via notify_session_state(True) and resumes in a finally block

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 6 wake word API endpoints are available for the settings form (plan 02-02) and Phase 3 UI panel
- Blueprint registration in app factory means routes are active on next server restart
- Calibration and runtime-config routes persist changes to .env and update controller in real time

## Self-Check: PASSED

- All created files exist on disk
- All commit hashes found in git log
- No stubs or placeholders detected

---
*Phase: 02-web-routes-settings*
*Completed: 2026-03-23*
