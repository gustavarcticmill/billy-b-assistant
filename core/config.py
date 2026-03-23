import asyncio
import configparser
import os

from dotenv import load_dotenv

from .persona import (
    PersonaProfile,
    load_traits_from_ini,
)


def _float_env(key: str, default: str) -> float:
    value = os.getenv(key)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        print(
            f"⚠️ Invalid float for {key}={value!r}, falling back to {default}",
            flush=True,
        )
        return float(default)


def _int_env(
    key: str,
    default: str,
    *,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Load an integer env var with optional range validation."""
    value = os.getenv(key)
    if value is None:
        return int(default)
    try:
        result = int(value)
    except (TypeError, ValueError):
        print(
            f"Warning: Invalid integer for {key}={value!r}, "
            f"falling back to {default}",
            flush=True,
        )
        return int(default)
    if min_val is not None and result < min_val:
        print(
            f"Warning: {key}={result} below minimum {min_val}, "
            f"falling back to {default}",
            flush=True,
        )
        return int(default)
    if max_val is not None and result > max_val:
        print(
            f"Warning: {key}={result} above maximum {max_val}, "
            f"falling back to {default}",
            flush=True,
        )
        return int(default)
    return result


def _float_env_ranged(
    key: str,
    default: str,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
) -> float:
    """Load a float env var with optional range validation."""
    result = _float_env(key, default)
    if min_val is not None and result < min_val:
        print(
            f"Warning: {key}={result} below minimum {min_val}, "
            f"falling back to {default}",
            flush=True,
        )
        return float(default)
    if max_val is not None and result > max_val:
        print(
            f"Warning: {key}={result} above maximum {max_val}, "
            f"falling back to {default}",
            flush=True,
        )
        return float(default)
    return result


# === Paths ===
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
PERSONA_PATH = os.path.join(ROOT_DIR, "persona.ini")

# === Load .env ===
load_dotenv(dotenv_path=ENV_PATH)

# === Load traits.ini ===
traits = load_traits_from_ini(PERSONA_PATH)

# === Build Personality ===
PERSONALITY = PersonaProfile(**traits)

_config = configparser.ConfigParser()
_config.read(PERSONA_PATH)

# === Instructions for GPT ===
TOOL_INSTRUCTIONS = """
=== CRITICAL: EVERY RESPONSE MUST END WITH conversation_state ===
AFTER you speak, ALWAYS call conversation_state(expects_follow_up=true/false).
Set expects_follow_up=true if you asked a question, false otherwise.
NEVER skip this - the system breaks without it.
NEVER speak or print tool calls out loud. Do NOT include text like
"conversation_state(...)" in spoken output. Tool calls are internal only.

=== TOOLS ===

PERSONALITY: Use update_personality when users request changes (e.g., "be funnier" -> update_personality({"humor": 80}))

SMART HOME: Only call smart_home_command for DIRECT commands ("turn on lights"). If asked to "ask if" or "check if", just speak the question.
NEWS: When the user asks for news, headlines, or updates, you MUST call get_news_digest. Do NOT just say you will check — actually call the tool. Set category="headlines" and a concise subject keyword. Do NOT call conversation_state before the tool returns. Call the tool FIRST, wait for results, THEN speak.

USER SYSTEM:
- identify_user: Call when someone introduces themselves ("I am Tom")
- store_memory: Store lasting facts users voluntarily share (NOT answers to your questions)
- manage_profile/switch_persona: Change personas

SONGS: Use play_song for special songs

WEB SEARCH: When the user needs live information from the web, use the web_search tool with their exact question.

WEATHER: When the user asks about the weather, use the get_weather tool to retrieve the latest conditions.

=== STOP COMMAND ===
If the user says "Stop Billy" (or close variations like "stopp Billy", "sluta Billy"), IMMEDIATELY:
1. Say a very brief goodbye (max 3 words, e.g., "Hejdå!" or "Okej, hejdå!")
2. Call conversation_state(expects_follow_up=false)
Do NOT continue the conversation. Do NOT ask follow-up questions. End instantly.

=== RESPONSE FLOW ===
1. [Optional: call tool functions]
2. Generate speech (ALWAYS speak - never respond with only function calls)
3. Call conversation_state (MANDATORY - NEVER skip this)

EXAMPLES:
✓ User: "Hello" -> Speak "Hey!" -> [internal tool call: conversation_state(expects_follow_up=false)]
✓ User: "What's up?" -> Speak "Not much, you?" -> [internal tool call: conversation_state(expects_follow_up=true)]
✗ User: "Hello" -> Speak "Hey! conversation_state(expects_follow_up=false)" (WRONG: tool call spoken)
✗ User: "Hello" -> Speak "Hey!" -> NO conversation_state (SYSTEM BREAKS)
""".strip()

TOOL_INSTRUCTIONS_NO_CONVERSATION_STATE = """
=== TOOLS ===

PERSONALITY: Use update_personality when users request changes (e.g., "be funnier" -> update_personality({"humor": 80}))

SMART HOME: Only call smart_home_command for DIRECT commands ("turn on lights"). If asked to "ask if" or "check if", just speak the question.
NEWS: When the user asks for news, headlines, or updates, you MUST call get_news_digest. Do NOT just say you will check — actually call the tool. Set category="headlines" and a concise subject keyword. Do NOT call conversation_state before the tool returns. Call the tool FIRST, wait for results, THEN speak.

USER SYSTEM:
- identify_user: Call when someone introduces themselves ("I am Tom")
- store_memory: Store lasting facts users voluntarily share (NOT answers to your questions)
- manage_profile/switch_persona: Change personas

SONGS: Use play_song for special songs

WEB SEARCH: When the user needs live information from the web, use the web_search tool with their exact question.

WEATHER: When the user asks about the weather, use the get_weather tool to retrieve the latest conditions.

=== STOP COMMAND ===
If the user says "Stop Billy" (or close variations like "stopp Billy", "sluta Billy"), IMMEDIATELY:
1. Say a very brief goodbye (max 3 words, e.g., "Hejdå!" or "Okej, hejdå!")
2. End the conversation immediately.
Do NOT continue the conversation. Do NOT ask follow-up questions. End instantly.

=== RESPONSE FLOW ===
1. [Optional: call tool functions]
2. Generate speech (ALWAYS speak - never respond with only function calls)
3. End naturally. Do NOT speak or print internal tool-call text.
""".strip()

CUSTOM_INSTRUCTIONS = _config.get("META", "instructions")
if _config.has_section("BACKSTORY"):
    BACKSTORY = dict(_config.items("BACKSTORY"))
    BACKSTORY_FACTS = "\n".join([
        f"- {key}: {value}" for key, value in BACKSTORY.items()
    ])
else:
    BACKSTORY = {}
    BACKSTORY_FACTS = (
        "You are an enigma and nobody knows anything about you because the person "
        "talking to you hasn't configured your backstory. You might remind them to do "
        "that."
    )

_LANG_CODE = os.getenv("HA_LANG", "EN").strip().upper()
_LANG_DIRECTIVE = ""
if _LANG_CODE != "EN":
    _LANG_NAMES = {
        "SV": "Swedish", "NL": "Dutch", "IT": "Italian", "FR": "French",
        "DE": "German", "ES": "Spanish", "PT": "Portuguese", "HI": "Hindi",
        "JA": "Japanese", "ZH": "Chinese", "KO": "Korean", "RU": "Russian",
        "PL": "Polish", "CS": "Czech", "TR": "Turkish", "RO": "Romanian",
    }
    _lang_name = _LANG_NAMES.get(_LANG_CODE, _LANG_CODE)
    _LANG_DIRECTIVE = (
        f"\n---\n# Language\n"
        f"ALWAYS respond in {_lang_name}. The user's primary language is {_lang_name}. "
        f"All spoken output, confirmations, weather summaries, news briefings, "
        f"and error messages MUST be in {_lang_name}. "
        f"Tool results may arrive in English — translate them to {_lang_name} before speaking."
    )

INSTRUCTIONS = f"""
# Role & Objective
{CUSTOM_INSTRUCTIONS.strip()}
---
# Tools
{TOOL_INSTRUCTIONS.strip()}
---
# Personality & Tone
{PERSONALITY.generate_prompt()}
---
# Context (backstory)
Use your backstory to inspire jokes, metaphors, or occasional references in conversation, staying consistent with your personality.
{BACKSTORY_FACTS}
{_LANG_DIRECTIVE}
""".strip()

# === OpenAI Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-realtime-mini")
CONVERSATION_STATE_ENABLED_MODELS = {"gpt-realtime", "gpt-realtime-1.5"}


def is_conversation_state_enabled(model: str | None = None) -> bool:
    """Whether conversation_state tool/instructions should be enabled."""
    m = (model or os.getenv("OPENAI_MODEL", OPENAI_MODEL) or "").strip()
    return m in CONVERSATION_STATE_ENABLED_MODELS


def get_tool_instructions(model: str | None = None) -> str:
    """Return tool instructions appropriate for the selected model."""
    return (
        TOOL_INSTRUCTIONS
        if is_conversation_state_enabled(model)
        else TOOL_INSTRUCTIONS_NO_CONVERSATION_STATE
    )


# === XAI Config ===
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# === Provider Config ===
REALTIME_AI_PROVIDER = os.getenv("REALTIME_AI_PROVIDER", None)

# === Modes ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Legacy DEBUG_MODE for backward compatibility
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
DEBUG_MODE_INCLUDE_DELTA = (
    os.getenv("DEBUG_MODE_INCLUDE_DELTA", "false").lower() == "true"
)
TEXT_ONLY_MODE = os.getenv("TEXT_ONLY_MODE", "false").lower() == "true"
RUN_MODE = os.getenv("RUN_MODE", "normal").lower()

# === Billy Hardware ===
BILLY_MODEL = os.getenv("BILLY_MODEL", "modern").strip().lower()
BILLY_PINS = os.getenv("BILLY_PINS", "new").strip().lower()

# === Audio Config ===
SPEAKER_PREFERENCE = os.getenv("SPEAKER_PREFERENCE")
MIC_PREFERENCE = os.getenv("MIC_PREFERENCE")
MIC_TIMEOUT_SECONDS = _int_env("MIC_TIMEOUT_SECONDS", "5", min_val=1, max_val=300)
SILENCE_THRESHOLD = _float_env_ranged("SILENCE_THRESHOLD", "1000", min_val=0.0)
CHUNK_MS = _int_env("CHUNK_MS", "40", min_val=10, max_val=200)
FOLLOW_UP_RETRY_LIMIT = int(os.getenv("FOLLOW_UP_RETRY_LIMIT", "1"))
PLAYBACK_VOLUME = 1
MOUTH_ARTICULATION = int(os.getenv("MOUTH_ARTICULATION", "5"))
TURN_EAGERNESS = os.getenv("TURN_EAGERNESS", "high").strip().lower()
HEAD_RETRACT_DELAY_SECONDS = float(os.getenv("HEAD_RETRACT_DELAY_SECONDS", "1.5"))
if TURN_EAGERNESS not in {"low", "medium", "high"}:
    TURN_EAGERNESS = "medium"

# Server VAD parameters based on eagerness
# Lower silence_duration_ms = faster turn detection (more eager)
# Higher threshold = less sensitive to noise (more conservative)
SERVER_VAD_PARAMS = {
    "low": {
        "threshold": 0.9,
        "prefix_padding_ms": 300,
        "silence_duration_ms": 1500,
    },
    "medium": {
        "threshold": 0.9,
        "prefix_padding_ms": 300,
        "silence_duration_ms": 1000,
    },
    "high": {
        "threshold": 0.7,
        "prefix_padding_ms": 150,
        "silence_duration_ms": 250,
    },
}

# === Wake Word Config ===
WAKE_WORD_ENABLED = os.getenv("WAKE_WORD_ENABLED", "false").lower() == "true"
WAKE_WORD_SENSITIVITY = _float_env_ranged("WAKE_WORD_SENSITIVITY", "0.5", min_val=0.0, max_val=1.0)
WAKE_WORD_THRESHOLD = _float_env_ranged("WAKE_WORD_THRESHOLD", "2400", min_val=0.0)
WAKE_WORD_ENDPOINT = os.getenv("WAKE_WORD_ENDPOINT", "").strip()
WAKE_WORD_PORCUPINE_ACCESS_KEY = (
    os.getenv("WAKE_WORD_PORCUPINE_ACCESS_KEY")
    or os.getenv("PICOVOICE_ACCESS_KEY", "")
).strip()

# === GPIO Config ===
BUTTON_PIN = 27 if BILLY_PINS == "legacy" else 24  # legacy=pin 13, new=pin 18

# === MQTT Config ===
MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "0"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# === Home Assistant Config ===
HA_HOST = os.getenv("HA_HOST")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_LANG = os.getenv("HA_LANG", "en")

# === Weather Config ===
WEATHER_LATITUDE = os.getenv("WEATHER_LATITUDE")
WEATHER_LONGITUDE = os.getenv("WEATHER_LONGITUDE")
WEATHER_LOCATION_NAME = os.getenv("WEATHER_LOCATION_NAME", "")

# === Personality Config ===
ALLOW_UPDATE_PERSONALITY_INI = (
    os.getenv("ALLOW_UPDATE_PERSONALITY_INI", "true").lower() == "true"
)

# === Software Config ===
FLASK_PORT = _int_env("FLASK_PORT", "80", min_val=1, max_val=65535)
SHOW_SUPPORT = os.getenv("SHOW_SUPPORT", True)
FORCE_PASS_CHANGE = os.getenv("FORCE_PASS_CHANGE", "false").lower() == "true"
SHOW_RC_VERSIONS = os.getenv("SHOW_RC_VERSIONS", "False")
FLAP_ON_BOOT = os.getenv("FLAP_ON_BOOT", "false").lower() == "true"
MOCKFISH = os.getenv("MOCKFISH", "false").lower() == "true"

# === News Digest Config ===
NEWS_REQUEST_TIMEOUT_SECONDS = float(os.getenv("NEWS_REQUEST_TIMEOUT_SECONDS", "6"))

# === User Profile Config ===
DEFAULT_USER = os.getenv("DEFAULT_USER", "guest").strip()
CURRENT_USER = os.getenv("CURRENT_USER", "").strip()


def is_classic_billy():
    return os.getenv("BILLY_MODEL", "modern").strip().lower() == "classic"


try:
    MAIN_LOOP = asyncio.get_event_loop()
except RuntimeError:
    MAIN_LOOP = None
