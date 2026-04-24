# Architecture

This document is the source of truth for repository boundaries, runtime packaging, and ABW system structure.

## Current Product Boundary

As of `v0.2.2`, the normal product entrypoint is the `abw` package CLI. The installer/workflow runtime remains supported, but the public user model is package-first:

- `abw init`
- `abw ask "..."`
- `abw ingest raw/<file>`
- `abw review`
- `abw doctor`
- `abw version`
- `abw migrate`
- `abw help`

Package facade commands such as `init`, `doctor`, `version`, `migrate`, and `upgrade` are local workspace/install reports. Routed AI work still flows through the legacy trust runner.

## System Layers

1. Repository layer: `workflows/`, `skills/`, `scripts/`, `schemas/`, `templates/`, `wiki/`, `.brain/`
2. Installer layer: `install.ps1`, `install.sh`
3. Runtime layer: `~/.gemini/GEMINI.md`, `~/.gemini/antigravity/` subfolders
4. Hybrid Operating Discipline (Action Governance):
   - routing (`/abw-ask`)
   - grounding (`/abw-query`, `wiki/`)
   - execution governance (**Continuation Kernel v1**)
   - delivery & evaluation (`/audit`, `/abw-eval`)
   - customization & utility

## Workflow Public Surface

Public surface means the commands a normal user is expected to discover and run after installer registration.

- ABW commands in `workflows/abw-*.md`
- promoted delivery/session workflows:
- `abw-resume.md` (Governed Action Entrypoint)
- `abw-execute.md` (Governed Executor Wrapper)
- `audit.md` (Product/Sec Audit)
- `abw-learn.md` (Lesson Ingestion)
- `save_brain.md` (State Preservation)
- `recap.md` (Context Restoration)
- `brainstorm.md` / `plan.md` / `code.md` / `test.md`
- `help.md` / `customize.md`

## Legacy Boundary

Hybrid ABW no longer ships or installs legacy AWF helper skills. Runtime behavior must come from ABW workflows, ABW skills, and ABW scripts only.

- Do not add `awf_skills/` back to the installer.
- Do not register `awf-context-help`; `/help` must resolve to `workflows/help.md`.
- Historical docs may mention AWF, but the public/runtime command surface must not depend on it.

## Internal / Maintainer Artifacts

- `HYBRID_ABW_*.md`
- `docs/BRIEF.hybrid-abw.md`
- release and architecture docs

## Source of Truth Order

1. `docs/ARCHITECTURE.md`
2. `README.md`
3. `workflows/README.md`
4. `workflows/help.md`
5. installer files

If these disagree, update the repo until they converge.

## Runtime Assembly

The installer is responsible for:

1. copying workflows into Gemini runtime
2. copying skills into Gemini runtime
3. copying runtime scripts into Gemini runtime
4. injecting the ABW block into `GEMINI.md`
5. verifying required files after install

Cloning the repo alone does not activate the command surface.

## Grounding Boundary

Current real backend:

- NotebookLM MCP
- `nlm` CLI

Architectural direction:

- keep ABW semantics stable
- allow future backend abstraction

Current implementation is still NotebookLM-first.

## Evaluation Boundary

Official evaluation commands:

- `/abw-review`
- `/abw-audit`
- `/abw-meta-audit`
- `/abw-rollback`
- `/abw-accept`
- `/abw-eval`

## Execution Proof (Action Governance)

`examples/resume-abw/` is the primary reference workspace for Continuation Kernel v1 logic. See `EVAL_REPORT.md` for a documented execution trace of gated continuation.

`examples/hello-abw/` remains as a minimal workspace for pack/sync/eval smoke testing.
