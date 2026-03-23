---
phase: 2
slug: web-routes-settings
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-23
---

# Phase 2 — UI Design Contract

> Visual and interaction contract for the Wake Word settings form section added in Phase 2. Phase 2 is primarily backend routes (JSON API), but includes settings form additions (SETS-01, SETS-02) that integrate into the existing Settings panel. The full Wake Word dashboard panel is Phase 3 scope.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (Flask/Jinja2 + Tailwind CSS — shadcn not applicable) |
| Preset | not applicable |
| Component library | none (vanilla HTML + Tailwind utility classes) |
| Icon library | Material Icons (self-hosted woff2 at /static/fonts/material-icons.woff2) |
| Font | System font stack (Tailwind `font-sans` default) |

Source: Detected from `webconfig/tailwind/src/input.css`, `webconfig/package.json`, `webconfig/templates/base.html`.

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, inline padding |
| sm | 8px | Compact element spacing, gap-2 |
| md | 16px | Default element spacing, p-4 |
| lg | 24px | Section padding, p-6 |
| xl | 32px | Layout gaps |
| 2xl | 48px | Major section breaks |
| 3xl | 64px | Page-level spacing |

Exceptions: none

Source: Matches existing patterns in settings-form.html (`p-4` on section containers, `p-3` on inputs, `gap-2`/`gap-4` between elements, `mb-4` between form groups).

---

## Typography

| Role | Size | Weight | Line Height | Tailwind Class |
|------|------|--------|-------------|----------------|
| Body | 14px | 400 (normal) | 1.5 | `text-sm` |
| Label | 14px | 600 (semibold) | 1.5 | `text-sm font-semibold` |
| Section Heading | 18px | 700 (bold) | 1.2 | `text-lg font-bold` |
| Tooltip | 12px | 400 (normal) | 1.5 | `text-xs` |

Source: Detected from settings-form.html — labels use `font-semibold text-sm text-slate-300`, section headings use `text-lg font-bold text-slate-200`, tooltips use `text-xs`.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | Animated gradient (cyan-800 through slate-800) | Body background |
| Secondary (30%) | `zinc-900/50` with `backdrop-blur-xs` + `border-zinc-700` | Collapsible section cards, modal backgrounds |
| Accent (10%) | `emerald-500` / `emerald-400` (hover) | Save Settings button, active section icons, CTA buttons only |
| Interactive focus | `cyan-500` | Input focus rings (`focus:ring-2 focus:ring-cyan-500`), slider thumbs, tooltip highlights |
| Destructive | `rose-500` / `rose-400` | Stop/shutdown actions only |
| Warning | `amber-500` / `amber-400` | Restart actions, update badges |
| Input surface | `zinc-800` | All form inputs (text, number, select, password) |
| Text primary | `white` | Body text, input values |
| Text secondary | `slate-300` | Form labels |
| Text muted | `slate-200` / `zinc-200` | Section headings |

Accent reserved for: Save Settings button, active collapsible section icons (emerald-400 when expanded), split-button borders.

Source: Detected from input.css (`#22d3ee` = cyan-400 for sliders, `#34d399` = emerald-400 for prose links), settings-panel.html (emerald-500 on Save), settings-form.html (emerald-400 on hover states), service-status.js (emerald/amber/rose status pattern).

---

## Component Patterns (Existing — Match Exactly)

### Collapsible Section Container
```html
<div class="bg-zinc-900/50 backdrop-blur-xs border border-zinc-700 p-4 rounded-lg shadow-lg mb-4 collapsible-section"
     id="section-wake-word">
    <h3 class="flex items-center gap-2 cursor-pointer group text-lg grow justify-between font-bold mb-4 text-slate-200 hover:text-emerald-400 transition-colors">
        <span class="material-icons text-white group-hover:text-emerald-400 transition-colors">{icon}</span>
        {Section Title}
        <span class="material-icons transition-transform duration-200 ml-2 rotate-0 group-hover:text-emerald-400">expand_more</span>
    </h3>
    <!-- content children hidden/shown by Sections.collapsible() -->
</div>
```

### Text Input
```html
<div class="mb-4">
    <label for="{ID}" class="block font-semibold text-sm text-slate-300">{Label}</label>
    <input id="{ID}" name="{ID}" type="text"
           class="w-full p-3 mt-1 bg-zinc-800 text-white rounded focus:outline-none focus:ring-2 focus:ring-cyan-500"
           value="{{ config.get('{KEY}', '') }}">
</div>
```

### Password Input (with visibility toggle)
```html
<div class="mb-4">
    <label for="{ID}" class="block font-semibold text-sm text-slate-300">{Label}</label>
    <div class="relative">
        <input id="{ID}" name="{ID}" type="password"
               class="w-full p-3 mt-1 pr-10 bg-zinc-800 text-white rounded focus:outline-none focus:ring-2 focus:ring-cyan-500"
               value="{{ config.get('{KEY}', '') }}">
        <button type="button" onclick="toggleInputVisibility('{ID}', this)"
                class="absolute inset-y-0 right-0 flex items-center px-2 text-slate-400 hover:text-white cursor-pointer">
            <span class="material-icons" id="{ID}_icon">visibility</span>
        </button>
    </div>
</div>
```

### Label with Tooltip
```html
<label for="{ID}" class="flex justify-between items-center font-semibold text-sm text-slate-300 relative">
    {Label Text}
    <span class="material-icons align-middle hover:text-cyan-400 cursor-pointer ml-1"
          onclick="toggleTooltip(this)">help_outline</span>
</label>
<div class="relative">
    <div data-tooltip>{Tooltip HTML content}</div>
    <!-- input element -->
</div>
```

### Number Input (inline pair)
```html
<div class="flex mb-4 gap-4">
    <div class="flex-1/2 flex flex-col justify-between">
        <label for="{ID}" class="flex justify-between items-center font-semibold text-sm text-slate-300">{Label}</label>
        <input type="number" step="{step}" min="{min}" max="{max}" id="{ID}" name="{ID}"
               class="w-full p-3 mt-1 bg-zinc-800 text-white rounded focus:outline-none focus:ring-2 focus:ring-cyan-500"
               value="{{ config.get('{KEY}', '{default}') }}">
    </div>
</div>
```

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Section heading | Wake Word Settings |
| Section icon | `hearing` (Material Icons) |
| Sensitivity label | Sensitivity (0.0 - 1.0) |
| Sensitivity tooltip | How sensitive the wake word engine is to detections. Higher values catch more utterances but may produce false positives. Default: 0.5 |
| Threshold label | RMS Threshold (0 - 32768) |
| Threshold tooltip | Minimum audio RMS level to consider as speech. Use the calibration tool in the Wake Word panel to find the right value for your environment. Default: 1000 |
| Endpoint path label | Porcupine Endpoint Path |
| Endpoint tooltip | Path to a custom Porcupine .ppn endpoint file. Leave empty to use the built-in "Porcupine" keyword. |
| Access key label | Porcupine Access Key |
| Access key tooltip | Your Picovoice Console access key. Required for Porcupine wake word detection. Get one free at <a href="https://console.picovoice.ai/" class="underline hover:text-cyan-400" target="_blank">console.picovoice.ai</a> |
| Enable toggle label | Enable Wake Word Detection |
| Enable tooltip | When enabled, Billy listens for the wake word and starts a conversation session hands-free. Disable to use button-only mode. |
| Empty state (no access key) | Wake word detection requires a Porcupine access key. |
| Error state (controller error) | Wake word controller failed to start. Check the debug log for details. |
| Save CTA | Save Settings (existing button — no new CTA needed; wake word fields are part of the main settings form) |

---

## Phase 2 Form Elements Inventory

These form elements are added to `settings-form.html` inside a new collapsible section `id="section-wake-word"`, placed between the Audio Settings section (`section-audio`) and the MQTT Settings section (`section-mqtt`).

| Field | HTML Element | ID / name | Config Key | Default | Constraints |
|-------|-------------|-----------|------------|---------|-------------|
| Enable toggle | `<select>` | `WAKE_WORD_ENABLED` | `WAKE_WORD_ENABLED` | `false` | Options: `true` / `false` |
| Sensitivity | `<input type="number">` | `SENSITIVITY` | `SENSITIVITY` | `0.5` | min=0.0, max=1.0, step=0.05 |
| RMS Threshold | `<input type="number">` | `THRESHOLD` | `THRESHOLD` | `1000` | min=0, max=32768, step=1 |
| Endpoint path | `<input type="text">` | `ENDPOINT` | `ENDPOINT` | (empty) | Free text, file path |
| Access key | `<input type="password">` | `PORCUPINE_ACCESS_KEY` | `PORCUPINE_ACCESS_KEY` | (empty) | Password field with visibility toggle |

Layout:
- Enable toggle: full width
- Sensitivity + RMS Threshold: side-by-side in `flex gap-4` row (matches Mic Timeout + Silence Threshold pattern in Audio Settings)
- Endpoint path: full width
- Access key: full width, password type with visibility toggle

---

## API Response Shapes (Phase 3 Consumer Contract)

These JSON response shapes are defined by Phase 2 routes and consumed by Phase 3 UI. Documenting here so Phase 3 UI-SPEC can reference them.

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

### GET /wake-word/events
```json
{
  "events": [
    {"timestamp": "2026-03-23T12:00:00", "type": "detection", "detail": "..."},
    ...
  ],
  "count": 50
}
```

### POST /wake-word/calibrate (response)
```json
{
  "mode": "ambient",
  "rms_mean": 245.3,
  "rms_peak": 892.1,
  "suggested_threshold": 1200,
  "duration_seconds": 3
}
```

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| not applicable | none | not applicable — no component registry (vanilla HTML + Tailwind) |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
