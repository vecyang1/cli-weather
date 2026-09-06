#!/usr/bin/env python3
"""
weather_engine.py - Core weather pipeline orchestrator.
Manages geo-resolution, caching, concurrent execution, provider fallback cascade:
Open-Meteo -> Met.no -> wttr.in -> Agentic Search.
Configurable via WeatherConfig.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from pathlib import Path
import sys

try:
    from .models import CityWeather, ResolvedLocation
    from .geo_resolver import GeoResolver
    from .cache_manager import CacheManager
    from .config import WeatherConfig
    from .providers.open_meteo_provider import OpenMeteoProvider
    from .providers.met_no_provider import MetNoProvider
    from .providers.wttr_provider import WttrProvider
    from .providers.agentic_search_provider import AgenticSearchProvider
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation
        from cli_weather.geo_resolver import GeoResolver
        from cli_weather.cache_manager import CacheManager
        from cli_weather.config import WeatherConfig
        from cli_weather.providers.open_meteo_provider import OpenMeteoProvider
        from cli_weather.providers.met_no_provider import MetNoProvider
        from cli_weather.providers.wttr_provider import WttrProvider
        from cli_weather.providers.agentic_search_provider import AgenticSearchProvider
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from models import CityWeather, ResolvedLocation
        from geo_resolver import GeoResolver
        from cache_manager import CacheManager
        from config import WeatherConfig
        from providers.open_meteo_provider import OpenMeteoProvider
        from providers.met_no_provider import MetNoProvider
        from providers.wttr_provider import WttrProvider
        from providers.agentic_search_provider import AgenticSearchProvider


class WeatherEngine:
    """Orchestrates weather queries with caching, multi-tier fallback, and concurrency."""

    def __init__(
        self,
        geo_resolver: Optional[GeoResolver] = None,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[WeatherConfig] = None,
        timeout_sec: float = 4.0,
    ):
        self.config = config or WeatherConfig()
        self.geo_resolver = geo_resolver or GeoResolver(timeout_sec=timeout_sec)
        self.cache_manager = cache_manager or CacheManager(
            default_ttl_sec=self.config.cache_ttl,
            cache_dir=self.config.cache_dir,
        )
        self.open_meteo = OpenMeteoProvider(timeout_sec=timeout_sec)
        self.met_no = MetNoProvider(timeout_sec=timeout_sec)
        self.wttr = WttrProvider(timeout_sec=timeout_sec)
        self.agentic_search = AgenticSearchProvider(timeout_sec=timeout_sec + 2.0)

    def query_single(
        self,
        query: str,
        lang: Optional[str] = None,
        no_cache: bool = False,
        preferred_provider: Optional[str] = None,
    ) -> CityWeather:
        """Query weather for a single location string with fallback cascade."""
        effective_lang = lang or self.config.lang or "zh"
        effective_provider = preferred_provider or self.config.provider or "auto"

        raw_query = query.strip()
        location = self.geo_resolver.resolve(raw_query)

        # 1. Check cache (unless bypassed or special like Moon)
        if not no_cache and not location.is_special:
            cached = self.cache_manager.get(location.canonical_name, lang=effective_lang)
            if cached:
                return cached

        # 2. Provider selection & cascade
        weather: Optional[CityWeather] = None

        if effective_provider == "open-meteo":
            weather = self._try_open_meteo(location, effective_lang)
        elif effective_provider == "met-no":
            weather = self._try_met_no(location, effective_lang)
        elif effective_provider == "wttr":
            weather = self._try_wttr(location, effective_lang)
        elif effective_provider == "search":
            weather = self._try_agentic_search(location, effective_lang)
        else:
            # "auto" cascade: Open-Meteo -> Met.no -> wttr -> Agentic Search
            has_coords = not location.is_special and (location.lat != 0.0 or location.lon != 0.0)

            # Tier 1: Open-Meteo
            if has_coords:
                weather = self._try_open_meteo(location, effective_lang)

            # Tier 2: Met.no (Norwegian Meteorological Institute)
            if (weather is None or not weather.is_success) and has_coords:
                weather = self._try_met_no(location, effective_lang)

            # Tier 3: wttr.in
            if weather is None or not weather.is_success:
                weather = self._try_wttr(location, effective_lang)

            # Tier 4: Agentic Search / Web Fallback
            if (weather is None or not weather.is_success) and not location.is_special:
                weather = self._try_agentic_search(location, effective_lang)

        # 3. Final validation & caching
        if weather and weather.is_success:
            if not no_cache and not location.is_special:
                self.cache_manager.set(weather, lang=effective_lang)
            return weather

        # Fallback failure record
        err = weather.error_message if weather else "All weather providers failed or location could not be resolved."
        return CityWeather(
            query=raw_query,
            location=location,
            temp_c=0.0,
            feels_like_c=0.0,
            humidity_pct=0,
            wind_speed_kmh=0.0,
            provider="none",
            is_success=False,
            error_message=err,
        )

    def query_multiple(
        self,
        queries: List[str],
        lang: Optional[str] = None,
        no_cache: bool = False,
        preferred_provider: Optional[str] = None,
        max_workers: int = 8,
    ) -> List[CityWeather]:
        """
        Query multiple cities concurrently while strictly preserving order.
        """
        if not queries:
            return []

        effective_lang = lang or self.config.lang or "zh"
        effective_provider = preferred_provider or self.config.provider or "auto"

        results = [None] * len(queries)
        with ThreadPoolExecutor(max_workers=min(max_workers, len(queries))) as executor:
            future_to_idx = {
                executor.submit(
                    self.query_single,
                    query=q,
                    lang=effective_lang,
                    no_cache=no_cache,
                    preferred_provider=effective_provider,
                ): i
                for i, q in enumerate(queries)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    raw_q = queries[idx]
                    loc = self.geo_resolver.resolve(raw_q)
                    results[idx] = CityWeather(
                        query=raw_q,
                        location=loc,
                        temp_c=0.0,
                        feels_like_c=0.0,
                        humidity_pct=0,
                        wind_speed_kmh=0.0,
                        is_success=False,
                        error_message=str(e),
                    )

        return results

    def _try_open_meteo(self, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        try:
            return self.open_meteo.fetch(location, lang=lang)
        except Exception:
            return None

    def _try_met_no(self, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        try:
            return self.met_no.fetch(location, lang=lang)
        except Exception:
            return None

    def _try_wttr(self, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        try:
            return self.wttr.fetch(location, lang=lang)
        except Exception:
            return None

    def _try_agentic_search(self, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        try:
            return self.agentic_search.fetch(location, lang=lang)
        except Exception:
            return None
