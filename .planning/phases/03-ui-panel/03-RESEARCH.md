# Phase 3: UI Panel - Research

**Researched:** 2026-03-23
**Domain:** Frontend UI (Flask/Jinja2 templates, vanilla JavaScript, Tailwind CSS)
**Confidence:** HIGH

## Summary

Phase 3 is a pure frontend implementation phase. It creates a new dashboard panel (HTML template + JS module) that consumes the Phase 2 REST API endpoints. No backend code changes are required. The entire implementation follows well-established patterns already present in the codebase: IIFE JavaScript modules, Jinja2 template includes, Tailwind CSS utility classes, Material Icons, and collapsible sections with localStorage persistence.

The primary complexity lies in the calibration wizard (3-step state machine with countdown timers, auto-advance, and conditional API calls) and the dual polling loops (status at 3s, events at 2s) with smart auto-scroll behavior. All other components (status badge, toggle, action buttons, event log) are straightforward DOM manipulation following existing patterns in `audio-panel.js`, `service-status.js`, and `sections.js`.

**Primary recommendation:** Follow the existing IIFE module pattern exactly. Create two new files (`wake-word-panel.html` and `wake-word-panel.js`) and make three small modifications to existing files (`index.html`, `base.html`, `init.js`). The UI-SPEC provides pixel-perfect HTML/CSS for every component -- the implementation task is primarily wiring up the JavaScript behavior.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Poll GET /wake-word/events every 2 seconds. Faster than existing service-status (5s) because detection events are time-sensitive.
- **D-02:** Auto-scroll to latest event unless user has scrolled up to read history. Resume auto-scroll when user scrolls back to bottom.
- **D-03:** Countdown timer with status text during recording -- "3... 2... 1..." countdown, status text changes ("Recording ambient noise...", "Say the wake word now..."), button disabled during recording.
- **D-04:** Auto-advance between wizard steps. After "Measure Background" completes, results show briefly then auto-advance to "Record Wake Phrase". After that completes, results grid and "Apply Suggestions" button appear.
- **D-05:** "Persist to .env" checkbox is checked by default on the Apply Suggestions step. Most users want calibration to persist across reboots.
- **D-06:** Poll GET /wake-word/status every 3 seconds. Separate from event poll (2s). Badge color updates on each response reflecting Listening/Disabled/Paused/Error/Unavailable states.
- **D-07:** New template component file `webconfig/templates/components/wake-word-panel.html`. Separate include following the pattern of audio-panel, profile-panel. Included via Jinja2 `{% include %}`.
- **D-08:** Panel placed after Audio Settings, before MQTT in the dashboard layout. Wake word is audio-adjacent functionality.

### Claude's Discretion
- Exact badge color mapping for each state (Listening/Disabled/Paused/Error/Unavailable) -- **Resolved in UI-SPEC**: emerald for Listening, zinc for Disabled, amber for Paused, rose for Error, zinc-500 for Unavailable
- Event log entry format and styling -- **Resolved in UI-SPEC**: icon + type + timestamp + detail layout with per-type icon/color mapping
- Calibration results grid layout -- **Resolved in UI-SPEC**: 2x2 grid with bg-zinc-900/50 cards
- Auto-advance delay between wizard steps -- **Resolved in UI-SPEC**: 1500ms
- Polling start/stop lifecycle -- **Resolved in UI-SPEC**: never stop, runs regardless of collapse state
- How enable/disable toggle calls the runtime-config endpoint -- **Resolved in UI-SPEC**: POST /wake-word/runtime-config with { "enabled": true/false }

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WWUI-01 | Enable/disable toggle with listener status badge (Listening/Disabled/Paused/Error/Unavailable) | UI-SPEC provides complete HTML/CSS for status badge and toggle. Status derivation logic documented. Badge colors resolved. Toggle wires to POST /wake-word/runtime-config. |
| WWUI-02 | Porcupine endpoint path and access key input fields | ALREADY IMPLEMENTED in settings-form.html (Phase 2 SETS-01). Fields exist at `WAKE_WORD_ENDPOINT` and `WAKE_WORD_PORCUPINE_ACCESS_KEY`. The dashboard panel does NOT duplicate these -- they are settings-modal fields. Phase 3 panel focuses on runtime control, not configuration form fields. |
| WWUI-03 | Sensitivity slider (0.0-1.0, step 0.05) and RMS threshold input | ALREADY IMPLEMENTED in settings-form.html (Phase 2 SETS-01). Fields exist at `WAKE_WORD_SENSITIVITY` (step 0.05) and `WAKE_WORD_THRESHOLD`. The dashboard panel handles threshold via calibration wizard (Apply Suggestions), not a direct input. |
| WWUI-04 | Simulate Detection / Stop Session / Refresh Status buttons | UI-SPEC provides complete HTML/CSS. Wires to POST /wake-word/test (simulate/stop) and GET /wake-word/status (refresh). Stop Session has click-to-arm confirmation (2s window). |
| WWUI-05 | Event stream display showing last 50 events (scrollable) | UI-SPEC provides complete HTML/CSS for event log container and individual entries. 2s poll interval (D-01). Auto-scroll with suppression (D-02). 50-event client-side cap. |
| WWUI-06 | Calibration wizard: Measure Background -> Record Wake Phrase -> Apply Suggestions | UI-SPEC provides complete HTML/CSS for 3-step wizard with stepper indicators. Auto-advance with 1500ms delay (D-04). Countdown timer during recording (D-03). |
| WWUI-07 | Calibration results grid showing ambient noise RMS, peak, suggested threshold, and wake phrase peak RMS | UI-SPEC provides 2x2 grid layout with metric cards. Suggested threshold highlighted in emerald-400. |
| WWUI-08 | "Apply Suggestions" button with threshold display and "persist to .env" checkbox | UI-SPEC provides complete HTML/CSS for Step 3. Persist checkbox checked by default (D-05). Routes to POST /wake-word/calibrate/apply (persist) or POST /wake-word/runtime-config (runtime-only). |
| WWUI-09 | Panel is collapsible, visually consistent with Audio Settings / MQTT / HA sections | Panel uses `collapsible-section` class with `section-wake-word-panel` ID. Sections.collapsible() handles initialization automatically. UI-SPEC matches existing panel styling. |
| WWUI-10 | JS module follows IIFE pattern, calls WakeWordPanel.init() on DOMContentLoaded | IIFE pattern documented in UI-SPEC. init() called from init.js. Script loaded before sections.js in base.html. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS | 4.1.11 | Utility-first CSS styling | Already in webconfig/package.json, used throughout all templates |
| Material Icons | self-hosted woff2 | Icon library | Already loaded at /static/fonts/material-icons.woff2, used by all panels |
| Vanilla JavaScript | ES6+ | DOM manipulation, fetch API, setInterval | Project convention: no frameworks, IIFE module pattern |
| Flask/Jinja2 | 2.x | HTML templating with includes | Project convention: template components in webconfig/templates/components/ |

### Supporting
No additional libraries needed. This phase uses only what already exists in the project.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| setInterval polling | WebSocket push for events/status | Would add complexity and is inconsistent with existing polling patterns (service-status.js uses polling). CONTEXT.md explicitly chose polling (D-01, D-06). |
| Vanilla JS state machine | Alpine.js or Petite-Vue for wizard reactivity | Project convention mandates IIFE + vanilla JS. Adding a micro-framework would break consistency. |

## Architecture Patterns

### Recommended Project Structure
```
webconfig/
  templates/
    components/
      wake-word-panel.html          # NEW - Jinja2 template include
  static/
    js/
      wake-word-panel.js            # NEW - IIFE module
```

Modified files:
```
webconfig/templates/index.html      # Add {% include %}
webconfig/templates/base.html       # Add <script> tag
webconfig/static/js/init.js         # Add WakeWordPanel.init() call
```

### Pattern 1: IIFE Module (Mandatory)
**What:** Self-contained JavaScript module using Immediately Invoked Function Expression
**When to use:** Every JS file in this project
**Example:**
```javascript
// Source: webconfig/static/js/audio-panel.js (existing pattern)
const WakeWordPanel = (() => {
    // Private state
    let statusInterval = null;
    let eventInterval = null;

    // Private functions
    async function pollStatus() { /* ... */ }
    async function pollEvents() { /* ... */ }

    // Public API
    function init() {
        bindUI();
        startPolling();
    }

    return { init };
})();
```

### Pattern 2: Collapsible Section (Mandatory)
**What:** Panel container with collapsible header managed by Sections.collapsible()
**When to use:** Every dashboard panel
**Example:**
```html
<!-- Source: webconfig/templates/components/settings-form.html (existing pattern) -->
<div class="bg-zinc-900/50 backdrop-blur-xs border border-zinc-700 p-4 rounded-lg shadow-lg mb-4 collapsible-section"
     id="section-wake-word-panel">
    <h3 class="flex items-center gap-2 cursor-pointer group text-lg grow justify-between font-semibold mb-4 text-slate-200 hover:text-emerald-400 transition-colors">
        <!-- icon + title + expand_more chevron -->
    </h3>
    <!-- content children toggled by Sections.collapsible() -->
</div>
```

### Pattern 3: Fetch with Notification (Mandatory)
**What:** All API calls use fetch() with try/catch and showNotification() for user feedback
**When to use:** Every API call in the panel
**Example:**
```javascript
// Source: webconfig/static/js/audio-panel.js, motor-panel.js (existing pattern)
try {
    const res = await fetch("/wake-word/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "simulate" })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    showNotification("Detection simulated", "success");
} catch (err) {
    showNotification("Simulation failed: " + err.message, "error");
}
```

### Pattern 4: Polling with setInterval (Mandatory)
**What:** Periodic API polling using setInterval, following service-status.js pattern
**When to use:** Status badge updates (3s) and event log updates (2s)
**Example:**
```javascript
// Source: webconfig/static/js/service-status.js (existing pattern)
statusInterval = setInterval(pollStatus, 3000);
eventInterval = setInterval(pollEvents, 2000);
```

### Anti-Patterns to Avoid
- **Using font-bold in new code:** The codebase has both font-bold (legacy) and font-semibold. Per UI-SPEC, all new Phase 3 code uses font-semibold exclusively. Do NOT use font-bold.
- **Duplicating collapsible logic:** Do NOT write custom collapse/expand code. Use `collapsible-section` class and let `Sections.collapsible()` handle it.
- **Adding framework dependencies:** Do NOT add Alpine.js, htmx, Petite-Vue, or any JS framework. Vanilla JS only.
- **Using SSE (EventSource):** Although audio-panel.js uses EventSource for mic-check, the wake word panel uses polling per CONTEXT.md decisions D-01/D-06.
- **Creating a new CSS file:** Use Tailwind utility classes inline. No custom CSS needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible sections | Custom collapse/expand with localStorage | `Sections.collapsible()` from sections.js | Already handles init-prevention (data-collapsible-initialized), localStorage persistence, icon rotation, emerald-400 active state |
| Toast notifications | Custom notification system | `showNotification(msg, type)` from ui-helpers.js | Already handles colors (info/success/warning/error), auto-dismiss, z-index |
| Tooltip show/hide | Custom tooltip toggling | `toggleTooltip(el)` from ui-helpers.js | Already handles data-visible, click-outside-to-close |
| Password visibility toggle | Custom input type toggle | `toggleInputVisibility(id)` from ui-helpers.js | Already handles icon swap (visibility/visibility_off) |

**Key insight:** The existing codebase provides all needed UI utilities. Phase 3 only needs to compose these existing pieces with new panel-specific logic (polling, wizard state machine, event log management).

## Common Pitfalls

### Pitfall 1: Section ID Collision
**What goes wrong:** Using `section-wake-word` as the collapsible section ID causes localStorage collision with the settings-form wake word section that uses the same ID.
**Why it happens:** Both the settings modal and dashboard have wake word sections.
**How to avoid:** Use `section-wake-word-panel` as specified in UI-SPEC.
**Warning signs:** Collapsing one section unexpectedly collapses the other.

### Pitfall 2: Script Load Order
**What goes wrong:** `wake-word-panel.js` loads after `sections.js`, so the collapsible section inside the panel template never gets initialized.
**Why it happens:** `Sections.collapsible()` runs once on DOMContentLoaded. If the wake-word-panel script loads after sections.js, the panel's collapsible-section div exists in the DOM but wasn't present when collapsible() first scanned.
**How to avoid:** Load `wake-word-panel.js` BEFORE `sections.js` in base.html as specified in UI-SPEC. Alternatively, since `Sections.collapsible()` is called from `init.js` (after all scripts load), this is actually safe either way -- but the UI-SPEC ordering is the safest approach.
**Warning signs:** Panel header click does not expand/collapse content.

### Pitfall 3: Event Deduplication on Poll
**What goes wrong:** Events drain from the server queue on each GET. If the poll fires while the previous response is still being processed, events could be missed or the client could get confused.
**Why it happens:** The server's `get_event_queue()` drains events destructively (queue.get_nowait). Once drained, they're gone.
**How to avoid:** Events are append-only on the client side. Each poll response returns NEW events only (the server queue accumulates between polls). Simply prepend new events to the client list. No deduplication needed since the server guarantees each event is returned exactly once.
**Warning signs:** Events disappearing from the log or appearing duplicated.

### Pitfall 4: Calibration API Blocking Duration
**What goes wrong:** The POST /wake-word/calibrate endpoint blocks for 3 seconds while recording audio. If the fetch has no timeout, it works but the UI must handle the delay gracefully.
**Why it happens:** Server-side recording is synchronous (time.sleep(3)).
**How to avoid:** Show the countdown UI immediately on button click (client-side countdown is decorative -- it mirrors the known 3-second server duration), then replace with results when the response arrives. The countdown provides visual feedback during the blocking request.
**Warning signs:** UI appears frozen for 3 seconds with no feedback.

### Pitfall 5: Toggle Checkbox Revert on Error
**What goes wrong:** User clicks enable toggle, request fails, but checkbox stays in new state.
**Why it happens:** Forgetting to revert the checkbox value on API error.
**How to avoid:** Read the current checked state BEFORE making the request. On error, set it back. Per UI-SPEC: "On error: revert checkbox to previous state."
**Warning signs:** Toggle shows "enabled" but status badge shows "disabled" after a failed request.

### Pitfall 6: Auto-Scroll Logic Inverted
**What goes wrong:** Events prepend newest at top, but auto-scroll logic uses scrollTop === 0 to detect "at top". Since newest events are at top, "at top" means user sees the latest -- so auto-scroll should keep scrollTop at 0 when user hasn't scrolled down.
**Why it happens:** Confusing "scroll to newest" with "scroll to bottom" (which would apply if newest were at bottom).
**How to avoid:** Per UI-SPEC: "New events are prepended (newest at top). Auto-scroll: scrolls to top (showing newest) unless user has scrolled down. If scrollTop > 0, auto-scroll is suppressed. Resume when user scrolls back to scrollTop === 0." The scroll logic is: if scrollTop === 0, user is at the top seeing newest events, keep them there. If scrollTop > 0, user scrolled down to read older events, don't interrupt.
**Warning signs:** Event log keeps jumping to bottom when new events arrive, or user can never read older events.

## Code Examples

Verified patterns from the existing codebase:

### Status Badge Update
```javascript
// Derived from: UI-SPEC status badge color map + service-status.js pattern
function updateStatusBadge(statusData) {
    const badge = document.getElementById("ww-status-badge");
    const dot = document.getElementById("ww-status-dot");
    const text = document.getElementById("ww-status-text");

    // Derive state from status response
    let state = "unavailable";
    if (statusData.error) {
        state = "error";
    } else if (!statusData.enabled) {
        state = "disabled";
    } else if (!statusData.running) {
        state = "unavailable";
    } else {
        state = "listening";
    }

    const badgeStyles = {
        listening:   { bg: "bg-emerald-500/20", text: "text-emerald-400", dot: "bg-emerald-400", pulse: true },
        disabled:    { bg: "bg-zinc-600/20",    text: "text-zinc-400",    dot: "bg-zinc-400",    pulse: false },
        paused:      { bg: "bg-amber-500/20",   text: "text-amber-400",   dot: "bg-amber-400",   pulse: false },
        error:       { bg: "bg-rose-500/20",     text: "text-rose-400",    dot: "bg-rose-400",    pulse: false },
        unavailable: { bg: "bg-zinc-600/20",    text: "text-zinc-500",    dot: "bg-zinc-500",    pulse: false },
    };

    const style = badgeStyles[state] || badgeStyles.unavailable;

    // Clear and apply classes
    badge.className = `flex items-center gap-2 px-3 py-1.5 rounded-full ${style.bg}`;
    dot.className = `w-2 h-2 rounded-full ${style.dot}${style.pulse ? " animate-pulse" : ""}`;
    text.className = `text-xs font-semibold ${style.text}`;
    text.textContent = state.charAt(0).toUpperCase() + state.slice(1);
}
```

### Event Log Prepend with Auto-Scroll
```javascript
// Derived from: UI-SPEC event log behavior + D-02 auto-scroll decision
function appendEvents(newEvents) {
    const log = document.getElementById("ww-event-log");
    const empty = document.getElementById("ww-event-empty");
    const countEl = document.getElementById("ww-event-count");

    if (newEvents.length === 0) return;
    if (empty) empty.classList.add("hidden");

    const wasAtTop = log.scrollTop === 0;

    newEvents.forEach(event => {
        const entry = createEventEntry(event);
        log.prepend(entry);
        eventList.push(event);
    });

    // Cap at 50 entries
    while (log.children.length > 51) { // 51 = 50 entries + hidden empty div
        log.removeChild(log.lastChild);
    }

    if (wasAtTop) {
        log.scrollTop = 0;
    }

    countEl.textContent = `${Math.min(log.children.length - 1, 50)} events`;
}
```

### Calibration Wizard State Machine
```javascript
// Derived from: UI-SPEC calibration wizard flow + D-03/D-04 decisions
const CAL_ADVANCE_DELAY = 1500;

async function runCalibrationStep(mode) {
    // Disable button, show recording UI
    showRecordingState(mode);

    // Client-side countdown (decorative, mirrors 3s server recording)
    startCountdown(3);

    try {
        const res = await fetch("/wake-word/calibrate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        // Store results and show grid
        if (mode === "ambient") {
            calState.ambient = data;
            calState.suggested = data.suggested_threshold;
        } else {
            calState.phrase = data;
        }
        showCalibrationResults(mode, data);

        // Auto-advance after delay
        setTimeout(() => advanceToNextStep(), CAL_ADVANCE_DELAY);
    } catch (err) {
        showNotification(`Calibration failed: ${err.message}`, "error");
        restoreButtonState(mode);
    }
}
```

### Stop Button Click-to-Arm
```javascript
// Derived from: UI-SPEC stop session confirmation pattern
let stopArmed = false;
let stopTimer = null;

function handleStopClick() {
    const btn = document.getElementById("ww-stop-btn");
    if (stopArmed) {
        // Second click within window: execute stop
        clearTimeout(stopTimer);
        stopArmed = false;
        resetStopButton(btn);
        executeStop();
    } else {
        // First click: arm the button
        stopArmed = true;
        btn.innerHTML = '<span class="material-icons text-base">stop</span> Hold to Stop';
        btn.classList.remove("bg-zinc-800", "hover:bg-zinc-700", "text-white");
        btn.classList.add("bg-rose-500/20", "text-rose-400");
        stopTimer = setTimeout(() => {
            stopArmed = false;
            resetStopButton(btn);
        }, 2000);
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| font-bold for all headings | font-semibold for consistency | Phase 3 UI-SPEC normalization | All new Phase 3 code uses font-semibold. Existing settings-form.html still uses font-bold (no migration needed). |

**Deprecated/outdated:**
- Nothing deprecated in this domain. The project's vanilla JS + Tailwind approach is stable and appropriate for the Raspberry Pi resource constraints.

## Open Questions

1. **WWUI-02 and WWUI-03 already implemented by Phase 2**
   - What we know: The settings-form.html already contains Porcupine endpoint path, access key, sensitivity, and threshold input fields (created in Phase 2 SETS-01/SETS-02). The Phase 3 UI-SPEC does not include these fields in the dashboard panel.
   - What's unclear: Whether the planner should mark WWUI-02 and WWUI-03 as "satisfied by Phase 2" or create a task to verify they work correctly.
   - Recommendation: Mark WWUI-02 and WWUI-03 as pre-satisfied by Phase 2. The dashboard panel's calibration wizard (WWUI-06/07/08) provides the runtime equivalent for threshold adjustment. No additional work needed for WWUI-02/03.

2. **"Paused" state detection**
   - What we know: The GET /wake-word/status response does not directly include a "paused" field. "Paused" occurs when a session is active and the wake word listener is paused.
   - What's unclear: Whether the controller's `get_status()` returns any indication of paused state, or if the JS must infer it from events.
   - Recommendation: The simplest approach is to check if `running === true && enabled === true` but the controller reports it is not actively listening (if such a field exists). If no direct paused indicator exists in the status response, the "Listening" state is shown and "Paused" becomes unreachable from the status poll alone. This is acceptable for v1 -- sessions are typically short-lived. The planner should include a note to check the actual `get_status()` response shape at implementation time.

3. **index.html panel placement (D-08)**
   - What we know: D-08 says "after Audio Settings, before MQTT". But index.html currently shows: main grid (user-profile + persona-form) -> settings-panel (modal) -> env-editor-modal -> songs-modal -> news-sources-modal. The wake word panel is a page-level section, not inside the settings modal.
   - What's unclear: The exact insertion point. The UI-SPEC says "after the settings panel include block" which means after `{% include "components/settings-panel.html" %}` and before `{% include "components/env-editor-modal.html" %}`.
   - Recommendation: Insert `{% include "components/wake-word-panel.html" %}` between the settings-panel include and env-editor-modal include in index.html. This matches the UI-SPEC's explicit instruction.

## Project Constraints (from CLAUDE.md)

Directives that the planner MUST enforce:

1. **IIFE JS module pattern** -- All JavaScript must use the IIFE pattern (`const X = (() => { ... return { init }; })();`)
2. **Same Tailwind classes** -- Use existing Tailwind utility class conventions, no custom CSS
3. **Blueprint pattern for routes** -- Not applicable to Phase 3 (no new routes), but existing routes must not be modified
4. **Use `logger` not `print()`** -- Not applicable to Phase 3 (no Python code)
5. **Follow existing patterns** -- Panel structure, collapsible sections, fetch calls, notification usage must match existing code
6. **Hardware module: core/hotword.py must not be modified** -- Phase 3 is frontend-only, no risk
7. **JavaScript naming: camelCase** -- All JS variables and functions use camelCase
8. **JavaScript files: lowercase-with-hyphens.js** -- New file: `wake-word-panel.js`
9. **Preserve upstream refactored architecture** -- Only add new files and minimal modifications to existing includes

## Sources

### Primary (HIGH confidence)
- `webconfig/static/js/audio-panel.js` -- IIFE module pattern, fetch API usage, showNotification pattern
- `webconfig/static/js/sections.js` -- Collapsible section initialization, localStorage persistence, icon color toggling
- `webconfig/static/js/service-status.js` -- Polling pattern with setInterval, status UI update, cached data
- `webconfig/static/js/ui-helpers.js` -- showNotification, toggleInputVisibility, toggleTooltip APIs
- `webconfig/static/js/init.js` -- DOMContentLoaded initialization pattern, module.init() calls
- `webconfig/templates/base.html` -- Script load order, template structure
- `webconfig/templates/index.html` -- Template include pattern, insertion points
- `webconfig/templates/components/settings-form.html` -- Collapsible section HTML structure, existing wake word form fields
- `webconfig/app/routes/wake_word.py` -- All 6 API endpoints and their response shapes
- `.planning/phases/03-ui-panel/03-UI-SPEC.md` -- Complete visual and interaction contract
- `.planning/phases/03-ui-panel/03-CONTEXT.md` -- All locked decisions (D-01 through D-08)

### Secondary (MEDIUM confidence)
- None needed -- all information sourced from existing codebase and planning artifacts

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies, uses only existing project tools
- Architecture: HIGH -- Every pattern has a working reference implementation in the codebase
- Pitfalls: HIGH -- Identified from direct code reading and UI-SPEC analysis

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no external dependencies that could change)
