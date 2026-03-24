# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- Python modules: `lowercase_with_underscores.py` (e.g., `logger.py`, `persona_manager.py`)
- JavaScript files: `lowercase-with-hyphens.js` for utility modules (e.g., `config-service.js`, `ui-helpers.js`)
- Route modules: Named after their domain (e.g., `audio.py`, `system.py`, `profiles.py` in `webconfig/app/routes/`)

**Functions:**
- Python: `snake_case` (e.g., `ensure_env_file()`, `_normalize_source_payload()`, `detect_devices()`)
- Private/internal functions: Prefixed with `_` (e.g., `_float_env()`, `_get_current_level()`, `_pick_mic_rate()`)
- JavaScript: `camelCase` (e.g., `fetchConfig()`, `showNotification()`, `toggleInputVisibility()`)

**Variables:**
- Python: `snake_case` for local/module variables (e.g., `playback_queue`, `MIC_DEVICE_INDEX`, `configCache`)
- Python: `UPPER_SNAKE_CASE` for constants and global configuration variables (e.g., `CHUNK_MS`, `MIC_PREFERENCE`, `RESPONSE_HISTORY_DIR`)
- JavaScript: `camelCase` (e.g., `configCache`, `CACHE_DURATION`)

**Classes:**
- Python: `PascalCase` (e.g., `BillyLogger`, `PersonaManager`, `UserProfile`, `BillySession`)
- Private/Mock classes: Prefixed with underscore or "Mock" (e.g., `MockButton`, `MockLgpio`)

**Enums:**
- Python: `PascalCase` for class, `UPPER_CASE` for members (e.g., `LogLevel.ERROR`, `LogLevel.INFO`)

## Code Style

**Formatting:**
- Tool: `ruff` (via ruff-format)
- Line length: 88 characters
- Indent width: 4 spaces
- Line ending: native (auto-detect)
- Quote style: preserve existing quotes

**Linting:**
- Tool: `ruff` with custom configuration
- Config file: `pyproject.toml` in root

**Ruff Configuration Details:**
- Format preview mode enabled
- Import sorting follows `isort` profile with 2 blank lines after imports
- Docstring style: triple double quotes
- Maximum line length enforced at 88 characters

## Import Organization

**Order:**
1. Standard library imports (e.g., `import os`, `import asyncio`, `import json`)
2. Third-party imports (e.g., `import numpy as np`, `import paho.mqtt.client as mqtt`)
3. Relative local imports from current package (e.g., `from . import config`, `from .logger import logger`)
4. Absolute imports from other packages (e.g., `from core.config import CHUNK_MS`)

**Path Aliases:**
- Relative imports use dot notation: `from .module import name` or `from . import module`
- Absolute imports from `core/`: `from core.logger import logger`
- Absolute imports in Flask routes: `from ..core_imports import core_config`

**Import Pattern Example:**
```python
import asyncio
import json
import os

import numpy as np
import paho.mqtt.client as mqtt

from .config import CHUNK_MS
from .logger import logger
from .movements import stop_all_motors
```

**Flask Blueprint Pattern:**
```python
from flask import Blueprint, jsonify, render_template, request
bp = Blueprint("system", __name__)
```

## Error Handling

**Patterns:**
- Broad exception catching with `except Exception as e:` is common for operational robustness
- Specific exception types used when recovery differs (e.g., `except json.JSONDecodeError`)
- Error messages logged via `logger.error()` with emoji prefix
- Fallback values returned on error rather than raising (e.g., `_float_env()` returns default on ValueError)
- Recovery attempts for corrupted data (see `profile_manager.py` memory recovery logic)
- Try-except blocks used extensively in audio initialization and device detection

**Error Handling Example:**
```python
try:
    return float(value)
except (TypeError, ValueError):
    print(f"⚠️ Invalid float for {key}={value!r}, falling back to {default}")
    return float(default)
```

**Graceful Degradation:**
- Missing optional dependencies trigger mock implementations (e.g., `MockButton`, `MockLgpio`)
- GPIO library optionally imported with fallback to keyboard input
- Device detection continues with default values if unavailable

## Logging

**Framework:** Custom `BillyLogger` class in `core/logger.py`

**Patterns:**
- All logging goes through global `logger` singleton instance
- Log methods accept optional `emoji` parameter for visual distinction
- Log levels: `ERROR`, `WARNING`, `INFO`, `VERBOSE` (enum-based)
- Configuration via `LOG_LEVEL` environment variable
- Special methods for common patterns: `logger.success()`, `logger.debug()`

**Logging Usage Examples:**
```python
from .logger import logger

logger.info("Message here", "ℹ️")
logger.success("Operation worked", "✅")
logger.error("Something broke", "❌")
logger.warning("Caution", "⚠️")
logger.verbose("Debug info", "🔍")
```

**Convenience Functions:**
- Module-level convenience functions provided (e.g., `log_info()`, `log_error()`) for backward compatibility
- Direct access via `logger` object preferred in new code

## Comments

**When to Comment:**
- Complex logic that isn't immediately clear (e.g., sample rate detection logic in `audio.py`)
- Configuration sections marked with `# === SECTION NAME ===` pattern
- Emoji comments for visual scanning (e.g., `# 🐟 Play wake-up clip`)
- TODO/FIXME comments tracked in code
- Comments above function definitions explaining non-obvious behavior

**JSDoc/TSDoc:**
- Python docstrings use triple double quotes
- Module-level docstrings present (e.g., `core/persona_manager.py` has module docstring)
- Class docstrings provided (e.g., `"""Manages different Billy personas and personality configurations."""`)
- Function docstrings use imperative mood where applicable
- Single-line docstrings for simple functions

**Docstring Example:**
```python
def get_available_personas(self) -> list[dict]:
    """Get list of available persona files with their metadata."""
    personas = []
```

## Function Design

**Size:**
- Functions typically 10-50 lines
- Single-letter variables avoided (use `card_index` not `c`)
- Helper functions prefixed with underscore for privacy

**Parameters:**
- Type hints used consistently (e.g., `def _float_env(key: str, default: str) -> float:`)
- Optional parameters use `Optional[]` type hint
- Dictionary parameters documented in docstring or comments

**Return Values:**
- Explicit return types via type hints
- `Optional[Type]` for nullable returns
- Union types for multiple possible types

**Function Design Example:**
```python
def load_persona(self, persona_name: str) -> Optional[dict[str, Any]]:
    """Load a persona configuration from file."""
    if persona_name in self._persona_cache:
        return self._persona_cache[persona_name]
    # ... implementation
    return None
```

## Module Design

**Exports:**
- Classes and functions intended for external use not prefixed with underscore
- Private module-level functions prefixed with `_`
- Global configuration accessed via `core.config` module

**Barrel Files:**
- `__init__.py` files kept minimal in `core/` (mostly empty)
- Routes registered via Blueprint pattern in `webconfig/app/routes/`
- Direct imports from modules preferred

**Module Example:**
```python
# core/logger.py - Global instance exported
logger = BillyLogger()

# Module-level convenience functions
def log_error(message: str, emoji: str = "❌"):
    logger.error(message, emoji)
```

## Type Hints

**Usage:**
- Type hints consistently applied to function signatures
- Generic types used: `list[dict]`, `dict[str, Any]`, `Optional[Type]`
- Union types: `BillySession | None` (using `|` syntax)
- Type hints for class attributes in `__init__`

**Enum Types:**
```python
class LogLevel(Enum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    VERBOSE = 3
```

## Threading and Async

**Pattern:**
- `threading.Thread()` used for daemon threads (e.g., `start_mqtt`, `motor_watchdog`)
- `asyncio` for async operations in Flask routes
- Global locks using `threading.Lock()` for critical sections
- Queue objects from `queue.Queue` for thread-safe communication

**Example:**
```python
threading.Thread(target=start_mqtt, daemon=True).start()
_session_start_lock = threading.Lock()
```

## JavaScript Conventions

**Pattern:**
- Immediately-invoked function expressions (IIFE) for module encapsulation
- Object return with public methods (e.g., `ConfigService`)
- DOM manipulation via vanilla JavaScript (no framework)
- Event listeners attached to document for delegation

**JavaScript Module Pattern:**
```javascript
const ConfigService = (() => {
    let configCache = null;
    const fetchConfig = async (forceRefresh = false) => { /* ... */ };
    return { fetchConfig, getCachedConfig, clearCache };
})();
```

---

*Convention analysis: 2026-03-24*
