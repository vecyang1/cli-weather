#!/usr/bin/env python3
"""
geo_resolver.py - Robust Geographic Disambiguation & Location Resolution.
Resolves city names, typos (e.g. Chiangamai -> Chiang Mai), aliases (Danang -> Da Nang),
Chinese/English names, and coordinates.
"""

import json
import re
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any
try:
    from .models import ResolvedLocation
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import ResolvedLocation


# Pre-seeded canonical locations for zero-latency, deterministic resolution.
# Solves ambiguous geographic queries (e.g. Dali in Yunnan vs Dali in Shaanxi/Cyprus).
PRESEEDED_LOCATIONS: Dict[str, Dict[str, Any]] = {
    # Cadence core cities
    "foshan": {
        "canonical": "Foshan",
        "zh": "佛山",
        "en": "Foshan",
        "country": "China",
        "country_code": "CN",
        "lat": 23.0215,
        "lon": 113.1214,
        "timezone": "Asia/Shanghai",
    },
    "chiang mai": {
        "canonical": "Chiang Mai",
        "zh": "清迈",
        "en": "Chiang Mai",
        "country": "Thailand",
        "country_code": "TH",
        "lat": 18.7904,
        "lon": 98.9847,
        "timezone": "Asia/Bangkok",
    },
    "da nang": {
        "canonical": "Da Nang",
        "zh": "岘港",
        "en": "Da Nang",
        "country": "Vietnam",
        "country_code": "VN",
        "lat": 16.0544,
        "lon": 108.2022,
        "timezone": "Asia/Ho_Chi_Minh",
    },
    "shanghai": {
        "canonical": "Shanghai",
        "zh": "上海",
        "en": "Shanghai",
        "country": "China",
        "country_code": "CN",
        "lat": 31.2304,
        "lon": 121.4737,
        "timezone": "Asia/Shanghai",
    },
    "dali": {
        "canonical": "Dali",
        "zh": "大理",
        "en": "Dali",
        "country": "China",
        "country_code": "CN",
        "lat": 25.5847,
        "lon": 100.2123,
        "timezone": "Asia/Shanghai",
    },
    "guilin": {
        "canonical": "Guilin",
        "zh": "桂林",
        "en": "Guilin",
        "country": "China",
        "country_code": "CN",
        "lat": 25.2736,
        "lon": 110.2902,
        "timezone": "Asia/Shanghai",
    },
    "tokyo": {
        "canonical": "Tokyo",
        "zh": "东京",
        "en": "Tokyo",
        "country": "Japan",
        "country_code": "JP",
        "lat": 35.6895,
        "lon": 139.6917,
        "timezone": "Asia/Tokyo",
    },
    # Frequent nomad / business hubs
    "bangkok": {
        "canonical": "Bangkok",
        "zh": "曼谷",
        "en": "Bangkok",
        "country": "Thailand",
        "country_code": "TH",
        "lat": 13.7563,
        "lon": 100.5018,
        "timezone": "Asia/Bangkok",
    },
    "ho chi minh city": {
        "canonical": "Ho Chi Minh City",
        "zh": "胡志明市",
        "en": "Ho Chi Minh City",
        "country": "Vietnam",
        "country_code": "VN",
        "lat": 10.8231,
        "lon": 106.6297,
        "timezone": "Asia/Ho_Chi_Minh",
    },
    "hanoi": {
        "canonical": "Hanoi",
        "zh": "河内",
        "en": "Hanoi",
        "country": "Vietnam",
        "country_code": "VN",
        "lat": 21.0285,
        "lon": 105.8542,
        "timezone": "Asia/Ho_Chi_Minh",
    },
    "beijing": {
        "canonical": "Beijing",
        "zh": "北京",
        "en": "Beijing",
        "country": "China",
        "country_code": "CN",
        "lat": 39.9042,
        "lon": 116.4074,
        "timezone": "Asia/Shanghai",
    },
    "guangzhou": {
        "canonical": "Guangzhou",
        "zh": "广州",
        "en": "Guangzhou",
        "country": "China",
        "country_code": "CN",
        "lat": 23.1291,
        "lon": 113.2644,
        "timezone": "Asia/Shanghai",
    },
    "shenzhen": {
        "canonical": "Shenzhen",
        "zh": "深圳",
        "en": "Shenzhen",
        "country": "China",
        "country_code": "CN",
        "lat": 22.5431,
        "lon": 114.0579,
        "timezone": "Asia/Shanghai",
    },
    "hong kong": {
        "canonical": "Hong Kong",
        "zh": "香港",
        "en": "Hong Kong",
        "country": "China (HK)",
        "country_code": "HK",
        "lat": 22.3193,
        "lon": 114.1694,
        "timezone": "Asia/Hong_Kong",
    },
    "singapore": {
        "canonical": "Singapore",
        "zh": "新加坡",
        "en": "Singapore",
        "country": "Singapore",
        "country_code": "SG",
        "lat": 1.3521,
        "lon": 103.8198,
        "timezone": "Asia/Singapore",
    },
    "london": {
        "canonical": "London",
        "zh": "伦敦",
        "en": "London",
        "country": "United Kingdom",
        "country_code": "GB",
        "lat": 51.5074,
        "lon": -0.1278,
        "timezone": "Europe/London",
    },
    "new york": {
        "canonical": "New York",
        "zh": "纽约",
        "en": "New York",
        "country": "United States",
        "country_code": "US",
        "lat": 40.7128,
        "lon": -74.0060,
        "timezone": "America/New_York",
    },
    "paris": {
        "canonical": "Paris",
        "zh": "巴黎",
        "en": "Paris",
        "country": "France",
        "country_code": "FR",
        "lat": 48.8566,
        "lon": 2.3522,
        "timezone": "Europe/Paris",
    },
}

# Aliases and common misspellings pointing to preseeded canonical keys
ALIAS_MAP: Dict[str, str] = {
    # Typos & Variants for Chiang Mai
    "chiangmai": "chiang mai",
    "chiangamai": "chiang mai",
    "chiang mai": "chiang mai",
    "changmai": "chiang mai",
    "清迈": "chiang mai",
    "cnx": "chiang mai",

    # Variants for Da Nang
    "danang": "da nang",
    "da nang": "da nang",
    "đa nẵng": "da nang",
    "岘港": "da nang",
    "dad": "da nang",

    # Variants for Foshan
    "foshan": "foshan",
    "fo shan": "foshan",
    "佛山": "foshan",
    "南海": "foshan",
    "顺德": "foshan",

    # Variants for Dali
    "dali": "dali",
    "大理": "dali",
    "dali city": "dali",
    "dali yunnan": "dali",

    # Variants for Guilin
    "guilin": "guilin",
    "gui lin": "guilin",
    "桂林": "guilin",
    "kwl": "guilin",
    "can": "guangzhou",
    "pek": "beijing",
    "pkx": "beijing",
    "szx": "shenzhen",
    "hkg": "hong kong",
    "dmk": "bangkok",
    "lhr": "london",
    "jfk": "new york",
    "cdg": "paris",


    # Variants for Shanghai
    "shanghai": "shanghai",
    "shang hai": "shanghai",
    "上海": "shanghai",
    "pvg": "shanghai",
    "sha": "shanghai",

    # Variants for Tokyo
    "tokyo": "tokyo",
    "东京": "tokyo",
    "hnd": "tokyo",
    "nrt": "tokyo",

    # Other common aliases
    "beijing": "beijing",
    "北京": "beijing",
    "guangzhou": "guangzhou",
    "广州": "guangzhou",
    "shenzhen": "shenzhen",
    "深圳": "shenzhen",
    "hongkong": "hong kong",
    "hong kong": "hong kong",
    "香港": "hong kong",
    "bangkok": "bangkok",
    "曼谷": "bangkok",
    "bkk": "bangkok",
    "singapore": "singapore",
    "新加坡": "singapore",
    "sin": "singapore",
    "saigon": "ho chi minh city",
    "hcmc": "ho chi minh city",
    "胡志明": "ho chi minh city",
    "胡志明市": "ho chi minh city",
    "sgn": "ho chi minh city",
    "hanoi": "hanoi",
    "河内": "hanoi",
    "han": "hanoi",
    "london": "london",
    "伦敦": "london",
    "nyc": "new york",
    "new york": "new york",
    "纽约": "new york",
    "paris": "paris",
    "巴黎": "paris",
}

def normalize_query_key(query: str) -> str:
    """Normalize input query string for dictionary matching."""
    s = query.strip().lower()
    # Replace punctuation / underscores with space
    s = re.sub(r"[_\-\+]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

class GeoResolver:
    """Resolves arbitrary user location strings to canonical coordinates."""

    def __init__(self, timeout_sec: float = 3.0):
        self.timeout_sec = timeout_sec

    def resolve(self, query: str) -> ResolvedLocation:
        """
        Resolve a query to a ResolvedLocation object.
        1. Check special types (Moon, landmarks)
        2. Check pre-seeded alias map
        3. Dynamic online geocoding via Open-Meteo Geocoding API with smart disambiguation
        4. Fallback default
        """
        raw_query = query.strip()
        if not raw_query:
            # Default to IP / current location indicator
            return ResolvedLocation(
                query="",
                canonical_name="Local Location",
                display_name_zh="当前位置",
                display_name_en="Current Location",
                country="",
                country_code="",
                lat=0.0,
                lon=0.0,
                is_special=True,
            )

        # Check special: Moon
        if raw_query.lower().startswith("moon"):
            return ResolvedLocation(
                query=raw_query,
                canonical_name="Moon",
                display_name_zh="月相",
                display_name_en="Moon Phase",
                country="Space",
                country_code="",
                lat=0.0,
                lon=0.0,
                is_special=True,
            )

        # Check landmark (~ notation)
        if raw_query.startswith("~") or raw_query.startswith("@"):
            name = raw_query[1:].strip()
            coords = self._geocode_landmark(name)
            lat = coords[0] if coords else 0.0
            lon = coords[1] if coords else 0.0
            display_title = coords[2] if coords else name
            return ResolvedLocation(
                query=raw_query,
                canonical_name=display_title,
                display_name_zh=display_title,
                display_name_en=display_title,
                country="",
                country_code="",
                lat=lat,
                lon=lon,
                is_landmark=True,
            )

        norm_key = normalize_query_key(raw_query)

        # 1. Direct or alias hit in preseeded locations
        canonical_key = ALIAS_MAP.get(norm_key, norm_key)
        if canonical_key in PRESEEDED_LOCATIONS:
            info = PRESEEDED_LOCATIONS[canonical_key]
            return ResolvedLocation(
                query=raw_query,
                canonical_name=info["canonical"],
                display_name_zh=info["zh"],
                display_name_en=info["en"],
                country=info["country"],
                country_code=info["country_code"],
                lat=info["lat"],
                lon=info["lon"],
                timezone=info.get("timezone", "auto"),
            )

        # 2. Dynamic geocoding via Open-Meteo Geocoding API
        online_res = self._geocode_online(raw_query)
        if online_res:
            return online_res

        # 3. Fallback: Return raw location with zero coordinates (will prompt wttr / search fallback)
        return ResolvedLocation(
            query=raw_query,
            canonical_name=raw_query,
            display_name_zh=raw_query,
            display_name_en=raw_query,
            country="",
            country_code="",
            lat=0.0,
            lon=0.0,
        )

    def _geocode_online(self, query: str) -> Optional[ResolvedLocation]:
        """Perform geocoding via Open-Meteo Geocoding API with population/tier filtering."""
        try:
            encoded = urllib.parse.quote(query.strip())
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=5&language=en&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "cli-weather/2.0"})
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = data.get("results")
            if not results:
                return None

            # Pick highest population / most relevant city
            # Filter prefer capital or administrative centers (PPLC, PPLA, PPLA2)
            best = None
            max_pop = -1
            for r in results:
                pop = r.get("population", 0) or 0
                fcode = r.get("feature_code", "")
                # Prefer administrative centers
                score = pop
                if fcode in ("PPLC", "PPLA", "PPLA2"):
                    score += 500000
                if score > max_pop:
                    max_pop = score
                    best = r

            if not best:
                best = results[0]

            name = best.get("name", query)
            country = best.get("country", "")
            country_code = best.get("country_code", "")
            admin1 = best.get("admin1", "")
            lat = float(best.get("latitude", 0.0))
            lon = float(best.get("longitude", 0.0))
            tz = best.get("timezone", "auto")

            display_en = f"{name}, {admin1}".strip(", ") if admin1 and admin1 != name else name
            display_zh = name  # Default to English name if no zh provided by Open-Meteo

            return ResolvedLocation(
                query=query,
                canonical_name=name,
                display_name_zh=display_zh,
                display_name_en=display_en,
                country=country,
                country_code=country_code,
                lat=lat,
                lon=lon,
                timezone=tz,
            )
        except Exception:
            return None

    def _geocode_landmark(self, name: str) -> Optional[tuple[float, float, str]]:
        """Geocode a landmark or tourist attraction via Wikipedia API with OSM fallback."""
        # 1. Wikipedia API
        try:
            encoded = urllib.parse.quote(name)
            url = f"https://en.wikipedia.org/w/api.php?action=query&prop=coordinates&titles={encoded}&format=json&redirects=1"
            req = urllib.request.Request(url, headers={"User-Agent": "cli-weather/2.0"})
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                if "coordinates" in pdata and pdata["coordinates"]:
                    c = pdata["coordinates"][0]
                    return float(c["lat"]), float(c["lon"]), pdata.get("title", name)
        except Exception:
            pass

        # 2. Nominatim OSM fallback
        try:
            encoded = urllib.parse.quote(name)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "cli-weather/2.0"})
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                first = data[0]
                return float(first["lat"]), float(first["lon"]), first.get("display_name", name).split(",")[0]
        except Exception:
            pass

        return None
