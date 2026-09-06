#!/usr/bin/env python3
"""
wttr_provider.py - Secondary fallback provider using wttr.in.
Supports structured JSON (format=j1), formatted strings, and special entities (Moon, landmarks).
Includes comprehensive English-to-Chinese translation table and dynamic icon mapping.
"""

import json
import re
import urllib.request
import urllib.parse
import subprocess
from typing import Optional, List, Dict, Tuple
import sys
from pathlib import Path

try:
    from ..models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast
    from .base_provider import BaseWeatherProvider
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast
        from cli_weather.providers.base_provider import BaseWeatherProvider
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models import CityWeather, ResolvedLocation, WeatherCondition, DailyForecast
        from providers.base_provider import BaseWeatherProvider

MOON_PHASE_MAP: Dict[str, Tuple[str, str]] = {
    "new moon": ("新月", "🌑"),
    "waxing crescent": ("峨眉月", "🌒"),
    "first quarter": ("上弦月", "🌓"),
    "waxing gibbous": ("盈凸月", "🌔"),
    "full moon": ("满月", "🌕"),
    "waning gibbous": ("亏凸月", "🌖"),
    "last quarter": ("下弦月", "🌗"),
    "third quarter": ("下弦月", "🌗"),
    "waning crescent": ("残月", "🌘"),
}

# Common wttr.in English descriptions to Chinese translation & Icon mapping
WTTR_CONDITION_MAP: Dict[str, Tuple[str, str]] = {
    "sunny": ("晴朗", "☀️"),
    "clear": ("晴朗", "☀️"),
    "partly cloudy": ("多云", "⛅"),
    "cloudy": ("多云", "☁️"),
    "overcast": ("阴天", "☁️"),
    "mist": ("大雾", "🌫️"),
    "fog": ("大雾", "🌫️"),
    "freezing fog": ("冻雾", "🌫️"),
    "patchy rain possible": ("局部有雨", "🌦️"),
    "patchy rain nearby": ("附近有零星小雨", "🌦️"),
    "patchy light drizzle": ("零星小雨", "🌦️"),
    "light drizzle": ("小毛毛雨", "🌦️"),
    "freezing drizzle": ("冻毛毛雨", "🌨️"),
    "patchy light rain": ("零星小雨", "🌦️"),
    "light rain": ("小雨", "🌧️"),
    "moderate rain at times": ("时有中雨", "🌧️"),
    "moderate rain": ("中雨", "🌧️"),
    "heavy rain at times": ("时有大雨", "🌧️"),
    "heavy rain": ("大雨", "🌧️"),
    "light freezing rain": ("小冻雨", "🌨️"),
    "moderate or heavy freezing rain": ("中到大冻雨", "🌨️"),
    "light rain shower": ("小阵雨", "🌦️"),
    "moderate or heavy rain shower": ("强阵雨", "⛈️"),
    "torrential rain shower": ("暴雨", "⛈️"),
    "patchy snow possible": ("局部有雪", "🌨️"),
    "light snow": ("小雪", "❄️"),
    "moderate snow": ("中雪", "❄️"),
    "heavy snow": ("大雪", "❄️"),
    "patchy sleet possible": ("局部雨夹雪", "🌨️"),
    "light sleet": ("轻度雨夹雪", "🌨️"),
    "moderate or heavy sleet": ("雨夹雪", "🌨️"),
    "thundery outbreaks possible": ("雷阵雨可能", "⛈️"),
    "patchy light rain with thunder": ("雷阵雨伴小雨", "⛈️"),
    "moderate or heavy rain with thunder": ("雷阵雨伴大雨", "⛈️"),
    "patchy light snow with thunder": ("雷阵雪伴小雪", "❄️"),
    "moderate or heavy snow with thunder": ("雷阵雪伴大雪", "❄️"),
}

def translate_wttr_condition(text: str, lang: str = "zh") -> Tuple[str, str]:
    """Translate English wttr.in condition text to target language with icon."""
    clean = text.strip().lower()
    if clean in WTTR_CONDITION_MAP:
        zh, icon = WTTR_CONDITION_MAP[clean]
        return (zh if lang == "zh" else text, icon)

    # Partial keyword matching
    if "thunder" in clean or "storm" in clean:
        return ("雷阵雨" if lang == "zh" else text, "⛈️")
    if "heavy rain" in clean or "downpour" in clean:
        return ("大雨" if lang == "zh" else text, "🌧️")
    if "rain" in clean or "shower" in clean or "drizzle" in clean:
        return ("阵雨" if lang == "zh" else text, "🌦️")
    if "snow" in clean or "blizzard" in clean:
        return ("雪" if lang == "zh" else text, "❄️")
    if "sleet" in clean:
        return ("雨夹雪" if lang == "zh" else text, "🌨️")
    if "overcast" in clean:
        return ("阴天" if lang == "zh" else text, "☁️")
    if "cloud" in clean:
        return ("多云" if lang == "zh" else text, "⛅")
    if "fog" in clean or "mist" in clean or "haze" in clean:
        return ("雾" if lang == "zh" else text, "🌫️")
    if "clear" in clean or "sunny" in clean:
        return ("晴朗" if lang == "zh" else text, "☀️")

    return (text, "⛅")

class WttrProvider(BaseWeatherProvider):
    """Fetches weather from wttr.in service."""

    def __init__(self, timeout_sec: float = 4.5):
        self.timeout_sec = timeout_sec

    @property
    def name(self) -> str:
        return "wttr"

    def fetch(self, location: ResolvedLocation, lang: str = "zh") -> Optional[CityWeather]:
        query_str = location.query or location.canonical_name
        # Format location for wttr.in
        if not (query_str.startswith("~") or query_str.startswith("@") or query_str.lower().startswith("moon")):
            query_loc = query_str.replace(" ", "_")
        else:
            query_loc = query_str

        encoded_loc = urllib.parse.quote(query_loc)

        # 1. Handle special queries like Moon
        if location.is_special or query_str.lower().startswith("moon"):
            return self._fetch_special(encoded_loc, location)

        # 2. Try format=j1 for structured weather
        url = f"https://wttr.in/{encoded_loc}?format=j1&m"
        if lang:
            url += f"&lang={lang}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "curl/7.81.0", "Accept-Language": lang}
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current_arr = data.get("current_condition", [])
            if not current_arr:
                return None
            curr = current_arr[0]

            temp_c = float(curr.get("temp_C", 0.0))
            feels_like_c = float(curr.get("FeelsLikeC", temp_c))
            humidity_pct = int(curr.get("humidity", 0))
            wind_speed_kmh = float(curr.get("windspeedKmph", 0.0))
            wind_dir = curr.get("winddir16Point", "")

            # Weather desc
            weather_desc_arr = curr.get("weatherDesc", [])
            raw_desc = weather_desc_arr[0].get("value", "Clear") if weather_desc_arr else "Clear"
            cond_text, cond_icon = translate_wttr_condition(raw_desc, lang=lang)

            # Min/max from weather[0]
            weather_days = data.get("weather", [])
            temp_min_c = None
            temp_max_c = None
            precip_mm = float(curr.get("precipMM", 0.0)) if curr.get("precipMM") else None
            daily_list: List[DailyForecast] = []

            if weather_days:
                today = weather_days[0]
                temp_min_c = float(today.get("mintempC", temp_c))
                temp_max_c = float(today.get("maxtempC", temp_c))

                for day in weather_days:
                    d_min = float(day.get("mintempC", 0.0))
                    d_max = float(day.get("maxtempC", 0.0))
                    hourly = day.get("hourly", [])
                    d_raw = hourly[len(hourly)//2].get("weatherDesc", [{}])[0].get("value", raw_desc) if hourly else raw_desc
                    d_text, d_icon = translate_wttr_condition(d_raw, lang=lang)
                    daily_list.append(DailyForecast(
                        date=day.get("date", ""),
                        temp_min_c=d_min,
                        temp_max_c=d_max,
                        condition_code=0,
                        condition_text=d_text,
                        icon=d_icon,
                    ))

            # UV index
            uv_val = curr.get("uvIndex")
            if uv_val is None and weather_days:
                uv_val = weather_days[0].get("uvIndex")
            uv_index = float(uv_val) if uv_val is not None else None

            condition = WeatherCondition(
                code=0,
                text=cond_text,
                icon=cond_icon,
            )

            return CityWeather(
                query=location.query,
                location=location,
                temp_c=temp_c,
                feels_like_c=feels_like_c,
                humidity_pct=humidity_pct,
                wind_speed_kmh=wind_speed_kmh,
                wind_dir_compass=wind_dir,
                condition=condition,
                temp_min_c=temp_min_c,
                temp_max_c=temp_max_c,
                precip_mm=precip_mm,
                uv_index=uv_index,
                provider=self.name,
                forecast=daily_list,
                is_success=True,
            )

        except Exception:
            # Fallback to curl execution if urllib fails or SSL issue
            return self._fetch_curl_fallback(encoded_loc, location, lang)

    def _fetch_special(self, encoded_loc: str, location: ResolvedLocation) -> CityWeather:
        """Fetch structured or raw response for Moon phase or special queries."""
        try:
            # 1. Try format=j1 for structured astronomical details
            try:
                url = f"https://wttr.in/{encoded_loc}?format=j1&m"
                req = urllib.request.Request(url, headers={"User-Agent": "curl/7.81.0"})
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                astronomy = data.get("weather", [{}])[0].get("astronomy", [{}])[0]
                phase = astronomy.get("moon_phase", "Moon")
                illum = astronomy.get("moon_illumination", "")
                zh_phase, icon = MOON_PHASE_MAP.get(phase.strip().lower(), (phase, "🌕"))
                cond_text = f"{zh_phase} (亮度 {illum}%)" if illum else zh_phase
                return CityWeather(
                    query=location.query,
                    location=location,
                    temp_c=0.0,
                    feels_like_c=0.0,
                    humidity_pct=0,
                    wind_speed_kmh=0.0,
                    condition=WeatherCondition(0, cond_text, icon),
                    provider=self.name,
                    is_success=True,
                )
            except Exception:
                pass

            # 2. Fallback: query ASCII summary
            cmd = ["curl", "-s", "--max-time", str(self.timeout_sec), f"wttr.in/{encoded_loc}?m&T"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            output = re.sub(r'\[[0-9;]*[a-zA-Z]', '', res.stdout.strip())
            lines = [l.strip() for l in output.splitlines() if l.strip()]
            desc = lines[-1] if lines else "Moon"

            return CityWeather(
                query=location.query,
                location=location,
                temp_c=0.0,
                feels_like_c=0.0,
                humidity_pct=0,
                wind_speed_kmh=0.0,
                condition=WeatherCondition(0, desc, "🌕"),
                provider=self.name,
                is_success=True,
            )
        except Exception as e:
            return CityWeather(
                query=location.query,
                location=location,
                temp_c=0.0,
                feels_like_c=0.0,
                humidity_pct=0,
                wind_speed_kmh=0.0,
                provider=self.name,
                is_success=False,
                error_message=str(e),
            )


    def _fetch_curl_fallback(self, encoded_loc: str, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        """Try fetching custom formatted string via curl as fallback."""
        try:
            format_str = "%t|%f|%h|%w|%C|%p"
            url = f"https://wttr.in/{encoded_loc}?format={format_str}&m"
            if lang:
                url += f"&lang={lang}"
            cmd = ["curl", "-s", "--max-time", str(self.timeout_sec), url]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0 or not res.stdout or "|" not in res.stdout:
                return None
            parts = [p.strip() for p in res.stdout.strip().split("|")]
            if len(parts) >= 5:
                def parse_num(s: str) -> float:
                    clean = "".join(c for c in s if c in "0123456789.-")
                    return float(clean) if clean else 0.0

                temp_c = parse_num(parts[0])
                feels_c = parse_num(parts[1])
                humidity = int(parse_num(parts[2]))
                wind = parse_num(parts[3])
                raw_cond = parts[4]
                cond_text, cond_icon = translate_wttr_condition(raw_cond, lang=lang)

                return CityWeather(
                    query=location.query,
                    location=location,
                    temp_c=temp_c,
                    feels_like_c=feels_c,
                    humidity_pct=humidity,
                    wind_speed_kmh=wind,
                    condition=WeatherCondition(0, cond_text, cond_icon),
                    provider=self.name,
                    is_success=True,
                )
        except Exception:
            pass
        return None
