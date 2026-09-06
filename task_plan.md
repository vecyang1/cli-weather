# Task Plan

> Active and near-term work only. Keep this file small; archive old
> completed/dropped rows before it becomes a giant database.
> Every task row includes `Created` (first entered into this ledger) and
> `Updated` (last change to the row, status, or evidence), both as `YYYY-MM-DD`.

## Active

| ID | Status | Created | Updated | Task | Owner | Next Action | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T-001 | done | 2026-09-06 | 2026-09-06 | Scaffold standalone package repository & governance | Vec + Antigravity | Package structure established | `src/`, `tests/`, `bin/`, `VAULT.md` |
| T-002 | done | 2026-09-06 | 2026-09-06 | Implement configuration manager & imperial/metric units | Antigravity | Full tests passing | `src/cli_weather/config.py`, `tests/test_config.py`, `tests/test_units.py` |
| T-003 | done | 2026-09-06 | 2026-09-06 | Create executables & symlinks | Antigravity | Test `~/.local/bin/weather` and `cli-weather` | `~/.local/bin/weather`, `~/.local/bin/cli-weather` |
| T-004 | active | 2026-09-06 | 2026-09-06 | Publish repository to GitHub | Antigravity | Run `gh repo create vecyang1/cli-weather` | `https://github.com/vecyang1/cli-weather` |
| T-005 | planned | 2026-09-06 | 2026-09-06 | Connect skill & 2nd Brain registries | Antigravity | Single source of truth update & 2nd Brain audit | `project-index.md`, `project-capabilities.md`, `project-links.md` |

## Backlog

| ID | Priority | Created | Updated | Task | Why It Matters | Link |
| --- | --- | --- | --- | --- | --- | --- |
| T-006 | medium | 2026-09-06 | 2026-09-06 | Optional PyPI publishing | Enable `pip install cli-weather` globally | `pyproject.toml` |

## Rollover Rule

When this file reaches roughly 80-120 task rows or roughly 60 completed/dropped
rows, move older closed rows to `99 - Archive/task-ledger/YYYY-completed-tasks.md`
or the project's chosen archive owner, then leave a pointer here.
