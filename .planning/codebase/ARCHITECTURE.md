# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Layered event-driven architecture with separation between voice conversation engine, hardware control, configuration management, and web-based administration interface.

**Key Characteristics:**
- Real-time voice conversation sessions powered by OpenAI Realtime API or similar providers
- Hardware integration: GPIO-based button/motor control, audio I/O via sounddevice
- Configuration driven by INI files (personas, profiles, traits) and environment variables
- Web dashboard for configuration and monitoring via Flask with WebSockets for live updates
- MQTT integration for smart home commands and remote control

## Layers

**1. Entry Point & Signal Handling:**
- Location: `main.py`
- Purpose: Application initialization, environment setup, signal handling (graceful shutdown)
- Contains: .env file setup, daemon thread spawning, cleanup routines
- Depends on: All core modules (audio, button, mqtt, movements)
- Used by: OS when application starts

**2. Hardware Abstraction (Peripherals):**
- Location: `core/button.py`, `core/movements.py`, `core/audio.py`, `core/mic.py`
- Purpose: Abstract GPIO pins, motor control, audio playback/capture
- Contains: Mock implementations for non-hardware environments
- Key patterns:
  - `core/button.py`: Button press detection with debouncing, long-press handling
  - `core/movements.py`: Head/tail motor control with async support
  - `core/audio.py`: Microphone input queue, playback queue, WAV file handling
  - `core/mic.py`: Device enumeration and audio source management
- Depends on: gpiozero (optional), sounddevice, scipy
- Used by: Session manager, button handler, playback system

**3. Configuration & State Management:**
- Location: `core/config.py`, `core/persona.py`, `core/persona_manager.py`, `core/profile_manager.py`
- Purpose: Load and manage environment variables, personas, user profiles, personality traits
- Contains:
  - `core/config.py`: Environment variable parsing, numeric validation, cache paths
  - `core/persona.py`: PersonaProfile dataclass for trait scoring
  - `core/persona_manager.py`: Load/list available personas from INI files
  - `core/profile_manager.py`: UserProfile class for user-specific memories and preferences
- Depends on: dotenv, configparser
- Used by: Session manager, web routes, instruction builder

**4. Conversation Engine (Session Management):**
- Location: `core/session_manager.py` with supporting handlers in `core/session/`
- Purpose: Orchestrate real-time voice conversations with AI providers
- Contains:
  - `core/session_manager.py`: BillySession class managing session lifecycle, event routing
  - `core/session/state_machine.py`: SessionState for turn-level detection, transcript tracking
  - `core/session/audio_handler.py`: Audio encoding/decoding for provider communication
  - `core/session/function_handler.py`: Route function calls (conversation_state, play_song, etc.)
  - `core/session/instruction_builder.py`: Generate AI prompts with persona + user context
  - `core/session/tool_manager.py`: Tool availability based on mode (guest/user)
  - `core/session/user_handler.py`: identify_user, store_memory, manage_profile operations
  - `core/session/persona_handler.py`: update_personality, switch_persona operations
- Depends on: websockets, audio handlers, configuration managers
- Used by: Button press handler, MQTT command handler

**5. Voice Provider Integration:**
- Location: `core/realtime_ai_provider.py`, `core/providers/openai_provider.py`, `core/providers/xai_provider.py`
- Purpose: Abstract different AI voice providers (OpenAI Realtime, xAI Grok)
- Contains: Provider registry, connection management, WebSocket event handling
- Depends on: websockets, configured API credentials
- Used by: Session manager for WebSocket communication

**6. Domain-Specific Services:**
- Location: `core/news_digest.py`, `core/weather.py`, `core/search.py`, `core/song_manager.py`, `core/hotword.py`
- Purpose: Handle specific features
- Key services:
  - `core/news_digest.py`: Fetch news, weather, sports via external APIs
  - `core/weather.py`: Weather data retrieval
  - `core/search.py`: Web search capability
  - `core/song_manager.py`: Manage and play special songs
  - `core/hotword.py`: Wake word detection (currently disabled in recent commits)
- Used by: Function handler for tool implementations

**7. Smart Home & MQTT:**
- Location: `core/mqtt.py`, `core/ha.py`
- Purpose: MQTT subscription for remote commands, Home Assistant integration
- Contains:
  - `core/mqtt.py`: MQTT client lifecycle, message routing (billy/command, billy/say, billy/song)
  - `core/ha.py`: Send conversation prompts to Home Assistant
- Depends on: paho.mqtt
- Used by: Session manager for responding to MQTT events

**8. Web Administration (Flask):**
- Location: `webconfig/server.py`, `webconfig/app/`, `webconfig/templates/`, `webconfig/static/js/`
- Purpose: Configuration interface, system monitoring, profile management
- Contains:
  - `webconfig/app/__init__.py`: Flask app factory with blueprint registration
  - `webconfig/app/routes/`: System, persona, profile, audio, songs, misc endpoints
  - `webconfig/app/websocket.py`: WebSocket for real-time log streaming
  - `webconfig/static/js/`: Client-side forms, config service, WebSocket client
  - `webconfig/templates/`: Jinja2 templates for HTML pages
- Depends on: Flask, Flask-Sock
- Used by: Browser clients

**9. Utilities & Logging:**
- Location: `core/logger.py`, `core/say.py`, `core/base_tools.py`, `core/wakeup.py`
- Purpose: Shared utilities
- Key utilities:
  - `core/logger.py`: Custom logger with emoji formatting and level control
  - `core/say.py`: Text-to-speech via playback queue
  - `core/base_tools.py`: Base tool implementations
- Depends on: All layers for logging

## Data Flow

**Voice Conversation Flow (Primary):**

1. Button press detected in `core/button.py` → calls `start_loop()` → awaits voice session
2. `core/session_manager.py` creates `BillySession` instance
3. Session connects to OpenAI Realtime API via `core/providers/openai_provider.py`
4. Audio input streamed from `core/audio.py` playback_queue → WebSocket → Provider
5. Provider sends events (transcript_delta, response_created, audio_delta, function_call_arguments_done)
6. `core/session/state_machine.py` tracks turn state, signals response readiness
7. `core/session/audio_handler.py` decodes provider audio → playback_queue
8. `core/audio.py` playback thread renders audio + synchronizes motor animations
9. Function calls routed through `core/session/function_handler.py`:
   - conversation_state → state tracking
   - play_song → `core/song_manager.py`
   - get_news_digest → `core/news_digest.py`
   - identify_user → `core/session/user_handler.py`
   - smart_home_command → `core/ha.py` or MQTT
10. Session ends when user stops speaking or max turns exceeded

**MQTT Command Flow:**

1. MQTT message received on `billy/command` or `billy/say` topic
2. `core/mqtt.py` on_message callback → creates session with kickoff text
3. Session processes like button-initiated flow (steps 2-10 above)
4. Result published back to `billy/response` or `billy/state`

**Configuration Load Flow:**

1. `main.py` or `webconfig/server.py` calls `core/profile_manager.user_manager.load_default_user()`
2. UserManager loads user from INI → populates context
3. Session instruction builder (`core/session/instruction_builder.py`) combines:
   - Base instructions from `core/config.INSTRUCTIONS`
   - Persona traits from `core/persona_manager.load_persona()`
   - User memories from `core/profile_manager.UserProfile`
4. Instruction string sent to AI provider as system prompt

**State Management:**

- **Session State:** Tracked in `core/session/state_machine.py` SessionState object:
  - Full response text accumulation
  - Turn announcement flags
  - Transcript stream tracking
  - Short audio response detection
  - Follow-up detection
- **Conversation State:** Stored via conversation_state tool calls indicating expects_follow_up flag
- **User Memory:** Persistent in INI files (`profiles/*.ini` or `persona.ini`)
- **Motor State:** Global tracking in `core/movements.py` prevents concurrent operations

## Key Abstractions

**BillySession:**
- Purpose: Single conversation session orchestrator
- Examples: `core/session_manager.py` lines 90-200
- Pattern: Async context manager with event loop integration
- Lifecycle: __init__ → connect → handle_events → cleanup

**SessionState:**
- Purpose: Granular turn-level state tracking
- Examples: `core/session/state_machine.py`
- Pattern: Nested state machine (response_active, allow_mic_input, follow_up_expected)
- Methods: on_response_created(), on_transcript_delta(), detect_short_audio_response()

**InstructionBuilder:**
- Purpose: Context-aware prompt generation
- Examples: `core/session/instruction_builder.py` lines 22-124
- Pattern: Singleton with context-specific branching (guest vs user mode)
- Method: build(InstructionContext) → formatted instruction string

**FunctionHandler:**
- Purpose: Route AI tool calls to implementations
- Examples: `core/session/function_handler.py` lines 16-58
- Pattern: Dispatch table with async handlers
- Handlers for: conversation_state, update_personality, play_song, smart_home_command, identify_user, store_memory, get_news_digest

**PersonaManager & UserProfile:**
- Purpose: Load and switch between personas; track user preferences and memories
- Examples: `core/persona_manager.py`, `core/profile_manager.py`
- Pattern: INI file backed with in-memory cache
- Methods: load_persona(), get_available_personas(), switch_persona()

**VoiceProviderRegistry:**
- Purpose: Support multiple AI voice providers with common interface
- Examples: `core/realtime_ai_provider.py`, `core/providers/openai_provider.py`
- Pattern: Registry pattern with provider-specific implementations
- Methods: get_provider() → OpenAIProvider | XAIProvider

## Entry Points

**1. CLI - Voice Assistant:**
- Location: `main.py`
- Triggers: `python main.py` when application starts
- Responsibilities:
  - Ensure .env exists (copy from .env.example if missing)
  - Load environment via dotenv
  - Initialize logger and reload log level
  - Load default user profile
  - Start MQTT daemon thread
  - Start motor watchdog
  - Run button event loop (waits for hardware or Enter key)

**2. Web Server:**
- Location: `webconfig/server.py`
- Triggers: `python webconfig/server.py`
- Responsibilities:
  - Load .env before app initialization
  - Create Flask app via `webconfig/app/__init__.py`
  - Bootstrap cached data (versions, release notes)
  - Register route blueprints (system, persona, profiles, audio, misc, songs)
  - Register WebSocket blueprint for log streaming
  - Listen on 0.0.0.0:FLASK_PORT

**3. Button Press:**
- Location: `core/button.py`
- Triggers: Physical button press on GPIO pin or Enter key in mock mode
- Responsibilities:
  - Debounce physical press (50ms)
  - Detect long-press for alternative actions
  - Create BillySession and start conversation
  - Handle press/hold/release callbacks

**4. MQTT Commands:**
- Location: `core/mqtt.py`
- Triggers: Message on `billy/command`, `billy/say`, `billy/song`, `billy/wakeup/play` topics
- Responsibilities:
  - Subscribe to command topics
  - Create session with kickoff text from message payload
  - Route to appropriate handler (play song, wakeup sound, conversation)

**5. Web Routes:**
- Location: `webconfig/app/routes/`
- Triggers: HTTP requests to `/system/*`, `/persona/*`, `/profiles/*`, `/audio/*`, `/songs/*`, `/misc/*`
- Responsibilities: Return JSON or HTML responses for configuration changes, file uploads, system info

## Error Handling

**Strategy:** Try-except with logging at boundaries, graceful degradation

**Patterns:**

1. **Session Errors:**
   - Caught in `main.py` main() try-except block
   - Motors stopped via cleanup_gpio()
   - MQTT stopped via stop_mqtt()
   - Logged via logger.error()

2. **Provider Connection Errors:**
   - Caught in `BillySession.__init__()` and reconnect loops
   - Logged but session continues (fallback to text-only mode if configured)
   - Retry logic with exponential backoff in MQTT connection thread

3. **Function Handler Errors:**
   - Caught in `FunctionHandler.handle()` lines 43-58
   - Tool errors logged but don't crash session
   - Malformed JSON automatically repaired (lines 60-80)

4. **Audio Device Errors:**
   - Caught in `core/audio.py` device initialization
   - Falls back to default device if preferred unavailable
   - Logs warning, continues with fallback

5. **Configuration Errors:**
   - Missing env vars default to reasonable values (see `core/config.py` _float_env)
   - Missing persona files logged as warning, uses fallback instructions
   - Corrupted profile JSON recovered via regex pattern matching (lines 50-60 in profile_manager.py)

## Cross-Cutting Concerns

**Logging:**
- Framework: Custom `core/logger.py` wrapper around standard logging
- Levels: VERBOSE, INFO, WARNING, ERROR, SUCCESS
- Pattern: logger.info(message, emoji) used throughout
- Configuration: LOG_LEVEL env var controls verbosity

**Validation:**
- Instructions built with InstructionContext dataclass (type hints)
- Function arguments parsed via _parse_json_args() with fallback repair
- Audio device validation in audio.py before creating streams
- Profile data validated during load (JSON recovery)

**Authentication:**
- Web routes use Flask session-based auth (username/password)
- MQTT uses username/password stored in env (MQTT_USERNAME, MQTT_PASSWORD)
- AI provider auth via API_KEY env var

**State Persistence:**
- User profiles: INI files in `profiles/` directory
- Personas: INI files in `persona_presets/` or root `persona.ini`
- Session state: In-memory, cleared per session
- Conversation state: Persisted via conversation_state function calls to session

---

*Architecture analysis: 2026-03-24*
