# Changelog

All notable changes to the Hybrid ABW Command Surface system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **NotebookLM account verification:** `/abw-setup` now requires an explicit Google email and must verify the authenticated account before marking the MCP bridge as authenticated. It no longer permits account inference from Windows usernames, IDE/browser profiles, notebook lists, git config, or workspace files.

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
