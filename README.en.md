# Hybrid ABW

> Version: 1.3.1  
> Turn a fast-answering LLM into a grounded, stateful, evaluation-aware working system.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW is an operating discipline for AI work. It combines:

- grounded project knowledge in `wiki/`
- working state in `.brain/`
- bounded reasoning for hard questions
- explicit evaluation before acceptance

## Core Idea

- Do not fake knowledge.
- Do not claim grounding when grounding is unavailable.
- Do not skip evaluation when output quality matters.

## Two Entrypoints

- `/abw-ask`: work entrypoint
- `/abw-eval`: evaluation entrypoint

## Mental Model: 6 Lanes

1. Ask & Think
2. Build Knowledge
3. Build Product
4. Session & Memory
5. Evaluation & Acceptance
6. Utility & Customization

## Quick Start

Clone the repo, then run the installer to register all Hybrid ABW commands into Gemini. Cloning alone does not activate the command surface.

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

After install:

1. Run `/abw-init` to bootstrap or repair the ABW workspace structure.
2. Run `/abw-setup` to configure grounding.
3. Use `/abw-ask` for routing.
4. Use `/abw-eval` before acceptance.
5. Use `/abw-update` to refresh the local Gemini runtime command surface.
6. Use `/audit` for delivery-loop review of code, product behavior, or security.
7. Use `/abw-learn` when a user correction should become a reusable behavioral lesson.

## Documentation Map

- `README.md`: bilingual overview
- `workflows/README.md`: Vietnamese command model
- `workflows/help.md`: operator-facing help
- `workflows/audit.md`: delivery-loop review workflow
- `workflows/abw-learn.md`: reusable behavioral lesson recorder
- `docs/ARCHITECTURE.md`: boundaries and source of truth
- `docs/RELEASE_CHECKLIST.md`: maintainer release gate
- `examples/hello-abw/`: minimal example workspace

## Scope Boundaries

- Public surface: installed ABW command surface
- Compatibility layer: older workflows kept for migration and convenience
- Internal docs/playbooks: maintainer-facing artifacts and design notes
