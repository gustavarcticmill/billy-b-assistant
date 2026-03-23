---
phase: 01-core-integration
plan: 02
subsystem: session-resilience
tags: [asyncio, aiohttp, websocket, deadlock-prevention, timeout, home-assistant]

# Dependency graph
requires:
  - phase: 01-core-integration/01
    provides: "trigger abstraction and session start/stop in button.py"
provides:
  - "SRES-01: playback_done_event always set on all code paths (prevents mic deadlock)"
  - "SRES-02: Dead websocket detection via consecutive timeout counter with auto-teardown"
  - "SRES-03: Double-stop prevention in mic timeout checker"
  - "HARE-01: 5-second timeout on Home Assistant conversation API calls"
  - "HARE-02: HA availability cache (30s cool-down after failure)"
affects: [01-core-integration/03, session-manager, wake-word-trigger]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Consecutive failure counter with threshold-based teardown"
    - "Availability cache with TTL for external service calls"
    - "_stopping guard pattern for async double-invocation prevention"

key-files:
  created: []
  modified:
    - core/audio.py
    - core/ha.py
    - core/session_manager.py
    - core/session/mic_manager_wrapper.py

key-decisions:
  - "Used asyncio.create_task for teardown in send path to avoid deadlock with ws_lock"
  - "30s HA cache TTL balances fast recovery with avoiding repeated timeout waste"
  - "Checked session._stopping directly rather than adding a public method (minimal change)"

patterns-established:
  - "Consecutive timeout counter: track failures, tear down after threshold"
  - "Availability cache: mark external service down for TTL after failure"

requirements-completed: [SRES-01, SRES-02, SRES-03, HARE-01, HARE-02]

# Metrics
duration: 4min
completed: 2026-03-23
---

# Phase 01 Plan 02: Session & HA Resilience Summary

**Five defensive fixes: playback deadlock guard, dead websocket auto-teardown, double-stop prevention, HA 5s timeout, and HA 30s availability cache**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T11:51:50Z
- **Completed:** 2026-03-23T11:56:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- SRES-01: play_random_wake_up_clip now sets playback_done_event on all code paths, preventing mic start deadlock when no clips exist
- SRES-02: _ws_send_json tracks consecutive send timeouts and auto-tears down session after 3 failures (dead websocket detection)
- SRES-03: Mic timeout checker skips stop_session() if session is already stopping, preventing double-stop race condition
- HARE-01: Home Assistant conversation API calls now have explicit 5-second timeout via aiohttp.ClientTimeout
- HARE-02: After HA failure, availability is cached as "down" for 30s, avoiding repeated timeout waste
- Replaced all print() calls with logger in play_random_wake_up_clip and ha.py (follows project conventions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix playback deadlock and HA resilience** - `f78d971` (fix)
2. **Task 2: Fix dead websocket detection and double-stop race** - `060ca84` (fix)

## Files Created/Modified
- `core/audio.py` - SRES-01: playback_done_event.set() on empty clips path; print->logger migration
- `core/ha.py` - HARE-01: 5s aiohttp timeout; HARE-02: _ha_unavailable_until cache with 30s TTL
- `core/session_manager.py` - SRES-02: _consecutive_send_timeouts counter, _DEAD_WS_THRESHOLD=3, auto-teardown via create_task
- `core/session/mic_manager_wrapper.py` - SRES-03: _stopping guard before stop_session() in timeout_checker

## Decisions Made
- Used `asyncio.create_task(self.stop_session())` for teardown in _ws_send_json to avoid deadlocking on ws_lock (the send path already holds or is attempting the lock)
- Set HA cache TTL to 30 seconds: long enough to avoid hammering a down HA instance, short enough to recover quickly
- Accessed `session._stopping` directly from mic_manager_wrapper rather than adding a public method, keeping the change minimal and localized

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff SIM103 lint warning in ha_available()**
- **Found during:** Task 1 (ha.py rewrite)
- **Issue:** Ruff flagged redundant if/return True pattern in ha_available()
- **Fix:** Changed `if _time.time() < _ha_unavailable_until: return False; return True` to `return _time.time() >= _ha_unavailable_until`
- **Files modified:** core/ha.py
- **Verification:** ruff check passed
- **Committed in:** f78d971 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - code style)
**Impact on plan:** Trivial style adjustment, no scope change.

## Issues Encountered
- dotenv module not installed in worktree, preventing module-level import verification. Used AST parsing and string-based source inspection as alternative verification. All files parse as valid Python and pass ruff lint.
- ruff was not installed; installed it during execution to ensure lint compliance.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All five resilience fixes are in place, protecting session lifecycle from deadlock, silent failure, and HA timeout issues
- Plan 03 (wake word trigger integration) can now safely wire up wake word sessions knowing these failure modes are guarded

## Self-Check: PASSED

All 4 modified files exist. Both task commits (f78d971, 060ca84) found in git log. SUMMARY.md created.

---
*Phase: 01-core-integration*
*Completed: 2026-03-23*
