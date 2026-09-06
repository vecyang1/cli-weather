#!/usr/bin/env python3
"""
cli_weather - Production-grade, ultra-compact terminal weather interface (<150 tokens)
with multi-city concurrency, 4-tier provider cascade (Open-Meteo, Met.no, wttr.in, Agentic Search),
atomic caching, and robust geographic disambiguation.
"""

from .models import (
    CityWeather,
    ResolvedLocation,
    WeatherCondition,
    DailyForecast,
    c_to_f,
    f_to_c,
    kmh_to_mph,
)
from .config import (
    WeatherConfig,
    load_config,
    save_config,
)
from .geo_resolver import GeoResolver
from .cache_manager import CacheManager
from .weather_engine import WeatherEngine
from .formatters import (
    format_table,
    format_json,
    format_oneline,
    format_brief_natural,
)
from .cli import main, __version__

__all__ = [
    "__version__",
    "main",
    "WeatherEngine",
    "WeatherConfig",
    "load_config",
    "save_config",
    "GeoResolver",
    "CacheManager",
    "CityWeather",
    "ResolvedLocation",
    "WeatherCondition",
    "DailyForecast",
    "format_table",
    "format_json",
    "format_oneline",
    "format_brief_natural",
    "c_to_f",
    "f_to_c",
    "kmh_to_mph",
]
