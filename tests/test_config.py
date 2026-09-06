#!/usr/bin/env python3
import unittest
import tempfile
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.config import (
    WeatherConfig,
    load_config,
    save_config,
    load_config_file,
    get_config_candidates,
    _parse_simple_toml,
)

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config_values(self):
        cfg = WeatherConfig()
        self.assertEqual(cfg.units, "metric")
        self.assertEqual(cfg.lang, "zh")
        self.assertEqual(cfg.provider, "auto")
        self.assertEqual(cfg.cache_ttl, 1200)
        self.assertEqual(cfg.format, "auto")
        self.assertEqual(cfg.default_cities, [])
        self.assertEqual(cfg.validate(), [])

    def test_validate_invalid_values(self):
        cfg = WeatherConfig(units="kelvin", provider="yahoo", format="xml", cache_ttl=-1)
        errors = cfg.validate()
        self.assertEqual(len(errors), 4)

    def test_save_and_load_json(self):
        target = self.config_dir / "config.json"
        cfg = WeatherConfig(
            default_cities=["Tokyo", "Osaka"],
            units="imperial",
            lang="en",
            provider="met-no",
            cache_ttl=600,
        )
        saved = save_config(cfg, target_path=target)
        self.assertTrue(saved.is_file())

        loaded_cfg, loaded_path = load_config(custom_path=str(target))
        self.assertEqual(loaded_path, target.resolve())
        self.assertEqual(loaded_cfg.default_cities, ["Tokyo", "Osaka"])
        self.assertEqual(loaded_cfg.units, "imperial")
        self.assertEqual(loaded_cfg.lang, "en")
        self.assertEqual(loaded_cfg.provider, "met-no")
        self.assertEqual(loaded_cfg.cache_ttl, 600)

    def test_simple_toml_parser(self):
        toml_content = """
        # Weather config
        units = "imperial"
        lang = "en"
        cache_ttl = 1800
        default_cities = ["London", "Paris", "Rome"]
        """
        data = _parse_simple_toml(toml_content)
        self.assertEqual(data["units"], "imperial")
        self.assertEqual(data["lang"], "en")
        self.assertEqual(data["cache_ttl"], 1800)
        self.assertEqual(data["default_cities"], ["London", "Paris", "Rome"])

    def test_env_var_overrides(self):
        target = self.config_dir / "config.json"
        target.write_text(json.dumps({"units": "metric", "lang": "zh"}), encoding="utf-8")

        with unittest.mock.patch.dict(os.environ, {
            "CLI_WEATHER_UNITS": "imperial",
            "CLI_WEATHER_LANG": "ja",
            "CLI_WEATHER_DEFAULT_CITIES": "Tokyo,Kyoto",
        }):
            cfg, _ = load_config(custom_path=str(target))
            self.assertEqual(cfg.units, "imperial")
            self.assertEqual(cfg.lang, "ja")
            self.assertEqual(cfg.default_cities, ["Tokyo", "Kyoto"])

if __name__ == "__main__":
    unittest.main()
