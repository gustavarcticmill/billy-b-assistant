# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.x - Core backend logic, AI integration, audio processing, hardware control
- JavaScript - Web configuration UI frontend, WebSocket communication
- HTML/CSS - Web interface templates and styling (Tailwind CSS)

**Secondary:**
- Bash - System setup and initialization scripts in `setup/system/`

## Runtime

**Environment:**
- Linux/Raspberry Pi OS - Target deployment platform

**Package Manager:**
- pip (Python)
- npm (Node.js/JavaScript)

## Frameworks

**Core Backend:**
- Flask 2.x - Web server framework in `webconfig/server.py` and `webconfig/app/`
- Flask-Sock - WebSocket support for real-time communication in `webconfig/app/websocket.py`
- python-dotenv - Environment configuration management

**Audio & Voice:**
- sounddevice - Microphone and speaker device management in `core/audio.py`
- scipy - Audio signal processing and resampling
- pydub - Audio file manipulation and conversion
- numpy - Numerical array operations for audio data

**AI/LLM Integration:**
- OpenAI API - Real-time AI via WebSocket in `core/providers/openai_provider.py`
- X.AI (xAI) API - Alternative AI provider in `core/providers/xai_provider.py`
- websockets.asyncio.client - WebSocket client for AI provider connections

**Hardware Control:**
- gpiozero - GPIO control for motors, buttons, LEDs on Raspberry Pi
- lgpio - Low-level GPIO library alternative

**Smart Home & Automation:**
- paho-mqtt - MQTT client for Home Assistant integration in `core/mqtt.py`
- aiohttp - Async HTTP client for Home Assistant API in `core/ha.py`

**Web Search & Data:**
- requests - HTTP requests for news feeds in `core/news_digest.py`
- aiohttp - Async HTTP client for weather and search APIs in `core/weather.py`, `core/search.py`

**Wake Word Detection:**
- pvporcupine - Picovoice Porcupine wake word detection engine

**Frontend:**
- TailwindCSS 4.1.11 - CSS utility framework in `webconfig/package.json`
- PostCSS 8.4.38 - CSS processing pipeline
- Autoprefixer 10.4.21 - CSS vendor prefix automation

## Key Dependencies

**Critical:**
- sounddevice - Essential for audio input/output on hardware
- openai (implicit via websockets) - Primary AI conversation provider
- paho-mqtt - Core integration with Home Assistant via MQTT
- gpiozero - Hardware motor and button control

**Infrastructure:**
- websockets - Real-time bidirectional communication with AI providers
- aiohttp - Async HTTP for weather, news, and Home Assistant APIs
- scipy & numpy - Audio signal processing and manipulation
- flask, flask-sock - Web interface and WebSocket endpoint
- pvporcupine - Wake word detection

## Configuration

**Environment:**
- Location: `.env` file (created from `.env.example` if missing in `main.py`)
- Loaded via: `python-dotenv` in `core/config.py`
- Key configs:
  - `OPENAI_API_KEY` - OpenAI API authentication
  - `OPENAI_MODEL` - Model selection (e.g., "gpt-realtime-mini", "gpt-realtime-1.5")
  - `XAI_API_KEY` - X.AI provider authentication
  - `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` - MQTT broker connection
  - `HA_HOST`, `HA_TOKEN`, `HA_LANG` - Home Assistant configuration
  - `WEATHER_LATITUDE`, `WEATHER_LONGITUDE`, `WEATHER_LOCATION_NAME` - Location for weather
  - `SPEAKER_PREFERENCE`, `MIC_PREFERENCE` - Audio device selection
  - `FLASK_PORT` - Web server port (default 80)
  - `LOG_LEVEL` - Logging verbosity
  - `TEXT_ONLY_MODE` - Disable audio I/O for testing
  - `DEBUG_MODE` - Debug logging
  - `BILLY_MODEL`, `BILLY_PINS` - Hardware variant configuration
  - `WAKE_WORD_ENABLED`, `WAKE_WORD_ENDPOINT`, `WAKE_WORD_PORCUPINE_ACCESS_KEY` - Wake word config

**Build:**
- `pyproject.toml` - Python project metadata and ruff linter/formatter configuration
- `webconfig/package.json` - Node.js dependencies for frontend CSS building
- `.pre-commit-config.yaml` - Pre-commit hooks for ruff (lint/format)

**Code Quality:**
- Ruff - Linting and formatting (Python) via `.pre-commit-config.yaml`
  - Line length: 88 characters
  - Enabled rules: isort import sorting, flake8 checks, pyupgrade, simplify, return checks, docstring checks
  - Ignored rules: specific docstring and return rules

## Platform Requirements

**Development:**
- Python 3.x with pip
- Node.js with npm (for CSS building only)
- Raspberry Pi or compatible Linux system (for GPIO)
- Audio input/output devices
- MQTT broker (optional, for smart home integration)
- Home Assistant instance (optional)

**Production:**
- Raspberry Pi or similar ARM/Linux single-board computer
- Microphone and speaker devices
- GPIO pins for motors/buttons (specific pins in `core/config.py`)
- Network connectivity for API calls
- Optional: MQTT broker (home automation)
- Optional: Home Assistant instance

**Runtime Dependencies:**
- FLASK_PORT environment variable to specify web server port
- `.env` file with API keys and configuration
- `persona.ini` file for personality configuration
- `news_sources.json` file for news feed configuration (auto-generated with defaults)

---

*Stack analysis: 2026-03-24*
