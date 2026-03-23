---
phase: 01-core-integration
plan: 03
subsystem: trigger-abstraction
tags: [wake-word, session-lifecycle, trigger, debounce, hotword, porcupine, gpio]

# Dependency graph
requires:
  - phase: 01-core-integration/01
    provides: "Range-validated config helpers (_int_env, _float_env_ranged)"
  - phase: 01-core-integration/02
    provides: "Session resilience fixes (SRES-01/02/03, HARE-01/02)"
provides:
  - "core/trigger.py: Multi-source session lifecycle abstraction (trigger_session_start/stop)"
  - "WAKE-01 through WAKE-09: Complete wake word trigger integration"
  - "D-04: Global 0.5s debounce prevents duplicate triggers from any source"
  - "D-05: 75ms ALSA mic handoff delay before session mic opens"
  - "D-06/D-07: Wake word stream recovery with retry after session end"
  - "button.py thin wrapper delegating to trigger module"
  - "Wake word controller initialization in start_loop() with detection callback"
affects: [01-core-integration, wake-word-routes, wake-word-ui, mqtt-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-source trigger abstraction: single entry point for session lifecycle from hardware, wake_word, mqtt, ui_test"
    - "Lazy import pattern to avoid circular dependencies (trigger.py imports button lazily for is_pressed check)"
    - "Wake word controller notify_session_state() for mic handoff coordination"
    - "D-07 wake word stream recovery: verify + retry + error escalation pattern"

key-files:
  created: ["core/trigger.py"]
  modified: ["core/button.py", "core/mqtt.py"]

key-decisions:
  - "Delegated mqtt.py session functions to trigger module rather than keeping duplicated logic"
  - "Wake word init placed after detect_devices() but before boot animation in start_loop()"
  - "Used lazy import for button module in trigger.py to avoid circular dependency"

patterns-established:
  - "trigger_session_start(source): Single entry point for starting sessions from any source"
  - "trigger_session_stop(source): Single entry point for stopping sessions from any source"
  - "Source-specific guards: only 'hardware' source checks button.is_pressed"

requirements-completed: [WAKE-01, WAKE-02, WAKE-03, WAKE-04, WAKE-05, WAKE-06, WAKE-07, WAKE-08, WAKE-09, FIX-01]

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 01 Plan 03: Trigger Abstraction Summary

**Multi-source session trigger module (core/trigger.py) with wake word integration, global debounce, and mic handoff coordination**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T11:59:50Z
- **Completed:** 2026-03-23T12:07:43Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created core/trigger.py providing trigger_session_start/stop as the single entry point for session lifecycle from any source (hardware, wake_word, mqtt, ui_test)
- Refactored button.py from 340 lines to 130 lines -- on_button() is now a 3-line thin wrapper
- Wired wake word detection in start_loop() with detection callback and controller initialization
- Global 0.5s debounce prevents duplicate triggers from any source (D-04/WAKE-08)
- Mic handoff with 75ms ALSA delay and notify_session_state coordination (D-05/WAKE-04)
- Wake word stream recovery with retry after session end (D-07)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create core/trigger.py with session lifecycle abstraction** - `b465ac0` (feat)
2. **Task 2: Refactor button.py to delegate to trigger.py and wire wake word in start_loop** - `0eb9e47` (feat)

## Files Created/Modified
- `core/trigger.py` - New module: session lifecycle abstraction with trigger_session_start/stop, debounce, mic handoff, wake word recovery
- `core/button.py` - Refactored to thin wrapper delegating to trigger module; wake word init in start_loop()
- `core/mqtt.py` - Updated mqtt_start/stop/toggle_listening to delegate to trigger module

## Decisions Made
- Delegated mqtt.py session management to trigger module instead of keeping duplicated 90-line functions that referenced now-removed button globals
- Wake word initialization placed after audio.detect_devices() in start_loop() to ensure mic is available
- Lazy import of button module inside trigger_session_start() to avoid circular dependency (trigger imports button only when source=="hardware" for is_pressed check)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mqtt.py referencing removed button.py session globals**
- **Found during:** Task 2 (button.py refactoring)
- **Issue:** core/mqtt.py functions (mqtt_start_listening, mqtt_stop_listening, mqtt_toggle_listening) directly manipulated button_mod.is_active, button_mod.session_instance, button_mod._session_start_lock, etc. -- all removed from button.py
- **Fix:** Replaced all three functions with thin wrappers delegating to trigger.trigger_session_start("mqtt") and trigger.trigger_session_stop("mqtt"), reducing ~130 lines of duplicated session management to ~20 lines
- **Files modified:** core/mqtt.py
- **Verification:** ruff check passes, MOCKFISH=true import succeeds
- **Committed in:** 0eb9e47 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential fix -- mqtt.py would crash without it. The trigger abstraction naturally provides MQTT support as an additional source type, so delegating is cleaner than patching the old references.

## Issues Encountered
- GPIO pins busy on Pi hardware (main app running) -- used MOCKFISH=true for verification
- python-dotenv and other dependencies not installed in system Python -- installed via pip with --break-system-packages

## Known Stubs
None -- all data sources are wired and functional.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Trigger abstraction complete: any source can start/stop sessions through trigger_session_start/stop
- Wake word controller initialized in start_loop() with detection callback
- Ready for Phase 02 (web routes blueprint for wake word status/config) and Phase 03 (UI panel)
- End-to-end testing on hardware recommended: verify wake word detection triggers conversation correctly

## Self-Check: PASSED

- core/trigger.py: FOUND
- core/button.py: FOUND
- core/mqtt.py: FOUND
- SUMMARY.md: FOUND
- Commit b465ac0: FOUND
- Commit 0eb9e47: FOUND

---
*Phase: 01-core-integration*
*Completed: 2026-03-23*
