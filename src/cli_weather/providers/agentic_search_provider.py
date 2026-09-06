#!/usr/bin/env python3
"""
agentic_search_provider.py - Dynamic Agentic Search & Web Fallback Provider.
When primary APIs fail, leverages web proxies (Jina reader) and search scraping
to extract structured weather data without manual intervention.
"""

import re
import urllib.request
import urllib.parse
from typing import Optional, Tuple
import sys
from pathlib import Path

try:
    from ..models import CityWeather, ResolvedLocation, WeatherCondition
    from .base_provider import BaseWeatherProvider
    from .wttr_provider import translate_wttr_condition
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition
        from cli_weather.providers.base_provider import BaseWeatherProvider
        from cli_weather.providers.wttr_provider import translate_wttr_condition
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from models import CityWeather, ResolvedLocation, WeatherCondition
        from providers.base_provider import BaseWeatherProvider
        from providers.wttr_provider import translate_wttr_condition

class AgenticSearchProvider(BaseWeatherProvider):
    """Fallback provider that extracts weather via web proxy & search queries."""

    def __init__(self, timeout_sec: float = 6.0):
        self.timeout_sec = timeout_sec

    @property
    def name(self) -> str:
        return "agentic-search"

    def fetch(self, location: ResolvedLocation, lang: str = "zh") -> Optional[CityWeather]:
        target = location.canonical_name or location.query

        # 1. First attempt: Resilient web extraction via Jina reader proxy
        jina_weather = self._fetch_via_jina_proxy(target, location, lang=lang)
        if jina_weather:
            return jina_weather

        # 2. Second attempt: Search engine snippet parsing
        search_weather = self._fetch_via_search(target, location, lang=lang)
        if search_weather:
            return search_weather

        # 3. If all automated search paths fail, return explicit diagnostic failure
        return CityWeather(
            query=location.query,
            location=location,
            temp_c=0.0,
            feels_like_c=0.0,
            humidity_pct=0,
            wind_speed_kmh=0.0,
            provider=self.name,
            is_success=False,
            error_message="Agentic search could not extract confident weather metrics. Suggest using web_search tool.",
        )

    def _fetch_via_jina_proxy(self, target: str, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        """Extract weather via Jina web proxy on open weather formats."""
        try:
            encoded = urllib.parse.quote(target.replace(" ", "_"))
            url = f"https://r.jina.ai/http://wttr.in/{encoded}?format=%t|%f|%h|%w|%C|%p&m"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "cli-weather-agentic/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                content = resp.read().decode("utf-8", errors="ignore")

            for line in content.splitlines():
                if "|" in line and re.match(r"^[+-]?\d+", line.strip()):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 5:
                        def parse_num(s: str) -> float:
                            clean = "".join(c for c in s if c in "0123456789.-")
                            return float(clean) if clean else 0.0

                        temp_c = parse_num(parts[0])
                        feels_c = parse_num(parts[1]) if parts[1] else temp_c
                        humidity = int(parse_num(parts[2])) if parts[2] else 60
                        wind = parse_num(parts[3]) if parts[3] else 10.0
                        raw_cond = parts[4]
                        cond_text, cond_icon = translate_wttr_condition(raw_cond, lang=lang)

                        precip_mm = parse_num(parts[5]) if len(parts) > 5 and parts[5] else None

                        return CityWeather(
                            query=location.query,
                            location=location,
                            temp_c=temp_c,
                            feels_like_c=feels_c,
                            humidity_pct=humidity,
                            wind_speed_kmh=wind,
                            precip_mm=precip_mm,
                            condition=WeatherCondition(0, cond_text, cond_icon),
                            provider=self.name,
                            is_success=True,
                        )
        except Exception:
            pass
        return None

    def _fetch_via_search(self, target: str, location: ResolvedLocation, lang: str) -> Optional[CityWeather]:
        """Extract weather via DuckDuckGo HTML / Bing search snippets."""
        try:
            query = f"{target} weather current temperature"
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")

            temp_c = self._extract_temperature(html_text)
            if temp_c is None:
                return None

            cond_text, icon = self._extract_condition(html_text, lang=lang)
            humidity = self._extract_humidity(html_text) or 60

            return CityWeather(
                query=location.query,
                location=location,
                temp_c=temp_c,
                feels_like_c=temp_c,
                humidity_pct=humidity,
                wind_speed_kmh=10.0,
                condition=WeatherCondition(code=0, text=cond_text, icon=icon),
                provider=self.name,
                is_success=True,
            )
        except Exception:
            pass
        return None

    def _extract_temperature(self, text: str) -> Optional[float]:
        """Regex parse temperature in Celsius or Fahrenheit."""
        m = re.search(r"(-?\d{1,2}(?:\.\d+)?)\s*(?:°C|℃|degrees\s*celsius)", text, re.IGNORECASE)
        if m:
            return float(m.group(1))
        m_f = re.search(r"(-?\d{1,3}(?:\.\d+)?)\s*(?:°F|℉|degrees\s*fahrenheit)", text, re.IGNORECASE)
        if m_f:
            f_val = float(m_f.group(1))
            return round((f_val - 32) * 5 / 9, 1)
        return None

    def _extract_condition(self, text: str, lang: str = "zh") -> Tuple[str, str]:
        lower = text.lower()
        if any(w in lower for w in ["thunderstorm", "lightning", "雷阵雨", "暴雨"]):
            return ("雷阵雨" if lang == "zh" else "Thunderstorm", "⛈️")
        if any(w in lower for w in ["heavy rain", "downpour", "大雨"]):
            return ("大雨" if lang == "zh" else "Heavy Rain", "🌧️")
        if any(w in lower for w in ["rain", "shower", "drizzle", "雨", "阵雨"]):
            return ("阵雨" if lang == "zh" else "Rain", "🌦️")
        if any(w in lower for w in ["snow", "flurries", "雪"]):
            return ("雪" if lang == "zh" else "Snow", "❄️")
        if any(w in lower for w in ["cloudy", "overcast", "多云", "阴"]):
            return ("多云" if lang == "zh" else "Cloudy", "⛅")
        if any(w in lower for w in ["fog", "mist", "haze", "雾", "霾"]):
            return ("雾" if lang == "zh" else "Fog", "🌫️")
        if any(w in lower for w in ["clear", "sunny", "晴", "晴朗"]):
            return ("晴朗" if lang == "zh" else "Clear", "☀️")
        return ("晴间多云" if lang == "zh" else "Partly Cloudy", "🌤️")

    def _extract_humidity(self, text: str) -> Optional[int]:
        m = re.search(r"(?:humidity|湿度)[\s:]*(\d{1,2})%", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return None
