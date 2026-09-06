#!/usr/bin/env python3
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.weather_engine import WeatherEngine
from cli_weather.models import CityWeather, ResolvedLocation, WeatherCondition

class TestWeatherEngine(unittest.TestCase):
    def setUp(self):
        self.engine = WeatherEngine()

    def _dummy_weather(self, city, temp=25.0):
        loc = ResolvedLocation(city, city, city, city, "CN", "CN", 23.0, 113.0)
        return CityWeather(
            query=city,
            location=loc,
            temp_c=temp,
            feels_like_c=temp,
            humidity_pct=60,
            wind_speed_kmh=10.0,
            condition=WeatherCondition(0, "晴朗", "☀️"),
            is_success=True,
        )

    def test_query_multiple_order_preservation(self):
        cities = ["Tokyo", "Foshan", "Da Nang", "Shanghai"]
        with patch.object(self.engine, "query_single") as mock_query:
            mock_query.side_effect = lambda query, **kwargs: self._dummy_weather(query)
            results = self.engine.query_multiple(cities)
            self.assertEqual(len(results), len(cities))
            for i, c in enumerate(cities):
                self.assertEqual(results[i].query, c)

    def test_fallback_cascade_tier1_to_tier2(self):
        loc = ResolvedLocation("TestCity", "TestCity", "测试", "TestCity", "CN", "CN", 25.0, 100.0)
        self.engine.geo_resolver.resolve = MagicMock(return_value=loc)
        self.engine.open_meteo.fetch = MagicMock(return_value=None)
        met_no_res = self._dummy_weather("TestCity", 20.0)
        met_no_res.provider = "met-no"
        self.engine.met_no.fetch = MagicMock(return_value=met_no_res)

        res = self.engine.query_single("TestCity", no_cache=True)
        self.assertEqual(res.provider, "met-no")
        self.assertEqual(res.temp_c, 20.0)

    def test_fallback_cascade_tier2_to_tier3(self):
        loc = ResolvedLocation("TestCity", "TestCity", "测试", "TestCity", "CN", "CN", 25.0, 100.0)
        self.engine.geo_resolver.resolve = MagicMock(return_value=loc)
        self.engine.open_meteo.fetch = MagicMock(return_value=None)
        self.engine.met_no.fetch = MagicMock(return_value=None)
        wttr_res = self._dummy_weather("TestCity", 22.0)
        wttr_res.provider = "wttr"
        self.engine.wttr.fetch = MagicMock(return_value=wttr_res)

        res = self.engine.query_single("TestCity", no_cache=True)
        self.assertEqual(res.provider, "wttr")
        self.assertEqual(res.temp_c, 22.0)

    def test_fallback_cascade_tier3_to_tier4(self):
        loc = ResolvedLocation("TestCity", "TestCity", "测试", "TestCity", "CN", "CN", 25.0, 100.0)
        self.engine.geo_resolver.resolve = MagicMock(return_value=loc)
        self.engine.open_meteo.fetch = MagicMock(return_value=None)
        self.engine.met_no.fetch = MagicMock(return_value=None)
        self.engine.wttr.fetch = MagicMock(return_value=None)
        search_res = self._dummy_weather("TestCity", 23.5)
        search_res.provider = "agentic-search"
        self.engine.agentic_search.fetch = MagicMock(return_value=search_res)

        res = self.engine.query_single("TestCity", no_cache=True)
        self.assertEqual(res.provider, "agentic-search")
        self.assertEqual(res.temp_c, 23.5)
        self.assertTrue(res.is_success)

    def test_all_providers_fail_gracefully(self):
        loc = ResolvedLocation("GhostCity", "GhostCity", "幽灵城", "GhostCity", "CN", "CN", 25.0, 100.0)
        self.engine.geo_resolver.resolve = MagicMock(return_value=loc)
        self.engine.open_meteo.fetch = MagicMock(return_value=None)
        self.engine.met_no.fetch = MagicMock(return_value=None)
        self.engine.wttr.fetch = MagicMock(return_value=None)
        self.engine.agentic_search.fetch = MagicMock(return_value=None)

        res = self.engine.query_single("GhostCity", no_cache=True)
        self.assertFalse(res.is_success)
        self.assertIn("All weather providers failed", res.error_message)

    def test_error_containment(self):
        cities = ["CityA", "FailCity", "CityC"]
        def mock_query(query=None, **kwargs):
            if query == "FailCity":
                raise RuntimeError("Catastrophic connection drop")
            return self._dummy_weather(query)

        with patch.object(self.engine, "query_single", side_effect=mock_query):
            results = self.engine.query_multiple(cities)
            self.assertEqual(len(results), 3)
            self.assertTrue(results[0].is_success)
            self.assertFalse(results[1].is_success)
            self.assertIn("Catastrophic connection drop", results[1].error_message)
            self.assertTrue(results[2].is_success)

if __name__ == "__main__":
    unittest.main()
