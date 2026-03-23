---
status: diagnosed
phase: milestone-e2e
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 02-01-SUMMARY.md, 02-02-SUMMARY.md, 03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-03-23T16:05:00Z
updated: 2026-03-23T17:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Dashboard loads cleanly
expected: Dashboard loads with no console errors related to wake word. Both Wake Word Settings and Wake Word panel visible.
result: pass

### 2. Wake Word panel status badge
expected: Status badge shows colored state (Listening/Disabled/Paused/Error). Should reflect actual controller state.
result: issue
reported: "Badge always shows Disabled with grey color. Enable toggle is inverted — first press says disabled, second says enabled. Status never updates."
severity: major

### 3. Enable/disable toggle
expected: Flipping toggle shows notification and badge updates within 3 seconds.
result: blocked
blocked_by: prior-phase
reason: "Cross-process issue — webconfig and billy service are separate processes. Wake word routes operate on a local uninitialized controller, not the running one in billy.service."

### 4. Button press starts session
expected: Press physical button, wake-up sound plays, session starts with voice and movement.
result: pass

### 5. Wake word triggers session
expected: Say "Hey Billy", same wake-up sound and session as button press.
result: pass

### 6. Session ends and wake word resumes
expected: After session ends, wake word listening resumes. Say "Hey Billy" again triggers new session.
result: pass

### 7. Simulate Detection button
expected: Click Simulate Detection, notification appears, session starts.
result: blocked
blocked_by: prior-phase
reason: "Cross-process issue — simulate calls trigger_session_start on webconfig's process, not billy.service process."

### 8. Stop Session button
expected: Click-to-arm confirmation, session stops.
result: blocked
blocked_by: prior-phase
reason: "Cross-process issue — stop calls trigger_session_stop on webconfig's process."

### 9. Refresh Status button
expected: Click Refresh Status, notification appears, badge updates.
result: blocked
blocked_by: prior-phase
reason: "Cross-process issue — reads from local controller, not billy.service controller."

### 10. Event log populates
expected: Events appear with timestamps after detections. Scrollable, up to 50 events.
result: blocked
blocked_by: prior-phase
reason: "Cross-process issue — event queue is in billy.service process, webconfig drains its own empty queue."

### 11. Wake Word Settings form fields
expected: Enable checkbox, sensitivity, threshold, endpoint path, access key with visibility toggle.
result: pass

### 12. Settings save persists wake word config
expected: Change sensitivity, save, refresh — value persists.
result: pass

### 13. Calibration wizard — Measure Background
expected: Click Measure Background, countdown, results grid with RMS metrics.
result: blocked
blocked_by: prior-phase
reason: "Cross-process issue — calibration records audio in webconfig process but needs to pause wake word listener in billy.service process."

### 14. Calibration wizard — Record Wake Phrase
expected: Auto-advance to step 2, record, results update.
result: blocked
blocked_by: prior-phase
reason: "Depends on calibration step 1 working."

### 15. Calibration wizard — Apply Suggestions
expected: Auto-advance to step 3, persist checkbox checked, apply works.
result: blocked
blocked_by: prior-phase
reason: "Depends on calibration steps 1-2 working."

### 16. Config validation at startup
expected: No warnings about invalid config values in billy service logs at startup.
result: pass

### 17. GET /wake-word/status API
expected: Returns JSON with controller state fields.
result: pass

### 18. GET /wake-word/events API
expected: Returns JSON array of events.
result: pass

## Summary

total: 18
passed: 8
issues: 1
pending: 0
skipped: 0
blocked: 9

## Gaps

- truth: "Wake word panel status badge reflects actual controller state and toggle controls the running controller"
  status: failed
  reason: "User reported: Badge always shows Disabled. Toggle inverted. Cross-process architecture — webconfig runs separate Python process from billy.service, so core.hotword.controller in webconfig is an uninitialized local instance, not the live controller."
  severity: major
  test: 2
  root_cause: "webconfig/app/routes/wake_word.py imports core.hotword.controller but gets a process-local instance. billy.service (main.py) runs the actual controller in a different process. No IPC mechanism exists between them."
  artifacts:
    - path: "webconfig/app/routes/wake_word.py"
      issue: "All routes operate on process-local controller singleton, not billy.service controller"
    - path: "core/hotword.py"
      issue: "Module-level singleton is per-process — cannot be shared across systemd services"
  missing:
    - "IPC mechanism between webconfig and billy.service (MQTT relay, unix socket, shared file, or merge into single process)"
  debug_session: ""
