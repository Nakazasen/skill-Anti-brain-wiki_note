# Hybrid ABW Workflow Surface

This directory currently contains two layers:

- **Primary surface:** the `/abw-*` workflows for Hybrid Anti-Brain-Wiki
- **Legacy layer:** older AWF workflows kept for compatibility and reuse

If you are reading this repository for the first time, treat **`/abw-*` as the main product surface**.

---

## Primary Commands

| Command | Purpose |
|---------|---------|
| `/abw-init` | Bootstrap or repair the Hybrid ABW project structure |
| `/abw-setup` | Activate NotebookLM MCP and verify fallback state |
| `/abw-status` | Check MCP bridge and grounding queue status |
| `/abw-ingest` | Ingest source material into processed/wiki artifacts |
| `/abw-query` | Fast wiki-first retrieval path |
| `/abw-query-deep` | Bounded TTC query path for synthesis and hard questions |
| `/abw-lint` | Audit wiki, manifest, queue, and deliberation health |

---

## Recommended ABW Flow

```text
/abw-init
   -> /abw-setup
   -> /abw-ingest
   -> /abw-query
   -> /abw-query-deep
   -> /abw-lint
```

### Short Interpretation

- start with `/abw-init`
- activate NotebookLM using `/abw-setup`
- ingest knowledge using `/abw-ingest`
- use `/abw-query` for fast answers
- use `/abw-query-deep` for comparison, RCA, design, and contradiction-heavy prompts
- use `/abw-lint` to keep the knowledge base healthy

---

## Fallback-First Behavior

Hybrid ABW is intentionally honest when MCP is unavailable.

If NotebookLM is not active:

- ingest produces `draft` artifacts, not fake `grounded` artifacts
- query falls back to wiki-first answers plus gap logging
- grounding operations are queued in `.brain/grounding_queue.json`

This is by design.

---

## Legacy AWF Workflows

This repository still contains legacy AWF workflows such as `/init`, `/plan`, `/design`, `/code`, `/debug`, and `/deploy`.
These files are kept because:

- some users still run a mixed ABW + AWF setup
- some helper flows remain useful outside the ABW command surface
- the repository still bundles AWF helper skills for session restore, autosave, onboarding, and error translation

However, **legacy AWF workflows are not the primary public command surface of this repository**.

If you want the full upstream AWF experience, install upstream AWF separately.

---

## Mapping: Intent -> ABW Command

| Intent | Use |
|--------|-----|
| Create ABW structure | `/abw-init` |
| Connect NotebookLM | `/abw-setup` |
| Check whether ABW is in fallback mode | `/abw-status` |
| Turn raw sources into wiki knowledge | `/abw-ingest` |
| Ask a quick grounded question | `/abw-query` |
| Ask a hard synthesis or comparison question | `/abw-query-deep` |
| Audit wiki and grounding health | `/abw-lint` |

---

## Notes for Maintainers

If you continue evolving this repository toward ABW-first positioning:

1. keep `/abw-*` documentation in sync with installer behavior
2. keep legacy AWF docs clearly labeled as secondary or compatibility-only
3. avoid presenting `/plan`, `/design`, and `/code` as the primary path unless the repo intentionally pivots back to full AWF