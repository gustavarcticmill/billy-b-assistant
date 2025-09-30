# Wake Word Feature Implementation Plan

## Goals
- Allow Billy to react to a voice wake phrase ("Hey Billy") as an alternative to the physical button.
- Provide UI controls for enabling/disabling the wake word and tuning sensitivity/behavior parameters.
- Offer guided calibration to help users capture ambient noise levels and choose detection thresholds.
- Deliver a UI-driven test harness so users can validate wake-word detection without touching code.

## High-Level Flow
1. A wake-word listener runs continuously whenever Billy is idle, sharing the microphone with existing audio capture.
2. On detection, the listener triggers the same start/stop logic currently used by the physical button.
3. UI updates allow users to manage configuration values stored in `.env` and preview the detector behavior.
4. Calibration and testing tools use temporary audio capture to compute noise baselines and simulate detections.

## Backend Workstreams

### 1. Configuration and State Management
- Add new env keys (e.g., `WAKE_WORD_ENABLED`, `WAKE_WORD_ENGINE`, `WAKE_WORD_SENSITIVITY`, `WAKE_WORD_THRESHOLD`, `WAKE_WORD_ENDPOINT`) with sane defaults.
- Extend `core/config.py` so the new keys are exposed through `core.config` and available to both the listener and the web UI server.
- Update `webconfig/server.py` to include the new keys in `CONFIG_KEYS`, `/config`, and `/save` routes.
- Decide where runtime state lives (e.g., a small `WakeWordController` singleton) to enable toggling the listener without restarting the whole app.

### 2. Wake Word Listener Service
- Create a dedicated module (`core/hotword.py`) responsible for:
  - Initializing the third-party detector (Porcupine/OpenWakeWord) with configurable models.
  - Owning a `sounddevice.RawInputStream` that mirrors the current audio settings.
  - Providing `start()`, `stop()`, and `set_parameters()` methods invoked through both button logic and UI events.
- Coordinate microphone access between the listener and `BillySession`:
  - Pause or shut down the listener whenever a session is active.
  - Restart the listener after the session concludes using callbacks wired through `core/button.trigger_session_start/stop`.
- Emit structured events (e.g., via `asyncio.Queue` or MQTT) so the UI can subscribe to real-time detection status during testing.

### 3. Trigger Integration
- Refactor `core/button.py` by extracting the common start/stop routines into helper functions that accept a source argument (`hardware`, `wake_word`, `ui-test`).
- Ensure debounce logic and playback control is shared so wake-word triggers behave identically to physical presses.
- Add instrumentation logs that capture wake word events for UI consumption and debugging.

### 4. Calibration Support APIs
- Build a `/wake-word/calibrate` Flask route that:
  - Collects a short audio sample, calculates RMS/noise floor, and recommends threshold/sensitivity values.
  - Returns data points for graphing (e.g., time-series RMS, suggested threshold) as JSON.
- Provide a `/wake-word/preview` route that proxies the listener's event stream so the frontend can run real-time visualizations.
- Add validation to persist calibration results back to `.env` when the user accepts the recommendation.

### 5. Test Hooks and Telemetry
- Add a `/wake-word/test` route that can:
  - Simulate a wake word event (triggering the button helpers).
  - Optionally accept uploaded audio to feed through the detector offline.
- Record test outcomes in dedicated logs (date, threshold, pass/fail) for future debugging.

## Frontend (Web UI) Workstreams

### 1. Settings Panel Enhancements
- Introduce a "Wake Word" accordion section in `templates/index.html` with controls for:
  - Enable/disable toggle (writes `WAKE_WORD_ENABLED`).
  - Engine selection dropdown (porcupine, openwakeword, custom) pulling options from `/config`.
  - Numeric sliders/inputs for sensitivity and detection threshold, with live tooltips explaining trade-offs.
  - Text input for custom model path or endpoint when applicable.
- Update the JS config loader to populate the new fields and include them in the payload submitted to `/save`.
- Add inline validation and success/error toasts to confirm changes.

### 2. Calibration Wizard
- Build a modal or multi-step drawer triggered by a "Calibrate" button inside the Wake Word section.
- Steps:
  1. Instructions & microphone selection confirmation.
  2. Background capture phase with waveform/RMS graph fed by `/mic-check` / new calibration endpoint.
  3. Optional voice test where the user says the wake phrase to visualize peak levels.
  4. Summary screen suggesting threshold values with "Apply" and "Discard" actions.
- Use existing Tailwind styling utilities for consistency; reuse log panel graph components if available or integrate a lightweight chart library already approved in `package.json`.

### 3. Live Detection Test Console
- Add a collapsible panel showing real-time event logs:
  - Feed updates via WebSocket/EventSource hitting `/wake-word/preview`.
  - Display recent detections with timestamp, confidence score, and whether they triggered an action.
- Include buttons:
  - "Simulate Detection" to call `/wake-word/test?action=simulate`.
  - "Play Sample Clip" to stream a bundled wake phrase through device speakers so the mic hears it (optional future enhancement).
  - "Export Logs" to download the latest wake-word telemetry for troubleshooting.

### 4. UX & Accessibility Considerations
- Provide contextual help icons linking to documentation about recommended sensitivity ranges.
- Ensure controls degrade gracefully when the wake-word feature is disabled or unsupported on the host hardware (e.g., hide calibration wizard if no mic is detected).
- Implement loading states and error banners for each async request so users know when calibration is running.

## Documentation & Ops
- Create/extend README or docs entry summarizing how to enable wake-word detection and use the calibration/test tools.
- Document required packages or model downloads in the setup guide and ensure `package.json`/`requirements.txt` include them.
- Plan regression tests: unit tests for new helper functions, integration tests for Flask routes, and manual checklist for UI flows.
- Coordinate deployment steps (e.g., migrations to new env keys, ensuring service restart picks up listener state).

## Rollout Checklist
- [ ] Backend listener behind a feature flag with default off.
- [ ] UI shows wake-word section only when enabled or hardware capable.
- [ ] Calibration wizard verified on target platforms (Pi, desktop dev machine).
- [ ] Automated tests green and new manual QA scripts completed.
- [ ] Release notes drafted describing wake-word activation and UI tools.
