#!/usr/bin/env python3
"""
base_provider.py - Abstract base class for weather providers.
"""

import sys
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional

try:
    from ..models import CityWeather, ResolvedLocation
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models import CityWeather, ResolvedLocation


class BaseWeatherProvider(ABC):
    """Abstract interface for a weather data source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @abstractmethod
    def fetch(self, location: ResolvedLocation, lang: str = "zh") -> Optional[CityWeather]:
        """
        Fetch weather data for a resolved location.
        Returns CityWeather if successful, None or raises exception if failed.
        """
        pass
