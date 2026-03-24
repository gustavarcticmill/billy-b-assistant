# Billy B Assistant — Wake Word Reintegration & Stabilization

## What This Is

A voice-activated animatronic fish (Billy Bass) running on Raspberry Pi that serves as a conversational AI assistant. Users interact via hardware button press or wake word detection. The fish talks back using AI (Claude via Anthropic API or Home Assistant's conversation agent), moves its mouth/tail in sync, and can control smart home devices via Home Assistant/MQTT integration. A Flask-based web dashboard provides configuration, persona management, and audio calibration.

## Core Value

The fish responds to voice — both button press and hands-free wake word activation — routing queries intelligently between Claude (general conversation, news, knowledge) and Home Assistant (device control, local automations).

## Requirements

### Validated

These capabilities exist in the current codebase and work (pre-wake-word):

- Session management with real-time AI conversation via OpenAI Realtime API / xAI provider
- Hardware button press triggers conversation sessions with debounce
- Audio capture/playback with sounddevice, mic device enumeration
- Motor control (head/tail) with movement synchronization during speech
- Persona system with INI-based profiles and personality traits
- User profile management with memories and preferences
- Web configuration dashboard (Flask app factory with blueprints)
- MQTT integration for Home Assistant commands and remote control
- Home Assistant API integration for device control and conversation agent
- News digest, weather, and web search tool capabilities
- Audio settings panel with mic check, gain control, speaker test
- Mock hardware support for development without GPIO

### Active

- [ ] Wake word detection reintegration (Porcupine-based, with RMS fallback)
- [ ] Wake word trigger integration in button.py (trigger_session_start/stop abstraction)
- [ ] Wake word web routes blueprint (status, events, runtime config, test, calibration)
- [ ] Wake word UI panel (enable/disable, calibration wizard, event stream, status badge)
- [ ] Settings form integration for wake word config persistence to .env
- [ ] Investigate and fix other breakages from upstream merge
- [ ] End-to-end verification: button press + wake word both trigger sessions correctly

### Out of Scope

- Rewriting core/hotword.py — it works as-is, only integration points needed
- Changing the upstream refactored architecture — work within the new blueprint/app factory structure
- Adding new AI providers — existing OpenAI/xAI/HA routing is sufficient
- Mobile app or remote access beyond the local web dashboard

## Context

This codebase was forked from `Thokoop/billy-b-assistant`. The upstream recently underwent a major refactor:
- `webconfig/server.py` monolith → Flask app factory with blueprints (`webconfig/app/`)
- `webconfig/templates/index.html` → component-based Jinja2 includes
- `webconfig/static/js/config.js` → separate JS modules
- `core/button.py` rewritten with MockButton support, different session management (no wake word)
- `core/session.py` renamed to `core/session_manager.py` with provider-based architecture

The wake word module (`core/hotword.py`) survived the merge intact with full `WakeWordController` implementation (Porcupine + RMS fallback, event queue, state management). All wake word config vars exist in `core/config.py`. But all integration points — button.py triggers, web routes, UI panel, settings persistence — were lost.

The AI routing strategy: Home Assistant conversation agent handles local/device queries ("turn off kitchen lamp"), while Claude/Anthropic handles general conversation, knowledge, and news queries.

Hardware: Raspberry Pi with GPIO for button/motor control, USB microphone, speaker output.

## Constraints

- **Platform**: Raspberry Pi (Linux/ARM) — must work with limited resources
- **Existing code**: Must preserve upstream's refactored architecture (app factory, blueprints, modular JS)
- **Hardware module**: core/hotword.py must not be modified unless strictly necessary for integration
- **Style**: Follow existing patterns — use `logger` not `print()`, same Tailwind classes, IIFE JS module pattern, blueprint pattern for routes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Work within upstream's refactored architecture | Upstream is actively maintained, staying compatible enables future merges | -- Pending |
| Keep core/hotword.py untouched | It works, minimize risk of breaking wake word detection logic | -- Pending |
| Add trigger_session_start/stop abstraction to button.py | Clean multi-source trigger support (hardware, wake_word, ui-test) | -- Pending |
| Wake word routes as separate blueprint | Follows upstream's blueprint pattern, keeps concerns separated | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-24 after initialization*
