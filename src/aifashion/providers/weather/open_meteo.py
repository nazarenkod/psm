"""Адаптер погоды на Open-Meteo (бесплатно, без ключа). Реализует WeatherProvider."""
from __future__ import annotations

import httpx

_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoProvider:
    async def current(self, lat: float, lon: float) -> dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_URL, params=params)
            resp.raise_for_status()
            return resp.json().get("current", {})
