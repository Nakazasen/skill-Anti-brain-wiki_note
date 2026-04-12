# Hybrid Anti-Brain-Wiki (Hybrid ABW)

> Version: 1.1.1
> Tagline: Turn AI from fast response mode into a grounded, memory-aware, bounded-deliberation system.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW is a knowledge and reasoning architecture for AI agents. It is designed to address two common LLM failure modes:

- weak long-term memory
- plausible but weakly grounded answers

---

## Why Hybrid ABW?

Instead of letting the model answer in a single loose pass, Hybrid ABW routes work through a strict structure:

1. read operational context from `.brain/`
2. search compiled knowledge in `wiki/`
3. escalate to NotebookLM when deep grounding is needed
4. log gaps honestly instead of pretending certainty

## The 4-layer architecture

- `raw/`: untouched source material
- `processed/`: evidence and provenance layer
- `wiki/`: persistent knowledge with schema and citations
- `.brain/`: operational state, queues, gap logs, deliberation logs

NotebookLM is treated as a grounding tool, not an unquestionable oracle.

---

## TTC Deliberation Engine

Hybrid ABW exposes `/abw-query-deep` for difficult prompts such as:

- synthesis
- comparison
- root cause analysis
- design tradeoffs
- contradiction-heavy questions

The TTC loop has 5 passes:

1. Decomposition
2. Evidence Assembly
3. Grounding
4. Self-Critique
5. Repair or Exit

The loop is bounded by:

- a score-based exit gate
- a circuit breaker
- a NotebookLM query budget

---

## Fallback-first, no fake success

This is the most important public contract of the repo.

If NotebookLM MCP is unavailable:

- `/abw-ingest` may create only `draft` or `pending_grounding` artifacts
- `/abw-query` falls back to wiki-first answers plus gap logging
- `/abw-query-deep` still runs, but Pass 3 may be skipped or budgeted to zero
- `/abw-lint` must report reduced grounding capability honestly

Hybrid ABW prefers honesty over confident-sounding output.

---

## Quick Start

### 1. Install the global workflows

Windows:

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

### 2. Install the NotebookLM CLI bridge

```bash
uv tool install notebooklm-mcp-cli
```

### 3. Run the primary flow

```text
/abw-init
/abw-setup
/abw-ingest
/abw-query
/abw-query-deep
/abw-lint
```

### 4. Recommended usage

1. Drop source files into `raw/`
2. Run `/abw-ingest`
3. Ask fast questions with `/abw-query`
4. Ask hard questions with `/abw-query-deep`
5. Run `/abw-lint` to audit grounding and knowledge health

---

## Primary command surface

| Command | Purpose |
|---------|---------|
| `/abw-init` | Bootstrap or repair the Hybrid ABW structure |
| `/abw-setup` | Authenticate NotebookLM MCP and verify the bridge |
| `/abw-status` | Check MCP health and grounding queue status |
| `/abw-ingest` | Process raw sources into manifest and wiki artifacts |
| `/abw-query` | Fast wiki-first query path |
| `/abw-query-deep` | TTC deliberation path for difficult questions |
| `/abw-lint` | Audit wiki, grounding, contradictions, and TTC health |

---

## Legacy AWF compatibility

This repo still keeps some older AWF workflows for compatibility and reference.

However, the public command surface of this repository is `/abw-*`.
This repository should not be read as a generic AWF installer.

If you want the full upstream AWF experience, install upstream AWF separately.

---

## Grounding principle

> A cited answer beats a confident guess.
> A logged gap beats a fake answer.

Important artifacts should always be traceable back to:

- the raw source
- the manifest line
- the grounding outcome
- the confidence status

---

## Important files

- `AGENTS.md`: system architecture and invariants
- `skills/`: workflow execution logic
- `workflows/`: IDE command wrappers
- `wiki/_schemas/note.schema.md`: schema for persistent knowledge notes

---

## Contributing

Contributions are especially welcome in these areas:

- TTC tuning
- grounding bridge quality
- lint coverage
- wiki schema evolution
- fallback honesty and reliability

See `CONTRIBUTING.md` for details.