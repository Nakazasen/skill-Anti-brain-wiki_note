# Hybrid ABW Workflow Surface

This directory contains workflow files, compatibility docs, and internal guidance for Hybrid ABW.

It is not a guarantee that every file here is an equal public runtime command.
The v2 product surface is intentionally smaller and is defined by the CLI/help facade:

- `abw ask "..."`
- `abw init`
- `abw ingest <path>`
- `abw review`
- `abw doctor`
- `abw version`
- `abw migrate`
- `abw help`

Advanced maintainer commands remain available but hidden from normal UX:

- `abw upgrade`
- `abw rollback`
- `abw repair`
- `abw help --advanced`

`abw version` and `abw doctor` expose runtime source diagnostics (`scripts` vs `src/abw/_legacy`) and mirror status for topology checks.

## Core Entry Points

- `/abw-ask`: primary router for Hybrid ABW requests
- `/abw-eval`: evaluation and acceptance chain
- `/abw-start`: session start and runtime status check
- `/abw-update`: runtime deployment and sync verification
- `/abw-health`: read-only runtime health audit
- `/abw-repair`: runtime health repair path

## `/abw-update` Runtime Contract

`/abw-update` is not just a file copy command. It is the deployment path that must prove runtime readiness.

The package CLI command `abw upgrade` is intentionally guidance-only. It tells the user how to update the installed package for their install mode. Do not treat `abw upgrade` as equivalent to the governed `/abw-update` workflow.

The update flow must distinguish:

- `repo_state`
- `workspace_state`
- `runtime_state`
- `mcp_sync_result`

The update flow must verify:

- required runtime scripts exist after install
- required runtime workflows exist after install
- MCP config contains a valid `abw_runner` registration
- the configured runner path exists
- `GEMINI.md` registration was refreshed if managed by the installer

Required scripts:

- `abw_runner.py`
- `finalization_check.py`
- `abw_accept.py`
- `continuation_gate.py`
- `continuation_execute.py`

Required workflows:

- `abw-ask.md`
- `abw-update.md`
- `finalization.md`

Expected update result fields:

- `source_sync_result`
- `runtime_sync_result`
- `mcp_sync_result`
- `verification_result`
- `final_verdict`

Allowed verdicts:

- `PASS`
- `PARTIAL`
- `FAIL`

## Command Naming

- `abw-*` commands are the ABW-first workflow surface.
- Non-`abw-*` commands such as `/plan`, `/code`, and `/test` remain compatibility and delivery workflows.
- If a public workflow name changes, installer/runtime registration and docs must be updated together.

## Operational Rule

Do not claim the runtime is updated unless the installed runtime, MCP registration, and verification checks all pass.

## Command Surface References

- `docs/COMMAND_SURFACE.md`
- `docs/COMMAND_MIGRATION.md`
- `workflows/abw-commands.md`
