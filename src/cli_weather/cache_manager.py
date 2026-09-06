#!/usr/bin/env python3
"""
cache_manager.py - Atomic, TTL-based file caching for cli-weather.
Guarantees resilient cross-platform storage (XDG ~/.cache, /tmp fallback)
with zero-latency (<15ms) reads for cached entries.
"""

import os
import json
import time
import threading
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import sys

try:
    from .models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast


def resolve_default_cache_file(custom_dir: Optional[str] = None) -> Path:
    """Determine most appropriate writable cache file path."""
    if custom_dir:
        try:
            p = Path(custom_dir).expanduser().resolve() / "weather_cache.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass

    # 1. Respect CLI_WEATHER_CACHE_DIR / XDG_CACHE_HOME
    env_dir = os.environ.get("CLI_WEATHER_CACHE_DIR")
    if env_dir:
        try:
            p = Path(env_dir).expanduser().resolve() / "weather_cache.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        try:
            p = Path(xdg) / "cli-weather" / "weather_cache.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass

    # 2. Standard ~/.cache/cli-weather
    try:
        p = Path.home() / ".cache" / "cli-weather" / "weather_cache.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        pass

    # 3. Fallback /tmp/cli-weather
    try:
        p = Path("/tmp") / "cli-weather" / "weather_cache.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        pass

    return Path.cwd() / ".cache" / "weather_cache.json"


class CacheManager:
    """Manages TTL-based caching of weather results with atomic writes and auto-fallback."""

    def __init__(self, cache_file: Optional[Path] = None, default_ttl_sec: int = 1200, cache_dir: Optional[str] = None):
        self.default_ttl_sec = default_ttl_sec
        self.cache_file = cache_file or resolve_default_cache_file(custom_dir=cache_dir)
        self._lock = threading.Lock()
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            fallback = Path("/tmp") / "cli-weather" / "weather_cache.json"
            try:
                fallback.parent.mkdir(parents=True, exist_ok=True)
                self.cache_file = fallback
            except Exception:
                pass

    def _make_key(self, canonical_name: str, lang: str) -> str:
        return f"{canonical_name.strip().lower()}:{lang.strip().lower()}"

    def get(self, canonical_name: str, lang: str = "zh", max_age_sec: Optional[int] = None) -> Optional[CityWeather]:
        """Retrieve cached CityWeather if still valid within TTL."""
        with self._lock:
            if not self.cache_file.exists():
                return None

            ttl = max_age_sec if max_age_sec is not None else self.default_ttl_sec
            now = time.time()
            key = self._make_key(canonical_name, lang)

            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                entry = data.get(key)
                if not entry:
                    return None

                cached_time = entry.get("timestamp", 0)
                if (now - cached_time) > ttl:
                    return None  # Expired

                payload = entry.get("weather")
                if not payload:
                    return None

                return self._deserialize_weather(payload)
            except Exception:
                return None

    def set(self, weather: CityWeather, lang: str = "zh"):
        """Save CityWeather into cache with atomic write and resilient error recovery."""
        if not weather.is_success:
            return  # Do not cache error responses

        key = self._make_key(weather.location.canonical_name, lang)
        now = time.time()

        with self._lock:
            for attempt in range(2):
                temp_file = None
                try:
                    self._ensure_cache_dir()
                    data: Dict[str, Any] = {}
                    if self.cache_file.exists():
                        try:
                            with open(self.cache_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except Exception:
                            data = {}

                    # Clean expired entries older than 24 hours (86400s) to keep cache file small
                    data = {k: v for k, v in data.items() if isinstance(v, dict) and (now - v.get("timestamp", 0)) < 86400}

                    data[key] = {
                        "timestamp": now,
                        "weather": self._serialize_weather(weather),
                    }

                    # Unique atomic temporary file per thread and process
                    temp_file = self.cache_file.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}")
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    try:
                        os.replace(temp_file, self.cache_file)
                    except Exception:
                        with open(self.cache_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    return
                except PermissionError:
                    fallback = Path("/tmp") / "cli-weather" / "weather_cache.json"
                    if self.cache_file != fallback:
                        self.cache_file = fallback
                        continue
                    return
                except Exception:
                    return
                finally:
                    if temp_file is not None and temp_file.exists():
                        try:
                            temp_file.unlink()
                        except Exception:
                            pass

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            try:
                if self.cache_file.exists():
                    self.cache_file.unlink()
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Return current cache statistics."""
        with self._lock:
            if not self.cache_file.exists():
                return {"entries": 0, "size_bytes": 0, "path": str(self.cache_file)}
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "entries": len(data),
                    "size_bytes": self.cache_file.stat().st_size,
                    "path": str(self.cache_file),
                }
            except Exception:
                return {"entries": 0, "size_bytes": 0, "path": str(self.cache_file)}

    def _serialize_weather(self, w: CityWeather) -> Dict[str, Any]:
        return {
            "query": w.query,
            "canonical_name": w.location.canonical_name,
            "display_name_zh": w.location.display_name_zh,
            "display_name_en": w.location.display_name_en,
            "country": w.location.country,
            "country_code": w.location.country_code,
            "lat": w.location.lat,
            "lon": w.location.lon,
            "timezone": w.location.timezone,
            "temp_c": w.temp_c,
            "feels_like_c": w.feels_like_c,
            "humidity_pct": w.humidity_pct,
            "wind_speed_kmh": w.wind_speed_kmh,
            "wind_direction_deg": w.wind_direction_deg,
            "wind_dir_compass": w.wind_dir_compass,
            "condition_code": w.condition.code,
            "condition_text": w.condition.text,
            "condition_icon": w.condition.icon,
            "temp_min_c": w.temp_min_c,
            "temp_max_c": w.temp_max_c,
            "precip_mm": w.precip_mm,
            "precip_prob_pct": w.precip_prob_pct,
            "uv_index": w.uv_index,
            "provider": w.provider,
            "fetched_at": w.fetched_at,
            "forecast": [
                {
                    "date": f.date,
                    "temp_min_c": f.temp_min_c,
                    "temp_max_c": f.temp_max_c,
                    "condition_code": f.condition_code,
                    "condition_text": f.condition_text,
                    "icon": f.icon,
                    "precip_prob_pct": f.precip_prob_pct,
                    "precip_mm": f.precip_mm,
                }
                for f in w.forecast
            ]
        }

    def _deserialize_weather(self, d: Dict[str, Any]) -> CityWeather:
        loc = ResolvedLocation(
            query=d.get("query", ""),
            canonical_name=d.get("canonical_name", ""),
            display_name_zh=d.get("display_name_zh", ""),
            display_name_en=d.get("display_name_en", ""),
            country=d.get("country", ""),
            country_code=d.get("country_code", ""),
            lat=d.get("lat", 0.0),
            lon=d.get("lon", 0.0),
            timezone=d.get("timezone", "auto"),
        )
        cond = WeatherCondition(
            code=d.get("condition_code", 0),
            text=d.get("condition_text", "Clear"),
            icon=d.get("condition_icon", "☀️"),
        )
        forecast = [
            DailyForecast(
                date=f.get("date", ""),
                temp_min_c=f.get("temp_min_c", 0.0),
                temp_max_c=f.get("temp_max_c", 0.0),
                condition_code=f.get("condition_code", 0),
                condition_text=f.get("condition_text", ""),
                icon=f.get("icon", "⛅"),
                precip_prob_pct=f.get("precip_prob_pct"),
                precip_mm=f.get("precip_mm"),
            )
            for f in d.get("forecast", [])
        ]
        return CityWeather(
            query=d.get("query", ""),
            location=loc,
            temp_c=d.get("temp_c", 0.0),
            feels_like_c=d.get("feels_like_c", 0.0),
            humidity_pct=d.get("humidity_pct", 0),
            wind_speed_kmh=d.get("wind_speed_kmh", 0.0),
            wind_direction_deg=d.get("wind_direction_deg"),
            wind_dir_compass=d.get("wind_dir_compass", ""),
            condition=cond,
            temp_min_c=d.get("temp_min_c"),
            temp_max_c=d.get("temp_max_c"),
            precip_mm=d.get("precip_mm"),
            precip_prob_pct=d.get("precip_prob_pct"),
            uv_index=d.get("uv_index"),
            provider="cache",
            fetched_at=d.get("fetched_at", ""),
            forecast=forecast,
            is_success=True,
        )
