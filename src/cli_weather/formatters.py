#!/usr/bin/env python3
"""
formatters.py - Output formatting and token optimization for cli-weather.
Produces ultra-compact Markdown tables (<150 tokens for 7 cities), compact JSON,
one-line summaries, and natural language briefings.
Supports both metric (℃, km/h) and imperial (℉, mph) units.
"""

import json
from typing import List, Dict, Any
from pathlib import Path
import sys

try:
    from .models import CityWeather
except (ImportError, ValueError):
    try:
        from cli_weather.models import CityWeather
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from models import CityWeather


def format_table(cities: List[CityWeather], lang: str = "zh", units: str = "metric") -> str:
    """
    Format a list of CityWeather into an ultra-compact Markdown table.
    Designed for maximum readability and minimal LLM token consumption.
    """
    if not cities:
        return "无天气数据。" if lang == "zh" else "No weather data available."

    is_imp = (units == "imperial")
    temp_unit_label = "℉" if is_imp else "℃"

    if lang == "zh":
        headers = ["城市", "天气", f"气温({temp_unit_label})", f"体感({temp_unit_label})", "湿度", "风况", "降水概率", "紫外线"]
        sep = [":---", ":---", ":---", ":---", ":---", ":---", ":---", ":---"]
    else:
        headers = ["City", "Condition", f"Temp({temp_unit_label})", f"Feels({temp_unit_label})", "Humidity", "Wind", "Precip Prob", "UV"]
        sep = [":---", ":---", ":---", ":---", ":---", ":---", ":---", ":---"]

    rows = []
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(sep) + " |")

    for w in cities:
        if not w.is_success:
            city_name = w.query
            err = w.error_message or ("查询失败" if lang == "zh" else "Failed")
            rows.append(f"| {city_name} | ❌ {err} | - | - | - | - | - | - |")
            continue

        city_name = w.city_label_zh if lang == "zh" else w.city_label_en
        if w.location.country_code:
            city_label = f"{city_name} ({w.location.country_code})"
        else:
            city_label = city_name

        cond_str = f"{w.condition.icon} {w.condition.text}"

        # Special handling for Moon / non-terrestrial entities
        if w.location.is_special or w.location.canonical_name.lower() == "moon":
            rows.append(f"| {city_label} | {cond_str} | - | - | - | - | - | - |")
            continue

        temp_str = w.temp_range_formatted(units=units)
        feels_val = round(w.feels_like_f if is_imp else w.feels_like_c)
        feels_str = f"{feels_val}"
        hum_str = f"{w.humidity_pct}%"

        wind_speed_val = round(w.wind_speed_mph if is_imp else w.wind_speed_kmh)
        wind_unit = "mph" if is_imp else "km/h"
        wind_parts = []
        if w.wind_dir_compass:
            wind_parts.append(w.wind_dir_compass)
        wind_parts.append(f"{wind_speed_val}{wind_unit}")
        wind_str = " ".join(wind_parts)

        if w.precip_prob_pct is not None:
            precip_str = f"{w.precip_prob_pct}%"
        elif w.precip_mm is not None and w.precip_mm > 0:
            if is_imp:
                precip_in = round(w.precip_mm * 0.0393701, 2)
                precip_str = f"{precip_in}in"
            else:
                precip_str = f"{w.precip_mm}mm"
        else:
            precip_str = "无" if lang == "zh" else "None"

        if w.uv_index is not None:
            uv_val = round(w.uv_index, 1)
            if lang == "zh":
                if uv_val >= 11:
                    uv_str = f"{uv_val} (极强)"
                elif uv_val >= 8:
                    uv_str = f"{uv_val} (很强)"
                elif uv_val >= 6:
                    uv_str = f"{uv_val} (强)"
                elif uv_val >= 3:
                    uv_str = f"{uv_val} (中等)"
                else:
                    uv_str = f"{uv_val} (弱)"
            else:
                uv_str = f"{uv_val}"
        else:
            uv_str = "-"

        row = f"| {city_label} | {cond_str} | {temp_str} | {feels_str} | {hum_str} | {wind_str} | {precip_str} | {uv_str} |"
        rows.append(row)

    return "\n".join(rows)


def format_json(cities: List[CityWeather], compact: bool = True, lang: str = "zh", units: str = "metric") -> str:
    """Format list of CityWeather as JSON."""
    if compact:
        data = [c.to_compact_dict(lang=lang, units=units) for c in cities]
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        data = []
        for c in cities:
            d = c.to_compact_dict(lang=lang, units=units)
            d["provider"] = c.provider
            d["fetched_at"] = c.fetched_at
            data.append(d)
        return json.dumps(data, ensure_ascii=False, indent=2)


def format_oneline(cities: List[CityWeather], lang: str = "zh", units: str = "metric") -> str:
    """Format list of CityWeather as one-line strings per city or joined."""
    lines = []
    is_imp = (units == "imperial")
    temp_unit = "℉" if is_imp else "℃"

    for w in cities:
        if not w.is_success:
            lines.append(f"{w.query}: ❌ {w.error_message or 'Error'}")
            continue
        city_name = w.city_label_zh if lang == "zh" else w.city_label_en
        if w.location.is_special or w.location.canonical_name.lower() == "moon":
            lines.append(f"{city_name}: {w.condition.icon} {w.condition.text}")
            continue

        feels_val = round(w.feels_like_f if is_imp else w.feels_like_c)
        temp_str = w.temp_range_formatted(units=units)
        uv_extra = f", UV {round(w.uv_index, 1)}" if w.uv_index is not None else ""

        line = (
            f"{city_name}: {w.condition.icon} {w.condition.text} {temp_str} "
            f"(体感 {feels_val}{temp_unit}, 湿度 {w.humidity_pct}%{uv_extra})"
            if lang == "zh" else
            f"{city_name}: {w.condition.icon} {w.condition.text} {temp_str} "
            f"(Feels {feels_val}{temp_unit}, Humidity {w.humidity_pct}%{uv_extra})"
        )
        lines.append(line)
    return "\n".join(lines)


def format_brief_natural(cities: List[CityWeather], lang: str = "zh", units: str = "metric") -> str:
    """Format a compact natural language summary report."""
    if lang == "zh":
        parts = ["【今日多城天气速报】\n"]
        parts.append(format_table(cities, lang="zh", units=units))
        parts.append("\n💡 提示：")
        rain_cities = [c.city_label_zh for c in cities if c.is_success and not c.location.is_special and ((c.precip_prob_pct or 0) >= 40 or (c.precip_mm or 0) > 1.0 or "雨" in c.condition.text)]
        hot_cities = [c.city_label_zh for c in cities if c.is_success and not c.location.is_special and (c.temp_c >= 33 or (c.temp_max_c or 0) >= 33)]
        cold_cities = [c.city_label_zh for c in cities if c.is_success and not c.location.is_special and (c.temp_c <= 15 or (c.temp_min_c or 0) <= 15)]
        uv_cities = [f"{c.city_label_zh}(UV {round(c.uv_index, 1)})" for c in cities if c.is_success and not c.location.is_special and (c.uv_index or 0) >= 8]

        tips = []
        if rain_cities:
            tips.append(f"- 携带雨具：{'、'.join(rain_cities)}有降水或阵雨概率较高。")
        if uv_cities:
            tips.append(f"- 紫外线强：{'、'.join(uv_cities)}紫外线偏强，建议做好遮阳防晒与防紫外线保护。")
        if hot_cities:
            tips.append(f"- 防暑降温：{'、'.join(hot_cities)}气温较高，注意补水遮阳。")
        if cold_cities:
            tips.append(f"- 注意保暖：{'、'.join(cold_cities)}早晚温差较大或气温较低。")
        if not tips:
            tips.append("- 各城市天气整体平稳，适宜出行。")
        parts.extend(tips)
        return "\n".join(parts)
    else:
        parts = ["【Daily Weather Summary】\n"]
        parts.append(format_table(cities, lang="en", units=units))
        parts.append("\n💡 Tips:")
        rain_cities = [c.city_label_en for c in cities if c.is_success and not c.location.is_special and ((c.precip_prob_pct or 0) >= 40 or (c.precip_mm or 0) > 1.0 or any(w in c.condition.text.lower() for w in ["rain", "shower", "drizzle", "thunder"]))]
        hot_cities = [c.city_label_en for c in cities if c.is_success and not c.location.is_special and (c.temp_c >= 33 or (c.temp_max_c or 0) >= 33)]
        cold_cities = [c.city_label_en for c in cities if c.is_success and not c.location.is_special and (c.temp_c <= 15 or (c.temp_min_c or 0) <= 15)]
        uv_cities = [f"{c.city_label_en} (UV {round(c.uv_index, 1)})" for c in cities if c.is_success and not c.location.is_special and (c.uv_index or 0) >= 8]

        tips = []
        if rain_cities:
            tips.append(f"- Rain gear: High probability of precipitation/showers in {', '.join(rain_cities)}.")
        if uv_cities:
            tips.append(f"- High UV: Strong UV index in {', '.join(uv_cities)}. Sunscreen & sunglasses recommended.")
        if hot_cities:
            tips.append(f"- Heat & hydration: High temperatures in {', '.join(hot_cities)}. Stay hydrated.")
        if cold_cities:
            tips.append(f"- Keep warm: Cooler temperatures in {', '.join(cold_cities)}.")
        if not tips:
            tips.append("- Mild weather conditions overall across all cities.")
        parts.extend(tips)
        return "\n".join(parts)
