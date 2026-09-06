# Configuration Guide

`cli-weather` supports flexible configuration via configuration files, environment variables, and command-line flags.

## Priority Order (Highest to Lowest)
1. Command-line flags (`--units imperial`, `--provider met-no`, etc.)
2. Environment variables (`CLI_WEATHER_UNITS`, `CLI_WEATHER_PROVIDER`, etc.)
3. Configuration files (`~/.config/cli-weather/config.json` or `config.toml`)
4. Built-in defaults (metric units, Chinese language, 20-minute cache TTL)

## Initializing Configuration
```bash
cli-weather --init-config
```
This generates `~/.config/cli-weather/config.json`:
```json
{
  "default_cities": [
    "Foshan",
    "Chiang Mai",
    "Da Nang",
    "Shanghai",
    "Dali",
    "Guilin",
    "Tokyo"
  ],
  "units": "metric",
  "lang": "zh",
  "provider": "auto",
  "cache_ttl": 1200,
  "format": "auto",
  "cache_dir": null
}
```

## Environment Variables
- `CLI_WEATHER_CONFIG`: Custom path to configuration file.
- `CLI_WEATHER_DEFAULT_CITIES`: Comma-separated list of default cities.
- `CLI_WEATHER_UNITS`: `metric` or `imperial`.
- `CLI_WEATHER_LANG`: `zh`, `en`, `ja`, etc.
- `CLI_WEATHER_PROVIDER`: `auto`, `open-meteo`, `met-no`, `wttr`, `search`.
- `CLI_WEATHER_CACHE_TTL`: Cache expiration in seconds.
- `CLI_WEATHER_CACHE_DIR`: Custom cache directory.
