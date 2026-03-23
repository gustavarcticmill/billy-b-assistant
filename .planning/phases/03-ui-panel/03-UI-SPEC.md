---
phase: 3
slug: ui-panel
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-23
---

# Phase 3 --- UI Design Contract

> Visual and interaction contract for the Wake Word dashboard panel. This panel provides live status monitoring, enable/disable control, event logging, action buttons, and a 3-step calibration wizard. It is a standalone panel included in index.html, separate from the settings form Wake Word section built in Phase 2.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (Flask/Jinja2 + Tailwind CSS --- shadcn not applicable) |
| Preset | not applicable |
| Component library | none (vanilla HTML + Tailwind utility classes) |
| Icon library | Material Icons (self-hosted woff2 at /static/fonts/material-icons.woff2) |
| Font | System font stack (Tailwind `font-sans` default) |

Source: Inherited from Phase 2 UI-SPEC. No changes.

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, inline padding, gap-1 |
| sm | 8px | Compact element spacing, gap-2 |
| input | 12px | Input inner padding (p-3) |
| md | 16px | Default element spacing, p-4, section container padding |
| lg | 24px | Section padding, p-6 |
| xl | 32px | Layout gaps |
| 2xl | 48px | Major section breaks |
| 3xl | 64px | Page-level spacing |

Exceptions: 12px (`p-3`) is inherited from Phase 2 for input consistency. Event log entries use `py-2 px-3` (8px vertical, 12px horizontal) for compact density in a scrollable list.

Source: Inherited from Phase 2 UI-SPEC. Matches existing patterns in settings-form.html.

---

## Typography

| Role | Size | Weight | Line Height | Tailwind Class |
|------|------|--------|-------------|----------------|
| Body | 14px | 400 (normal) | 1.5 | `text-sm` |
| Label | 14px | 600 (semibold) | 1.5 | `text-sm font-semibold` |
| Section Heading | 18px | 700 (bold) | 1.2 | `text-lg font-bold` |
| Tooltip / Muted | 12px | 400 (normal) | 1.5 | `text-xs` |
| Badge Text | 12px | 600 (semibold) | 1.0 | `text-xs font-semibold` |
| Calibration Metric Value | 16px | 600 (semibold) | 1.2 | `text-base font-semibold` |
| Calibration Metric Label | 12px | 400 (normal) | 1.5 | `text-xs` |

Weights used: 400 (normal), 600 (semibold), 700 (bold) --- 3 effective weights. Note: The actual codebase uses `font-semibold` (600) for labels (28 occurrences in settings-form.html) and `font-bold` (700) only for section headings (7 occurrences). Phase 3 matches the real codebase pattern, not the Phase 2 UI-SPEC normalization to 2 weights.

Source: Detected from settings-form.html actual usage. Labels use `font-semibold`, headings use `font-bold`.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | Animated gradient (cyan-800 through slate-800) | Body background |
| Secondary (30%) | `zinc-900/50` with `backdrop-blur-xs` + `border-zinc-700` | Panel container, event log container, calibration results card |
| Accent (10%) | `emerald-500` / `emerald-400` (hover) | Apply Suggestions button, active section icon, enabled status badge |
| Interactive focus | `cyan-500` | Input focus rings, slider thumbs, tooltip highlights |
| Destructive | `rose-500` / `rose-400` | Stop Session button, Error status badge |
| Warning | `amber-500` / `amber-400` | Paused status badge |
| Input surface | `zinc-800` | Button backgrounds (action buttons), event log background |
| Text primary | `white` | Body text, button labels |
| Text secondary | `slate-300` | Labels, badge labels |
| Text muted | `slate-400` | Event timestamps, placeholder text |

### Status Badge Color Map

| State | Background | Text | Dot Color |
|-------|-----------|------|-----------|
| Listening | `bg-emerald-500/20` | `text-emerald-400` | `bg-emerald-400` (pulsing) |
| Disabled | `bg-zinc-600/20` | `text-zinc-400` | `bg-zinc-400` |
| Paused | `bg-amber-500/20` | `text-amber-400` | `bg-amber-400` |
| Error | `bg-rose-500/20` | `text-rose-400` | `bg-rose-400` |
| Unavailable | `bg-zinc-600/20` | `text-zinc-500` | `bg-zinc-500` |

Source: Badge colors follow the established service-status.js pattern (emerald=active, amber=warning, rose=error). The semi-transparent backgrounds (`/20` opacity) are used for badge pills to blend with the dark panel surface.

Accent reserved for: Apply Suggestions button, active collapsible section icons (emerald-400 when expanded), enabled badge background tint.

---

## Component Patterns

### Panel Container (New --- Standalone Dashboard Panel)

This panel is NOT inside the settings modal. It is a standalone panel included in `index.html` after the settings panel include and before any modals. It follows the same collapsible section pattern but is a top-level page component, not a form section.

```html
<section id="wake-word-panel" class="max-w-6xl mx-auto mt-2 px-2 md:px-0">
    <div class="bg-zinc-900/50 backdrop-blur-xs border border-zinc-700 p-4 rounded-lg shadow-lg mb-4 collapsible-section"
         id="section-wake-word-panel">
        <h3 class="flex items-center gap-2 cursor-pointer group text-lg grow justify-between font-bold mb-4 text-slate-200 hover:text-emerald-400 transition-colors">
            <span class="material-icons text-white group-hover:text-emerald-400 transition-colors">hearing</span>
            Wake Word
            <span class="material-icons transition-transform duration-200 ml-2 rotate-0 group-hover:text-emerald-400">expand_more</span>
        </h3>
        <!-- panel content children -->
    </div>
</section>
```

Note: The section ID is `section-wake-word-panel` (distinct from `section-wake-word` in settings-form.html) to avoid localStorage collision with the settings section collapse state.

### Status Header Row

Top row inside the panel showing status badge and enable/disable toggle side-by-side.

```html
<div class="flex items-center justify-between mb-4">
    <!-- Status Badge -->
    <div id="ww-status-badge" class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20">
        <span id="ww-status-dot" class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span id="ww-status-text" class="text-xs font-semibold text-emerald-400">Listening</span>
    </div>
    <!-- Enable/Disable Toggle -->
    <label class="flex items-center gap-2 cursor-pointer">
        <span class="text-sm text-slate-300">Enable</span>
        <div class="relative">
            <input type="checkbox" id="ww-enable-toggle" class="sr-only peer">
            <div class="w-10 h-5 bg-zinc-700 rounded-full peer peer-checked:bg-emerald-500 transition-colors"></div>
            <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
        </div>
    </label>
</div>
```

### Action Buttons Row

Three action buttons in a horizontal row below the status header.

```html
<div class="flex gap-2 mb-4">
    <button id="ww-simulate-btn"
            class="flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-white text-sm px-3 py-2 rounded transition-colors">
        <span class="material-icons text-base">play_arrow</span>
        Simulate Detection
    </button>
    <button id="ww-stop-btn"
            class="flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-white text-sm px-3 py-2 rounded transition-colors">
        <span class="material-icons text-base">stop</span>
        Stop Session
    </button>
    <button id="ww-refresh-btn"
            class="flex items-center gap-1 bg-zinc-800 hover:bg-zinc-700 text-white text-sm px-3 py-2 rounded transition-colors">
        <span class="material-icons text-base">refresh</span>
        Refresh
    </button>
</div>
```

Button style matches existing audio-panel test buttons (`bg-zinc-800 hover:bg-zinc-700 text-white text-sm`).

### Event Log Container

Scrollable container displaying the last 50 detection events.

```html
<div class="mb-4">
    <div class="flex items-center justify-between mb-2">
        <h4 class="text-sm font-semibold text-slate-300">Event Log</h4>
        <span id="ww-event-count" class="text-xs text-slate-400">0 events</span>
    </div>
    <div id="ww-event-log"
         class="bg-zinc-800 rounded border border-zinc-700 max-h-48 overflow-y-auto text-sm font-mono">
        <!-- Event entries appended here -->
        <div id="ww-event-empty" class="py-6 text-center text-slate-500 text-xs">
            No detection events yet. Events appear here when the wake word is detected.
        </div>
    </div>
</div>
```

### Event Log Entry

Individual event row inside the scrollable log.

```html
<div class="flex items-start gap-2 py-2 px-3 border-b border-zinc-700/50 last:border-0">
    <span class="material-icons text-base text-emerald-400 mt-0.5 shrink-0">mic</span>
    <div class="flex-1 min-w-0">
        <div class="flex items-baseline justify-between gap-2">
            <span class="text-sm text-white truncate">{event.type}</span>
            <span class="text-xs text-slate-400 shrink-0">{formatted_time}</span>
        </div>
        <div class="text-xs text-slate-400 truncate">{event.detail}</div>
    </div>
</div>
```

Event type icon mapping:
- `detection` -> `mic` icon, `text-emerald-400`
- `error` -> `error_outline` icon, `text-rose-400`
- `started` / `stopped` -> `power_settings_new` icon, `text-amber-400`
- fallback -> `info` icon, `text-slate-400`

Time format: `HH:MM:SS` (24-hour, local timezone). No date -- events are recent.

### Calibration Wizard

Three-step wizard below the event log, using a stepper-style layout.

```html
<div class="mb-4">
    <h4 class="text-sm font-semibold text-slate-300 mb-3">Calibration</h4>

    <!-- Step Indicators -->
    <div class="flex items-center gap-2 mb-4">
        <div id="ww-cal-step-1" class="flex items-center gap-1.5">
            <span class="w-6 h-6 rounded-full bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center">1</span>
            <span class="text-xs text-slate-300">Background</span>
        </div>
        <div class="flex-1 h-px bg-zinc-700"></div>
        <div id="ww-cal-step-2" class="flex items-center gap-1.5">
            <span class="w-6 h-6 rounded-full bg-zinc-700 text-zinc-400 text-xs font-semibold flex items-center justify-center">2</span>
            <span class="text-xs text-zinc-500">Wake Phrase</span>
        </div>
        <div class="flex-1 h-px bg-zinc-700"></div>
        <div id="ww-cal-step-3" class="flex items-center gap-1.5">
            <span class="w-6 h-6 rounded-full bg-zinc-700 text-zinc-400 text-xs font-semibold flex items-center justify-center">3</span>
            <span class="text-xs text-zinc-500">Apply</span>
        </div>
    </div>

    <!-- Step Content Area -->
    <div id="ww-cal-content" class="bg-zinc-800 rounded border border-zinc-700 p-4">
        <!-- Step 1: Initial state -->
        <div id="ww-cal-step1-content">
            <p class="text-sm text-slate-300 mb-3">Measure your environment's background noise level. Keep the room quiet and press Start.</p>
            <button id="ww-cal-ambient-btn"
                    class="flex items-center gap-1 bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-3 py-2 rounded transition-colors">
                <span class="material-icons text-base">graphic_eq</span>
                Measure Background
            </button>
        </div>
    </div>
</div>
```

Step indicator states:
- **Active step:** circle `bg-emerald-500 text-white`, label `text-slate-300`
- **Future step:** circle `bg-zinc-700 text-zinc-400`, label `text-zinc-500`
- **Completed step:** circle `bg-emerald-500 text-white` with `check` icon replacing number, label `text-slate-300`

### Calibration Recording State

During active recording, the button area transforms to show countdown and status.

```html
<div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-full bg-rose-500/20 flex items-center justify-center">
        <span class="w-3 h-3 rounded-full bg-rose-500 animate-pulse"></span>
    </div>
    <div>
        <p id="ww-cal-status" class="text-sm text-white font-semibold">Recording ambient noise...</p>
        <p id="ww-cal-countdown" class="text-xs text-slate-400">3 seconds remaining</p>
    </div>
</div>
```

Button is disabled during recording (add `opacity-50 cursor-not-allowed` classes and `disabled` attribute).

### Calibration Results Grid

Displayed after each recording step completes. 2x2 grid for ambient, 1x2 for phrase.

```html
<div class="grid grid-cols-2 gap-3 mt-3 mb-3">
    <div class="bg-zinc-900/50 rounded p-3 text-center">
        <div class="text-base font-semibold text-white">{value}</div>
        <div class="text-xs text-slate-400">Ambient RMS</div>
    </div>
    <div class="bg-zinc-900/50 rounded p-3 text-center">
        <div class="text-base font-semibold text-white">{value}</div>
        <div class="text-xs text-slate-400">Peak RMS</div>
    </div>
    <div class="bg-zinc-900/50 rounded p-3 text-center">
        <div class="text-base font-semibold text-emerald-400">{value}</div>
        <div class="text-xs text-slate-400">Suggested Threshold</div>
    </div>
    <div class="bg-zinc-900/50 rounded p-3 text-center">
        <div class="text-base font-semibold text-white">{value}</div>
        <div class="text-xs text-slate-400">Wake Phrase Peak</div>
    </div>
</div>
```

The suggested threshold value uses `text-emerald-400` to highlight it as the recommended value.

### Apply Suggestions Area (Step 3)

```html
<div id="ww-cal-step3-content" class="hidden">
    <div class="flex items-center justify-between mb-3">
        <div>
            <p class="text-sm text-slate-300">Suggested threshold:</p>
            <p id="ww-cal-suggested-value" class="text-base font-semibold text-emerald-400">{value}</p>
        </div>
        <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" id="ww-cal-persist" checked
                   class="w-4 h-4 rounded bg-zinc-700 border-zinc-600 text-emerald-500 focus:ring-cyan-500 focus:ring-2">
            <span class="text-sm text-slate-300">Persist to .env</span>
        </label>
    </div>
    <button id="ww-cal-apply-btn"
            class="flex items-center gap-1 bg-emerald-500 hover:bg-emerald-400 text-zinc-800 font-semibold text-sm px-4 py-2 rounded transition-colors">
        <span class="material-icons text-base">check</span>
        Apply Suggestions
    </button>
</div>
```

---

## Interaction Contracts

### Polling Lifecycle

| Poll Target | Interval | Start | Stop |
|-------------|----------|-------|------|
| `GET /wake-word/status` | 3000ms | Panel init (WakeWordPanel.init()) | Never (runs regardless of collapse state) |
| `GET /wake-word/events` | 2000ms | Panel init (WakeWordPanel.init()) | Never (runs regardless of collapse state) |

Rationale for not pausing on collapse: Status badge must stay current even when collapsed so the user sees accurate state on expand. Events must continue draining so the buffer does not overflow on the server side. Both requests are lightweight JSON payloads.

Source: D-01 (2s events), D-06 (3s status).

### Enable/Disable Toggle

1. User clicks the toggle checkbox.
2. JS reads new checked state.
3. `POST /wake-word/runtime-config` with `{ "enabled": true/false }`.
4. On success: status poll will reflect the change on next tick (within 3s). `showNotification("Wake word detection enabled", "success")` or `showNotification("Wake word detection disabled", "info")`.
5. On error: revert checkbox to previous state. `showNotification("Failed to update wake word: " + error, "error")`.

### Action Buttons

| Button | Endpoint | Payload | On Success | On Error |
|--------|----------|---------|------------|----------|
| Simulate Detection | `POST /wake-word/test` | `{ "action": "simulate" }` | `showNotification("Detection simulated", "success")` | `showNotification("Simulation failed: " + err, "error")` |
| Stop Session | `POST /wake-word/test` | `{ "action": "stop" }` | `showNotification("Session stopped", "info")` | `showNotification("Stop failed: " + err, "error")` |
| Refresh | `GET /wake-word/status` | (none) | Update badge immediately, `showNotification("Status refreshed", "info")` | `showNotification("Refresh failed: " + err, "error")` |

### Event Log Behavior

- New events are prepended (newest at top).
- Events accumulate in the client-side list, capped at 50 entries. When exceeding 50, oldest entries are removed from the DOM.
- Auto-scroll: The log scrolls to top (showing newest) unless the user has scrolled down. If `scrollTop > 0`, auto-scroll is suppressed. Resume when user scrolls back to `scrollTop === 0`.
- Empty state div is hidden when the first event arrives.

Source: D-02 (auto-scroll behavior).

### Calibration Wizard Flow

**Step 1: Measure Background**
1. User clicks "Measure Background".
2. Button becomes disabled. Recording state UI replaces button content.
3. Countdown: "3 seconds remaining" -> "2 seconds remaining" -> "1 second remaining". Status text: "Recording ambient noise..."
4. `POST /wake-word/calibrate` with `{ "mode": "ambient" }`.
5. On response: Show results grid (Ambient RMS, Peak RMS, Suggested Threshold). Store `suggested_threshold` in JS state.
6. After 1500ms delay, auto-advance to Step 2. Step 1 indicator changes to completed (check icon). Step 2 becomes active.

Source: D-03 (countdown), D-04 (auto-advance).

**Step 2: Record Wake Phrase**
1. Content area shows: "Say your wake word clearly. Press Start and speak normally."
2. User clicks "Record Wake Phrase" button.
3. Same countdown/recording state as Step 1. Status text: "Say the wake word now..."
4. `POST /wake-word/calibrate` with `{ "mode": "phrase" }`.
5. On response: Show results (Wake Phrase Peak RMS, plus the full 2x2 grid combining ambient and phrase data).
6. After 1500ms delay, auto-advance to Step 3.

**Step 3: Apply Suggestions**
1. Shows suggested threshold value (emerald-highlighted).
2. "Persist to .env" checkbox is checked by default.
3. User clicks "Apply Suggestions".
4. If persist checked: `POST /wake-word/calibrate/apply` with `{ "threshold": suggested_value }`. This persists to .env AND updates runtime.
5. If persist unchecked: `POST /wake-word/runtime-config` with `{ "threshold": suggested_value }`. Runtime-only, lost on reboot.
6. On success: `showNotification("Calibration applied", "success")`. Reset wizard to Step 1 initial state.
7. On error: `showNotification("Failed to apply calibration: " + err, "error")`. Keep wizard at Step 3 so user can retry.

Source: D-04 (auto-advance), D-05 (persist checked by default).

Auto-advance delay: 1500ms between steps. Long enough to read results, short enough to maintain flow.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Panel heading | Wake Word |
| Panel icon | `hearing` (Material Icons) |
| Status badge: Listening | Listening |
| Status badge: Disabled | Disabled |
| Status badge: Paused | Paused |
| Status badge: Error | Error |
| Status badge: Unavailable | Unavailable |
| Enable toggle label | Enable |
| Simulate button | Simulate Detection |
| Stop button | Stop Session |
| Refresh button | Refresh |
| Event log heading | Event Log |
| Event count label | {N} events |
| Event log empty state | No detection events yet. Events appear here when the wake word is detected. |
| Calibration heading | Calibration |
| Step 1 label | Background |
| Step 2 label | Wake Phrase |
| Step 3 label | Apply |
| Step 1 description | Measure your environment's background noise level. Keep the room quiet and press Start. |
| Step 1 button | Measure Background |
| Step 2 description | Say your wake word clearly. Press Start and speak normally. |
| Step 2 button | Record Wake Phrase |
| Recording status (ambient) | Recording ambient noise... |
| Recording status (phrase) | Say the wake word now... |
| Countdown template | {N} seconds remaining |
| Calibration metric: ambient RMS | Ambient RMS |
| Calibration metric: peak RMS | Peak RMS |
| Calibration metric: suggested threshold | Suggested Threshold |
| Calibration metric: wake phrase peak | Wake Phrase Peak |
| Suggested threshold label | Suggested threshold: |
| Persist checkbox label | Persist to .env |
| Apply CTA | Apply Suggestions |
| Apply success notification | Calibration applied |
| Apply error notification | Failed to apply calibration: {error} |
| Enable success notification | Wake word detection enabled |
| Disable info notification | Wake word detection disabled |
| Toggle error notification | Failed to update wake word: {error} |
| Simulate success notification | Detection simulated |
| Stop info notification | Session stopped |
| Refresh info notification | Status refreshed |
| Error state (controller error) | Wake word controller failed to start. Check the debug log for details. |

---

## Component Inventory

| Component | File | New/Existing |
|-----------|------|-------------|
| Wake Word Panel template | `webconfig/templates/components/wake-word-panel.html` | NEW |
| Wake Word Panel JS module | `webconfig/static/js/wake-word-panel.js` | NEW |
| index.html include | `webconfig/templates/index.html` | MODIFY (add include) |
| base.html script tag | `webconfig/templates/base.html` | MODIFY (add script) |
| init.js initialization | `webconfig/static/js/init.js` | MODIFY (add WakeWordPanel.init()) |

### JS Module Structure (IIFE Pattern)

```javascript
const WakeWordPanel = (() => {
    // Private state
    let statusInterval = null;
    let eventInterval = null;
    let eventList = [];
    let calState = { ambient: null, phrase: null, suggested: null };

    // Public API
    function init() { /* bind UI, start polling */ }

    return { init };
})();
```

Source: Follows AudioPanel, ServiceStatus, Sections IIFE patterns. init() called from init.js DOMContentLoaded handler.

### Template Include Location

In `index.html`, add after the settings panel include block:

```html
<!-- Settings Panel -->
{% include "components/settings-panel.html" %}

<!-- Wake Word Panel -->
{% include "components/wake-word-panel.html" %}

{% include "components/env-editor-modal.html" %}
```

Source: D-08 (after Audio Settings -- this is the standalone panel, separate from settings).

### Script Tag Location

In `base.html`, add before `sections.js`:

```html
<script src="{{ url_for('static', filename='js/wake-word-panel.js') }}"></script>
<script src="{{ url_for('static', filename='js/sections.js') }}"></script>
```

The script must load before `sections.js` so the collapsible section within the panel template is initialized by `Sections.collapsible()`.

---

## API Response Shapes (Consumed)

These shapes are defined by Phase 2 routes. The JS module must handle each.

### GET /wake-word/status
```json
{
  "running": true,
  "mode": "porcupine",
  "error": null,
  "enabled": true,
  "sensitivity": 0.5,
  "threshold": 1000
}
```

Badge state derivation logic:
- `error` is truthy -> **Error**
- `enabled === false` -> **Disabled**
- `running === false && enabled === true` -> **Unavailable** (enabled but controller not running)
- `running === true && mode !== "unavailable"` -> **Listening**
- During active session (inferred from events) -> **Paused**

Note: "Paused" state is not directly in the status response. It occurs when a session is active (controller pauses listening). The JS module can infer this from receiving a `started` event without a subsequent `stopped` event, or from the status response if the controller reports paused state.

### GET /wake-word/events
```json
{
  "events": [
    {"timestamp": "2026-03-23T12:00:00", "type": "detection", "detail": "..."}
  ],
  "count": 50
}
```

### POST /wake-word/calibrate
```json
{
  "mode": "ambient",
  "rms_mean": 245.3,
  "rms_peak": 892.1,
  "suggested_threshold": 1200,
  "duration_seconds": 3,
  "sample_count": 47
}
```

### POST /wake-word/calibrate/apply
```json
{
  "status": "ok",
  "applied": { "threshold": "1200" }
}
```

### POST /wake-word/runtime-config
```json
{
  "status": "ok",
  "applied": ["enabled"]
}
```

### POST /wake-word/test
```json
{
  "status": "ok",
  "action": "simulate"
}
```

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| not applicable | none | not applicable --- no component registry (vanilla HTML + Tailwind) |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
