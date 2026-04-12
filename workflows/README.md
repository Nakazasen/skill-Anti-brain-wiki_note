# Hybrid ABW Workflow Surface

This directory currently contains two layers:

- **Primary surface:** the `/abw-*` workflows for Hybrid Anti-Brain-Wiki
- **Legacy layer:** older AWF workflows kept for compatibility and reuse

If you are reading this repository for the first time, treat **`/abw-*` as the main product surface**.

---

## Primary Commands

| Command | Purpose |
| --------- | --------- |
| `/abw-init` | Bootstrap or repair the Hybrid ABW project structure |
| `/abw-setup` | Activate NotebookLM MCP and verify fallback state |
| `/abw-status` | Check MCP bridge and grounding queue status |
| `/abw-ingest` | Ingest source material into processed/wiki artifacts |
| `/abw-ask` | **Smart Router: Default entrypoint for any question** |
| `/abw-query` | Tier 1: Fast wiki-first retrieval path |
| `/abw-query-deep` | Tier 2: Bounded TTC query path for synthesis and hard questions |
| `/abw-bootstrap` | Tier 3: Greenfield reasoning and hypothesis generation |
| `/abw-lint` | Audit wiki, manifest, queue, and deliberation health |

---

## Recommended ABW Flow

```text
/abw-init
   -> /abw-setup
   -> /abw-status
   -> /abw-ingest
   -> /abw-ask 
        |-> (Tier 1) /abw-query
        |-> (Tier 2) /abw-query-deep
        |-> (Tier 3) /abw-bootstrap
   -> /abw-lint
```

### Short Interpretation

- start with `/abw-init`
- activate NotebookLM using `/abw-setup`
- check status using `/abw-status`
- ingest knowledge using `/abw-ingest`
- use `/abw-ask` as the default router for any question you have
- (the router will internally bypass or direct you to `/abw-query`, `/abw-query-deep`, or `/abw-bootstrap`)
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
| -------- | ----- |
| Create ABW structure | `/abw-init` |
| Connect NotebookLM | `/abw-setup` |
| Check whether ABW is in fallback mode | `/abw-status` |
| Turn raw sources into wiki knowledge | `/abw-ingest` |
| Ask the system any general question | `/abw-ask` |
| Ask a quick grounded question directly | `/abw-query` |
| Ask a hard synthesis or comparison question directly | `/abw-query-deep` |
| Formulate hypotheses for a greenfield project directly | `/abw-bootstrap` |
| Audit wiki and grounding health | `/abw-lint` |

---

## Notes for Maintainers

If you continue evolving this repository toward ABW-first positioning:

1. keep `/abw-*` documentation in sync with installer behavior
2. keep legacy AWF docs clearly labeled as secondary or compatibility-only
3. avoid presenting `/plan`, `/design`, and `/code` as the primary path unless the repo intentionally pivots back to full AWF