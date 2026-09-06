# Project Links

> Scope: project-local — this file governs only this project root. Cross-project truth lives in the 2nd Brain vault: /Users/vecsatfoxmailcom/Documents/Cowork/Antigravity Cowork/26.06.06 2nd Brain (contract: 00 - System/contracts/project-link-bridge.md).

This file is the project-local bridge card. It keeps roots findable without copying another root's source of truth.

## Control Card

| Field | Value |
|---|---|
| Project ID | `a_coding-26-09-06-cli-weather-362d8878` |
| Project Name | CLI Weather (Standalone Production Engine & CLI) |
| Canonical Hub | `/Users/vecsatfoxmailcom/Documents/A-coding/26.09.06-cli-weather` |
| Code Root | `/Users/vecsatfoxmailcom/Documents/A-coding/26.09.06-cli-weather` |
| 2nd Brain Router | `/Users/vecsatfoxmailcom/Documents/Cowork/Antigravity Cowork/26.06.06 2nd Brain/00 - System/registries/project-index.md` |
| Live URL | `https://github.com/vecyang1/cli-weather` |
| Deploy Owner | GitHub Releases / PyPI / Local Symlink |
| Decision Owner | `decisions.md` (Technical architecture) |
| Current Next Gate | Public GitHub release and 2nd Brain capability registration |
| Init Gate | `PYTHONPATH=src python3 -m unittest discover -s tests` |
| Operation Gate | `./bin/weather --version` |
| QA Gate | `PYTHONPATH=src python3 -m unittest discover -s tests` |
| Do Not Edit Here | Cross-project routing tables; edit in 2nd Brain registries |
| Last Verified | 2026-09-06 |

## Ownership

Truth ownership is one-way. Navigation is two-way.

- Hub root (`/Users/vecsatfoxmailcom/Documents/A-coding/26.09.06-cli-weather`) owns source code, tests, packaging, documentation, and technical execution.
- Skill (`~/.gemini/antigravity/skills/cli-weather`) is a thin pointer / consumer of this engine.
- 2nd Brain owns stable memory, capabilities, and router context only.

## Safety

Do not store secrets, customer records, private health URLs, provider credentials, or raw API keys in this file.
