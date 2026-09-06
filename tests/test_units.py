#!/usr/bin/env python3
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.models import (
    c_to_f,
    f_to_c,
    kmh_to_mph,
    CityWeather,
    ResolvedLocation,
    WeatherCondition,
)

class TestUnits(unittest.TestCase):
    def test_c_to_f_and_f_to_c(self):
        self.assertAlmostEqual(c_to_f(0.0), 32.0)
        self.assertAlmostEqual(c_to_f(100.0), 212.0)
        self.assertAlmostEqual(c_to_f(25.0), 77.0)
        self.assertAlmostEqual(f_to_c(32.0), 0.0)
        self.assertAlmostEqual(f_to_c(212.0), 100.0)
        self.assertAlmostEqual(f_to_c(77.0), 25.0)

    def test_kmh_to_mph(self):
        self.assertAlmostEqual(kmh_to_mph(100.0), 62.1371, places=3)
        self.assertAlmostEqual(kmh_to_mph(0.0), 0.0)

    def test_city_weather_imperial_properties(self):
        loc = ResolvedLocation("New York", "New York", "纽约", "New York", "US", "US", 40.7, -74.0)
        w = CityWeather(
            query="New York",
            location=loc,
            temp_c=25.0,
            feels_like_c=27.0,
            humidity_pct=50,
            wind_speed_kmh=16.0934,  # ~10 mph
            temp_min_c=20.0,
            temp_max_c=30.0,
            condition=WeatherCondition(0, "Clear", "☀️"),
        )
        self.assertAlmostEqual(w.temp_f, 77.0)
        self.assertAlmostEqual(w.feels_like_f, 80.6)
        self.assertAlmostEqual(w.wind_speed_mph, 10.0, places=1)
        self.assertEqual(w.temp_range_formatted(units="metric"), "20~30℃")
        self.assertEqual(w.temp_range_formatted(units="imperial"), "68~86℉")

    def test_to_compact_dict_imperial(self):
        loc = ResolvedLocation("Chicago", "Chicago", "芝加哥", "Chicago", "US", "US", 41.8, -87.6)
        w = CityWeather(
            query="Chicago",
            location=loc,
            temp_c=10.0,
            feels_like_c=8.0,
            humidity_pct=60,
            wind_speed_kmh=20.0,
            condition=WeatherCondition(0, "Sunny", "☀️"),
            uv_index=4.0,
        )
        d_imp = w.to_compact_dict(lang="en", units="imperial")
        self.assertIn("℉", d_imp["temp"])
        self.assertIn("℉", d_imp["feels"])
        self.assertIn("mph", d_imp["wind"])

if __name__ == "__main__":
    unittest.main()
