#!/usr/bin/env python3
import unittest
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.weather_engine import WeatherEngine
from cli_weather.formatters import format_table, format_json, format_brief_natural

class TestE2ELive(unittest.TestCase):
    def test_live_seven_cadence_cities(self):
        cities = ["Foshan", "Chiangamai", "Danang", "Shanghai", "Dali", "Guilin", "Tokyo"]
        engine = WeatherEngine()

        t0 = time.time()
        results = engine.query_multiple(cities, lang="zh", no_cache=True)
        cold_time = time.time() - t0

        self.assertEqual(len(results), 7)
        for r in results:
            self.assertTrue(r.is_success, f"City query failed: {r.query}, err={r.error_message}")
            self.assertGreater(r.temp_c, -50.0)
            self.assertLess(r.temp_c, 60.0)

        # Output formats
        table = format_table(results, lang="zh")
        self.assertIn("佛山 (CN)", table)
        self.assertIn("清迈 (TH)", table)
        self.assertIn("岘港 (VN)", table)
        self.assertIn("上海 (CN)", table)
        self.assertIn("大理 (CN)", table)
        self.assertIn("桂林 (CN)", table)
        self.assertIn("东京 (JP)", table)

        brief = format_brief_natural(results, lang="zh")
        self.assertIn("【今日多城天气速报】", brief)

        # Warm cache test
        t1 = time.time()
        cached_results = engine.query_multiple(cities, lang="zh", no_cache=False)
        warm_time = time.time() - t1

        self.assertEqual(len(cached_results), 7)
        for r in cached_results:
            self.assertEqual(r.provider, "cache")

        self.assertLess(warm_time, 0.2, f"Warm cache took too long: {warm_time}s")

if __name__ == "__main__":
    unittest.main()
