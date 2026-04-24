# Changelog

All notable changes to the Hybrid ABW Command Surface system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.5] - 2026-04-24

### Added
- Command behavior parity test suite for canonical CLI/slash pairs: doctor, version, ask, review, migrate.
- `abw self-check` diagnostic command to troubleshoot stale install/runtime path confusion.

### Changed
- Canonical CLI commands now route through canonical slash command handlers to keep behavior and output aligned.
- Installer guidance and README update flow now explicitly include `py -m pip install -U .` and git+repo update path.

### Fixed
- Resolved behavior drift between CLI and slash command outputs (exit behavior, key fields, workspace handling, and hints).
- Added stale-install hint in doctor/version flows: run `abw self-check`.

### Security / Trust
- No changes to proof, nonce, acceptance, finalization, rollback, router fallback, or trusted wiki promotion semantics.

## [0.2.4] - 2026-04-24

### Added
- `abw migrate` git hygiene diagnostics for branch, dirty file count, and migration-scope files.
- Adoption-safe migration guidance when unrelated dirty files exist in the workspace repository.

### Changed
- Migration report now includes explicit commit scope recommendation: `.gitignore` and `abw_config.json`.
- Migration output now surfaces unrelated dirty files to prevent accidental business-file commits.

### Fixed
- Reduced migration adoption friction in dirty repositories by making isolation guidance part of standard `abw migrate` output.

### Security / Trust
- No changes to proof, nonce, acceptance, finalization, rollback, router fallback, or trusted wiki promotion semantics.

## [0.2.3] - 2026-04-24

### Added
- Runtime mirror manifest in `src/abw/runtime_manifest.py`
- Runtime source reporting in `abw version` and `abw doctor`
- Expanded manifest-driven mirror drift guard coverage

### Changed
- Editable/dev installs now prefer `scripts/` runtime as canonical source
- Packaged fallback remains `src/abw/_legacy/`

### Fixed
- Reduced silent drift risk between `scripts/` and packaged legacy runtime

### Security / Trust
- No changes to proof, nonce, acceptance, finalization, rollback, or trusted wiki promotion semantics

## [0.2.2] - 2026-04-24

### Added
- Release smoke flow through `scripts/release_smoke.py`
- Drift guard tests for critical `scripts/` and `src/abw/_legacy/` runtime mirrors
- Entrypoint parity tests for `abw`, `py -m abw.cli`, `py scripts/abw_cli.py`, and `abw.bat`

### Changed
- Unified public command surface contract behind shared command metadata
- Improved entrypoint parity for help, version, doctor, and dashboard smoke flows
- Clarified `doctor` workspace health vs engine health signals
- Clarified `version` release match state

### Fixed
- Hidden command leakage in normal CLI help
- Script entrypoint integrity checks now evaluate the runtime root instead of the user workspace
- Stale upgrade-style warning when release match cannot be verified

### Security / Trust
- Proof, nonce/replay, acceptance, finalization, and rollback semantics are unchanged

## [0.2.1] - 2026-04-24

### Added
- Multi-project workspace initialization through `abw init`
- Package-level `abw version` report with install mode, source path, git tag, commit, and workspace schema
- Package-level `abw migrate` report that creates missing workspace folders/config without moving existing raw/wiki/draft data
- Package-level `abw doctor` report for workspace and install health
- Package-level `abw upgrade` guidance that explains the correct update command for pip, git+pip, or editable installs

### Changed
- Public command surface is now: `init`, `ask`, `ingest`, `review`, `doctor`, `version`, `migrate`, `help`
- `doctor`, `version`, `migrate`, and `upgrade` are direct package facade reports; routed work still uses the trust runner
- Help output now uses the product facade directly instead of routing a help request through the runner
- Workspace config now records `workspace_schema`, `abw_version`, and project-local raw/wiki/drafts directories

### Fixed
- Package CLI help no longer depends on agent-only runner execution path
- Package legacy help mirror now matches the script runtime help implementation
- Multi-project workspace isolation is covered by tests

### Security / Trust
- Proof, nonce, acceptance, finalization, routing, and continuation gate semantics are unchanged
- Release only changes command facade/reporting and workspace initialization behavior

## [0.2.0] - 2026-04-23

### Added
- Executive Overview (`abw overview`)
- Save Candidate Memory (`abw save "..."`)
- Contradiction Detection during ingest with safe warning/report flow under `drafts/conflicts/`

### Changed
- Public ABW command surface simplified to:
  - `ask`
  - `ingest`
  - `review`
  - `doctor`
  - `help`
- Added power-user commands:
  - `upgrade`
  - `rollback`
  - `repair`
  - `research` (placeholder)
- README rewritten with a user-first Quick Start
- Help, menu, and output views redesigned toward product UX

### Fixed
- Full `py -m unittest` suite restored to green after Phase 1
- Legacy runtime compatibility paths preserved for runner, dashboard, help, and suggestions
- Wizard non-interactive safety path improved for automated execution and tests
- CLI rendering consistency improved for subprocess entry paths

### Security / Trust
- Proof, nonce, and acceptance core unchanged
- No trust model regressions introduced in this release

### Internal Notes
- `0.2.0` marks the transition from an engineering-heavy command surface to a more product-facing ABW surface
- Historical anchors for this release:
  - `522323b` v2 surface cleanup
  - `2cc41c6` Phase 1 features
  - `83b3a24` full-suite restoration

## [0.1.0]

Initial package, CLI, and multi-project workspace milestone before the v2 product surface cleanup.

## [Unreleased]

### Added
- Official migration guide: `docs/ABW_MIGRATION_PLAYBOOK.md` for converting legacy projects into clean ABW package-workspace mode

### Fixed
- **NotebookLM account verification:** `/abw-setup` now requires an explicit Google email and must verify the authenticated account before marking the MCP bridge as authenticated. It no longer permits account inference from Windows usernames, IDE/browser profiles, notebook lists, git config, or workspace files.
- **Legacy AWF cleanup:** Installers no longer ship `awf_skills/*`, remove stale installed `awf-*` helper skills, and keep `/help` bound to the ABW help workflow.

## [1.2.0] - 2026-04-12

### Added
- **Fail-Fast Installer Path:** Both `install.ps1` and `install.sh` now support immediate abort on critical file download failures.
- **Post-Install Verification:** Added a diagnostic block that verifies all 9 workflows and 10 skills are correctly registered in the global environment.
- **Local Clone Detection:** Installers now detect if they are run from a local repository and copy files directly, significantly speeding up local deployment.
- **9-Command Surface:** Standardized `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-ask`, `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`, `/abw-lint`.
- **Primary Router (`/abw-ask`):** Implemented the adaptive router as the primary entry point for all agent interactions.

### Changed
- **Non-Destructive Registration:** Installer logic updated to preserve existing `GEMINI.md` content (like AWF blocks) during Hybrid ABW registration.
- **Manifest Cleanup:** Removed non-existent entries (`ingest-wiki-deliberative.md`) and added actual missing templates (`deliberation_run.example.json`).
- **Standardized Surface Banner:** Uniform public command banners across all 14+ core workflows.

### Fixed
- **Mojibake Resolution:** Normalized character encoding (ASCII-safe UTF-8) across all core documentation and logic files to eliminate mojibake.
- **Markdown Linting:** Resolved MD060 (table spacing) and MD047 (trailing newline) warnings in `workflows/README.md`.
- **Installer Syntax Error:** Resolved a PowerShell syntax error in the skills manifest array.

## [1.1.0] - 2026-04-10

### Added
- **TTC Deliberation Engine:** Initial implementation of Tier 2 Reasoning (/abw-query-deep).
- **Hybrid ABW Core Architecture:** Established the 3-Tier reasoning structure (Fast/Deep/Bootstrap).
- **Grounding Queue System:** Implemented semi-automated ingest/verification path.

---

## Release Discipline

- Patch releases (`0.2.1`) are for bug fixes and compatibility-only changes.
- Minor releases (`0.3.0`) are for new safe features that preserve the public model.
- Major releases (`1.0.0`) are for intentional breaking command or runtime contract changes.

Examples:
- `0.2.1` contradiction heuristics fixes
- `0.3.0` guided research and richer overview
- `1.0.0` stable public API and mature command/runtime contracts
