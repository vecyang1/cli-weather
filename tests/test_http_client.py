#!/usr/bin/env python3
"""
test_http_client.py - Unit tests for resilient http_client.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error

from cli_weather.http_client import safe_urlopen


class TestHttpClient(unittest.TestCase):
    """Test safe_urlopen proxy-aware logic and fallbacks."""

    @patch("urllib.request.build_opener")
    def test_direct_connection_by_default(self, mock_build_opener):
        # Ensure no proxy env vars
        env = {k: v for k, v in os.environ.items() if not k.lower().endswith("proxy")}
        with patch.dict(os.environ, env, clear=True):
            mock_opener = MagicMock()
            mock_build_opener.return_value = mock_opener
            mock_opener.open.return_value = MagicMock()

            req = urllib.request.Request("https://api.open-meteo.com")
            safe_urlopen(req, timeout=3.0)

            mock_build_opener.assert_called_once()
            mock_opener.open.assert_called_once_with(req, timeout=3.0)

    @patch("urllib.request.urlopen")
    @patch("urllib.request.build_opener")
    def test_direct_fallback_to_system_on_failure(self, mock_build_opener, mock_urlopen):
        env = {k: v for k, v in os.environ.items() if not k.lower().endswith("proxy")}
        with patch.dict(os.environ, env, clear=True):
            mock_opener = MagicMock()
            mock_opener.open.side_effect = urllib.error.URLError("Connection refused")
            mock_build_opener.return_value = mock_opener
            mock_urlopen.return_value = MagicMock()

            req = urllib.request.Request("https://api.open-meteo.com")
            safe_urlopen(req, timeout=3.0, honor_mock=False)

            mock_opener.open.assert_called_once()
            mock_urlopen.assert_called_once_with(req, timeout=3.0)

    @patch("urllib.request.urlopen")
    def test_explicit_proxy_honored(self, mock_urlopen):
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://127.0.0.1:8888"}):
            mock_urlopen.return_value = MagicMock()
            req = urllib.request.Request("https://api.open-meteo.com")
            safe_urlopen(req, timeout=3.0)

            mock_urlopen.assert_called_once_with(req, timeout=3.0)


if __name__ == "__main__":
    unittest.main()
