# Roadmap: Billy B Assistant — Wake Word Reintegration & Stabilization

## Overview

This milestone reconnects the dormant wake word detection engine to the session lifecycle, exposes it through web routes, and surfaces it in the dashboard UI. The work moves in strict dependency order: first prove the backend integration works on real Pi hardware (including session trigger abstraction, mic handoff, and all defensive fixes), then build the web API layer on top, then add the UI panel. No phase can be safely skipped or reordered — each unblocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Integration** - Wire wake word to session lifecycle, harden resilience, fix merge breakages
- [ ] **Phase 2: Web Routes & Settings** - Blueprint endpoints, SSE stream, calibration routes, .env persistence
- [ ] **Phase 3: UI Panel** - Wake word dashboard panel with status, controls, event log, and calibration wizard

## Phase Details

### Phase 1: Core Integration
**Goal**: The fish responds to "Billy" hands-free — wake word detection triggers sessions identically to button press, with clean mic handoff and no race conditions
**Depends on**: Nothing (first phase)
**Requirements**: WAKE-01, WAKE-02, WAKE-03, WAKE-04, WAKE-05, WAKE-06, WAKE-07, WAKE-08, WAKE-09, SRES-01, SRES-02, SRES-03, HARE-01, HARE-02, CONF-01, CONF-02, FIX-01
**Success Criteria** (what must be TRUE):
  1. Saying the wake word causes Billy to start a conversation session with audio feedback, identical to pressing the button
  2. Button press still starts a session correctly — the trigger abstraction does not break the existing button path
  3. When a session ends, wake word listening resumes without mic resource errors or self-triggering on Billy's own voice
  4. Invalid or out-of-range config values log a warning and fall back to defaults at startup rather than silently misbehaving
  5. Any merge-introduced breakages discovered during integration are catalogued and fixed
**Plans**: TBD

### Phase 2: Web Routes & Settings
**Goal**: The wake word controller is fully accessible via HTTP — status queryable, events streamable, configuration changeable at runtime, calibration recordable, and settings persistable across reboots
**Depends on**: Phase 1
**Requirements**: WWEB-01, WWEB-02, WWEB-03, WWEB-04, WWEB-05, WWEB-06, WWEB-07, SETS-01, SETS-02
**Success Criteria** (what must be TRUE):
  1. `GET /wake-word/status` returns JSON showing whether the controller is running, its mode (Porcupine or RMS), and any error state
  2. `POST /wake-word/test` triggers a simulated detection session and `stop` ends it — callable without touching hardware
  3. Running the calibration endpoints records ambient and wake-phrase audio and returns suggested threshold and sensitivity values
  4. After a calibration `apply`, restarting the Pi shows the saved wake word settings in effect without re-entering them
**Plans**: TBD
**UI hint**: yes

### Phase 3: UI Panel
**Goal**: Users can configure, monitor, and calibrate wake word detection entirely through the web dashboard without SSH or manual .env editing
**Depends on**: Phase 2
**Requirements**: WWUI-01, WWUI-02, WWUI-03, WWUI-04, WWUI-05, WWUI-06, WWUI-07, WWUI-08, WWUI-09, WWUI-10
**Success Criteria** (what must be TRUE):
  1. The wake word panel shows a live status badge (Listening / Disabled / Paused / Error) that updates without page refresh
  2. Toggling the enable/disable switch takes effect immediately and the status badge reflects the change
  3. The event log shows the last 50 detection events in a scrollable panel, updating in real time
  4. Completing the calibration wizard (Measure Background → Record Wake Phrase → Apply Suggestions) produces a threshold recommendation and persists it to .env with one click
  5. The panel is visually consistent with Audio Settings, MQTT, and Home Assistant sections and collapses cleanly
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Integration | 0/TBD | Not started | - |
| 2. Web Routes & Settings | 0/TBD | Not started | - |
| 3. UI Panel | 0/TBD | Not started | - |
