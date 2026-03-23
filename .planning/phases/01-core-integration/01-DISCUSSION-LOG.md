# Phase 1: Core Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 01-Core Integration
**Areas discussed:** Trigger refactoring, Mic handoff timing, Config validation scope, Merge breakage approach

---

## Trigger refactoring

### Refactoring scope

| Option | Description | Selected |
|--------|-------------|----------|
| Extract functions only | Pull trigger_session_start/stop out of on_button() as standalone functions in button.py. Lowest risk. | |
| New trigger module | Create core/trigger.py with session trigger abstraction. Cleaner separation. | ✓ |
| Minimal inline changes | Add source parameter to on_button(). Least code change but no clean abstraction. | |

**User's choice:** New trigger module
**Notes:** User preferred cleaner separation over minimal risk.

### Initialization location

| Option | Description | Selected |
|--------|-------------|----------|
| In start_loop() | After audio.detect_devices() in button.py's start_loop(). Keeps startup in one place. | ✓ |
| In main.py | Initialize alongside other daemon threads. Separates concerns but splits startup logic. | |
| You decide | Claude picks during planning. | |

**User's choice:** In start_loop()

### is_pressed guard handling

| Option | Description | Selected |
|--------|-------------|----------|
| Source-aware guard | button.is_pressed check only applies to hardware source. Wake word and ui-test skip it. | ✓ |
| Remove is_pressed entirely | Replace guard with trigger-source validation. Physical button state irrelevant with abstraction. | |
| You decide | Claude determines guard approach. | |

**User's choice:** Source-aware guard

### Debounce strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Independent per-source | Each source tracks its own last_trigger_time with 0.5s debounce. | |
| Global debounce | Any trigger source resets global debounce timer. Simpler but could cause missed triggers. | ✓ |
| You decide | Claude picks debounce strategy. | |

**User's choice:** Global debounce
**Notes:** User preferred simplicity. Global debounce also prevents both sources triggering near-simultaneously.

---

## Mic handoff timing

### Mic release strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Notify then delay | notify_session_state(True) closes stream, wait 50-100ms delay, then session opens mic. | ✓ |
| Notify with callback | notify_session_state closes stream and invokes callback when confirmed released. Requires modifying hotword.py. | |
| You decide | Claude determines mechanism. | |

**User's choice:** Notify then delay

### Post-session resume

| Option | Description | Selected |
|--------|-------------|----------|
| Short cooldown | Wait ~1-2s after session teardown before resuming wake word. Prevents self-triggering. | |
| Immediate resume | Call notify_session_state(False) right away. Rely on controller's 2.0s cooldown_seconds. | ✓ |
| You decide | Claude picks resume strategy. | |

**User's choice:** Immediate resume
**Notes:** Controller's built-in cooldown_seconds (2.0s) provides sufficient self-trigger prevention.

### Stream reopen failure

| Option | Description | Selected |
|--------|-------------|----------|
| Log + retry once | Log warning, wait 500ms, retry. If still fails, disable wake word. Button still works. | ✓ |
| Silent degrade | Log error and disable wake word. No retry. User re-enables from web UI or restart. | |
| You decide | Claude picks recovery strategy. | |

**User's choice:** Log + retry once

---

## Config validation scope

### Validation location

| Option | Description | Selected |
|--------|-------------|----------|
| In config.py at load time | Validate where values are loaded. Range-checked helpers. Catches issues at startup. | ✓ |
| Separate validation pass | Load all values first, then validate_config() checks ranges. Easier to test. | |
| You decide | Claude picks approach. | |

**User's choice:** In config.py at load time

### Values to validate

| Option | Description | Selected |
|--------|-------------|----------|
| Just the listed ones | MIC_TIMEOUT_SECONDS, FLASK_PORT, thresholds, sensitivity, CHUNK_MS. Only CONF-01 mentioned values. | ✓ |
| All numeric values | Every int/float in config.py. More thorough but larger change. | |
| You decide | Claude determines which values. | |

**User's choice:** Just the listed ones

---

## Merge breakage approach

### Discovery strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Fix-as-found during integration | Catalogue breakages as encountered during wake word wiring and resilience fixes. | ✓ |
| Dedicated scan first | Systematic sweep before integration: import checks, route registration, template refs. | |
| You decide | Claude picks strategy. | |

**User's choice:** Fix-as-found during integration

### Out-of-scope breakages

| Option | Description | Selected |
|--------|-------------|----------|
| Fix if small, defer if large | Quick fixes inline, larger issues catalogued for later phases. | |
| Fix everything found | Any breakage gets fixed immediately regardless of scope. | ✓ |
| Catalogue only | Don't fix outside files being actively modified. Strictly catalogue. | |

**User's choice:** Fix everything found
**Notes:** User prefers a fully working state over strict phase scoping.

---

## Claude's Discretion

- core/trigger.py internals (class vs functions, lock strategy)
- Exact ALSA delay value (50-100ms range)
- Session resilience fix implementations (SRES-01, SRES-02, SRES-03)
- HA resilience implementations (HARE-01, HARE-02)
- Wake-up sound integration with wake word trigger

## Deferred Ideas

None — discussion stayed within phase scope.
