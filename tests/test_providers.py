#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.models import ResolvedLocation, get_wmo_condition
from cli_weather.providers.open_meteo_provider import OpenMeteoProvider, deg_to_compass
from cli_weather.providers.met_no_provider import MetNoProvider
from cli_weather.providers.wttr_provider import WttrProvider, translate_wttr_condition
from cli_weather.providers.agentic_search_provider import AgenticSearchProvider

class TestProviders(unittest.TestCase):
    def test_wmo_condition_day_night(self):
        day_cond = get_wmo_condition(0, lang="zh", is_day=1)
        self.assertEqual(day_cond["icon"], "☀️")
        self.assertEqual(day_cond["text"], "晴朗")

        night_cond = get_wmo_condition(0, lang="zh", is_day=0)
        self.assertEqual(night_cond["icon"], "🌙")
        self.assertEqual(night_cond["text"], "晴朗")

    def test_deg_to_compass(self):
        self.assertEqual(deg_to_compass(0, lang="zh"), "北风")
        self.assertEqual(deg_to_compass(90, lang="zh"), "东风")
        self.assertEqual(deg_to_compass(180, lang="zh"), "南风")
        self.assertEqual(deg_to_compass(270, lang="zh"), "西风")
        self.assertEqual(deg_to_compass(0, lang="en"), "N")
        self.assertEqual(deg_to_compass(180, lang="en"), "S")
        self.assertEqual(deg_to_compass(None), "")

    def test_translate_wttr_condition(self):
        zh, icon = translate_wttr_condition("Light rain shower", lang="zh")
        self.assertEqual(zh, "小阵雨")
        self.assertEqual(icon, "🌦️")

        zh, icon = translate_wttr_condition("Sunny", lang="zh")
        self.assertEqual(zh, "晴朗")
        self.assertEqual(icon, "☀️")

        zh, icon = translate_wttr_condition("Thundery outbreaks possible", lang="zh")
        self.assertEqual(zh, "雷阵雨可能")
        self.assertEqual(icon, "⛈️")

    def test_provider_zero_coords_return_none(self):
        loc = ResolvedLocation("Zero", "Zero", "Zero", "Zero", "", "", 0.0, 0.0)
        open_meteo = OpenMeteoProvider()
        self.assertIsNone(open_meteo.fetch(loc))

        met_no = MetNoProvider()
        self.assertIsNone(met_no.fetch(loc))

    def test_agentic_search_parsing(self):
        sp = AgenticSearchProvider()
        temp = sp._extract_temperature("Current temperature is 24.5 °C today")
        self.assertEqual(temp, 24.5)

        temp_f = sp._extract_temperature("Weather is 77 °F in the afternoon")
        self.assertEqual(temp_f, 25.0)

    def test_providers_package_exports(self):
        from cli_weather import providers
        self.assertIn("MetNoProvider", providers.__all__)
        self.assertIn("OpenMeteoProvider", providers.__all__)
        self.assertIn("WttrProvider", providers.__all__)
        self.assertIn("AgenticSearchProvider", providers.__all__)
        self.assertIn("BaseWeatherProvider", providers.__all__)

    def test_wttr_special_moon_parsing(self):
        wp = WttrProvider()
        loc = ResolvedLocation("Moon", "Moon", "月相", "Moon Phase", "", "", 0.0, 0.0, is_special=True)
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = b'{"weather": [{"astronomy": [{"moon_phase": "Waning Crescent", "moon_illumination": "31"}]}]}'
        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = wp._fetch_special("Moon", loc)
            self.assertTrue(res.is_success)
            self.assertIn("残月", res.condition.text)
            self.assertEqual(res.condition.icon, "🌘")

    def test_open_meteo_handles_errors_and_malformed_responses(self):
        op = OpenMeteoProvider()
        loc = ResolvedLocation("Tokyo", "Tokyo", "东京", "Tokyo", "JP", "JP", 35.68, 139.69)

        # 1. Network / URL error
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            self.assertIsNone(op.fetch(loc))

        # 2. Invalid JSON response
        mock_resp_bad_json = MagicMock()
        mock_resp_bad_json.__enter__.return_value = mock_resp_bad_json
        mock_resp_bad_json.read.return_value = b"<html>502 Bad Gateway</html>"
        with patch("urllib.request.urlopen", return_value=mock_resp_bad_json):
            self.assertIsNone(op.fetch(loc))

        # 3. Error response payload without current
        mock_resp_err = MagicMock()
        mock_resp_err.__enter__.return_value = mock_resp_err
        mock_resp_err.read.return_value = b'{"error": true, "reason": "Rate limited"}'
        with patch("urllib.request.urlopen", return_value=mock_resp_err):
            self.assertIsNone(op.fetch(loc))

        # 4. Incomplete current block missing temperature
        mock_resp_no_temp = MagicMock()
        mock_resp_no_temp.__enter__.return_value = mock_resp_no_temp
        mock_resp_no_temp.read.return_value = b'{"current": {"weather_code": 0}}'
        with patch("urllib.request.urlopen", return_value=mock_resp_no_temp):
            self.assertIsNone(op.fetch(loc))

if __name__ == "__main__":
    unittest.main()
