# Phase 3: UI Panel - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Wake word dashboard panel with live status badge, enable/disable toggle, sensitivity/threshold controls, simulate/stop/refresh buttons, scrollable event log, and 3-step calibration wizard. Users can configure, monitor, and calibrate wake word detection entirely through the web dashboard.

</domain>

<decisions>
## Implementation Decisions

### Event log polling
- **D-01:** Poll GET /wake-word/events every 2 seconds. Faster than existing service-status (5s) because detection events are time-sensitive.
- **D-02:** Auto-scroll to latest event unless user has scrolled up to read history. Resume auto-scroll when user scrolls back to bottom.

### Calibration wizard UX
- **D-03:** Countdown timer with status text during recording — "3... 2... 1..." countdown, status text changes ("Recording ambient noise...", "Say the wake word now..."), button disabled during recording.
- **D-04:** Auto-advance between wizard steps. After "Measure Background" completes, results show briefly then auto-advance to "Record Wake Phrase". After that completes, results grid and "Apply Suggestions" button appear.
- **D-05:** "Persist to .env" checkbox is checked by default on the Apply Suggestions step. Most users want calibration to persist across reboots.

### Status badge updates
- **D-06:** Poll GET /wake-word/status every 3 seconds. Separate from event poll (2s). Badge color updates on each response reflecting Listening/Disabled/Paused/Error/Unavailable states.

### Panel template structure
- **D-07:** New template component file `webconfig/templates/components/wake-word-panel.html`. Separate include following the pattern of audio-panel, profile-panel. Included via Jinja2 `{% include %}`.
- **D-08:** Panel placed after Audio Settings, before MQTT in the dashboard layout. Wake word is audio-adjacent functionality.

### Claude's Discretion
- Exact badge color mapping for each state (Listening/Disabled/Paused/Error/Unavailable)
- Event log entry format and styling (timestamp, event type, details)
- Calibration results grid layout (ambient RMS, peak, suggested threshold, wake phrase peak)
- Auto-advance delay between wizard steps (how long results display before next step)
- Polling start/stop lifecycle (pause when panel collapsed? resume on expand?)
- How enable/disable toggle calls the runtime-config endpoint

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and scope
- `.planning/REQUIREMENTS.md` — WWUI-01 through WWUI-10 (wake word UI panel)
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, dependency on Phase 2
- `.planning/PROJECT.md` — Constraints: IIFE JS module pattern, same Tailwind classes, follow existing patterns

### UI design contract
- `.planning/phases/02-web-routes-settings/02-UI-SPEC.md` — Visual specs, typography, color, spacing, component patterns for wake word UI elements

### Existing code patterns
- `webconfig/static/js/audio-panel.js` — IIFE module pattern, fetch-based API calls, `showNotification()` usage (reference implementation for panel JS)
- `webconfig/static/js/sections.js` — Collapsible section pattern with localStorage persistence, Material Icons, emerald-400 active state
- `webconfig/static/js/ui-helpers.js` — `showNotification()`, `toggleInputVisibility()`, shared utilities
- `webconfig/static/js/service-status.js` — Polling pattern with setInterval (reference for status/event polling)
- `webconfig/templates/components/settings-panel.html` — Panel include pattern, collapsible section HTML structure
- `webconfig/app/routes/wake_word.py` — Phase 2 route handlers the UI consumes (status, events, runtime-config, test, calibrate, calibrate/apply)

### Prior phase decisions
- `.planning/phases/02-web-routes-settings/02-CONTEXT.md` — D-05: polling-only events, D-06: CONFIG_KEYS integration

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AudioPanel` IIFE pattern — Direct reference for WakeWordPanel structure (fetch, DOM manipulation, event listeners)
- `Sections.collapsible()` — Handles all collapsible section init (expand/collapse, localStorage, icon rotation)
- `showNotification(msg, type)` from ui-helpers.js — Toast notifications for success/error/warning
- `toggleInputVisibility(el)` from ui-helpers.js — Password visibility toggle (reuse for access key field)
- `ConfigService` from config-service.js — Config caching if needed for pre-filling form values

### Established Patterns
- IIFE module: `const WakeWordPanel = (() => { ... return { init }; })();`
- DOM init: `document.addEventListener("DOMContentLoaded", () => WakeWordPanel.init());`
- Collapsible sections: `<div class="collapsible-section" id="section-wake-word">` with h3 header + Material Icon
- Fetch pattern: `await fetch("/wake-word/status")` with try/catch and showNotification on error
- Polling: `setInterval(pollFunction, intervalMs)` with clearInterval on cleanup

### Integration Points
- `webconfig/templates/index.html` — Add `{% include 'components/wake-word-panel.html' %}` after audio section
- `webconfig/static/js/init.js` — May need to add WakeWordPanel.init() call if not using DOMContentLoaded in the module
- Phase 2 API endpoints: GET /wake-word/status, GET /wake-word/events, POST /wake-word/runtime-config, POST /wake-word/test, POST /wake-word/calibrate, POST /wake-word/calibrate/apply

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

*Phase: 03-ui-panel*
*Context gathered: 2026-03-23*
