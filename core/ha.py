import asyncio
import time as _time

import aiohttp

from core.config import HA_HOST, HA_LANG, HA_TOKEN
from core.logger import logger


# HARE-02: Availability cache -- skip HA calls for 30s after a failure
_ha_unavailable_until: float = 0.0
_HA_CACHE_TTL: float = 30.0  # seconds


def _mark_ha_unavailable() -> None:
    """Mark HA as temporarily unavailable for ``_HA_CACHE_TTL`` seconds."""
    global _ha_unavailable_until
    _ha_unavailable_until = _time.time() + _HA_CACHE_TTL


def ha_available() -> bool:
    """Return True when HA is configured and not in the failure cool-down."""
    if not (HA_HOST and HA_TOKEN):
        return False
    return _time.time() >= _ha_unavailable_until


async def send_conversation_prompt(prompt: str) -> str | None:
    """Send a conversation prompt to Home Assistant's conversation API."""
    if not ha_available():
        logger.warning(
            "Home Assistant not configured or temporarily unavailable.", "⚠️"
        )
        return None

    url = f"{HA_HOST.rstrip('/')}/api/conversation/process"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"text": prompt, "language": HA_LANG}

    try:
        timeout = aiohttp.ClientTimeout(total=5)  # HARE-01: 5s timeout
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(url, headers=headers, json=payload) as resp,
        ):
            if resp.status == 200:
                data = await resp.json()
                return data.get("response", "")
            logger.warning(f"HA API returned HTTP {resp.status}", "⚠️")
            return None
    except asyncio.TimeoutError:
        logger.warning("HA conversation prompt timed out (5s)", "⏱️")
        _mark_ha_unavailable()
        return None
    except Exception as e:
        logger.error(f"Error reaching Home Assistant API: {e}")
        _mark_ha_unavailable()
        return None
