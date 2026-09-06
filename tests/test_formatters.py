#!/usr/bin/env python3
import unittest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.formatters import format_table, format_json, format_oneline, format_brief_natural
from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition

class TestFormatters(unittest.TestCase):
    def setUp(self):
        self.cities = [
            CityWeather(
                query="Foshan",
                location=ResolvedLocation("Foshan", "Foshan", "佛山", "Foshan", "China", "CN", 23.0, 113.0),
                temp_c=28.0,
                feels_like_c=31.0,
                humidity_pct=85,
                wind_speed_kmh=8.0,
                wind_dir_compass="南风",
                condition=WeatherCondition(code=80, text="小阵雨", icon="🌦️"),
                temp_min_c=25.0,
                temp_max_c=32.0,
                precip_prob_pct=70,
                uv_index=8.5,
                is_success=True,
            ),
            CityWeather(
                query="Tokyo",
                location=ResolvedLocation("Tokyo", "Tokyo", "东京", "Tokyo", "Japan", "JP", 35.6, 139.6),
                temp_c=22.0,
                feels_like_c=22.0,
                humidity_pct=60,
                wind_speed_kmh=12.0,
                wind_dir_compass="北风",
                condition=WeatherCondition(code=0, text="晴朗", icon="☀️"),
                temp_min_c=18.0,
                temp_max_c=24.0,
                precip_prob_pct=0,
                uv_index=2.0,
                is_success=True,
            ),
            CityWeather(
                query="InvalidCity",
                location=ResolvedLocation("InvalidCity", "InvalidCity", "InvalidCity", "InvalidCity", "", "", 0.0, 0.0),
                temp_c=0.0,
                feels_like_c=0.0,
                humidity_pct=0,
                wind_speed_kmh=0.0,
                is_success=False,
                error_message="City not found",
            )
        ]

    def test_format_table_zh(self):
        out = format_table(self.cities, lang="zh")
        self.assertIn("城市", out)
        self.assertIn("气温(℃)", out)
        self.assertIn("紫外线", out)
        self.assertIn("佛山 (CN)", out)
        self.assertIn("25~32℃", out)
        self.assertIn("8.5 (很强)", out)
        self.assertIn("东京 (JP)", out)
        self.assertIn("❌ City not found", out)

    def test_format_table_imperial(self):
        out = format_table(self.cities, lang="zh", units="imperial")
        self.assertIn("气温(℉)", out)
        self.assertIn("体感(℉)", out)
        self.assertIn("77~90℉", out)
        self.assertIn("88", out)

    def test_format_table_en(self):
        out = format_table(self.cities, lang="en")
        self.assertIn("City", out)
        self.assertIn("UV", out)
        self.assertIn("Foshan (CN)", out)
        self.assertIn("8.5", out)
        self.assertIn("Tokyo (JP)", out)

    def test_format_json_compact(self):
        out = format_json(self.cities, compact=True, lang="zh")
        data = json.loads(out)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["city"], "佛山")
        self.assertEqual(data[0]["temp"], "25~32℃")
        self.assertEqual(data[2]["status"], "error")

    def test_format_json_imperial(self):
        out = format_json(self.cities, compact=True, lang="en", units="imperial")
        data = json.loads(out)
        self.assertIn("℉", data[0]["temp"])
        self.assertIn("℉", data[0]["feels"])
        self.assertIn("mph", data[0]["wind"])

    def test_format_oneline(self):
        out = format_oneline(self.cities, lang="zh")
        lines = out.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("佛山:", lines[0])
        self.assertIn("东京:", lines[1])
        self.assertIn("InvalidCity: ❌", lines[2])

    def test_format_brief_natural(self):
        out = format_brief_natural(self.cities, lang="zh")
        self.assertIn("【今日多城天气速报】", out)
        self.assertIn("携带雨具", out)
        self.assertIn("佛山", out)

    def test_format_brief_natural_en(self):
        out = format_brief_natural(self.cities, lang="en")
        self.assertIn("【Daily Weather Summary】", out)
        self.assertIn("💡 Tips:", out)
        self.assertIn("Rain gear: High probability of precipitation/showers in Foshan", out)

    def test_format_moon_special(self):
        moon_city = CityWeather(
            query="Moon",
            location=ResolvedLocation("Moon", "Moon", "月相", "Moon Phase", "", "", 0.0, 0.0, is_special=True),
            temp_c=0.0,
            feels_like_c=0.0,
            humidity_pct=0,
            wind_speed_kmh=0.0,
            condition=WeatherCondition(0, "残月 (亮度 31%)", "🌘"),
            is_success=True,
        )
        table = format_table([moon_city], lang="zh")
        self.assertIn("月相", table)
        self.assertIn("🌘 残月 (亮度 31%)", table)
        self.assertNotIn("0℃", table)

        oneline = format_oneline([moon_city], lang="zh")
        self.assertEqual(oneline, "月相: 🌘 残月 (亮度 31%)")

if __name__ == "__main__":
    unittest.main()
