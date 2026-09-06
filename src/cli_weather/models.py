#!/usr/bin/env python3
"""
models.py - Core data contracts and domain entities for cli-weather.
Adheres to: Single Source of Truth, contract-first, type-safe, minimal redundant state.
Zero runtime dependencies (standard library only).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

# WMO Weather Code Mappings to English and Chinese with Emojis
WMO_CODE_MAP = {
    0: {"en": "Clear sky", "zh": "晴朗", "icon": "☀️"},
    1: {"en": "Mainly clear", "zh": "晴间多云", "icon": "🌤️"},
    2: {"en": "Partly cloudy", "zh": "多云", "icon": "⛅"},
    3: {"en": "Overcast", "zh": "阴天", "icon": "☁️"},
    45: {"en": "Fog", "zh": "雾", "icon": "🌫️"},
    48: {"en": "Depositing rime fog", "zh": "冻雾", "icon": "🌫️"},
    51: {"en": "Light drizzle", "zh": "小毛毛雨", "icon": "🌦️"},
    53: {"en": "Moderate drizzle", "zh": "毛毛雨", "icon": "🌦️"},
    55: {"en": "Dense drizzle", "zh": "密集毛毛雨", "icon": "🌧️"},
    56: {"en": "Light freezing drizzle", "zh": "轻微冻毛毛雨", "icon": "🌨️"},
    57: {"en": "Dense freezing drizzle", "zh": "冻毛毛雨", "icon": "🌨️"},
    61: {"en": "Slight rain", "zh": "小雨", "icon": "🌧️"},
    63: {"en": "Moderate rain", "zh": "中雨", "icon": "🌧️"},
    65: {"en": "Heavy rain", "zh": "大雨/暴雨", "icon": "🌧️"},
    66: {"en": "Light freezing rain", "zh": "小冻雨", "icon": "🌨️"},
    67: {"en": "Heavy freezing rain", "zh": "大冻雨", "icon": "🌨️"},
    71: {"en": "Slight snow fall", "zh": "小雪", "icon": "🌨️"},
    73: {"en": "Moderate snow fall", "zh": "中雪", "icon": "❄️"},
    75: {"en": "Heavy snow fall", "zh": "大雪/暴雪", "icon": "❄️"},
    77: {"en": "Snow grains", "zh": "雪粒", "icon": "❄️"},
    80: {"en": "Slight rain showers", "zh": "小阵雨", "icon": "🌦️"},
    81: {"en": "Moderate rain showers", "zh": "阵雨", "icon": "🌦️"},
    82: {"en": "Violent rain showers", "zh": "强阵雨", "icon": "⛈️"},
    85: {"en": "Slight snow showers", "zh": "小阵雪", "icon": "🌨️"},
    86: {"en": "Heavy snow showers", "zh": "强阵雪", "icon": "❄️"},
    95: {"en": "Thunderstorm", "zh": "雷阵雨", "icon": "⛈️"},
    96: {"en": "Thunderstorm with slight hail", "zh": "雷阵雨伴小冰雹", "icon": "⛈️"},
    99: {"en": "Thunderstorm with heavy hail", "zh": "雷阵雨伴大冰雹", "icon": "⛈️"},
}


def c_to_f(temp_c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return temp_c * 9.0 / 5.0 + 32.0


def f_to_c(temp_f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (temp_f - 32.0) * 5.0 / 9.0


def kmh_to_mph(speed_kmh: float) -> float:
    """Convert km/h to mph."""
    return speed_kmh * 0.621371


def get_wmo_condition(code: int, lang: str = "zh", is_day: Optional[int] = 1) -> Dict[str, str]:
    """Retrieve condition text and icon from WMO code with day/night awareness."""
    data = WMO_CODE_MAP.get(code, {"en": "Unknown", "zh": "未知", "icon": "🌡️"})
    icon = data["icon"]
    # Nighttime icon customization for clear/partly cloudy skies
    if is_day == 0:
        if code in (0, 1):
            icon = "🌙"
        elif code == 2:
            icon = "☁️"

    return {
        "text": data.get(lang, data["en"]),
        "icon": icon,
        "en": data["en"],
        "zh": data["zh"],
    }


@dataclass
class WeatherCondition:
    code: int
    text: str
    icon: str


@dataclass
class ResolvedLocation:
    query: str
    canonical_name: str
    display_name_zh: str
    display_name_en: str
    country: str
    country_code: str
    lat: float
    lon: float
    timezone: str = "auto"
    is_landmark: bool = False
    is_special: bool = False  # E.g. Moon phase


@dataclass
class DailyForecast:
    date: str
    temp_min_c: float
    temp_max_c: float
    condition_code: int
    condition_text: str
    icon: str
    precip_prob_pct: Optional[int] = None
    precip_mm: Optional[float] = None

    @property
    def temp_min_f(self) -> float:
        return c_to_f(self.temp_min_c)

    @property
    def temp_max_f(self) -> float:
        return c_to_f(self.temp_max_c)


@dataclass
class CityWeather:
    query: str
    location: ResolvedLocation
    temp_c: float
    feels_like_c: float
    humidity_pct: int
    wind_speed_kmh: float
    wind_direction_deg: Optional[int] = None
    wind_dir_compass: str = ""
    condition: WeatherCondition = field(default_factory=lambda: WeatherCondition(0, "Clear", "☀️"))
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    precip_mm: Optional[float] = None
    precip_prob_pct: Optional[int] = None
    uv_index: Optional[float] = None
    provider: str = "open-meteo"
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    forecast: List[DailyForecast] = field(default_factory=list)
    is_success: bool = True
    error_message: Optional[str] = None

    @property
    def temp_f(self) -> float:
        return c_to_f(self.temp_c)

    @property
    def feels_like_f(self) -> float:
        return c_to_f(self.feels_like_c)

    @property
    def temp_min_f(self) -> Optional[float]:
        return c_to_f(self.temp_min_c) if self.temp_min_c is not None else None

    @property
    def temp_max_f(self) -> Optional[float]:
        return c_to_f(self.temp_max_c) if self.temp_max_c is not None else None

    @property
    def wind_speed_mph(self) -> float:
        return kmh_to_mph(self.wind_speed_kmh)

    def temp_range_formatted(self, units: str = "metric") -> str:
        """Derive temperature range string dynamically with unit awareness."""
        if units == "imperial":
            if self.temp_min_f is not None and self.temp_max_f is not None:
                return f"{round(self.temp_min_f)}~{round(self.temp_max_f)}℉"
            return f"{round(self.temp_f)}℉"
        else:
            if self.temp_min_c is not None and self.temp_max_c is not None:
                return f"{round(self.temp_min_c)}~{round(self.temp_max_c)}℃"
            return f"{round(self.temp_c)}℃"

    @property
    def temp_range_str(self) -> str:
        """Default metric temperature range string for backward compatibility."""
        return self.temp_range_formatted(units="metric")

    @property
    def city_label_zh(self) -> str:
        return self.location.display_name_zh or self.location.canonical_name

    @property
    def city_label_en(self) -> str:
        return self.location.display_name_en or self.location.canonical_name

    def to_compact_dict(self, lang: str = "zh", units: str = "metric") -> Dict[str, Any]:
        """Ultra-compact dictionary for token-efficient LLM consumption."""
        if not self.is_success:
            return {
                "city": self.query,
                "status": "error",
                "error": self.error_message or "Lookup failed",
            }

        city_name = self.city_label_zh if lang == "zh" else self.city_label_en
        is_imp = (units == "imperial")
        temp_str = self.temp_range_formatted(units=units)
        feels_val = round(self.feels_like_f if is_imp else self.feels_like_c)
        feels_unit = "℉" if is_imp else "℃"
        wind_speed_val = round(self.wind_speed_mph if is_imp else self.wind_speed_kmh)
        wind_unit = "mph" if is_imp else "km/h"

        res: Dict[str, Any] = {
            "city": city_name,
            "weather": f"{self.condition.icon} {self.condition.text}",
            "temp": temp_str,
            "feels": f"{feels_val}{feels_unit}",
            "hum": f"{self.humidity_pct}%",
            "wind": f"{self.wind_dir_compass} {wind_speed_val}{wind_unit}".strip(),
        }
        if self.precip_prob_pct is not None and self.precip_prob_pct > 0:
            res["precip"] = f"{self.precip_prob_pct}%"
        elif self.precip_mm is not None and self.precip_mm > 0:
            res["precip"] = f"{self.precip_mm}mm"
        if self.uv_index is not None and self.uv_index > 0:
            res["uv"] = round(self.uv_index, 1)
        return res
