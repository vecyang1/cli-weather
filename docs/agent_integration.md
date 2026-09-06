# AI Agent Integration Guide

`cli-weather` is designed as a foundational tool for autonomous coding agents, cadences, and cron tasks.

## Why Agents Should Use `cli-weather`
- **Token Efficiency**: Consumes <120 tokens for 7 cities in `--json` mode versus 5,000~25,000 tokens for raw web search or scraping.
- **Deterministic Disambiguation**: Handles ambiguous queries (e.g. Dali in Yunnan vs Dali in Cyprus) via preseeded coordinates and alias tables.
- **Zero Hallucination**: Strict type contracts and ground-truth meteorological data.

## Recommended Invocations

### Cadence Table Summary:
```bash
weather "Foshan" "Chiang Mai" "Da Nang" "Shanghai" "Dali" "Guilin" "Tokyo" --lang zh
```

### JSON Ingestion for Pipeline Reasoning:
```bash
weather "Tokyo" "Shanghai" --json
```
Output:
```json
[{"city":"东京","weather":"🌧️ 密集毛毛雨","temp":"20~22℃","feels":"22℃","hum":"93%","wind":"西北偏北风 7km/h","precip":"100%","uv":0.7},{"city":"上海","weather":"☀️ 晴朗","temp":"24~29℃","feels":"31℃","hum":"64%","wind":"东北偏北风 12km/h","precip":"78%","uv":5.8}]
```

### Natural Language Daily Briefing:
```bash
weather --cities "Tokyo,Kyoto,Osaka" --brief --lang en
```
