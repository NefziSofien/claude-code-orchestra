# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - Unreleased

### Added
- Orchestrate skill: Resume step (reads `.orchestra/state.md` first), cost guard before each wave, Agent Teams row in the vehicle table (experimental, opt-in), guidance on native worktrees, and a `Wave:` line in `state.md`.
- `tests/`: stdlib `unittest` suite (installer, permissions merge, usage report, state validator).
- `.github/workflows/ci.yml`: tests on Linux, macOS and Windows, shellcheck, PSScriptAnalyzer.
- `tools/orchestra-validate.py`: validator for `.orchestra/state.md`.
- `hooks/`: `subagent-report-check.py` (report format) and `scope-guard.py` (file scope), with a README.
- `CONTRIBUTING.md`, issue templates and this changelog.

- Orchestrate skill: in the desktop app, parallel writers start as visible sessions (sidebar) instead of hidden subagents.
- `benchmarks/fixtures/` and `benchmarks/checks/`: task fixtures and pass checks (harness still pending).

### Fixed
- shellcheck and PSScriptAnalyzer findings in `install.sh` and `install.ps1`.

### Changed
- `tools/usage-report.py` split into functions so it can be tested.

### Coming
- Plugin packaging (`.claude-plugin`).
- `benchmarks/` (harness on a branch, no results yet).

## [0.1.0]

### Added
- Initial orchestration setup for Claude Code and Cursor: `orchestrate` skill, `explorer`, `implementer` and `verifier` agents, Cursor rule and agents, project skill examples, installers for bash and PowerShell.
- lean-ctx setup (locked-down shell permissions) and `tools/usage-report.py` token and model usage report.
- `docs/token-and-model-optimization.md`.
