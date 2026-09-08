# Changelog - cli-weather

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-09-07

### Fixed
- **Windows Runner Compatibility**: Fixed package entry point test fixtures to support Windows environment variable retention and path separators in CI.
- **Cache Invalidation & Writeback**: Ensured cache updates reliably persist across all successful live weather provider queries.
- **Damerau-Levenshtein Typo Tolerance**: Added true Damerau-Levenshtein edit-distance matching in `geo_resolver.py` for preseeded cities.
- **Provider Error Fallback**: Hardened Open-Meteo response validator to reject malformed payload structures instead of defaulting to invalid 0°C clear-sky states, allowing clean cascade to Met.no.
- **Multi-Token Lookahead**: Fixed argument parser lookahead in `parse_location_arguments` to prevent unquoted adjacent city names from joining improperly.

## [2.0.0] - 2026-09-06

### Added
- **Standalone Zero-Dependency Architecture**:
  - Pure Python standard library implementation (`urllib`, `json`, `concurrent.futures`, `dataclasses`).
  - Ultra-compact LLM token footprint (<150 tokens table, <120 tokens JSON).
  - 4-Tier Zero-Key Provider Cascade: Open-Meteo → Met.no → wttr.in → Agentic Search.
- **Multi-City Concurrency**: Parallel asynchronous weather fetching across multiple global destinations simultaneously.
- **Dual Unit Formatting**: Seamless Metric (°C, km/h, mm) and Imperial (°F, mph, in) conversion and display.
- **Geographic Resolution**: Preseeded database of 120+ top global cities with Wikipedia and OpenStreetMap Nominatim fallbacks.
- **CLI & Packaging**:
  - Bin wrappers `weather` and `cli-weather` with symlink support.
  - Multi-platform CI pipeline across Python 3.9 through 3.14 on Linux, macOS, and Windows.
  - 59 automated test cases covering models, providers, caching, CLI arguments, and error cascades.
