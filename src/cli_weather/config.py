#!/usr/bin/env python3
"""
config.py - Centralized configuration management for cli-weather.
Supports:
- Configuration files (~/.config/cli-weather/config.json, config.toml, .cli-weather.json)
- Environment variables (CLI_WEATHER_*)
- CLI argument overrides
- Zero-dependency runtime (pure standard library)
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cli-weather"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

VALID_UNITS = ("metric", "imperial")
VALID_PROVIDERS = ("auto", "open-meteo", "met-no", "wttr", "search")
VALID_FORMATS = ("auto", "table", "json", "compact-json", "oneline", "brief", "ascii")


@dataclass
class WeatherConfig:
    """Runtime configuration for cli-weather."""
    default_cities: List[str] = field(default_factory=list)
    units: str = "metric"       # "metric" (℃, km/h) or "imperial" (℉, mph)
    lang: str = "zh"            # "zh", "en", "ja", "fr", etc.
    provider: str = "auto"      # "auto", "open-meteo", "met-no", "wttr", "search"
    cache_ttl: int = 1200       # seconds (20 min)
    format: str = "auto"        # "auto", "table", "json", "compact-json", "oneline", "brief", "ascii"
    cache_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> List[str]:
        """Validate configuration values, returning any error warnings."""
        errors = []
        if self.units not in VALID_UNITS:
            errors.append(f"Invalid units '{self.units}'. Expected one of {VALID_UNITS}")
        if self.provider not in VALID_PROVIDERS:
            errors.append(f"Invalid provider '{self.provider}'. Expected one of {VALID_PROVIDERS}")
        if self.format not in VALID_FORMATS:
            errors.append(f"Invalid format '{self.format}'. Expected one of {VALID_FORMATS}")
        if self.cache_ttl < 0:
            errors.append(f"cache_ttl must be >= 0, got {self.cache_ttl}")
        return errors


def get_config_candidates(custom_path: Optional[str] = None) -> List[Path]:
    """Return ordered list of candidate config files."""
    candidates = []
    if custom_path:
        candidates.append(Path(custom_path).expanduser().resolve())
    if "CLI_WEATHER_CONFIG" in os.environ:
        candidates.append(Path(os.environ["CLI_WEATHER_CONFIG"]).expanduser().resolve())
    candidates.append(DEFAULT_CONFIG_FILE)
    candidates.append(DEFAULT_CONFIG_DIR / "config.toml")
    candidates.append(Path.cwd() / ".cli-weather.json")
    return candidates


def _parse_simple_toml(content: str) -> Dict[str, Any]:
    """Minimal fallback parser for simple TOML files without external dependencies."""
    data: Dict[str, Any] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            items = [item.strip().strip('"').strip("'") for item in v[1:-1].split(",") if item.strip()]
            data[k] = items
        elif v.isdigit():
            data[k] = int(v)
        elif v.lower() in ("true", "false"):
            data[k] = v.lower() == "true"
        else:
            data[k] = v.strip('"').strip("'")
    return data


def load_config_file(path: Path) -> Dict[str, Any]:
    """Safely read and parse a JSON or TOML config file."""
    if not path.is_file():
        return {}
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        if path.suffix == ".json":
            return json.loads(content)
        elif path.suffix == ".toml":
            if tomllib is not None:
                return tomllib.loads(content)
            return _parse_simple_toml(content)
    except Exception:
        return {}
    return {}


def load_config(custom_path: Optional[str] = None) -> Tuple[WeatherConfig, Optional[Path]]:
    """
    Load effective configuration merging:
    1. Base defaults
    2. File config (first existing candidate)
    3. Environment variables
    Returns (WeatherConfig, active_config_path_or_None)
    """
    base = WeatherConfig()
    loaded_from: Optional[Path] = None

    # 1. Config file
    for p in get_config_candidates(custom_path):
        if p.is_file():
            file_data = load_config_file(p)
            if file_data:
                loaded_from = p
                if "default_cities" in file_data and isinstance(file_data["default_cities"], list):
                    base.default_cities = [str(c).strip() for c in file_data["default_cities"] if str(c).strip()]
                elif "default_cities" in file_data and isinstance(file_data["default_cities"], str):
                    base.default_cities = [c.strip() for c in file_data["default_cities"].split(",") if c.strip()]
                if "units" in file_data and file_data["units"] in VALID_UNITS:
                    base.units = str(file_data["units"]).lower()
                if "lang" in file_data:
                    base.lang = str(file_data["lang"]).strip()
                if "provider" in file_data and file_data["provider"] in VALID_PROVIDERS:
                    base.provider = str(file_data["provider"]).lower()
                if "cache_ttl" in file_data:
                    try:
                        base.cache_ttl = int(file_data["cache_ttl"])
                    except (ValueError, TypeError):
                        pass
                if "format" in file_data and file_data["format"] in VALID_FORMATS:
                    base.format = str(file_data["format"]).lower()
                if "cache_dir" in file_data and file_data["cache_dir"]:
                    base.cache_dir = str(file_data["cache_dir"]).strip()
                break

    # 2. Environment variables override file config
    if "CLI_WEATHER_DEFAULT_CITIES" in os.environ or "CLI_WEATHER_CITIES" in os.environ:
        raw = os.environ.get("CLI_WEATHER_DEFAULT_CITIES") or os.environ.get("CLI_WEATHER_CITIES") or ""
        base.default_cities = [c.strip() for c in raw.split(",") if c.strip()]

    if "CLI_WEATHER_UNITS" in os.environ:
        u = os.environ["CLI_WEATHER_UNITS"].strip().lower()
        if u in VALID_UNITS:
            base.units = u

    if "CLI_WEATHER_LANG" in os.environ:
        base.lang = os.environ["CLI_WEATHER_LANG"].strip()

    if "CLI_WEATHER_PROVIDER" in os.environ:
        p = os.environ["CLI_WEATHER_PROVIDER"].strip().lower()
        if p in VALID_PROVIDERS:
            base.provider = p

    if "CLI_WEATHER_CACHE_TTL" in os.environ:
        try:
            base.cache_ttl = int(os.environ["CLI_WEATHER_CACHE_TTL"].strip())
        except ValueError:
            pass

    if "CLI_WEATHER_FORMAT" in os.environ:
        f = os.environ["CLI_WEATHER_FORMAT"].strip().lower()
        if f in VALID_FORMATS:
            base.format = f

    if "CLI_WEATHER_CACHE_DIR" in os.environ:
        base.cache_dir = os.environ["CLI_WEATHER_CACHE_DIR"].strip()

    return base, loaded_from


def save_config(config: WeatherConfig, target_path: Optional[Path] = None) -> Path:
    """Save configuration to target path (default: ~/.config/cli-weather/config.json)."""
    p = target_path or DEFAULT_CONFIG_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
