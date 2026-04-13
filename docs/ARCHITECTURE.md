# Architecture

This document is the source of truth for repository boundaries, runtime packaging, and ABW system structure.

## System Layers

1. Repository layer
   - `workflows/`
   - `skills/`
   - `scripts/`
   - `schemas/`
   - `templates/`
   - `wiki/`
   - `.brain/`
2. Installer layer
   - `install.ps1`
   - `install.sh`
3. Runtime layer
   - `~/.gemini/GEMINI.md`
   - `~/.gemini/antigravity/global_workflows`
   - `~/.gemini/antigravity/skills`
   - `~/.gemini/antigravity/scripts`
4. Operating discipline
   - routing
   - grounding
   - delivery
   - evaluation

## Public Surface

Public surface means the commands a normal user is expected to discover and run after installer registration.

- ABW commands in `workflows/abw-*.md`
- promoted delivery/session workflows:
  - `brainstorm.md`
  - `plan.md`
  - `design.md`
  - `visualize.md`
  - `code.md`
  - `run.md`
  - `debug.md`
  - `test.md`
  - `deploy.md`
  - `refactor.md`
  - `audit.md`
  - `save_brain.md`
  - `recap.md`
  - `next.md`
  - `help.md`

## Compatibility Layer

Compatibility files may still be useful, but they are not the main ABW-first entry surface.

- `awf_skills/`
- older AWF-oriented workflows
- files explicitly described as compatibility-oriented

## Internal / Maintainer Artifacts

- `HYBRID_ABW_*.md`
- `docs/PROMPT_V2.hybrid-abw.md`
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

## Example Workspace

`examples/hello-abw/` is the minimal example workspace for pack/sync/eval smoke testing.
