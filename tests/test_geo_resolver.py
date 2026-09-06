#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.geo_resolver import GeoResolver, normalize_query_key

class TestGeoResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = GeoResolver()

    def test_normalize_query_key(self):
        self.assertEqual(normalize_query_key("  Chiang-Mai  "), "chiang mai")
        self.assertEqual(normalize_query_key("FO_SHAN"), "fo shan")
        self.assertEqual(normalize_query_key("Da+Nang"), "da nang")

    def test_preseeded_core_cities(self):
        core_cases = [
            ("Foshan", "佛山", 23.0215, 113.1214),
            ("Chiang Mai", "清迈", 18.7904, 98.9847),
            ("Da Nang", "岘港", 16.0544, 108.2022),
            ("Shanghai", "上海", 31.2304, 121.4737),
            ("Dali", "大理", 25.5847, 100.2123),
            ("Guilin", "桂林", 25.2736, 110.2902),
            ("Tokyo", "东京", 35.6895, 139.6917),
        ]
        for name, exp_zh, lat, lon in core_cases:
            loc = self.resolver.resolve(name)
            self.assertEqual(loc.display_name_zh, exp_zh)
            self.assertAlmostEqual(loc.lat, lat, places=3)
            self.assertAlmostEqual(loc.lon, lon, places=3)

    def test_damerau_levenshtein_distance(self):
        from cli_weather.geo_resolver import damerau_levenshtein_distance
        self.assertEqual(damerau_levenshtein_distance("tokyo", "tokyo"), 0)
        self.assertEqual(damerau_levenshtein_distance("tokyoo", "tokyo"), 1)  # insertion
        self.assertEqual(damerau_levenshtein_distance("toky", "tokyo"), 1)   # deletion
        self.assertEqual(damerau_levenshtein_distance("tokya", "tokyo"), 1)  # substitution
        self.assertEqual(damerau_levenshtein_distance("shnaghai", "shanghai"), 1)  # transposition
        self.assertEqual(damerau_levenshtein_distance("fosahn", "foshan"), 1)      # transposition

    def test_typo_and_alias_tolerance(self):
        self.assertEqual(self.resolver.resolve("Chiangamai").canonical_name, "Chiang Mai")
        self.assertEqual(self.resolver.resolve("chiangmai").canonical_name, "Chiang Mai")
        self.assertEqual(self.resolver.resolve("chiangmai1").canonical_name, "Chiang Mai")
        self.assertEqual(self.resolver.resolve("Danang").canonical_name, "Da Nang")
        self.assertEqual(self.resolver.resolve("da nang").canonical_name, "Da Nang")
        self.assertEqual(self.resolver.resolve("大理").canonical_name, "Dali")
        self.assertEqual(self.resolver.resolve("dalli").canonical_name, "Dali")
        self.assertEqual(self.resolver.resolve("桂林").canonical_name, "Guilin")
        self.assertEqual(self.resolver.resolve("清迈").canonical_name, "Chiang Mai")
        self.assertEqual(self.resolver.resolve("岘港").canonical_name, "Da Nang")
        self.assertEqual(self.resolver.resolve("Tokyoo").canonical_name, "Tokyo")
        self.assertEqual(self.resolver.resolve("Shnaghai").canonical_name, "Shanghai")
        self.assertEqual(self.resolver.resolve("Fosahn").canonical_name, "Foshan")
        self.assertEqual(self.resolver.resolve("Beijng").canonical_name, "Beijing")
        self.assertEqual(self.resolver.resolve("Los Angeles").canonical_name, "Los Angeles")
        self.assertEqual(self.resolver.resolve("San Francisco").canonical_name, "San Francisco")

    def test_airport_iata_codes(self):
        self.assertEqual(self.resolver.resolve("cnx").canonical_name, "Chiang Mai")
        self.assertEqual(self.resolver.resolve("dad").canonical_name, "Da Nang")
        self.assertEqual(self.resolver.resolve("pvg").canonical_name, "Shanghai")
        self.assertEqual(self.resolver.resolve("sha").canonical_name, "Shanghai")
        self.assertEqual(self.resolver.resolve("hnd").canonical_name, "Tokyo")
        self.assertEqual(self.resolver.resolve("nrt").canonical_name, "Tokyo")
        self.assertEqual(self.resolver.resolve("kwl").canonical_name, "Guilin")
        self.assertEqual(self.resolver.resolve("can").canonical_name, "Guangzhou")

    def test_special_entities(self):
        moon = self.resolver.resolve("Moon")
        self.assertTrue(moon.is_special)
        self.assertEqual(moon.canonical_name, "Moon")

        empty = self.resolver.resolve("")
        self.assertTrue(empty.is_special)

if __name__ == "__main__":
    unittest.main()
