# Changelog

All notable changes to the Hybrid ABW Command Surface system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-25

### Added

- `abw upgrade` command with full execution path: resolution, backup, installation, workspace preservation, and post-upgrade health checks.
- `abw upgrade --check` dry-run mode that reports whether an upgrade is needed without applying changes.
- `abw upgrade --rollback` command that restores the last upgrade using backup manifests.
- `abw upgrade --to <version>` to pin exact target versions.
- `abw upgrade --channel <stable|beta>` for release channel selection.
- Local wheel discovery in `workspace/dist/` and `package_root/dist/` with version-aware picking.
- Workspace snapshot preservation validation (SHA-256) before and after every upgrade.
- Automatic backup manifest creation with rollback specs for every upgrade operation.
- Post-upgrade health checks (`abw version`, `abw doctor`, `abw ask "dashboard"`).

### Changed

- Upgrade report now distinguishes `check`, `pending`, `success`, and `failed` statuses.
- Upgrade flow integrates with the continuation kernel gate for action governance.

### Security / Trust

- No changes to proof, nonce, acceptance, finalization, rollback, router fallback policy, or trusted wiki promotion semantics.

## [0.2.9] - 2026-04-25

### Added

- Regression test coverage to ensure `/abw-doctor` uses runtime integrity root when `--runtime-root` is not provided.
- Drift compatibility test coverage for runtime layouts that store workflow mirrors under `workflows/` instead of `global_workflows/`.

### Changed

- `/abw-doctor` and `/abw-repair` now resolve health drift checks against the active runtime integrity root by default.
- Drift target resolution now supports both nested runtime layout (`scripts/`, `global_workflows/`) and flat runtime layout (`abw_*.py` files in runtime root).

### Fixed

- Eliminated frozen doctor metrics (`stability_score=50`, `drift_rate=100%`) caused by health drift checks reading mismatched runtime paths.
- Prevented false workflow drift when both `global_workflows/` and `workflows/` exist but only `workflows/` contains the mirrored file.

### Security / Trust

- No changes to proof, nonce, acceptance, finalization, rollback, router fallback policy, or trusted wiki promotion semantics.

## [0.2.8] - 2026-04-25

### Added

- Wheel-mode regression coverage for `abw ask "dashboard"` under forced packaged runtime selection.

### Changed

- Runtime integrity checks now resolve critical files from the active runtime source (`scripts/` in editable/dev mode, `_legacy/` in packaged mode).
- Integrity snapshots and mismatch reports now use stable workspace-relative paths.

### Fixed

- Eliminated packaged wheel `invalid runtime_id` failures caused by false `integrity_compromised` detection in `ask` flow.

### Security / Trust

- No changes to proof, nonce, acceptance, finalization, rollback, router fallback policy, or trusted wiki promotion semantics.

## [0.2.7] - 2026-04-25

### Added

- Production multimodal ingest coverage for images, scanned PDFs, and XLSX embedded media with provenance references.
- Optional local OCR adapter hooks for PaddleOCR and Tesseract, plus cloud vision routing metadata for Claude Vision, Gemini Vision, and OpenAI Vision.
- Regression tests using MOM-like PNG/PDF binary-marker samples to prevent fake OCR confidence inflation.

### Changed

- Image/PDF ingest confidence now requires real OCR or readable text quality gates; binary probes are metadata-only evidence.
- XLSX embedded image bytes are reported as metadata/text probes rather than OCR unless readable text quality gates pass.
- Review routing now keeps no-real-OCR image/PDF artifacts in `review_needed`.

### Fixed

- PNG/PDF signatures and container markers such as `IHDR`, `IDAT`, `xref`, `obj`, and `/Type/Page` no longer inflate OCR confidence.
- Screenshots and scanned PDFs without usable OCR no longer receive false high confidence.

### Security / Trust

- No changes to proof, nonce, acceptance, finalization, rollback, router fallback policy, or trusted wiki promotion semantics.

## [0.2.6] - 2026-04-24

### Added

- Recursive directory ingest for `abw ingest <path>` when `<path>` is a directory under `raw/`.
- `raw`/`raw/` shortcut support so `abw ingest raw` ingests supported files in the `raw/` tree.
- Explicit ingest path errors for missing/invalid inputs with actionable retry guidance.

### Changed

- Ingest path parsing now accepts both file and directory targets under `raw/`.
- Runner ingest error handling now blocks invalid ingest requests instead of silently falling back to query.

### Fixed

- `abw ingest raw` no longer drops into knowledge-query fallback; it now routes to ingest lane correctly.
- Added regression coverage for file ingest, directory ingest, raw shortcut, and no-query-fallback ingest mistakes.

### Security / Trust

- No changes to proof, nonce, acceptance, finalization, rollback, router fallback policy outside ingest input handling, or trusted wiki promotion semantics.

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
