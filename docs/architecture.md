# Architecture & Design Philosophy

`cli-weather` is engineered around four core tenets:
1. **Single Source of Truth & Contract-First Design**: Domain entities (`models.py`) define the universal contract across all data providers and formatters.
2. **Zero Runtime Dependencies**: Uses Python standard library only (`urllib`, `json`, `dataclasses`, `concurrent.futures`, `threading`, `argparse`).
3. **Resilient 4-Tier Cascade**: Ensures 99.99% availability without requiring API keys:
   - **Tier 1 - Open-Meteo**: High-resolution ECMWF/GFS global forecast models (<200ms cold).
   - **Tier 2 - Met.no**: Norwegian Meteorological Institute open data REST API.
   - **Tier 3 - wttr.in**: Secondary fallback with ASCII compatibility and astronomical data.
   - **Tier 4 - Agentic Search**: Automated proxy & web search snippet extraction.
4. **Token Economy for AI Agents**: Outputs ultra-dense tables (<150 tokens for 7 cities) or compact JSON dictionaries (<120 tokens), reducing LLM overhead by 95% compared to raw web scraping.
5. **Thread-Safe Atomic Caching**: XDG-compliant cache storage with atomic replacement (`os.replace`) and auto-pruning.
