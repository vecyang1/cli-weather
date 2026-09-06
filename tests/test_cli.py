#!/usr/bin/env python3
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli_weather.cli import parse_location_arguments, parse_args

class TestCLI(unittest.TestCase):
    def test_parse_location_arguments_unquoted_multiword(self):
        res = parse_location_arguments(["Chiang", "Mai"])
        self.assertEqual(res, ["Chiang Mai"])

        res_ny = parse_location_arguments(["New", "York"])
        self.assertEqual(res_ny, ["New York"])

        res_dn = parse_location_arguments(["Da", "Nang"])
        self.assertEqual(res_dn, ["Da Nang"])

    def test_parse_location_arguments_mixed_multiple(self):
        res = parse_location_arguments(["Foshan", "Chiang", "Mai", "Tokyo"])
        self.assertEqual(res, ["Foshan", "Chiang Mai", "Tokyo"])

    def test_parse_location_arguments_cities_flag(self):
        res = parse_location_arguments([], cities_arg="Foshan, Chiang Mai, Da Nang, Tokyo")
        self.assertEqual(res, ["Foshan", "Chiang Mai", "Da Nang", "Tokyo"])

    def test_parse_location_arguments_comma_in_positional(self):
        res = parse_location_arguments(["Foshan,Chiang Mai,Tokyo"])
        self.assertEqual(res, ["Foshan", "Chiang Mai", "Tokyo"])

    def test_parse_location_arguments_default_cities(self):
        res = parse_location_arguments([], default_cities=["Paris", "Berlin"])
        self.assertEqual(res, ["Paris", "Berlin"])

    def test_parse_location_arguments_special(self):
        res = parse_location_arguments(["~Eiffel Tower"])
        self.assertEqual(res, ["~Eiffel Tower"])

        res_moon = parse_location_arguments(["Moon"])
        self.assertEqual(res_moon, ["Moon"])

    def test_provider_choices_include_met_no(self):
        with patch("sys.argv", ["cli-weather", "Tokyo", "--provider", "met-no"]):
            args = parse_args()
            self.assertEqual(args.provider, "met-no")

    def test_units_flag(self):
        with patch("sys.argv", ["cli-weather", "Tokyo", "--units", "imperial"]):
            args = parse_args()
            self.assertEqual(args.units, "imperial")

    def test_format_flags(self):
        with patch("sys.argv", ["cli-weather", "Tokyo", "-f", "ascii"]):
            args = parse_args()
            self.assertEqual(args.format, "ascii")

if __name__ == "__main__":
    unittest.main()
