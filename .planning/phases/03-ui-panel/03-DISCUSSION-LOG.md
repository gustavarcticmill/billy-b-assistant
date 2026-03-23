# Phase 3: UI Panel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 03-UI Panel
**Areas discussed:** Event log polling, Calibration wizard UX, Status badge updates, Panel template structure

---

## Event log polling

### Poll interval

| Option | Description | Selected |
|--------|-------------|----------|
| 2 seconds | Fast enough for detection events, lighter than real-time. | ✓ |
| 5 seconds | Match existing service status. Less CPU overhead. | |
| You decide | Claude picks. | |

**User's choice:** 2 seconds

### Auto-scroll behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-scroll unless user scrolled up | Pauses when reading history, resumes at bottom. | ✓ |
| Always auto-scroll | New events always scroll to bottom. | |
| You decide | Claude picks. | |

**User's choice:** Auto-scroll unless user scrolled up

---

## Calibration wizard UX

### Recording feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Countdown timer with status text | "3...2...1..." countdown, status text changes, button disabled. | ✓ |
| Animated waveform | Real-time audio viz. Requires streaming data (not supported by Phase 2 endpoints). | |
| You decide | Claude picks. | |

**User's choice:** Countdown timer with status text

### Step advancement

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-advance between steps | Results show briefly, then auto-advance. Fewer clicks. | ✓ |
| Manual advance with Next button | User controls pacing with explicit clicks. | |
| You decide | Claude picks. | |

**User's choice:** Auto-advance between steps

### Persist checkbox default

| Option | Description | Selected |
|--------|-------------|----------|
| Checked by default | Most users want calibration to persist. Can uncheck to test. | ✓ |
| Unchecked by default | Explicit opt-in to .env persistence. | |
| You decide | Claude picks. | |

**User's choice:** Checked by default

---

## Status badge updates

### Update mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Poll /wake-word/status every 3s | Separate poll from event log. Badge color updates on response. | ✓ |
| Piggyback on event poll | Include status in events response. Fewer HTTP requests. | |
| You decide | Claude picks. | |

**User's choice:** Poll /wake-word/status every 3s

---

## Panel template structure

### File structure

| Option | Description | Selected |
|--------|-------------|----------|
| New component file | wake-word-panel.html as separate include. Follows audio-panel pattern. | ✓ |
| Extend settings-panel.html | Add panel inside existing settings panel. Fewer files. | |
| You decide | Claude picks. | |

**User's choice:** New component file

### Dashboard placement

| Option | Description | Selected |
|--------|-------------|----------|
| After Audio Settings, before MQTT | Audio-adjacent grouping. Same position as settings form section. | ✓ |
| Top of dashboard | Most prominent. Disrupts existing order. | |
| You decide | Claude picks. | |

**User's choice:** After Audio Settings, before MQTT

---

## Claude's Discretion

- Badge color mapping for each state
- Event log entry format and styling
- Calibration results grid layout
- Auto-advance delay between wizard steps
- Polling lifecycle (pause when collapsed?)
- Enable/disable toggle implementation

## Deferred Ideas

None — discussion stayed within phase scope.
