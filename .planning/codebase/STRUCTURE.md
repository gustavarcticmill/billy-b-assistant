# Codebase Structure

**Analysis Date:** 2026-03-24

## Directory Layout

```
billy-b-assistant/
├── main.py                          # Entry point for voice assistant
├── .env.example                     # Environment template (secrets redacted)
├── persona.ini.example              # Default persona template
├── versions.ini.example             # Version tracking template
├── pyproject.toml                   # Python project config
├── requirements.txt                 # Python dependencies
├── README.md                        # Documentation
├── CHANGELOG.md                     # Version history
├── LICENSE.md                       # License file
├── wake-word-feature.md             # Wake word implementation docs
├── WAKE_WORD_REINTEGRATION_PROMPT.md # Wake word reintegration notes
│
├── .claude/                         # Claude Code integration hooks
├── .git/                            # Git repository
├── .planning/                       # GSD planning documents
│   └── codebase/                    # Architecture analysis (this location)
│
├── core/                            # Core assistant logic
│   ├── __init__.py
│   ├── logger.py                    # Custom logging with emoji support
│   ├── config.py                    # Environment & config loading
│   ├── persona.py                   # PersonaProfile dataclass
│   ├── persona_manager.py           # Load/switch personas
│   ├── profile_manager.py           # User profile & memory management
│   │
│   ├── session_manager.py           # BillySession orchestrator
│   ├── realtime_ai_provider.py      # AI provider registry
│   │
│   ├── session/                     # Session components
│   │   ├── __init__.py
│   │   ├── state_machine.py         # Turn-level state tracking
│   │   ├── instruction_builder.py   # Prompt generation with context
│   │   ├── audio_handler.py         # Audio encoding/decoding
│   │   ├── function_handler.py      # Tool call routing
│   │   ├── tool_manager.py          # Tool availability
│   │   ├── user_handler.py          # User identification & memory
│   │   ├── persona_handler.py       # Persona switching
│   │   ├── mic_manager_wrapper.py   # Microphone management
│   │   └── error_handler.py         # Error handling
│   │
│   ├── providers/                   # Voice provider implementations
│   │   ├── __init__.py
│   │   ├── openai_provider.py       # OpenAI Realtime API
│   │   └── xai_provider.py          # xAI Grok provider
│   │
│   ├── button.py                    # GPIO button input handling
│   ├── movements.py                 # Motor control (head, tail)
│   ├── audio.py                     # Audio I/O queues & playback
│   ├── mic.py                       # Microphone device enumeration
│   │
│   ├── mqtt.py                      # MQTT client & message routing
│   ├── ha.py                        # Home Assistant integration
│   ├── base_tools.py                # Base tool implementations
│   │
│   ├── news_digest.py               # News/weather/sports fetching
│   ├── news_manager.py              # News management
│   ├── weather.py                   # Weather data
│   ├── search.py                    # Web search capability
│   ├── song_manager.py              # Special songs management
│   ├── wakeup.py                    # Wake-up sequence handling
│   ├── say.py                       # Text-to-speech queue helper
│   └── hotword.py                   # Wake word detection (disabled)
│
├── webconfig/                       # Web administration interface
│   ├── server.py                    # Flask app entry point
│   │
│   ├── app/                         # Flask application
│   │   ├── __init__.py              # App factory (create_app)
│   │   ├── core_imports.py          # Load core config
│   │   ├── state.py                 # Shared state (cache)
│   │   ├── websocket.py             # WebSocket log streaming
│   │   │
│   │   └── routes/                  # API endpoints
│   │       ├── __init__.py
│   │       ├── system.py            # System config, GPIO, updates
│   │       ├── persona.py           # Persona management
│   │       ├── profiles.py          # User profile CRUD
│   │       ├── audio.py             # Audio settings, wakeup clips
│   │       ├── songs.py             # Song management
│   │       └── misc.py              # Settings, logs, env editor
│   │
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── base.html                # Base template
│   │   ├── index.html               # Main page
│   │   ├── components/              # Reusable components
│   │   │   ├── header.html
│   │   │   ├── settings-panel.html
│   │   │   ├── settings-form.html
│   │   │   ├── persona-form.html
│   │   │   ├── profile-panel.html
│   │   │   ├── profile-overview.html
│   │   │   ├── user-profile-main.html
│   │   │   ├── songs-modal.html
│   │   │   ├── password-modal.html
│   │   │   ├── env-editor-modal.html
│   │   │   └── ... (more components)
│   │   └── pages/                   # Full pages
│   │       ├── system.html
│   │       ├── personas.html
│   │       ├── profiles.html
│   │       ├── audio.html
│   │       └── songs.html
│   │
│   ├── static/                      # JavaScript & CSS
│   │   ├── css/                     # Tailwind-generated styles
│   │   │   └── styles.css
│   │   │
│   │   └── js/                      # Client-side JavaScript
│   │       ├── init.js              # Page initialization
│   │       ├── app-config.js        # App-wide configuration
│   │       ├── config-service.js    # HTTP client for API
│   │       ├── websocket.js         # WebSocket connection
│   │       │
│   │       ├── ui-helpers.js        # DOM utilities
│   │       ├── sections.js          # Navigation & section handling
│   │       │
│   │       ├── settings-panel.js    # Settings UI
│   │       ├── settings-form.js     # Settings form logic
│   │       ├── audio-panel.js       # Audio settings UI
│   │       ├── motor-panel.js       # Motor control UI
│   │       ├── persona-form.js      # Persona editing UI
│   │       ├── profile-panel.js     # Profile management UI
│   │       ├── pin-profile.js       # GPIO pin configuration
│   │       ├── log-panel.js         # Log viewer UI
│   │       ├── service-status.js    # Service status display
│   │       ├── version-release.js   # Version & release notes
│   │       ├── wakeup-clips.js      # Wake-up clips management
│   │       ├── songs-manager.js     # Songs management UI
│   │       └── marked-min.js        # Markdown parser (library)
│   │
│   └── tailwind/                    # Tailwind CSS config
│       ├── tailwind.config.js
│       └── package.json
│
├── persona_presets/                 # Pre-configured personas
│   ├── billy-b/
│   ├── billy-bauhaus/
│   ├── billy-beholder/
│   ├── billy-bellissima/
│   ├── billy-berserk/
│   ├── billy-blackbeard/
│   ├── billy-bodhi/
│   ├── billy-bourgignon/
│   ├── billy-bro/
│   ├── billy-buckingham/
│   └── blank/
│       └── persona.ini              # Each contains persona.ini
│
├── setup/                           # Installation & setup scripts
│   └── system/                      # System-level setup
│
├── sounds/                          # Audio assets
│   ├── wake-up/                     # Wake-up sounds
│   │   ├── custom/                  # User-configured sounds
│   │   └── default/                 # Default wake-up sounds
│   │
│   └── songs/                       # Special song files
│
├── wake-word-models/                # Wake word ML models (disabled)
│   ├── billy_en/
│   └── leo_dk/
│
├── test/                            # Test utilities
│   └── replay.py                    # Session replay for testing
│
├── docs/                            # Documentation
│   └── images/                      # Doc images
│
└── .gitignore                       # Git ignore rules
```

## Directory Purposes

**core/:**
- Purpose: Core voice assistant logic, separated from web interface
- Contains: Session management, AI integration, hardware control, configuration, services
- Key responsibility: Handle button presses and MQTT commands to manage voice conversations

**core/session/:**
- Purpose: Modular session components for separation of concerns
- Contains: State tracking, instruction building, audio handling, function routing, user/persona handling
- Key responsibility: Orchestrate a single voice conversation from start to finish

**core/providers/:**
- Purpose: Plug-in support for different AI voice providers
- Contains: Provider-specific WebSocket clients and configuration
- Key responsibility: Abstract provider implementation details from session manager

**webconfig/:**
- Purpose: Administrative web interface separate from core
- Contains: Flask app, routes, templates, static assets
- Key responsibility: Provide HTTP API for configuration and monitoring

**webconfig/app/routes/:**
- Purpose: Modular API endpoints organized by feature
- Contains: System config, persona management, user profiles, audio settings, songs
- Key responsibility: Handle specific configuration domains

**webconfig/templates/:**
- Purpose: Server-rendered HTML for web interface
- Contains: Base layouts and reusable components
- Key responsibility: Render forms and pages for configuration UI

**webconfig/static/js/:**
- Purpose: Client-side interactivity
- Contains: Form handling, API communication, WebSocket client, UI helpers
- Key responsibility: Make web interface responsive and communicate with API

**persona_presets/:**
- Purpose: Pre-configured personality templates
- Contains: persona.ini files with traits, backstory, instructions
- Key responsibility: Provide switchable personality profiles

**sounds/:**
- Purpose: Audio asset storage
- Contains: Wake-up sounds and special song files
- Key responsibility: Hold media files loaded by audio module

**test/:**
- Purpose: Testing utilities
- Contains: Session replay tool for debugging
- Key responsibility: Enable offline testing of conversation flows

**docs/:**
- Purpose: User-facing documentation
- Contains: README content and images
- Key responsibility: Document features and usage

## Key File Locations

**Entry Points:**
- `main.py`: CLI entry point for voice assistant
- `webconfig/server.py`: Web server entry point
- `core/button.py`: Hardware button event handling
- `core/mqtt.py`: MQTT message routing

**Configuration:**
- `core/config.py`: Environment variable parsing and defaults
- `.env`: Runtime secrets and settings (not committed)
- `persona.ini`: Default persona file (generated from .env.example)
- `persona_presets/*/persona.ini`: Pre-configured persona templates
- `profiles/*.ini`: User profile files (generated dynamically)

**Core Logic:**
- `core/session_manager.py`: BillySession - main conversation orchestrator
- `core/session/state_machine.py`: Turn-level state tracking
- `core/session/instruction_builder.py`: Prompt generation with context
- `core/session/function_handler.py`: Tool call routing
- `core/persona_manager.py`: Persona loading and switching
- `core/profile_manager.py`: User profile management

**Testing:**
- `test/replay.py`: Session replay utility
- No automated test suite (manual testing approach)

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `session_manager.py`, `audio_handler.py`)
- Jinja2 templates: `kebab-case.html` (e.g., `persona-form.html`, `profile-panel.html`)
- JavaScript files: `kebab-case.js` (e.g., `config-service.js`, `ui-helpers.js`)
- INI config: `*.ini` (e.g., `persona.ini`, `profiles/tom.ini`)

**Directories:**
- Lowercase with hyphens: `persona_presets/`, `wake-up/`, `static/`
- Underscores in code dirs: `core/session/`, `webconfig/app/routes/`

**Python Classes:**
- PascalCase: `BillySession`, `SessionState`, `UserProfile`, `PersonaManager`, `FunctionHandler`

**Python Functions/Methods:**
- snake_case: `load_persona()`, `build()`, `on_response_created()`, `handle_conversation_state()`

**Python Constants:**
- UPPERCASE: `MQTT_HOST`, `MIC_TIMEOUT_SECONDS`, `INSTRUCTIONS`, `PERSONALITY`

**Python Private Members:**
- Leading underscore: `_cache`, `_persona_cache`, `_turn_announced`

## Where to Add New Code

**New Feature (e.g., Weather Alerts):**
- Primary code: Create `core/weather_alerts.py`
- Integration: Add handler in `core/session/function_handler.py` (new tool dispatch)
- Web UI: Add route in `webconfig/app/routes/misc.py`
- Templates: Add component in `webconfig/templates/components/weather-alerts.html`
- Tests: Add to `test/replay.py` scenario

**New Persona:**
- Implementation: Create `persona_presets/billy-newname/persona.ini`
- Template: Copy from `persona_presets/blank/persona.ini`
- Discovery: Auto-discovered by `core/persona_manager.py` via glob
- No code changes needed

**New Session Handler (for tool):**
- Implementation: Create `core/session/new_handler.py` (e.g., `music_handler.py`)
- Export: Add to `core/session/__init__.py` __all__
- Integration: Import in `core/session_manager.py` and inject into BillySession
- Tests: Add scenario to `test/replay.py`

**New Web Route:**
- Implementation: Create handler in appropriate `webconfig/app/routes/*.py`
- Registration: Blueprint already registered in `webconfig/app/__init__.py`
- Template: Create in `webconfig/templates/components/` or `webconfig/templates/pages/`
- JavaScript: Add to `webconfig/static/js/` if interactive

**Utility Function:**
- Shared helpers: `core/base_tools.py` for tool implementations
- UI helpers: `webconfig/static/js/ui-helpers.js`
- Math/audio utilities: Extend `core/audio.py` or create new module

**Configuration:**
- New env var: Add to `.env.example` and document in `core/config.py`
- New persona trait: Add field to `core/persona.py` PersonaProfile dataclass
- New profile section: Extend `core/profile_manager.py` UserProfile._load_profile()

## Special Directories

**`.claude/`:**
- Purpose: Claude Code IDE integration hooks
- Generated: Yes
- Committed: Yes
- Contents: GSD workflow guards and system hooks

**`.planning/`:**
- Purpose: GSD planning and analysis documents
- Generated: Yes
- Committed: Yes
- Contents: Architecture analysis (ARCHITECTURE.md, STRUCTURE.md, etc.)

**`persona_presets/`:**
- Purpose: Pre-configured persona templates
- Generated: No
- Committed: Yes
- Contents: persona.ini files with personality traits and instructions

**`profiles/`:**
- Purpose: User-specific memory and preferences (generated at runtime)
- Generated: Yes
- Committed: No (in .gitignore)
- Contents: User profile INI files created on first user identification

**`sounds/wake-up/custom/`:**
- Purpose: Custom wake-up sounds uploaded via web UI
- Generated: Yes
- Committed: No (in .gitignore)
- Contents: WAV files uploaded by users

**`sounds/response-history/`:**
- Purpose: Cache of recent AI responses as WAV files
- Generated: Yes
- Committed: No (in .gitignore)
- Contents: Audio files for replay capability

**`wake-word-models/`:**
- Purpose: ML models for wake word detection (currently disabled)
- Generated: No
- Committed: Yes
- Status: Disabled in recent commits; reintegration planned

## Import Patterns

**Core Module Imports:**
```python
from core.config import MQTT_HOST, DEBUG_MODE
from core.logger import logger
from core.persona_manager import persona_manager
from core.profile_manager import user_manager
from core.session import BillySession, InstructionContext
```

**Session Module Imports:**
```python
from ..config import DEBUG_MODE  # Relative parent imports within session/
from ..logger import logger
from .state_machine import SessionState
from .function_handler import FunctionHandler
```

**Web Module Imports:**
```python
from flask import Flask, jsonify
from core.config import FLASK_PORT
from webconfig.app.core_imports import core_config
```

**No absolute web imports in core:** webconfig does not import from core to avoid circular dependencies (core is independent, webconfig depends on core)

---

*Structure analysis: 2026-03-24*
