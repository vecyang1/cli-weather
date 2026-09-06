#!/usr/bin/env python3
"""
open_meteo_provider.py - Primary Open-Meteo API provider.
Fast (<200ms), 100% free, no API key required, highly reliable global forecasts.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List
import sys
from pathlib import Path

try:
    from ..models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast, get_wmo_condition
    from .base_provider import BaseWeatherProvider
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast, get_wmo_condition
        from cli_weather.providers.base_provider import BaseWeatherProvider
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast, get_wmo_condition
        from providers.base_provider import BaseWeatherProvider

COMPASS_POINTS = [
    ("北风", "N"),
    ("东北偏北风", "NNE"),
    ("东北风", "NE"),
    ("东北偏东风", "ENE"),
    ("东风", "E"),
    ("东南偏东风", "ESE"),
    ("东南风", "SE"),
    ("东南偏南风", "SSE"),
    ("南风", "S"),
    ("西南偏南风", "SSW"),
    ("西南风", "SW"),
    ("西南偏西风", "WSW"),
    ("西风", "W"),
    ("西北偏西风", "WNW"),
    ("西北风", "NW"),
    ("西北偏北风", "NNW"),
]

def deg_to_compass(deg: Optional[int], lang: str = "zh") -> str:
    """Convert degrees (0-360) to compass direction string."""
    if deg is None:
        return ""
    val = int((deg / 22.5) + 0.5) % 16
    zh, en = COMPASS_POINTS[val]
    return zh if lang == "zh" else en

class OpenMeteoProvider(BaseWeatherProvider):
    """Fetches weather from Open-Meteo REST API."""

    def __init__(self, timeout_sec: float = 4.0):
        self.timeout_sec = timeout_sec

    @property
    def name(self) -> str:
        return "open-meteo"

    def fetch(self, location: ResolvedLocation, lang: str = "zh") -> Optional[CityWeather]:
        # Coordinates must be valid non-zero
        if location.lat == 0.0 and location.lon == 0.0:
            return None

        tz = urllib.parse.quote(location.timezone) if location.timezone else "auto"
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={location.lat}&longitude={location.lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m,wind_direction_10m,uv_index"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,uv_index_max"
            f"&timezone={tz}&forecast_days=3"
        )

        req = urllib.request.Request(url, headers={"User-Agent": "cli-weather/2.0"})
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data.get("current", {})
        daily = data.get("daily", {})

        wmo_code = current.get("weather_code", 0)
        is_day = current.get("is_day", 1)
        cond_dict = get_wmo_condition(wmo_code, lang=lang, is_day=is_day)
        condition = WeatherCondition(
            code=wmo_code,
            text=cond_dict["text"],
            icon=cond_dict["icon"],
        )

        temp_c = float(current.get("temperature_2m", 0.0))
        feels_like_c = float(current.get("apparent_temperature", temp_c))
        humidity_pct = int(current.get("relative_humidity_2m", 0))
        wind_speed_kmh = float(current.get("wind_speed_10m", 0.0))
        wind_deg = current.get("wind_direction_10m")
        wind_dir = deg_to_compass(wind_deg, lang=lang)
        precip_mm = float(current.get("precipitation", 0.0))

        # Parse UV index (prefer current uv_index, fallback to daily max)
        uv_val = current.get("uv_index")
        if uv_val is None and daily and "uv_index_max" in daily:
            uv_max_arr = daily.get("uv_index_max", [])
            if uv_max_arr and uv_max_arr[0] is not None:
                uv_val = uv_max_arr[0]
        uv_index = float(uv_val) if uv_val is not None else None

        # Parse daily stats for today
        temp_min_c = None
        temp_max_c = None
        precip_prob = None
        daily_list: List[DailyForecast] = []

        if daily and "time" in daily:
            times = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            codes = daily.get("weather_code", [])
            probs = daily.get("precipitation_probability_max", [])
            sums = daily.get("precipitation_sum", [])

            if max_temps and len(max_temps) > 0:
                temp_max_c = float(max_temps[0])
            if min_temps and len(min_temps) > 0:
                temp_min_c = float(min_temps[0])
            if probs and len(probs) > 0 and probs[0] is not None:
                precip_prob = int(probs[0])

            for i in range(len(times)):
                d_code = codes[i] if i < len(codes) else 0
                d_cond = get_wmo_condition(d_code, lang=lang)
                daily_list.append(DailyForecast(
                    date=times[i],
                    temp_min_c=float(min_temps[i]) if i < len(min_temps) else 0.0,
                    temp_max_c=float(max_temps[i]) if i < len(max_temps) else 0.0,
                    condition_code=d_code,
                    condition_text=d_cond["text"],
                    icon=d_cond["icon"],
                    precip_prob_pct=int(probs[i]) if i < len(probs) and probs[i] is not None else None,
                    precip_mm=float(sums[i]) if i < len(sums) and sums[i] is not None else None,
                ))

        return CityWeather(
            query=location.query,
            location=location,
            temp_c=temp_c,
            feels_like_c=feels_like_c,
            humidity_pct=humidity_pct,
            wind_speed_kmh=wind_speed_kmh,
            wind_direction_deg=wind_deg,
            wind_dir_compass=wind_dir,
            condition=condition,
            temp_min_c=temp_min_c,
            temp_max_c=temp_max_c,
            precip_mm=precip_mm,
            precip_prob_pct=precip_prob,
            uv_index=uv_index,
            provider=self.name,
            forecast=daily_list,
            is_success=True,
        )
