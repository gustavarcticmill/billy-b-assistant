# Stack Research

**Domain:** Wake word detection reintegration + audio calibration for Raspberry Pi voice assistant
**Researched:** 2026-03-24
**Confidence:** HIGH

## Context

This is NOT a greenfield stack decision. The codebase already has a working `core/hotword.py` (WakeWordController using pvporcupine + RMS fallback) and a Flask app factory with blueprints. The research question is: what specific versions and patterns should be used when reintegrating the wake word system into the existing architecture?

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pvporcupine | 3.0.x (pin current) | On-device wake word detection | Already in use in `core/hotword.py`. Do NOT upgrade to 4.0.x during this milestone -- the existing `.ppn` keyword model files were trained for v3, and v4 has a new engine that may require re-training keywords. Upgrade is a separate task. |
| sounddevice | >=0.4.6 | Audio input stream for wake word listener | Already in use. Provides `sd.InputStream` with callback-based processing that `WakeWordController._audio_callback` depends on. No alternative needed. |
| numpy | <2 | Audio buffer manipulation, RMS calculation | Already pinned in requirements.txt. The `<2` constraint is correct -- numpy 2.0 introduced breaking C API changes that affect scipy and other compiled dependencies on ARM. |
| scipy | >=1.11 | Audio resampling (mic rate -> Porcupine's 16kHz) | Used in `_process_porcupine()` for `resample()`. No lighter alternative exists for proper signal resampling on Pi. |
| Flask | 3.1.x | Web dashboard, blueprint routes, SSE streaming | Current stable is 3.1.3. The app factory pattern is already in place. Wake word routes should be a new blueprint following the existing pattern in `webconfig/app/routes/`. |
| flask-sock | >=0.7.0 | WebSocket support (existing) | Already in use for real-time comms. Wake word event streaming should use SSE (not WebSocket) to avoid competing with the existing WebSocket session channel. |

### Supporting Libraries (Already Present -- No New Dependencies Needed)

| Library | Version | Purpose | Integration Role |
|---------|---------|---------|-----------------|
| python-dotenv | >=1.0 | .env configuration loading | Wake word config vars (`WAKE_WORD_ENABLED`, `WAKE_WORD_SENSITIVITY`, etc.) already defined in `core/config.py` via dotenv. Settings persistence writes back to `.env`. |
| threading (stdlib) | N/A | Wake word listener runs in background thread | `WakeWordController` already uses threading internally. Integration in `button.py` needs thread-safe session start/stop. |
| queue (stdlib) | N/A | Event queue for wake word events | `WakeWordController._event_queue` already provides a thread-safe `Queue[WakeWordEvent]` for SSE consumption. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ruff | Linting/formatting | Already configured in pyproject.toml. Line length 88, isort enabled. All new code must pass `ruff check` and `ruff format`. |
| pre-commit | Git hooks for ruff | Already configured in `.pre-commit-config.yaml`. |

## Installation

No new packages are needed. The existing `requirements.txt` already includes everything:

```bash
# Already in requirements.txt -- verify versions are pinned:
pip install pvporcupine  # Pin to current 3.0.x to avoid accidental v4 upgrade
pip install sounddevice numpy"<2" scipy flask flask-sock python-dotenv
```

**Recommendation:** Pin pvporcupine to `pvporcupine>=3.0.0,<4.0.0` in requirements.txt to prevent accidental upgrade to v4 which could break keyword model compatibility.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pvporcupine (Porcupine) | openWakeWord | If Picovoice licensing becomes a problem. openWakeWord is fully open-source but requires more CPU, has lower accuracy, and needs TFLite runtime on ARM. The codebase previously tried and removed openWakeWord (commit 53a0cb4). |
| pvporcupine (Porcupine) | Snowboy | Never. Snowboy is abandoned (2020), no Python 3.10+ support, no ARM64 builds. |
| pvporcupine (Porcupine) | Mycroft Precise | Never for new projects. Mycroft shut down in 2023. Community fork exists but is not actively maintained. |
| Native Flask SSE (generator + text/event-stream) | flask-sse (Redis-backed) | Only if you need multi-process pub/sub. This project runs single-process on Pi -- native SSE with `queue.Queue` is simpler and has zero extra dependencies. |
| Native Flask SSE | WebSocket for wake word events | Only if bidirectional comms needed. Wake word events are unidirectional (server -> client). SSE is simpler, auto-reconnects, and avoids competing with the existing flask-sock WebSocket channel. |
| RMS threshold (amplitude) fallback | VAD (Voice Activity Detection) like webrtcvad | If you need speech detection rather than loud-sound detection. RMS threshold is appropriate for wake word fallback because it just detects "someone is talking near the mic" as a trigger heuristic, not speech recognition. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| pvporcupine 4.0.x | v4 uses a new engine; existing `.ppn` keyword files were trained on v3 and may not be compatible. Upgrading requires re-training custom keywords via Picovoice Console and testing. Separate milestone. | pvporcupine 3.0.x (pin `<4.0.0`) |
| openWakeWord | Previously tried and removed from this project (commit 53a0cb4). Higher CPU usage on Pi, requires TFLite, lower accuracy than Porcupine for custom keywords. | pvporcupine (already works) |
| PyAudio | Legacy audio library with notoriously painful installation on ARM (requires portaudio-dev headers, often version conflicts). | sounddevice (already in use, wraps PortAudio cleanly) |
| flask-sse | Requires Redis as a dependency -- overkill for a single-process Pi application. Adds operational complexity for no benefit. | Native Flask SSE with `Response(generator, mimetype='text/event-stream')` |
| Polling (AJAX) for wake word status | Wastes CPU on Pi with constant HTTP requests. Wake word events are sporadic. | SSE -- single long-lived connection, server pushes events as they occur |
| asyncio for wake word listener | WakeWordController is synchronous/threaded by design. Mixing asyncio with the callback-based `sd.InputStream` adds complexity for no gain. | Threading (already used in hotword.py) |

## Stack Patterns for This Milestone

**Pattern: SSE for wake word event streaming**
- Flask route returns `Response(generate(), mimetype='text/event-stream')`
- Generator reads from `WakeWordController._event_queue` with timeout
- Frontend uses `EventSource` API (native browser, no library needed)
- Events: `meter` (RMS level), `detected` (wake word triggered), `status` (state changes), `error`
- This is the standard pattern for Flask SSE without dependencies

**Pattern: Blueprint for wake word routes**
- New file: `webconfig/app/routes/wakeword.py`
- Blueprint name: `wakeword_bp`
- Routes: `/wakeword/status`, `/wakeword/events` (SSE), `/wakeword/config` (GET/POST), `/wakeword/test`, `/wakeword/calibrate`
- Follows existing pattern in `webconfig/app/routes/audio.py`, `persona.py`, etc.

**Pattern: Trigger abstraction in button.py**
- Add `trigger_session_start(source: str)` and `trigger_session_stop(source: str)` functions
- `source` parameter: `"button"`, `"wake_word"`, `"ui_test"`
- Wake word callback calls `trigger_session_start("wake_word")`
- Existing `on_button()` calls `trigger_session_start("button")`
- Both share the same session lifecycle (lock, thread, BillySession)

**Pattern: .env persistence for wake word settings**
- Read: already handled by `core/config.py` via `python-dotenv`
- Write: use `dotenv.set_key()` to update `.env` file when user changes settings via web UI
- This matches how other settings (SPEAKER_PREFERENCE, MIC_PREFERENCE) are likely persisted

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pvporcupine 3.0.x | Python 3.9-3.12, Raspberry Pi OS (32-bit and 64-bit), Pi 3/4/5 | Requires Picovoice access key (free tier: 3 devices). Custom `.ppn` files must match engine version. |
| pvporcupine 3.0.x | numpy <2.0 | Porcupine processes int16 frames; numpy <2 constraint already in requirements.txt is compatible. |
| sounddevice 0.4.x | numpy <2.0, scipy >=1.7 | No known conflicts. Uses PortAudio C library underneath. |
| Flask 3.1.x | Python 3.9+, flask-sock 0.7+ | App factory pattern works unchanged. SSE routes are just standard Flask responses. |
| scipy >=1.11 | numpy <2.0, Python 3.9-3.12 | Used only for `scipy.signal.resample()` in hotword.py. Lightweight usage. |

## Key Constraints

1. **No new pip dependencies** -- everything needed is already in requirements.txt
2. **Pin pvporcupine <4.0.0** -- protect against breaking keyword model changes
3. **Single-process architecture** -- Pi runs one Flask process, one wake word listener thread. No need for Redis, Celery, or multi-process patterns.
4. **ARM compatibility** -- all packages must have ARM (aarch64 or armv7l) wheels or pure Python. Everything in the current stack satisfies this.

## Sources

- [pvporcupine on PyPI](https://pypi.org/project/pvporcupine/) -- version 4.0.2 is latest, but v3.0.x is what the project uses (HIGH confidence)
- [Porcupine GitHub releases](https://github.com/Picovoice/porcupine/releases) -- v4.0 release notes confirm engine changes, no Python-specific breaking changes documented but keyword model format likely changed (MEDIUM confidence on model compatibility)
- [Flask on PyPI](https://pypi.org/project/Flask/) -- 3.1.3 is current stable (HIGH confidence)
- [Flask SSE patterns](https://maxhalford.github.io/blog/flask-sse-no-deps/) -- native SSE without dependencies is the standard Flask approach (HIGH confidence)
- [Picovoice Porcupine docs](https://picovoice.ai/docs/porcupine/) -- Python quick start, API reference (HIGH confidence)
- Codebase analysis: `core/hotword.py`, `core/button.py`, `core/config.py`, `webconfig/app/routes/` -- direct code reading (HIGH confidence)

---
*Stack research for: Wake word reintegration on Raspberry Pi voice assistant*
*Researched: 2026-03-24*
