"""Helpers for retrieving weather information from Open-Meteo."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .config import WEATHER_LATITUDE, WEATHER_LONGITUDE, WEATHER_LOCATION_NAME


OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"


def weather_configured() -> bool:
    return bool(WEATHER_LATITUDE and WEATHER_LONGITUDE)


async def fetch_current_weather() -> str:
    """Return a formatted string describing the current weather."""

    if not weather_configured():
        return (
            "Weather lookup is not configured. Set WEATHER_LATITUDE and "
            "WEATHER_LONGITUDE in your .env file."
        )

    params = {
        "latitude": WEATHER_LATITUDE,
        "longitude": WEATHER_LONGITUDE,
        "current_weather": "true",
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(OPEN_METEO_ENDPOINT, params=params) as resp:
                if resp.status != 200:
                    return (
                        "Weather service responded with "
                        f"HTTP status {resp.status}."
                    )
                payload: dict[str, Any] = await resp.json()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - network failure path
            return f"Weather service request failed: {exc}"

    current = payload.get("current_weather") or {}
    temperature = current.get("temperature")
    windspeed = current.get("windspeed")
    winddirection = current.get("winddirection")
    weather_code = current.get("weathercode")

    location = WEATHER_LOCATION_NAME or "your area"

    if temperature is None:
        return "Weather data was not available right now."

    description_parts = [
        f"Current weather for {location}: {temperature}°C",
    ]

    if windspeed is not None:
        description_parts.append(f"wind {windspeed} km/h")
    if winddirection is not None:
        description_parts.append(f"direction {winddirection}°")
    if weather_code is not None:
        description_parts.append(f"weather code {weather_code}")

    return ", ".join(description_parts) + "."

