# Phase 2: Web Routes & Settings - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 02-Web Routes & Settings
**Areas discussed:** Calibration recording, Event delivery model, Settings integration, Blueprint structure

---

## Calibration recording

### Recording approach

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous with timeout | POST blocks for fixed duration, returns RMS metrics. Matches mic check pattern. | ✓ |
| Async with polling | POST starts recording, returns session ID. Client polls for completion. | |
| You decide | Claude picks. | |

**User's choice:** Synchronous with timeout

### Listener during calibration

| Option | Description | Selected |
|--------|-------------|----------|
| Pause during calibration | notify_session_state(True) to free mic. Same pattern as session handoff. | ✓ |
| Use separate stream | Second mic stream alongside wake word. Risky on Pi. | |
| You decide | Claude picks. | |

**User's choice:** Pause during calibration

---

## Event delivery model

### SSE vs polling

| Option | Description | Selected |
|--------|-------------|----------|
| Polling only for now | GET /wake-word/events drains queue, returns JSON. Phase 3 polls on interval. | ✓ |
| Both polling and SSE | Add SSE stream endpoint alongside polling. More work, saves Phase 3 effort. | |
| You decide | Claude picks. | |

**User's choice:** Polling only for now

---

## Settings integration

### Save flow

| Option | Description | Selected |
|--------|-------------|----------|
| Add to CONFIG_KEYS | Append 5 wake word keys to existing list. One save button, unified flow. | ✓ |
| Separate save endpoint | POST /wake-word/save-settings. Self-contained but second save flow. | |
| You decide | Claude picks. | |

**User's choice:** Add to CONFIG_KEYS

---

## Blueprint structure

### File organization

| Option | Description | Selected |
|--------|-------------|----------|
| Single file | One wake_word.py with all 6 routes. Follows audio.py/system.py pattern. | ✓ |
| Split by concern | Separate wake_word.py and wake_word_calibration.py. | |
| You decide | Claude picks. | |

**User's choice:** Single file

---

## Claude's Discretion

- Recording durations for ambient vs phrase calibration
- RMS computation approach
- JSON response shapes
- Error response format and HTTP status codes
- Runtime config update mechanics

## Deferred Ideas

None — discussion stayed within phase scope.
