#!/usr/bin/env python3
"""
met_no_provider.py - Secondary fallback provider using Norwegian Meteorological Institute API (api.met.no).
100% free, highly reliable, global open data coverage, no API key required.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Tuple
import sys
from pathlib import Path

try:
    from ..models import CityWeather, ResolvedLocation, WeatherCondition
    from .base_provider import BaseWeatherProvider
    from .open_meteo_provider import deg_to_compass
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition
        from cli_weather.providers.base_provider import BaseWeatherProvider
        from cli_weather.providers.open_meteo_provider import deg_to_compass
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models import CityWeather, ResolvedLocation, WeatherCondition
        from providers.base_provider import BaseWeatherProvider
        from providers.open_meteo_provider import deg_to_compass

# Met.no symbol code mapping to (zh_name, en_name, icon)
MET_NO_SYMBOLS: Dict[str, Tuple[str, str, str]] = {
    "clearsky_day": ("晴朗", "Clear sky", "☀️"),
    "clearsky_night": ("晴朗", "Clear sky", "🌙"),
    "clearsky_polartwilight": ("晴朗", "Clear sky", "🌙"),
    "fair_day": ("晴间多云", "Fair", "🌤️"),
    "fair_night": ("晴间多云", "Fair", "🌙"),
    "fair_polartwilight": ("晴间多云", "Fair", "🌙"),
    "partlycloudy_day": ("多云", "Partly cloudy", "⛅"),
    "partlycloudy_night": ("多云", "Partly cloudy", "☁️"),
    "partlycloudy_polartwilight": ("多云", "Partly cloudy", "☁️"),
    "cloudy": ("阴天", "Overcast", "☁️"),
    "rainshowers_day": ("阵雨", "Rain showers", "🌦️"),
    "rainshowers_night": ("阵雨", "Rain showers", "🌦️"),
    "rainshowers_polartwilight": ("阵雨", "Rain showers", "🌦️"),
    "rainshowersandthunder_day": ("雷阵雨", "Rain showers and thunder", "⛈️"),
    "rainshowersandthunder_night": ("雷阵雨", "Rain showers and thunder", "⛈️"),
    "sleetshowers_day": ("雨夹雪", "Sleet showers", "🌨️"),
    "sleetshowers_night": ("雨夹雪", "Sleet showers", "🌨️"),
    "snowshowers_day": ("阵雪", "Snow showers", "🌨️"),
    "snowshowers_night": ("阵雪", "Snow showers", "🌨️"),
    "rain": ("中雨", "Rain", "🌧️"),
    "heavyrain": ("大雨", "Heavy rain", "🌧️"),
    "heavyrainandthunder": ("暴雨伴雷电", "Heavy rain and thunder", "⛈️"),
    "sleet": ("雨夹雪", "Sleet", "🌨️"),
    "snow": ("小雪", "Snow", "❄️"),
    "heavysnow": ("大雪", "Heavy snow", "❄️"),
    "fog": ("雾", "Fog", "🌫️"),
    "lightrainshowers_day": ("小阵雨", "Light rain showers", "🌦️"),
    "lightrainshowers_night": ("小阵雨", "Light rain showers", "🌦️"),
    "heavyrainshowers_day": ("强阵雨", "Heavy rain showers", "⛈️"),
    "heavyrainshowers_night": ("强阵雨", "Heavy rain showers", "⛈️"),
    "lightrain": ("小雨", "Light rain", "🌦️"),
    "lightsnow": ("小雪", "Light snow", "🌨️"),
}

class MetNoProvider(BaseWeatherProvider):
    """Fetches weather from api.met.no REST API."""

    def __init__(self, timeout_sec: float = 4.5):
        self.timeout_sec = timeout_sec

    @property
    def name(self) -> str:
        return "met-no"

    def fetch(self, location: ResolvedLocation, lang: str = "zh") -> Optional[CityWeather]:
        if location.lat == 0.0 and location.lon == 0.0:
            return None

        lat_round = round(location.lat, 4)
        lon_round = round(location.lon, 4)
        url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat_round}&lon={lon_round}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "cli-weather-production/2.0 (github.com/vecyang1/cli-weather)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            timeseries = data.get("properties", {}).get("timeseries", [])
            if not timeseries:
                return None

            t0 = timeseries[0]
            data_block = t0.get("data", {})
            instant_details = data_block.get("instant", {}).get("details", {})

            temp_c = float(instant_details.get("air_temperature", 0.0))
            humidity_pct = int(round(instant_details.get("relative_humidity", 0.0)))
            wind_speed_ms = float(instant_details.get("wind_speed", 0.0))
            wind_speed_kmh = round(wind_speed_ms * 3.6, 1)
            wind_from_deg = instant_details.get("wind_from_direction")
            wind_deg_int = int(round(wind_from_deg)) if wind_from_deg is not None else None
            wind_dir = deg_to_compass(wind_deg_int, lang=lang)

            # Weather condition from next_1_hours or next_6_hours
            symbol = "cloudy"
            precip_prob = None
            precip_amount = None

            next_1h = data_block.get("next_1_hours")
            if next_1h:
                symbol = next_1h.get("summary", {}).get("symbol_code", "cloudy")
                details_1h = next_1h.get("details", {})
                precip_prob = details_1h.get("probability_of_precipitation")
                precip_amount = details_1h.get("precipitation_amount")
            else:
                next_6h = data_block.get("next_6_hours")
                if next_6h:
                    symbol = next_6h.get("summary", {}).get("symbol_code", "cloudy")
                    details_6h = next_6h.get("details", {})
                    precip_prob = details_6h.get("probability_of_precipitation")
                    precip_amount = details_6h.get("precipitation_amount")

            zh_text, en_text, icon = MET_NO_SYMBOLS.get(
                symbol,
                (symbol.replace("_", " "), symbol.replace("_", " "), "⛅")
            )
            cond_text = zh_text if lang == "zh" else en_text

            precip_prob_int = int(round(precip_prob)) if precip_prob is not None else None
            precip_mm_float = float(precip_amount) if precip_amount is not None else None

            # Calculate min/max over next 12 hours
            temp_min = temp_c
            temp_max = temp_c
            for point in timeseries[:12]:
                p_temp = point.get("data", {}).get("instant", {}).get("details", {}).get("air_temperature")
                if p_temp is not None:
                    if p_temp < temp_min:
                        temp_min = p_temp
                    if p_temp > temp_max:
                        temp_max = p_temp

            condition = WeatherCondition(code=0, text=cond_text, icon=icon)

            return CityWeather(
                query=location.query,
                location=location,
                temp_c=temp_c,
                feels_like_c=temp_c,
                humidity_pct=humidity_pct,
                wind_speed_kmh=wind_speed_kmh,
                wind_direction_deg=wind_deg_int,
                wind_dir_compass=wind_dir,
                condition=condition,
                temp_min_c=temp_min,
                temp_max_c=temp_max,
                precip_mm=precip_mm_float,
                precip_prob_pct=precip_prob_int,
                provider=self.name,
                is_success=True,
            )
        except Exception:
            return None
