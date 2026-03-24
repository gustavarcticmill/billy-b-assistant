<!-- GSD:project-start source:PROJECT.md -->
## Project

**Billy B Assistant — Wake Word Reintegration & Stabilization**

A voice-activated animatronic fish (Billy Bass) running on Raspberry Pi that serves as a conversational AI assistant. Users interact via hardware button press or wake word detection. The fish talks back using AI (Claude via Anthropic API or Home Assistant's conversation agent), moves its mouth/tail in sync, and can control smart home devices via Home Assistant/MQTT integration. A Flask-based web dashboard provides configuration, persona management, and audio calibration.

**Core Value:** The fish responds to voice — both button press and hands-free wake word activation — routing queries intelligently between Claude (general conversation, news, knowledge) and Home Assistant (device control, local automations).

### Constraints

- **Platform**: Raspberry Pi (Linux/ARM) — must work with limited resources
- **Existing code**: Must preserve upstream's refactored architecture (app factory, blueprints, modular JS)
- **Hardware module**: core/hotword.py must not be modified unless strictly necessary for integration
- **Style**: Follow existing patterns — use `logger` not `print()`, same Tailwind classes, IIFE JS module pattern, blueprint pattern for routes
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.x - Core backend logic, AI integration, audio processing, hardware control
- JavaScript - Web configuration UI frontend, WebSocket communication
- HTML/CSS - Web interface templates and styling (Tailwind CSS)
- Bash - System setup and initialization scripts in `setup/system/`
## Runtime
- Linux/Raspberry Pi OS - Target deployment platform
- pip (Python)
- npm (Node.js/JavaScript)
## Frameworks
- Flask 2.x - Web server framework in `webconfig/server.py` and `webconfig/app/`
- Flask-Sock - WebSocket support for real-time communication in `webconfig/app/websocket.py`
- python-dotenv - Environment configuration management
- sounddevice - Microphone and speaker device management in `core/audio.py`
- scipy - Audio signal processing and resampling
- pydub - Audio file manipulation and conversion
- numpy - Numerical array operations for audio data
- OpenAI API - Real-time AI via WebSocket in `core/providers/openai_provider.py`
- X.AI (xAI) API - Alternative AI provider in `core/providers/xai_provider.py`
- websockets.asyncio.client - WebSocket client for AI provider connections
- gpiozero - GPIO control for motors, buttons, LEDs on Raspberry Pi
- lgpio - Low-level GPIO library alternative
- paho-mqtt - MQTT client for Home Assistant integration in `core/mqtt.py`
- aiohttp - Async HTTP client for Home Assistant API in `core/ha.py`
- requests - HTTP requests for news feeds in `core/news_digest.py`
- aiohttp - Async HTTP client for weather and search APIs in `core/weather.py`, `core/search.py`
- pvporcupine - Picovoice Porcupine wake word detection engine
- TailwindCSS 4.1.11 - CSS utility framework in `webconfig/package.json`
- PostCSS 8.4.38 - CSS processing pipeline
- Autoprefixer 10.4.21 - CSS vendor prefix automation
## Key Dependencies
- sounddevice - Essential for audio input/output on hardware
- openai (implicit via websockets) - Primary AI conversation provider
- paho-mqtt - Core integration with Home Assistant via MQTT
- gpiozero - Hardware motor and button control
- websockets - Real-time bidirectional communication with AI providers
- aiohttp - Async HTTP for weather, news, and Home Assistant APIs
- scipy & numpy - Audio signal processing and manipulation
- flask, flask-sock - Web interface and WebSocket endpoint
- pvporcupine - Wake word detection
## Configuration
- Location: `.env` file (created from `.env.example` if missing in `main.py`)
- Loaded via: `python-dotenv` in `core/config.py`
- Key configs:
- `pyproject.toml` - Python project metadata and ruff linter/formatter configuration
- `webconfig/package.json` - Node.js dependencies for frontend CSS building
- `.pre-commit-config.yaml` - Pre-commit hooks for ruff (lint/format)
- Ruff - Linting and formatting (Python) via `.pre-commit-config.yaml`
## Platform Requirements
- Python 3.x with pip
- Node.js with npm (for CSS building only)
- Raspberry Pi or compatible Linux system (for GPIO)
- Audio input/output devices
- MQTT broker (optional, for smart home integration)
- Home Assistant instance (optional)
- Raspberry Pi or similar ARM/Linux single-board computer
- Microphone and speaker devices
- GPIO pins for motors/buttons (specific pins in `core/config.py`)
- Network connectivity for API calls
- Optional: MQTT broker (home automation)
- Optional: Home Assistant instance
- FLASK_PORT environment variable to specify web server port
- `.env` file with API keys and configuration
- `persona.ini` file for personality configuration
- `news_sources.json` file for news feed configuration (auto-generated with defaults)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python modules: `lowercase_with_underscores.py` (e.g., `logger.py`, `persona_manager.py`)
- JavaScript files: `lowercase-with-hyphens.js` for utility modules (e.g., `config-service.js`, `ui-helpers.js`)
- Route modules: Named after their domain (e.g., `audio.py`, `system.py`, `profiles.py` in `webconfig/app/routes/`)
- Python: `snake_case` (e.g., `ensure_env_file()`, `_normalize_source_payload()`, `detect_devices()`)
- Private/internal functions: Prefixed with `_` (e.g., `_float_env()`, `_get_current_level()`, `_pick_mic_rate()`)
- JavaScript: `camelCase` (e.g., `fetchConfig()`, `showNotification()`, `toggleInputVisibility()`)
- Python: `snake_case` for local/module variables (e.g., `playback_queue`, `MIC_DEVICE_INDEX`, `configCache`)
- Python: `UPPER_SNAKE_CASE` for constants and global configuration variables (e.g., `CHUNK_MS`, `MIC_PREFERENCE`, `RESPONSE_HISTORY_DIR`)
- JavaScript: `camelCase` (e.g., `configCache`, `CACHE_DURATION`)
- Python: `PascalCase` (e.g., `BillyLogger`, `PersonaManager`, `UserProfile`, `BillySession`)
- Private/Mock classes: Prefixed with underscore or "Mock" (e.g., `MockButton`, `MockLgpio`)
- Python: `PascalCase` for class, `UPPER_CASE` for members (e.g., `LogLevel.ERROR`, `LogLevel.INFO`)
## Code Style
- Tool: `ruff` (via ruff-format)
- Line length: 88 characters
- Indent width: 4 spaces
- Line ending: native (auto-detect)
- Quote style: preserve existing quotes
- Tool: `ruff` with custom configuration
- Config file: `pyproject.toml` in root
- Format preview mode enabled
- Import sorting follows `isort` profile with 2 blank lines after imports
- Docstring style: triple double quotes
- Maximum line length enforced at 88 characters
## Import Organization
- Relative imports use dot notation: `from .module import name` or `from . import module`
- Absolute imports from `core/`: `from core.logger import logger`
- Absolute imports in Flask routes: `from ..core_imports import core_config`
## Error Handling
- Broad exception catching with `except Exception as e:` is common for operational robustness
- Specific exception types used when recovery differs (e.g., `except json.JSONDecodeError`)
- Error messages logged via `logger.error()` with emoji prefix
- Fallback values returned on error rather than raising (e.g., `_float_env()` returns default on ValueError)
- Recovery attempts for corrupted data (see `profile_manager.py` memory recovery logic)
- Try-except blocks used extensively in audio initialization and device detection
- Missing optional dependencies trigger mock implementations (e.g., `MockButton`, `MockLgpio`)
- GPIO library optionally imported with fallback to keyboard input
- Device detection continues with default values if unavailable
## Logging
- All logging goes through global `logger` singleton instance
- Log methods accept optional `emoji` parameter for visual distinction
- Log levels: `ERROR`, `WARNING`, `INFO`, `VERBOSE` (enum-based)
- Configuration via `LOG_LEVEL` environment variable
- Special methods for common patterns: `logger.success()`, `logger.debug()`
- Module-level convenience functions provided (e.g., `log_info()`, `log_error()`) for backward compatibility
- Direct access via `logger` object preferred in new code
## Comments
- Complex logic that isn't immediately clear (e.g., sample rate detection logic in `audio.py`)
- Configuration sections marked with `# === SECTION NAME ===` pattern
- Emoji comments for visual scanning (e.g., `# 🐟 Play wake-up clip`)
- TODO/FIXME comments tracked in code
- Comments above function definitions explaining non-obvious behavior
- Python docstrings use triple double quotes
- Module-level docstrings present (e.g., `core/persona_manager.py` has module docstring)
- Class docstrings provided (e.g., `"""Manages different Billy personas and personality configurations."""`)
- Function docstrings use imperative mood where applicable
- Single-line docstrings for simple functions
## Function Design
- Functions typically 10-50 lines
- Single-letter variables avoided (use `card_index` not `c`)
- Helper functions prefixed with underscore for privacy
- Type hints used consistently (e.g., `def _float_env(key: str, default: str) -> float:`)
- Optional parameters use `Optional[]` type hint
- Dictionary parameters documented in docstring or comments
- Explicit return types via type hints
- `Optional[Type]` for nullable returns
- Union types for multiple possible types
## Module Design
- Classes and functions intended for external use not prefixed with underscore
- Private module-level functions prefixed with `_`
- Global configuration accessed via `core.config` module
- `__init__.py` files kept minimal in `core/` (mostly empty)
- Routes registered via Blueprint pattern in `webconfig/app/routes/`
- Direct imports from modules preferred
## Type Hints
- Type hints consistently applied to function signatures
- Generic types used: `list[dict]`, `dict[str, Any]`, `Optional[Type]`
- Union types: `BillySession | None` (using `|` syntax)
- Type hints for class attributes in `__init__`
## Threading and Async
- `threading.Thread()` used for daemon threads (e.g., `start_mqtt`, `motor_watchdog`)
- `asyncio` for async operations in Flask routes
- Global locks using `threading.Lock()` for critical sections
- Queue objects from `queue.Queue` for thread-safe communication
## JavaScript Conventions
- Immediately-invoked function expressions (IIFE) for module encapsulation
- Object return with public methods (e.g., `ConfigService`)
- DOM manipulation via vanilla JavaScript (no framework)
- Event listeners attached to document for delegation
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Real-time voice conversation sessions powered by OpenAI Realtime API or similar providers
- Hardware integration: GPIO-based button/motor control, audio I/O via sounddevice
- Configuration driven by INI files (personas, profiles, traits) and environment variables
- Web dashboard for configuration and monitoring via Flask with WebSockets for live updates
- MQTT integration for smart home commands and remote control
## Layers
- Location: `main.py`
- Purpose: Application initialization, environment setup, signal handling (graceful shutdown)
- Contains: .env file setup, daemon thread spawning, cleanup routines
- Depends on: All core modules (audio, button, mqtt, movements)
- Used by: OS when application starts
- Location: `core/button.py`, `core/movements.py`, `core/audio.py`, `core/mic.py`
- Purpose: Abstract GPIO pins, motor control, audio playback/capture
- Contains: Mock implementations for non-hardware environments
- Key patterns:
- Depends on: gpiozero (optional), sounddevice, scipy
- Used by: Session manager, button handler, playback system
- Location: `core/config.py`, `core/persona.py`, `core/persona_manager.py`, `core/profile_manager.py`
- Purpose: Load and manage environment variables, personas, user profiles, personality traits
- Contains:
- Depends on: dotenv, configparser
- Used by: Session manager, web routes, instruction builder
- Location: `core/session_manager.py` with supporting handlers in `core/session/`
- Purpose: Orchestrate real-time voice conversations with AI providers
- Contains:
- Depends on: websockets, audio handlers, configuration managers
- Used by: Button press handler, MQTT command handler
- Location: `core/realtime_ai_provider.py`, `core/providers/openai_provider.py`, `core/providers/xai_provider.py`
- Purpose: Abstract different AI voice providers (OpenAI Realtime, xAI Grok)
- Contains: Provider registry, connection management, WebSocket event handling
- Depends on: websockets, configured API credentials
- Used by: Session manager for WebSocket communication
- Location: `core/news_digest.py`, `core/weather.py`, `core/search.py`, `core/song_manager.py`, `core/hotword.py`
- Purpose: Handle specific features
- Key services:
- Used by: Function handler for tool implementations
- Location: `core/mqtt.py`, `core/ha.py`
- Purpose: MQTT subscription for remote commands, Home Assistant integration
- Contains:
- Depends on: paho.mqtt
- Used by: Session manager for responding to MQTT events
- Location: `webconfig/server.py`, `webconfig/app/`, `webconfig/templates/`, `webconfig/static/js/`
- Purpose: Configuration interface, system monitoring, profile management
- Contains:
- Depends on: Flask, Flask-Sock
- Used by: Browser clients
- Location: `core/logger.py`, `core/say.py`, `core/base_tools.py`, `core/wakeup.py`
- Purpose: Shared utilities
- Key utilities:
- Depends on: All layers for logging
## Data Flow
- **Session State:** Tracked in `core/session/state_machine.py` SessionState object:
- **Conversation State:** Stored via conversation_state tool calls indicating expects_follow_up flag
- **User Memory:** Persistent in INI files (`profiles/*.ini` or `persona.ini`)
- **Motor State:** Global tracking in `core/movements.py` prevents concurrent operations
## Key Abstractions
- Purpose: Single conversation session orchestrator
- Examples: `core/session_manager.py` lines 90-200
- Pattern: Async context manager with event loop integration
- Lifecycle: __init__ → connect → handle_events → cleanup
- Purpose: Granular turn-level state tracking
- Examples: `core/session/state_machine.py`
- Pattern: Nested state machine (response_active, allow_mic_input, follow_up_expected)
- Methods: on_response_created(), on_transcript_delta(), detect_short_audio_response()
- Purpose: Context-aware prompt generation
- Examples: `core/session/instruction_builder.py` lines 22-124
- Pattern: Singleton with context-specific branching (guest vs user mode)
- Method: build(InstructionContext) → formatted instruction string
- Purpose: Route AI tool calls to implementations
- Examples: `core/session/function_handler.py` lines 16-58
- Pattern: Dispatch table with async handlers
- Handlers for: conversation_state, update_personality, play_song, smart_home_command, identify_user, store_memory, get_news_digest
- Purpose: Load and switch between personas; track user preferences and memories
- Examples: `core/persona_manager.py`, `core/profile_manager.py`
- Pattern: INI file backed with in-memory cache
- Methods: load_persona(), get_available_personas(), switch_persona()
- Purpose: Support multiple AI voice providers with common interface
- Examples: `core/realtime_ai_provider.py`, `core/providers/openai_provider.py`
- Pattern: Registry pattern with provider-specific implementations
- Methods: get_provider() → OpenAIProvider | XAIProvider
## Entry Points
- Location: `main.py`
- Triggers: `python main.py` when application starts
- Responsibilities:
- Location: `webconfig/server.py`
- Triggers: `python webconfig/server.py`
- Responsibilities:
- Location: `core/button.py`
- Triggers: Physical button press on GPIO pin or Enter key in mock mode
- Responsibilities:
- Location: `core/mqtt.py`
- Triggers: Message on `billy/command`, `billy/say`, `billy/song`, `billy/wakeup/play` topics
- Responsibilities:
- Location: `webconfig/app/routes/`
- Triggers: HTTP requests to `/system/*`, `/persona/*`, `/profiles/*`, `/audio/*`, `/songs/*`, `/misc/*`
- Responsibilities: Return JSON or HTML responses for configuration changes, file uploads, system info
## Error Handling
## Cross-Cutting Concerns
- Framework: Custom `core/logger.py` wrapper around standard logging
- Levels: VERBOSE, INFO, WARNING, ERROR, SUCCESS
- Pattern: logger.info(message, emoji) used throughout
- Configuration: LOG_LEVEL env var controls verbosity
- Instructions built with InstructionContext dataclass (type hints)
- Function arguments parsed via _parse_json_args() with fallback repair
- Audio device validation in audio.py before creating streams
- Profile data validated during load (JSON recovery)
- Web routes use Flask session-based auth (username/password)
- MQTT uses username/password stored in env (MQTT_USERNAME, MQTT_PASSWORD)
- AI provider auth via API_KEY env var
- User profiles: INI files in `profiles/` directory
- Personas: INI files in `persona_presets/` or root `persona.ini`
- Session state: In-memory, cleared per session
- Conversation state: Persisted via conversation_state function calls to session
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
