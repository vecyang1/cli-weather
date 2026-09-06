#!/usr/bin/env python3
"""
cli.py - Main entry point and CLI interface for cli-weather.
Provides high-efficiency multi-city weather queries with multi-tier fallback cascade,
configurable defaults, atomic caching, and token-optimized formats.
"""

import sys
import argparse
import subprocess
import urllib.parse
from pathlib import Path
from typing import List, Optional

try:
    from .models import CityWeather
    from .config import load_config, save_config, WeatherConfig, DEFAULT_CONFIG_FILE, VALID_UNITS, VALID_PROVIDERS, VALID_FORMATS
    from .weather_engine import WeatherEngine
    from .cache_manager import CacheManager
    from .formatters import format_table, format_json, format_oneline, format_brief_natural
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather
        from cli_weather.config import load_config, save_config, WeatherConfig, DEFAULT_CONFIG_FILE, VALID_UNITS, VALID_PROVIDERS, VALID_FORMATS
        from cli_weather.weather_engine import WeatherEngine
        from cli_weather.cache_manager import CacheManager
        from cli_weather.formatters import format_table, format_json, format_oneline, format_brief_natural
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from models import CityWeather
        from config import load_config, save_config, WeatherConfig, DEFAULT_CONFIG_FILE, VALID_UNITS, VALID_PROVIDERS, VALID_FORMATS
        from weather_engine import WeatherEngine
        from cache_manager import CacheManager
        from formatters import format_table, format_json, format_oneline, format_brief_natural

__version__ = "2.0.0"

DEFAULT_CADENCE_CITIES = ["Foshan", "Chiang Mai", "Da Nang", "Shanghai", "Dali", "Guilin", "Tokyo"]


def parse_args():
    parser = argparse.ArgumentParser(
        prog="cli-weather",
        description="Production-grade, token-optimized terminal weather interface (<150 tokens) with multi-city concurrency and 4-tier provider cascade.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Multi-city batch query (ultra-compact Markdown table):
  cli-weather "Foshan" "Chiang Mai" "Da Nang" "Shanghai" "Dali" "Guilin" "Tokyo" --lang zh

  # Using configured default cities or comma-separated list:
  cli-weather --cities "Tokyo,Shanghai,London" --table

  # Compact JSON for agent ingestion (<120 tokens):
  cli-weather "Tokyo" "Shanghai" --json

  # Imperial units (℉, mph):
  cli-weather "New York" "San Francisco" --units imperial

  # One-line format for status bars / tmux:
  cli-weather "Tokyo" -o

  # Daily briefing with natural language tips:
  cli-weather "Foshan" "Chiangmai" "Danang" --brief --lang zh

  # Initialize default configuration file (~/.config/cli-weather/config.json):
  cli-weather --init-config
        """
    )

    parser.add_argument(
        "locations",
        nargs="*",
        help="One or more cities, IATA codes (muc), landmarks (~Eiffel Tower), or Moon"
    )
    parser.add_argument(
        "-c", "--cities",
        help="Comma-separated list of cities (e.g. 'Foshan,Chiang Mai,Tokyo')"
    )
    parser.add_argument(
        "-l", "--lang",
        help="Specify language for output (e.g. zh, en, ja, fr). Default from config or 'zh'"
    )
    parser.add_argument(
        "-u", "--units",
        choices=VALID_UNITS,
        help="Measurement units: 'metric' (℃, km/h) or 'imperial' (℉, mph). Default: metric"
    )
    parser.add_argument(
        "-f", "--format",
        choices=VALID_FORMATS,
        help="Output format: table, json, compact-json, oneline, brief, ascii, auto"
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Output as an ultra-compact Markdown table"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as compact JSON dictionary (<120 tokens)"
    )
    parser.add_argument(
        "-o", "--oneline",
        action="store_true",
        help="Output as one-line format (useful for status bars/tmux)"
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Output as natural language daily briefing with tips"
    )
    parser.add_argument(
        "--provider",
        choices=VALID_PROVIDERS,
        help="Force a specific provider (auto, open-meteo, met-no, wttr, search)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass local cache and query live APIs"
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        help="Cache expiration time in seconds (default: 1200 / 20 min)"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached weather data"
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics (file location, entry count, file size)"
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Path to custom configuration file (JSON or TOML)"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help=f"Initialize default config file at {DEFAULT_CONFIG_FILE}"
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Display active effective configuration"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"cli-weather {__version__}"
    )

    # Legacy flags for wttr.in compatibility
    parser.add_argument("--v2", action="store_true", help="Use data-rich v2 output format (legacy wttr.in)")
    parser.add_argument("-n", "--narrow", action="store_true", help="Narrow version for split panes (legacy wttr.in)")
    parser.add_argument("--ascii", action="store_true", help="Force raw wttr.in ASCII art output")

    return parser.parse_args()


def parse_location_arguments(raw_locations: List[str], cities_arg: Optional[str] = None, default_cities: Optional[List[str]] = None) -> List[str]:
    """
    Parse command-line location arguments into clean query strings.
    Handles:
    - Comma-separated lists: --cities 'Foshan, Tokyo' or 'Foshan,Tokyo'
    - Quoted multi-word cities: 'New York', 'Chiang Mai', 'Da Nang'
    - Unquoted multi-word cities: weather Chiang Mai -> ['Chiang Mai']
    - Configured default cities when none provided on CLI
    """
    queries: List[str] = []
    if cities_arg:
        for part in cities_arg.split(","):
            p = part.strip()
            if p:
                queries.append(p)

    if not raw_locations and not queries:
        if default_cities and len(default_cities) > 0:
            return list(default_cities)
        return list(DEFAULT_CADENCE_CITIES)

    expanded_tokens: List[str] = []
    for item in raw_locations:
        if "," in item:
            for sub in item.split(","):
                s = sub.strip()
                if s:
                    queries.append(s)
        else:
            clean = item.strip()
            if clean:
                expanded_tokens.append(clean)

    if not expanded_tokens:
        return queries if queries else list(default_cities or DEFAULT_CADENCE_CITIES)

    try:
        from .geo_resolver import PRESEEDED_LOCATIONS, ALIAS_MAP, normalize_query_key, GeoResolver
    except (ImportError, ValueError):
        try:
            from cli_weather.geo_resolver import PRESEEDED_LOCATIONS, ALIAS_MAP, normalize_query_key, GeoResolver
        except ImportError:
            from geo_resolver import PRESEEDED_LOCATIONS, ALIAS_MAP, normalize_query_key, GeoResolver

    _resolver = GeoResolver()

    def is_known(name: str) -> bool:
        k = normalize_query_key(name)
        return (
            k in PRESEEDED_LOCATIONS
            or k in ALIAS_MAP
            or k.startswith("~")
            or k.startswith("@")
            or k == "moon"
            or _resolver._find_fuzzy_preseeded(k) is not None
        )

    joined_all = " ".join(expanded_tokens)
    if is_known(joined_all):
        queries.append(joined_all)
        return queries

    # Greedy tokenizer
    i = 0
    n = len(expanded_tokens)
    parsed: List[str] = []

    while i < n:
        matched = False
        for length in range(min(4, n - i), 0, -1):
            candidate = " ".join(expanded_tokens[i : i + length])
            if is_known(candidate):
                parsed.append(candidate)
                i += length
                matched = True
                break
        if not matched:
            has_any_known_ahead = any(
                is_known(" ".join(expanded_tokens[j : j + k]))
                for j in range(i + 1, n)
                for k in range(1, min(5, n - j + 1))
            )
            if not has_any_known_ahead:
                parsed.append(" ".join(expanded_tokens[i:]))
                break
            else:
                parsed.append(expanded_tokens[i])
                i += 1

    queries.extend(parsed)
    return queries if queries else list(default_cities or DEFAULT_CADENCE_CITIES)


def handle_legacy_ascii(locations: List[str], v2: bool, oneline: bool, lang: str, narrow: bool):
    """Fallback handler for raw wttr.in ASCII art."""
    loc = " ".join(locations)
    if loc:
        if not (loc.startswith("~") or loc.startswith("@")):
            loc = loc.replace(" ", "_")
        encoded_loc = urllib.parse.quote(loc)
    else:
        encoded_loc = ""

    url = f"https://wttr.in/{encoded_loc}?m"
    if v2:
        url = url.replace("https://wttr.in/", "https://v2.wttr.in/")
    if oneline:
        url += "&format=3"
    if narrow:
        url += "&n"
    if lang:
        url += f"&lang={lang}"

    try:
        cmd = ["curl", "-s", "-H", "User-Agent: curl/7.81.0"]
        if lang:
            cmd.extend(["-H", f"Accept-Language: {lang}"])
        cmd.append(url)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            print(result.stdout)
        else:
            print(f"Weather data not found or error occurred for location: {loc}")
    except Exception as e:
        print(f"Error fetching weather: {e}")


def main():
    args = parse_args()

    # Load configuration
    config, loaded_from = load_config(custom_path=args.config_path)

    # CLI actions: init-config, show-config, clear-cache, cache-stats
    if args.init_config:
        target = Path(args.config_path).expanduser().resolve() if args.config_path else DEFAULT_CONFIG_FILE
        saved_path = save_config(config, target_path=target)
        print(f"Initialized configuration file at: {saved_path}")
        sys.exit(0)

    if args.show_config:
        import json
        info = {
            "loaded_from": str(loaded_from) if loaded_from else "defaults / env",
            "config": config.to_dict(),
        }
        print(json.dumps(info, indent=2, ensure_ascii=False))
        sys.exit(0)

    if args.clear_cache:
        cache_mgr = CacheManager(cache_dir=config.cache_dir)
        cache_mgr.clear()
        print("Weather cache cleared.")
        sys.exit(0)

    if args.cache_stats:
        cache_mgr = CacheManager(cache_dir=config.cache_dir)
        stats = cache_mgr.get_stats()
        print(f"Cache location: {stats['path']}")
        print(f"Entries: {stats['entries']}")
        print(f"Size: {stats['size_bytes']} bytes")
        sys.exit(0)

    # Resolve effective runtime parameters (CLI args override config)
    effective_lang = args.lang or config.lang or "zh"
    effective_units = args.units or config.units or "metric"
    effective_provider = args.provider or config.provider or "auto"
    effective_cache_ttl = args.cache_ttl if args.cache_ttl is not None else config.cache_ttl

    # Parse query locations
    queries = parse_location_arguments(
        args.locations or [],
        cities_arg=args.cities,
        default_cities=config.default_cities if config.default_cities else None,
    )

    # Check for legacy ASCII output
    is_ascii_mode = (
        args.ascii
        or args.v2
        or (args.format == "ascii")
        or (args.narrow and not args.table and not args.json and args.format != "table")
        or (len(queries) == 1 and queries[0].strip().lower() == "moon" and args.format == "auto" and not args.table and not args.json and not args.brief and not args.oneline)
    )
    if is_ascii_mode:
        handle_legacy_ascii(queries, v2=args.v2, oneline=args.oneline, lang=effective_lang, narrow=args.narrow)
        sys.exit(0)

    # Initialize Cache & Engine
    cache_mgr = CacheManager(default_ttl_sec=effective_cache_ttl, cache_dir=config.cache_dir)
    engine = WeatherEngine(cache_manager=cache_mgr, config=config)

    # Execute concurrent queries
    results = engine.query_multiple(
        queries=queries,
        lang=effective_lang,
        no_cache=args.no_cache,
        preferred_provider=effective_provider,
    )

    # Determine output format
    fmt = args.format or config.format
    if args.table:
        fmt = "table"
    elif args.json:
        fmt = "compact-json"
    elif args.oneline:
        fmt = "oneline"
    elif args.brief:
        fmt = "brief"
    elif fmt == "auto" or not fmt:
        fmt = "table"

    # Render output
    if fmt == "table":
        output = format_table(results, lang=effective_lang, units=effective_units)
    elif fmt in ("json", "compact-json"):
        output = format_json(results, compact=(fmt == "compact-json" or args.json), lang=effective_lang, units=effective_units)
    elif fmt == "oneline":
        output = format_oneline(results, lang=effective_lang, units=effective_units)
    elif fmt == "brief":
        output = format_brief_natural(results, lang=effective_lang, units=effective_units)
    else:
        output = format_table(results, lang=effective_lang, units=effective_units)

    print(output)


if __name__ == "__main__":
    main()
