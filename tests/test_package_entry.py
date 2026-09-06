#!/usr/bin/env python3
import unittest
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC_DIR = REPO_ROOT / "src"
BIN_DIR = REPO_ROOT / "bin"

class TestPackageEntry(unittest.TestCase):
    def test_import_cli_weather(self):
        sys.path.insert(0, str(SRC_DIR))
        import cli_weather
        self.assertIsNotNone(cli_weather.__version__)
        self.assertIn("WeatherEngine", cli_weather.__all__)
        self.assertIn("WeatherConfig", cli_weather.__all__)
        self.assertIn("CityWeather", cli_weather.__all__)

    def test_bin_weather_executable(self):
        weather_bin = BIN_DIR / "weather"
        self.assertTrue(weather_bin.is_file())
        res = subprocess.run([str(weather_bin), "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("cli-weather", res.stdout)

    def test_bin_cli_weather_executable(self):
        cli_weather_bin = BIN_DIR / "cli-weather"
        self.assertTrue(cli_weather_bin.is_file())
        res = subprocess.run([str(cli_weather_bin), "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("cli-weather", res.stdout)

    def test_python_m_cli_weather(self):
        res = subprocess.run(
            [sys.executable, "-m", "cli_weather", "--version"],
            cwd=str(REPO_ROOT),
            env={"PYTHONPATH": str(SRC_DIR)},
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("cli-weather", res.stdout)

if __name__ == "__main__":
    unittest.main()
