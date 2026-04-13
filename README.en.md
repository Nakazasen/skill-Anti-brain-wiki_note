# Hybrid Anti-Brain-Wiki (Hybrid ABW)

> Version: 1.3.1
> Tagline: Transforming AI from a fast-response state into a grounded knowledge system with memory and bounded deliberation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW is a knowledge management and reasoning architecture designed for AI Agents. Its goal is to address the two most common weaknesses of LLMs:

- Lack of reliable long-term memory.
- Responses that sound plausible but lack clear provenance.

---

## Why Hybrid ABW?

Instead of letting the AI respond in a "single-pass" manner (thinking once and speaking immediately), Hybrid ABW forces the model through a clear and rigorous framework:

1. Read the operational context in `.brain/`.
2. Search for compiled knowledge in the `wiki/` directory.
3. If necessary, perform grounding via NotebookLM to retrieve evidence.
4. If evidence is insufficient, the system is mandated to "log a gap" (recording a knowledge deficiency) instead of "fake success" (pretending to know and hallucinating a response).

## Four-Layer Architecture

- `raw/`: Unprocessed, raw source documents.
- `processed/`: Storage layer for evidence and provenance.
- `wiki/`: Durable knowledge, schema-compliant, with clear citations.
- `.brain/`: Operational state, including queues, gap logs, and deliberation logs.

\* *Note: NotebookLM is used as a deep grounding engine, and is not treated as an absolute "oracle" or magical solution.*

---

## Repo Boundary: Skill OS vs Project Workspace

This repository is the **Hybrid ABW OS / skill distribution**. It contains commands, workflows, skills, schemas, templates, and runtime scripts that can be installed globally into Antigravity/Gemini.

This repository is **not** a business project repository. A project such as `MES-MOM-AMS-VN-Integration` is a **workspace that uses ABW OS**. That workspace owns its own `raw/`, `processed/manifest.jsonl`, `wiki/`, `.brain/`, and `notebooks/packages/` runtime state.

Do not mix the two layers:

| Layer | Repository | Owns |
|---|---|---|
| OS / skill layer | `Nakazasen/skill-Anti-brain-wiki_note` | Commands, workflows, skills, installers, schemas, templates, scripts |
| Project data layer | `Nakazasen/MES-MOM-AMS-VN-Integration` or any user workspace | Source documents, manifests, wiki notes, package outputs, project memory |

Generated project data should stay in the project workspace. Improvements to ABW commands and skills should be made in this repo.

---

## TTC (Test-Time Compute) Deliberation Engine

Hybrid ABW provides the `/abw-query-deep` command path for extremely challenging questions such as:

- Information Synthesis
- Comparative Analysis
- Root Cause Analysis (RCA)
- Design Trade-offs
- Contradiction-heavy prompts

The TTC flow goes through 5 passes:

1. **Decomposition:** Breaking down the problem.
2. **Evidence Assembly:** Gathering evidence.
3. **Grounding:** Anchoring data with NotebookLM.
4. **Self-Critique:** Internal evaluation and counter-argumentation.
5. **Repair or Exit:** Fixing the response or exiting the loop.

The deliberation process is safely controlled by:

- An **Exit Gate** based on scoring metrics.
- A **Circuit Breaker** to prevent infinite loops.
- A **Query Budget** for NotebookLM to save tokens and time.

---

## Fallback-First, Never Fake Success

This is the **most important principle** of this repository.

If the NotebookLM MCP is not ready or encounters an error:

- The `/abw-ingest` command is only allowed to create artifacts in `draft` or `pending_grounding` states.
- The `/abw-query` command will prioritize replying from `wiki/` (wiki-first) and log a gap if evidence is missing.
- The `/abw-query-deep` command will still run but will proactively skip Step 3 (Grounding) or set the budget to 0 to avoid system hangups.
- The `/abw-lint` command must clearly warn that the system is in fallback mode (lacking deep grounding capabilities).

**Hybrid ABW always prioritizes honesty over "smart-sounding but hollow" answers.**

---

## ABW OS Philosophy

ABW OS is not a prompt bundle. It is an operating discipline for agentic work:

1. **Memory before response**: read `.brain/` and `wiki/` before answering.
2. **Provenance before confidence**: every important fact should trace back to source material or a logged gap.
3. **Grounding before import**: NotebookLM is a grounding engine, not a place to dump uncontrolled files.
4. **Packaging before scale**: when NotebookLM source limits are near, use `/abw-pack` to produce traceable compressed packages.
5. **Approval before sync**: `/abw-sync` defaults to dry-run and only uploads after explicit operator approval.
6. **Evaluation before acceptance**: use `/abw-eval`, `/abw-audit`, and `/abw-lint` to prevent shallow acceptance.

---

## Quick Start

### 1. Installers / Workflows

On Windows:

```powershell
irm https://github.com/Nakazasen/skill-Anti-brain-wiki_note/raw/refs/tags/v1.3.1/install.ps1 | iex
```

On macOS / Linux:

```bash
curl -fsSL https://github.com/Nakazasen/skill-Anti-brain-wiki_note/raw/refs/tags/v1.3.1/install.sh | sh
```

### 2. Install NotebookLM CLI Bridge

```bash
uv tool install notebooklm-mcp-cli
```

### 3. Core Workflow Execution

```text
/abw-init
   -> /abw-setup
   -> /abw-status
   -> /abw-ingest
   -> /abw-pack
   -> /abw-sync
   -> /abw-ask 
        |-> (Tier 1) /abw-query
        |-> (Tier 2) /abw-query-deep
        |-> (Tier 3) /abw-bootstrap
   -> /abw-lint
```

### 4. Recommended Workflow

1. Copy raw documents into `raw/`.
2. Run `/abw-ingest`.
3. If the workspace is approaching NotebookLM source limits, run `/abw-pack` to produce a safe local package under `notebooks/packages/<package_id>`.
4. Run `/abw-sync` in dry-run mode first, then execute sync only after an operator explicitly approves the package and NotebookLM target.
5. Instead of trying to "diagnose" manually, use `/abw-ask` for any question. The Smart Router will automatically classify and route the request to a Fast path, Deep path, or Bootstrap path for new ideas.
6. Maintain the project regularly with `/abw-lint`.

### 5. Using ABW OS inside a project workspace

When using this skill inside a real project such as `MES-MOM-AMS-VN-Integration`, keep this lifecycle:

```text
ABW OS repo:
  install/update commands and skills

Project workspace:
  raw/ -> processed/manifest.jsonl -> wiki/ -> /abw-pack -> notebooks/packages/ -> /abw-sync dry-run -> explicit sync
```

The packager and sync scripts are installed from this repo, but they operate on the active workspace you run them in. That is the intended separation.

---

## Command Surface

| Command | Purpose |
|---------|----------|
| `/abw-init` | Initialize or repair the Hybrid ABW directory structure. |
| `/abw-setup` | Log in, verify the explicit Google account, and verify the NotebookLM MCP connection. |
| `/abw-status` | Check the health of the MCP bridge and grounding queue. |
| `/abw-ingest` | Process raw documents to create manifests and wiki artifacts. |
| `/abw-pack` | Package wiki knowledge into compressed, traceable NotebookLM source bundles. |
| `/abw-sync` | Dry-run or explicitly sync an approved package to NotebookLM via `nlm`. |
| `/abw-ask` | **Smart Router: Automatically routes to fast query, deep deliberation, or idea bootstrapping!** |

**Internal/Extended Paths behind the Router:**
| Command | Purpose |
|---------|----------|
| `/abw-query` | Fast wiki-first response path (Tier 1). |
| `/abw-query-deep` | Deep deliberation path for complex questions via TTC (Tier 2). |
| `/abw-lint` | Audit tool for wiki standards, grounding status, and TTC health. |
| `/abw-bootstrap` | Logic for bootstrapping new ideas (Tier 3), creating assumptions & validation tasks. |

---

## Legacy AWF Compatibility

This repository maintains some legacy AWF workflows for backward compatibility and reference.

However, in a pure Hybrid ABW project, core commands always start with the `/abw-*` prefix. Do not confuse this repository with a standard AWF installation.

If you want a standard AWF experience based on the upstream version, please install the upstream AWF separately.

---

## Grounding Principle

> "A response with a cited source is always better than a patchwork guess delivered with confidence."
> 
> "Proactively logging a knowledge gap is always better than providing a false answer (fake success)."

Every major change in the shared `wiki/` directory must always be traceable back to:

- The raw source.
- The corresponding entry in the manifest.
- The grounding outcome (processing status).
- The confidence status of the data.

---

## Other Important Documents

- `AGENTS.md`: Summary of system architecture and mandatory invariants.
- `skills/` directory: Contains the core execution logic of the workflows.
- `workflows/` directory: Contains the command wrappers executed directly on the IDE.
- `wiki/_schemas/note.schema.md`: The standard schema defining the storage format for long-term knowledge notes.

---

## Contributing

Contributions are welcome, especially in the following areas:

- TTC tuning and limit refining.
- Enhancing the quality of the grounding bridge.
- Increasing the comprehensive coverage of the `lint` automation.
- Evolving the `wiki schema` versions.
- Improving the honesty and usability of the fallback procedures.

Details can be found in `CONTRIBUTING.md`.
