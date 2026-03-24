# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**AI/LLM Providers:**
- OpenAI - Primary real-time conversation and audio generation
  - SDK/Client: Built-in websockets.asyncio.client
  - Implementation: `core/providers/openai_provider.py`
  - Endpoint: `wss://api.openai.com/v1/realtime`
  - Models: "gpt-realtime-mini", "gpt-realtime-1.5", "gpt-realtime"
  - Auth: `OPENAI_API_KEY` environment variable
  - Features: Real-time audio streaming, function calling, tool integration

- X.AI (xAI) - Alternative AI provider with realtime support
  - SDK/Client: Built-in websockets.asyncio.client
  - Implementation: `core/providers/xai_provider.py`
  - Endpoint: `wss://api.x.ai/v1/realtime`
  - Auth: `XAI_API_KEY` environment variable
  - Features: Voice options (Ara, Rex, Sal, Eve, Leo), real-time audio streaming

**Search & Information:**
- DuckDuckGo Instant Answer API - Web search without authentication
  - Endpoint: `https://api.duckduckgo.com/`
  - Implementation: `core/search.py`
  - Usage: Live web search results for user queries
  - No API key required

- Google News RSS - News feeds
  - URL pattern: `https://news.google.com/rss/search?q={{query}}&hl=en-US&gl=US&ceid=US:en`
  - Implementation: `core/news_manager.py`, `core/news_digest.py`
  - Usage: Headline digests with topic filtering
  - Configuration: `news_sources.json` (auto-generated)

- Open-Meteo - Weather API
  - Endpoint: `https://api.open-meteo.com/v1/forecast`
  - Implementation: `core/weather.py`
  - Auth: None (public API)
  - Parameters: Latitude, longitude (from environment)
  - Features: Current weather, hourly forecast, wind data

## Data Storage

**Databases:**
- None detected - Project uses file-based storage only

**File Storage:**
- Local filesystem only
  - User profiles and personas: `core/profile_manager.py` (JSON/INI files)
  - News sources: `news_sources.json`
  - Personality config: `persona.ini`
  - Audio response history: `sounds/response-history/`
  - Wake-up sounds: `sounds/wake-up/custom/` and `sounds/wake-up/default/`
  - Wake word models: `wake-word-models/`
  - Persona presets: `persona_presets/` directory

**Caching:**
- None detected - All data is stored persistently to disk

## Authentication & Identity

**Auth Provider:**
- Custom implementation using Home Assistant (optional)
  - Implementation: `core/ha.py`
  - User identification: `core/profile_manager.py`
  - Features: User switching, profile persistence, custom personas

**User System:**
- `identify_user` tool - Called when user introduces themselves
- `store_memory` tool - Persistent user facts and preferences
- `manage_profile/switch_persona` tool - Persona switching
- Default user: Configurable via `DEFAULT_USER` environment variable

**Home Assistant Integration:**
- Conversation API endpoint: `{HA_HOST}/api/conversation/process`
- Auth: Bearer token in `HA_TOKEN` environment variable
- Language: Configurable via `HA_LANG` environment variable
- Features: Conversation processing, smart home query handling

## Monitoring & Observability

**Error Tracking:**
- None detected - Project uses console logging only

**Logs:**
- Console-based logging via custom logger in `core/logger.py`
- Log levels: Configurable via `LOG_LEVEL` environment variable (DEBUG, INFO, WARNING, ERROR)
- Verbosity: Separate verbose logging channel
- Debug mode: `DEBUG_MODE` environment variable for detailed output
- Delta logging: `DEBUG_MODE_INCLUDE_DELTA` for detailed WebSocket message logging

## CI/CD & Deployment

**Hosting:**
- Direct Raspberry Pi deployment (no cloud platform detected)
- Flask web server on configurable port (default 80)
- No container support detected (no Dockerfile)

**CI Pipeline:**
- Pre-commit hooks via `.pre-commit-config.yaml`
  - Ruff linting and formatting on commit
  - Tools: ruff v0.12.3

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - OpenAI API authentication (CRITICAL for main operation)
- `OPENAI_MODEL` - Model selection (default: "gpt-realtime-mini")
- `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` - For Home Assistant MQTT integration
- `HA_HOST`, `HA_TOKEN` - For Home Assistant conversation API
- `WEATHER_LATITUDE`, `WEATHER_LONGITUDE` - For weather functionality
- `SPEAKER_PREFERENCE` - Audio output device name (optional)
- `MIC_PREFERENCE` - Audio input device name (optional)

**Secrets location:**
- `.env` file in project root
- Created from `.env.example` if missing
- File is git-ignored (not committed)
- Note: Never read `.env` directly; use `python-dotenv` to load

## Webhooks & Callbacks

**Incoming:**
- MQTT topics subscribed in `core/mqtt.py`:
  - `billy/command` - Direct commands to Billy
  - `billy/say` - Text-to-speech requests
  - `billy/song` - Song play requests
  - `billy/wakeup/play` - Wake-up sound requests
  - Implementation: `on_message()` handler in MQTT connection

- WebSocket endpoints in Flask:
  - Location: `webconfig/app/websocket.py`
  - Purpose: Real-time communication between web UI and main process
  - Protocol: Flask-Sock WebSocket

**Outgoing:**
- MQTT publishing in `core/mqtt.py`:
  - `billy/state` - Current state (idle, busy, etc.)
  - Custom topics via `mqtt_publish()` function
  - Retained messages for state persistence

- Home Assistant API:
  - POST to `{HA_HOST}/api/conversation/process`
  - Sends: User text, language preference
  - Returns: Conversation response text

- OpenAI WebSocket (realtime):
  - Bidirectional audio/text streaming
  - Tool/function calls for smart home commands, weather, news, etc.
  - Server-side VAD (voice activity detection) responses

- X.AI WebSocket (realtime):
  - Similar to OpenAI realtime protocol
  - Alternative voice output options

## News Feed Sources

**Configured Sources (auto-managed):**
- Google News Global (English) - Generic news
- Billy Project Releases - GitHub releases feed
- User-configurable sources via `news_sources.json`
- Format: RSS/Atom feeds with topic filtering

**Tool Implementation:**
- `get_news_digest` tool called with:
  - `subject` - Topic/category (technology, sports, weather, etc.)
  - `query` - Specific search query (optional)
  - `team`/`location` - Context-specific parameters (optional)
- Source selection based on topic keywords

## Provider Registry

**Architecture:**
- `RealtimeAIProviderRegistry` in `core/realtime_ai_provider.py`
- Multiple providers registered at startup:
  - OpenAI provider (if `OPENAI_API_KEY` set)
  - X.AI provider (if `XAI_API_KEY` set)
- Provider selection via `REALTIME_AI_PROVIDER` environment variable
- Fallback to OpenAI if not specified

---

*Integration audit: 2026-03-24*
