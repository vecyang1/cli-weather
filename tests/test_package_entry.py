#!/usr/bin/env python3
import unittest
import subprocess
import sys
import os
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
        cmd = [sys.executable, str(weather_bin), "--version"] if sys.platform == "win32" else [str(weather_bin), "--version"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("cli-weather", res.stdout)

    def test_bin_cli_weather_executable(self):
        cli_weather_bin = BIN_DIR / "cli-weather"
        self.assertTrue(cli_weather_bin.is_file())
        cmd = [sys.executable, str(cli_weather_bin), "--version"] if sys.platform == "win32" else [str(cli_weather_bin), "--version"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("cli-weather", res.stdout)

    def test_python_m_cli_weather(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_DIR) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
        res = subprocess.run(
            [sys.executable, "-m", "cli_weather", "--version"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("cli-weather", res.stdout)

    def test_base_provider_standalone_execution(self):
        base_prov = SRC_DIR / "cli_weather" / "providers" / "base_provider.py"
        res = subprocess.run([sys.executable, str(base_prov)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"base_provider.py failed standalone execution: {res.stderr}")

if __name__ == "__main__":
    unittest.main()
