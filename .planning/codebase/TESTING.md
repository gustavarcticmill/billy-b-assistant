# Testing Patterns

**Analysis Date:** 2026-03-24

## Test Framework

**Runner:**
- Framework: Not formally configured
- Test files: `test/` directory exists but only contains utility scripts
- Primary test file: `test/replay.py` - audio playback testing utility, not unit tests

**Run Commands:**
```bash
# No automated test suite configured
# Manual testing via replay.py for audio playback
python test/replay.py              # Replay audio responses
```

## Test File Organization

**Location:**
- Test utilities stored in `test/` directory at root level
- No co-located test files (no `*_test.py` or `test_*.py` alongside source)
- Test directory contains functional/integration scripts rather than unit tests

**Naming:**
- Utility scripts: lowercase with underscores (e.g., `replay.py`)
- Not following standard pytest/unittest naming conventions

**Structure:**
```
test/
├── replay.py          # Audio playback replay utility
└── (no unit test files present)
```

## Test Structure

**Utility Script Pattern:**
The only test file `test/replay.py` demonstrates functional testing approach:

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize audio subsystem
detect_devices()
ensure_playback_worker_started(CHUNK_MS)

# Test audio playback
wake_up_clip = play_random_wake_up_clip()
if wake_up_clip:
    print(f"🎤 Playing wake-up clip: {wake_up_clip}")
    playback_queue.join()

# Play response file
file_path = os.path.join(RESPONSE_HISTORY_DIR, "response-1.wav")
if not os.path.exists(file_path):
    print("❌ No response-1.wav found.")
    exit(1)
```

**Patterns:**
- Manual path manipulation to import core modules
- Direct function calls for setup (initialization)
- Conditional checks for file existence
- Print-based assertion style
- Manual cleanup required

## Mocking

**Framework:** No formal mocking framework installed

**Patterns:**
- Mock implementations built into modules themselves
- Conditional import approach: if hardware library unavailable, use mock class
- Example: `MockButton` in `core/button.py` replaces `gpiozero.Button` when needed

**Mock Implementation Pattern:**
```python
try:
    from gpiozero import Button
    gpiozero_available = True
except ImportError:
    gpiozero_available = False

if config.MOCKFISH or not gpiozero_available:
    class MockButton:
        def __init__(self, pin, pull_up=True):
            self.pin = pin
            self.when_pressed = None
            self.is_pressed = False

        def close(self):
            pass

    Button = MockButton
```

**Mock Classes Present:**
- `MockButton` - Simulates GPIO button with stdin input fallback
- `MockLgpio` - Mocks motor control library (GPIO operations)
- These activate automatically when hardware unavailable or `MOCKFISH` mode enabled

**What to Mock:**
- Hardware interfaces (GPIO, audio devices) - always use mocks
- External hardware libraries - provide fallback implementations
- MQTT connectivity - can operate in degraded mode

**What NOT to Mock:**
- File I/O operations
- Logger calls (use directly)
- Core business logic (load/save profiles, persona management)

## Fixtures and Factories

**Test Data:**
- No formal fixture system in place
- Test data embedded in utility scripts
- `test/replay.py` expects `sounds/response-history/response-1.wav` to exist

**Sample Initialization Pattern:**
```python
# Setup code in test/replay.py
detect_devices()
ensure_playback_worker_started(CHUNK_MS)
core.movements.stop_all_motors()
```

**Location:**
- Test utilities live in `test/` directory
- No factory classes for test object creation
- Configuration pulled from environment variables and `.env` files

## Coverage

**Requirements:** No coverage targets enforced

**View Coverage:**
```bash
# No coverage tool configured
# Manual review of tested functionality only
```

## Test Types

**Unit Tests:**
- Not formally implemented
- Core modules designed for functional testing (e.g., `logger.py`, `config.py`)
- Logger has methods but no test cases
- Profile manager handles corruption recovery but untested

**Integration Tests:**
- `test/replay.py` serves as integration test for audio pipeline
- Tests: device detection → audio setup → wake-up clip playback → response file playback → motor cleanup
- Verifies full stack from hardware initialization to playback

**E2E Tests:**
- Not present
- Manual testing via replay.py covers core audio flow
- System-wide testing appears to be manual/development process

## Common Patterns

**Initialization Testing:**
```python
# Device detection
detect_devices()

# Feature availability checks
if not os.path.exists(file_path):
    print("❌ No response-1.wav found.")
    exit(1)
```

**Error Handling in Tests:**
- Print-based feedback for success/failure
- Early exit on critical failures
- Emoji-prefixed status messages

## Mock Mode

**Development Mode - Mockfish:**
- Configuration variable `MOCKFISH` enables mock mode globally
- When enabled:
  - GPIO operations use `MockLgpio`
  - Button input uses stdin instead of hardware
  - Audio device detection disabled
  - Full system runnable without hardware

**Activation:**
```python
from core.config import MOCKFISH

if MOCKFISH or not library_available:
    # Use mock implementation
```

## Testing Guidelines

**For New Code:**
1. Ensure mock implementations exist for any hardware dependencies
2. Use conditional imports: try real library, fallback to mock
3. Test initialization sequence with `test/replay.py` pattern if audio-related
4. Print status messages with emoji prefixes for manual verification
5. Add conditional checks for file existence and required resources

**Running Tests:**
- No automated test runner configured
- Manual execution: `python test/replay.py`
- Verify audio playback and motor movement manually
- Check logs for error messages

## Testing Limitations

**Not Covered:**
- API routes in Flask (`webconfig/app/routes/`) - no route tests
- News digest processing - complex logic untested
- MQTT client behavior - no mock MQTT broker tests
- Session management - no session lifecycle tests
- Profile corruption recovery - recovery logic exists but untested

**Fragile Areas Without Tests:**
- `core/profile_manager.py` - memory recovery logic (lines 43-79) has complex error handling but no tests
- `core/news_digest.py` - complex feed processing untested
- `webconfig/app/routes/` - Flask route handlers untested

---

*Testing analysis: 2026-03-24*
