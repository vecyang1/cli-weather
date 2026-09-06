# PROJECT VAULT - 26.09.06-cli-weather

> Scope: project-local — this file governs only this project root. Cross-project truth lives in the 2nd Brain vault: /Users/vecsatfoxmailcom/Documents/Cowork/Antigravity Cowork/26.06.06 2nd Brain (contract: 00 - System/contracts/project-link-bridge.md).

> Current-state router. Read `AGENTS.md` first for operating rules, then use
> this file to find the active owner docs.

## Snapshot

- Project: 26.09.06-cli-weather
- Summary: Production-grade, ultra-compact terminal weather interface (<150 tokens) and Python package with multi-city concurrency, 4-tier provider cascade, atomic caching, and flexible configuration.
- Current phase: Production Standalone Package & GitHub Release
- Last updated: 2026-09-06 09:05 by Antigravity (pair programming worker)
- Health: GREEN
- Existing docs found before init: 0

## Current Goal

- North star: Standalone, zero-key, token-efficient open-source weather engine and CLI serving both human terminal users and automated AI agent cadences.
- Near-term outcome: Publish to GitHub (`vecyang1/cli-weather`), symlink to `~/.local/bin/weather`, register in 2nd Brain, and point the local skill directly to this package.
- Constraints: Pure standard library (zero external runtime dependencies), Apache-2.0 license, deterministic type contracts, thread-safe atomic caching.

## Source Pointers

| Truth Type | Owner |
| --- | --- |
| Project rules | `AGENTS.md` |
| Public/community start page | `README.md` |
| Multi-root bridge card | `PROJECT_LINKS.md` |
| System architecture and module map | `docs/architecture.md` |
| Configuration reference | `docs/configuration.md` |
| Agent integration guide | `docs/agent_integration.md` |
| Current state, source pointers, and risks | `VAULT.md` |
| Active/backlog tasks with Created/Updated dates | `task_plan.md` |
| Dated execution evidence | `progress.md` |
| Latest resume card | `handoff.md` |
| Durable decisions | `decisions.md` |
| Folder and document boundaries | `FILE_MAP_INDEX.md` |
| Runbooks and health checks | `operations/` |
| Cross-project router and reciprocal backlink | 2nd Brain project index at `/Users/vecsatfoxmailcom/Documents/Cowork/Antigravity Cowork/26.06.06 2nd Brain/00 - System/registries/project-index.md` |

## Current Risks

- `Minor Robustness Risk`: Public upstream APIs (Open-Meteo, Met.no, wttr.in) may throttle bursts exceeding 100 queries/minute. Mitigated by atomic 20-minute local caching and 4-tier provider cascade.
- `Minor Robustness Risk`: Python <3.11 without `tomllib` uses regex fallback parser which supports standard keys and arrays but not multi-level nested tables.

## Next Actions

- All deployment and integration milestones complete.
- Future enhancement: Optional PyPI publishing (`twine upload dist/*`) if pip distribution is desired.
