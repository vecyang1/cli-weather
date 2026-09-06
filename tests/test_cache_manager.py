#!/usr/bin/env python3
import unittest
import tempfile
import time
import os
from pathlib import Path
import sys

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.cache_manager import CacheManager
from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition

class TestCacheManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "test_cache.json"
        self.cm = CacheManager(cache_file=self.cache_file, default_ttl_sec=2)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_dummy_weather(self, city="Foshan", temp=26.5):
        loc = ResolvedLocation(
            query=city,
            canonical_name=city,
            display_name_zh="佛山",
            display_name_en="Foshan",
            country="China",
            country_code="CN",
            lat=23.0215,
            lon=113.1214,
        )
        return CityWeather(
            query=city,
            location=loc,
            temp_c=temp,
            feels_like_c=temp + 2,
            humidity_pct=80,
            wind_speed_kmh=10.0,
            condition=WeatherCondition(code=0, text="晴朗", icon="☀️"),
            is_success=True,
        )

    def test_set_and_get(self):
        w = self._make_dummy_weather("Foshan", 28.0)
        self.cm.set(w, lang="zh")

        cached = self.cm.get("Foshan", lang="zh")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.temp_c, 28.0)
        self.assertEqual(cached.location.canonical_name, "Foshan")
        self.assertEqual(cached.provider, "cache")

    def test_ttl_expiration(self):
        w = self._make_dummy_weather("Tokyo", 22.0)
        self.cm.set(w, lang="zh")

        self.assertIsNotNone(self.cm.get("Tokyo", lang="zh", max_age_sec=1))

        time.sleep(1.2)
        self.assertIsNone(self.cm.get("Tokyo", lang="zh", max_age_sec=1))

    def test_error_responses_not_cached(self):
        loc = ResolvedLocation("ErrorCity", "ErrorCity", "ErrorCity", "ErrorCity", "", "", 0.0, 0.0)
        failed_w = CityWeather(
            query="ErrorCity",
            location=loc,
            temp_c=0.0,
            feels_like_c=0.0,
            humidity_pct=0,
            wind_speed_kmh=0.0,
            is_success=False,
            error_message="Lookup failed",
        )
        self.cm.set(failed_w)
        self.assertIsNone(self.cm.get("ErrorCity"))

    def test_clear_cache(self):
        w = self._make_dummy_weather("Shanghai", 25.0)
        self.cm.set(w)
        self.assertTrue(self.cache_file.exists())
        self.cm.clear()
        self.assertFalse(self.cache_file.exists())
        self.assertIsNone(self.cm.get("Shanghai"))

    def test_stats(self):
        self.assertEqual(self.cm.get_stats()["entries"], 0)
        w = self._make_dummy_weather("Guilin", 24.0)
        self.cm.set(w)
        stats = self.cm.get_stats()
        self.assertEqual(stats["entries"], 1)
        self.assertGreater(stats["size_bytes"], 0)

    def test_concurrent_multithreaded_writes(self):
        import threading
        errors = []

        def worker(i):
            try:
                w = self._make_dummy_weather(f"City{i}", 20.0 + i)
                self.cm.set(w, lang="zh")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent write errors: {errors}")
        stats = self.cm.get_stats()
        self.assertEqual(stats["entries"], 20)
        for i in range(20):
            cached = self.cm.get(f"City{i}", lang="zh")
            self.assertIsNotNone(cached, f"City{i} missing from cache")
            self.assertEqual(cached.temp_c, 20.0 + i)

if __name__ == "__main__":
    unittest.main()
