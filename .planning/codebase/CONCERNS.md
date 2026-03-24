# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**Legacy DEBUG_MODE Environment Variable:**
- Issue: System migrated to `LOG_LEVEL` system but retained backwards-compatible `DEBUG_MODE` variable that defaults to "true"
- Files: `core/config.py` (lines 166-170), `core/session_manager.py`, `core/hotword.py`, `core/button.py`, `core/session/mic_manager_wrapper.py`
- Impact: Old debug mode is globally enabled by default, creating excessive logging output and mixed logging approaches that should be fully migrated
- Fix approach: Complete migration to LOG_LEVEL system; remove DEBUG_MODE references and set default to INFO level instead of verbose output

**Excessive Print Statements Mixed with Logger:**
- Issue: 54 direct `print()` calls throughout core modules coexist with centralized logger system
- Files: `core/audio.py` (line 148), `core/logger.py` (lines 29, 55), `webconfig/app/routes/profiles.py`, `webconfig/app/routes/persona.py` (multiple DEBUG print statements at lines 137-179)
- Impact: Inconsistent logging behavior, difficulty controlling output verbosity, mixed stdio and logger patterns
- Fix approach: Consolidate all direct print calls to use logger module; remove inline print statements

**Bare Global State Management:**
- Issue: Multiple modules use global variables without locks for state that's accessed from threads
- Files: `core/audio.py` (lines 35-56, multiple global state variables), `core/button.py` (lines 65-71, session globals), `core/mqtt.py` (lines 15-16, mqtt_client and mqtt_connected)
- Impact: Race conditions on state updates; inconsistent module initialization; difficult testing
- Fix approach: Encapsulate global state in thread-safe classes; use locks for all cross-thread global access

**Hardcoded Pin Configuration Scattered Across Files:**
- Issue: GPIO pin mappings are hardcoded with legacy/new profiles in multiple locations
- Files: `core/movements.py` (lines 68-90 for pin mapping logic), `core/config.py` (line 224 for BUTTON_PIN)
- Impact: Difficult to extend hardware support; profile switching error-prone; inconsistent pin naming
- Fix approach: Create a dedicated hardware profile abstraction class; load all pins from config in single location

## Known Bugs

**Session Shutdown Race Conditions (Recently Partially Fixed):**
- Symptoms: Stuck session threads during shutdown, duplicate stop handling, noisy shutdown behavior
- Files: `core/button.py` (lines 108-170, session stop logic), `core/session_manager.py`, `core/session/state_machine.py`
- Trigger: Pressing button during active session; stopping session via MQTT while Billy is speaking
- Workaround: Force button press again after 3-5 seconds to force-release locks
- Status: Partially addressed in v2.1.0 (changelog line 160) but remaining edge cases noted

**Persona Voice Persistence Issue (Fixed in v2.1.0):**
- Symptoms: Voice doesn't update when switching personas despite instructions changing
- Files: `core/session_manager.py`, `core/session/persona_handler.py`, `core/realtime_ai_provider.py`
- Trigger: Switching user profiles or personas during/after session
- Current state: Fixed but mechanism remains fragile (requires careful voice parameter passing)

**gpiozero Button Hold Thread Race (Rare):**
- Symptoms: Button `_hold_thread` becomes None during operation causing button handlers to fail
- Files: `core/button.py` (lines 88-98, workaround present)
- Trigger: Rare threading race condition in gpiozero library
- Workaround: Implemented repair mechanism in code (line 95-96)

## Security Considerations

**API Keys in Environment Variables (Standard Practice):**
- Risk: OpenAI API key, XAI API key, Porcupine access key exposed if .env is committed or leaked
- Files: `core/config.py` (lines 138-139 for OPENAI_API_KEY, line 159 for XAI_API_KEY, line 220 for WAKE_WORD_PORCUPINE_ACCESS_KEY), `main.py` (lines 11-28, .env file handling)
- Current mitigation: .env files listed in .gitignore; .env.example provided as template
- Recommendations: Use environment-specific .env loading only (no fallback defaults for production keys); add .env encryption for sensitive deployments

**MQTT Authentication in Plaintext:**
- Risk: MQTT username/password transmitted over network without TLS enforcement
- Files: `core/mqtt.py` (lines 43-44, basic auth), `core/config.py` (lines 227-230)
- Current mitigation: None enforced
- Recommendations: Add MQTT_TLS_ENABLED flag; enforce certificate validation; add warning if TLS not enabled with external MQTT host

**No Input Validation on User/Profile Names:**
- Risk: Path traversal possible through profile name manipulation
- Files: `webconfig/app/routes/profiles.py` (lines 77, 103, uses profile_name directly in path)
- Current mitigation: Filename validation through .ini extension check only
- Recommendations: Validate profile names against whitelist/regex; use basename() to prevent path traversal; sanitize all user inputs

**Persona/Profile File Write Without Validation:**
- Risk: Malformed ini files or injection via profile data could corrupt system state
- Files: `webconfig/app/routes/profiles.py` (profile write/delete), `webconfig/app/routes/persona.py` (persona write)
- Current mitigation: try/except blocks but silent failures on read errors (line 57: `pass`)
- Recommendations: Add schema validation before write; validate ini structure before config.write(); log all write failures

## Performance Bottlenecks

**Large Core Modules (900+ Lines):**
- Problem: `core/session_manager.py` (903 lines), `core/news_digest.py` (888 lines) are difficult to test and maintain
- Files: `core/session_manager.py`, `core/news_digest.py`
- Cause: Complex state management and multi-tool coordination in single files
- Improvement path: Split session_manager into separate concern handlers (audio, state, tool dispatch); extract news source logic to separate module

**Audio Playback Worker Global Queue (Blocking/Inefficient):**
- Problem: `playback_worker()` in audio.py is a tight loop using Queue.get() that blocks on head movements
- Files: `core/audio.py` (lines 122-150, playback_worker function)
- Cause: Sequential processing of audio chunks with synchronous head movement coordination
- Improvement path: Use asyncio instead of threading for playback; implement event-driven head movement coordination

**News Digest Tool Multiple API Calls:**
- Problem: News digest makes separate calls to multiple providers without caching or rate limiting
- Files: `core/news_digest.py` (888 lines, multiple fetch functions)
- Cause: No request deduplication; no cache for recent queries
- Improvement path: Add in-memory cache with TTL; deduplicate requests within 5-minute window

**Realtime AI Provider Polling (Blocking):**
- Problem: Realtime AI connections maintained via websockets but polling-style event handling
- Files: `core/realtime_ai_provider.py`, `core/session_manager.py` (large event loop)
- Cause: Callback-driven architecture requires event loop overhead
- Improvement path: Implement proper async/await patterns throughout session lifecycle

## Fragile Areas

**Button/Session Lifecycle State Machine:**
- Files: `core/button.py` (108-170), `core/session/state_machine.py`
- Why fragile: Multiple globals track session state (is_active, session_thread, interrupt_event); asyncio.run_coroutine_threadsafe calls cross thread boundaries; timeout handling at multiple levels
- Safe modification: Always hold `_session_start_lock` before changing is_active; verify session_instance.loop exists before submitting coroutines; add timeouts to all asyncio.run_coroutine_threadsafe calls
- Test coverage: Button press events tested implicitly but edge cases (concurrent presses, shutdown during startup) not unit-tested

**Hotword Detection Initialization:**
- Files: `core/hotword.py` (lines 150-250, initialization logic)
- Why fragile: Optional dependency (pvporcupine) with fallback to amplitude detection; threading locks and stream initialization interleaved
- Safe modification: Test both porcupine and fallback modes; verify locks are released even on exception; test without audio devices (mock mode)
- Test coverage: No unit tests for hotword; initialization errors would be caught only at runtime

**MQTT Message Handling Daemon:**
- Files: `core/mqtt.py` (lines 37-59, connect_with_retry), global mqtt_client state
- Why fragile: Infinite retry loop in daemon thread with no backoff; global mqtt_client can be None when accessed from callbacks; async session commands sent from MQTT callbacks without error handling
- Safe modification: Add exponential backoff to retry loop; null-check mqtt_client in all callbacks; wrap MQTT-triggered session commands in try/except with logging
- Test coverage: No tests for MQTT connection/reconnection flows

**Web UI Profile/Persona Switching:**
- Files: `webconfig/app/routes/profiles.py`, `webconfig/app/routes/persona.py`
- Why fragile: Silent failures on config read (line 57: `except Exception: pass`); no atomic file updates; display_name parsing has fallback but no validation
- Safe modification: Use atomic file operations (write-to-temp then rename); validate ini structure before returning; log all exceptions instead of silent pass
- Test coverage: Routes tested manually only; no test coverage for concurrent profile switches or file corruption scenarios

## Scaling Limits

**Audio Device Enumeration (One-time at Startup):**
- Current capacity: Supports one input and one output device selected at startup
- Limit: Cannot switch audio devices without restart; multiple input/output device selection not supported
- Scaling path: Store device preference in config; add runtime device switching with audio stream restart; support device fallback lists

**WebSocket Log Streaming:**
- Current capacity: Single WebSocket connection per client; all logs broadcast to connected clients
- Limit: 100+ concurrent connections could saturate log output; no message batching
- Scaling path: Implement client-side buffering; add message batching (e.g., every 50ms or 10 messages); support filtered subscriptions by log level

**MQTT Topic Subscriptions:**
- Current capacity: Fixed subscriptions (billy/command, billy/say, billy/song, billy/wakeup/play)
- Limit: No dynamic topic subscription; no wildcard support
- Scaling path: Add configuration-driven topic subscriptions; support dynamic subscription via discovery messages

**Memory Usage in Long Sessions:**
- Current capacity: No explicit memory limits on logged transcripts or interaction history
- Limit: Long-running sessions (>1 hour) could accumulate large transcripts in memory
- Scaling path: Implement circular buffer for recent history; persist old interactions to disk; add memory usage monitoring

## Dependencies at Risk

**numpy < 2 (Pinned Below Major Version):**
- Risk: Pinned to numpy < 2 to maintain compatibility with scipy/sounddevice; missing critical numpy 2.0 improvements and security fixes
- Impact: Cannot use newer numpy features; potential security vulnerabilities in pinned version; scipy/sounddevice eventually require numpy 2
- Migration plan: Test with numpy 1.26.x for stability; monitor scipy/sounddevice for numpy 2 support; plan migration when dependencies update

**pvporcupine Optional Dependency:**
- Risk: Optional dependency with API key requirement; fallback amplitude detection is simpler but less reliable
- Impact: Wake word detection degrades to amplitude-only if access key missing; amplitude-based detection has high false positive rate
- Migration plan: Add fallback to alternative wake word engine (e.g., openai-whisper VAD); document fallback behavior; add warning if porcupine unavailable

**websockets Library (Async/Real-time):**
- Risk: WebSocket library underpins all realtime AI connections; network issues cause cascading session failures
- Impact: Connection drops disconnect entire session; no automatic reconnection logic
- Migration plan: Implement exponential backoff reconnection; buffer messages during disconnection; add heartbeat/ping mechanism

**gpiozero Library (GPIO Abstraction):**
- Risk: Rare threading race with _hold_thread (acknowledged in code with workaround)
- Impact: Button handler failures during long-running sessions
- Migration plan: Upstream bug fix to gpiozero or migrate to lgpio directly; remove MockButton complexity

## Missing Critical Features

**No Rate Limiting on API Calls:**
- Problem: No protection against token exhaustion if tools (news, weather, web search) are called repeatedly
- Blocks: Cannot safely expose to public/multi-user scenarios; risk of quota overages
- Recommendation: Add token counter; implement daily/hourly limits per tool; add user feedback when limits approached

**No Transaction/Atomicity for Profile Switches:**
- Problem: Profile switch involves loading ini file, updating .env, and reloading persona_manager but no atomic operation
- Blocks: Concurrent profile switch requests could leave system in partial state; rollback on error not implemented
- Recommendation: Implement profile switch transaction; validate entire state before commit; add rollback mechanism

**No Session History Persistence:**
- Problem: Session transcripts lost when session ends; no audit trail
- Blocks: Cannot replay/debug sessions; no history for user review
- Recommendation: Add session recording to database/file; implement encrypted transcript storage; provide UI to view history

**No Update Mechanism for Deployed Systems:**
- Problem: No built-in update/upgrade mechanism; requires manual git pull and service restart
- Blocks: Deployed devices cannot be updated remotely; bug fixes require manual intervention
- Recommendation: Add version checking endpoint; implement staged rollout mechanism; add rollback support

## Test Coverage Gaps

**GPIO/Motor Control:**
- What's not tested: Motor movement timing, PWM duty cycle correctness, pin state transitions
- Files: `core/movements.py`, motor control sections
- Risk: Servo/motor failures undetected until hardware test; incorrect timing causes jerky movement
- Priority: HIGH - Motors are hardware-facing; failures visible to users

**MQTT Connection/Reconnection:**
- What's not tested: Connection failures, message delivery during network outages, reconnect timing
- Files: `core/mqtt.py`
- Risk: Silent MQTT failures; remote commands ignored without feedback; unclear error states
- Priority: HIGH - Users cannot control device if MQTT fails

**Session State Transitions:**
- What's not tested: Concurrent button presses, shutdown during various session phases, error recovery paths
- Files: `core/button.py`, `core/session_manager.py`, `core/session/state_machine.py`
- Risk: Stuck sessions, orphaned threads, inconsistent state after errors
- Priority: HIGH - These are critical paths; failures block normal operation

**Profile/Persona Switching:**
- What's not tested: Concurrent profile switches, switching during active session, corrupted profile files
- Files: `webconfig/app/routes/profiles.py`, `webconfig/app/routes/persona.py`
- Risk: Partial state updates, inconsistent persona/profile combination, data loss on error
- Priority: MEDIUM - UI feature but affects user experience

**Hotword Detection:**
- What's not tested: Initialization with/without porcupine, stream state transitions, audio device failures
- Files: `core/hotword.py`
- Risk: Wake word detection silently fails without feedback
- Priority: MEDIUM - Fallback amplitude detection available but untested

**News/Weather API Integration:**
- What's not tested: API failures, rate limiting, malformed responses, network timeouts
- Files: `core/news_digest.py`, `core/weather.py`
- Risk: Partial responses returned; no user feedback on errors; silent tool failures
- Priority: MEDIUM - Tools are optional but impact assistant capability

---

*Concerns audit: 2026-03-24*
