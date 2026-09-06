# Decisions

> Scope: project-local — this file governs only this project root. Cross-project truth lives in the 2nd Brain vault: /Users/vecsatfoxmailcom/Documents/Cowork/Antigravity Cowork/26.06.06 2nd Brain (contract: 00 - System/contracts/project-link-bridge.md).

Use this file for durable choices, supersession, reversals, and rationale.
Keep execution proof in `progress.md` or `vault/sessions/`.

| ID | Date | Decision | Status | Rationale | Evidence | Supersedes |
| --- | --- | --- | --- | --- | --- | --- |
| D-001 | 2026-09-06 | Use V.A.U.L.T. owner-doc structure for project continuity | accepted | Future agents need one owner per truth type | `VAULT.md`, `FILE_MAP_INDEX.md` | - |
| D-002 | 2026-09-06 | Package cli-weather as a standalone zero-dependency library & CLI | accepted | Avoid snippet rot and code duplication; provide single source of truth across skill, CLI, and agents | `pyproject.toml`, `src/cli_weather/`, `tests/` | - |
| D-003 | 2026-09-06 | Release under Apache-2.0 License to public GitHub | accepted | Safe, permissive open source license enabling both agent and community reuse | `LICENSE`, `pyproject.toml` | - |
