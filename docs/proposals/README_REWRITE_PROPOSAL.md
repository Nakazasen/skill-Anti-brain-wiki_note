# ABW

ABW, Anti-Brain-Wiki, is a constitutional governance layer for local agent work. It is not a chat UI, inference engine, or product command center. ABW is the rule system that keeps an agent grounded in local evidence, honest about missing knowledge, and constrained before it writes.

At system level, ABW combines grounded memory, retrieval discipline, action governance, and release hygiene:

- grounded memory: `raw/`, `processed/`, `wiki/`, and provenance metadata define what the agent may claim;
- operational state: `.brain/` tracks gaps, routing, continuation state, handovers, evaluation, and runtime history;
- workflow constitution: `workflows/` and `skills/` define how an agent routes, queries, bootstraps, resumes, executes, audits, and accepts work;
- runtime implementation: `src/abw/`, `scripts/`, and `src/abw/_legacy/` expose package CLI, local API, and governed compatibility runtime;
- verification surface: `tests/`, `schemas/`, `templates/`, release notes, and audit docs keep the governance contract repeatable.

The short version: ABW is the canonical governance engine. Product shells and active agent runtimes can call it, but they should not absorb or mechanically merge its source.

## Current Status

This proposed README reflects the repository state audited on 2026-04-30.

- Package: `abw-skill`
- Current package version: `1.1.0`
- Latest release note present: `docs/releases/v1.1.0.md`
- Latest observed commit during audit: `4f35b10 docs: add v1.1.0 release notes`
- Latest tag observed during audit: `v1.1.0`
- Runtime package entrypoint: `abw = "abw.cli:main"`
- Local API module: `src/abw/api.py`
- Current public CLI surface includes: `init`, `ask`, `ingest`, `review`, `doctor`, `version`, `migrate`, `help`, plus inspection, recovery, provider, apply, and improvement commands.

The repository contains a mature governance body: package CLI, FastAPI/Starlette local API, legacy runtime mirror, workflows, skills, templates, schemas, examples, release notes, migration docs, and broad tests.

## Long-Term Vision

ABW should remain the canonical constitutional governance engine for agentic work across local projects.

The long-term role of ABW is to answer these questions before an agent acts:

1. What can be claimed as grounded knowledge?
2. What is missing, stale, contradictory, or only draft?
3. Which workspace should answer this request?
4. Which workflow path is appropriate for the request?
5. Is the next action small, reversible, within budget, and consistent with locked decisions?
6. What evidence proves that the work is actually complete?
7. What should be recorded so a future model can safely resume?

ABW should grow as a governance substrate that multiple shells can call: CLI, desktop admin UI, local API, and product runtimes such as NVIDIA Agent IDE. The governing semantics should stay stable even as shells change.

## System Model

ABW uses a layered model:

```text
-----------------------------+
| Product shell / agent IDE   |
| CLI, desktop UI, app shell  |
+--------------+--------------+
               |
               v
+-----------------------------+
| ABW governance interface    |
| CLI, local API, workflows   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Governance kernels          |
| router, grounding, resume,  |
| continuation, acceptance    |
+--------------+--------------+
               |
               v
+-----------------------------+
| Evidence and state          |
| .brain, raw, processed,     |
| wiki, templates, schemas    |
+-----------------------------+
```

ABW is intentionally separate from application shells. A shell may host conversations, agents, tools, terminals, and UI state. ABW defines whether claims and actions are allowed, grounded, incomplete, blocked, or accepted.

## Repository Layers

### `.brain/`

`.brain/` is operational memory, not canonical knowledge. It stores agent state, routing records, gaps, handovers, continuation state, evaluation traces, nonces, and runtime artifacts.

Important files include:

- `.brain/knowledge_gaps.json`: open, resolved, blocking, or advisory missing information.
- `.brain/resume_state.json`: current project phase, objective, active step, completed steps, and effective budget.
- `.brain/continuation_backlog.json`: approved pending work steps with preconditions and rollback contracts.
- `.brain/step_history.jsonl`: append-only outcome history.
- `.brain/handover_log.jsonl`: append-only continuity handover history.
- `.brain/workspaces.json`: local registry used by multi-workspace route-then-ask.
- `.brain/query_deep_runs.jsonl` and related logs: deliberative query traces.

Rule: do not treat `.brain/` as primary factual source. It can guide context reconstruction, but grounded answers must cite `wiki/`, `processed/`, or `raw/` provenance.

### `raw/`

`raw/` contains source material. Raw files are inputs, not final answers. ABW should preserve source identity through ingestion, rename chains, and later edits.

### `processed/`

`processed/` contains extracted or compiled intermediate data. `processed/manifest.jsonl` is part of the provenance chain and is used by evidence reference resolution.

### `wiki/`

`wiki/` is the local grounded knowledge layer. Wiki notes should be concise, source-backed, and typed by domain such as concepts, entities, timelines, and sources.

Wiki notes are where ABW should answer from first. If the wiki cannot answer, ABW logs the gap or escalates to grounding. It must not fill missing knowledge with confident prose.

### `workflows/`

`workflows/` defines the slash-command operating discipline. It includes router, query, query-deep, bootstrap, resume, execute, audit, review, eval, accept, rollback, repair, pack, sync, setup, and helper workflows.

The normal user should not need to learn every workflow. The canonical entrypoint is the adaptive router.

### `skills/`

`skills/` contains detailed execution policies behind workflows:

- `query-wiki.md`: fast wiki-first question answering.
- `query-wiki-deliberative.md`: bounded multi-pass reasoning for complex questions.
- `abw-bootstrap.md`: hypothesis-driven mode for greenfield projects.
- `continuation-kernel.md`: next-safe-step governance.
- `ingest-wiki.md`, `lint-wiki.md`, `notebooklm-*`: ingestion, grounding, packaging, and backend policies.

### `scripts/`

`scripts/` contains the legacy and machine-checkable runtime tools used by workflow mode. Important examples include:

- `ai_runner.py`: strict entrypoint used by workflow binding.
- `abw_runner.py`: trust runner and dispatch logic.
- `continuation_gate.py`: machine gate for next safe step selection.
- `continuation_execute.py`: governed execution state recorder.
- `abw_accept.py`: acceptance/evidence gate.
- `abw_query_deep.py`, `abw_knowledge.py`, `abw_ingest.py`: knowledge and retrieval implementation.

### `src/abw/`

`src/abw/` is the package runtime. It exposes:

- CLI facade in `cli.py`.
- local API in `api.py`.
- runtime loader in `legacy.py`.
- workspace registry and purpose detection.
- inspection, gaps, recovery, trend, improve, apply, doctor, version, provider, and migration helpers.

The package loader currently selects `scripts/` in editable/dev mode and `src/abw/_legacy/` as packaged fallback. This is intentional compatibility infrastructure and should stay visible in version and doctor reports.

### `schemas/`

`schemas/` contains machine-readable schemas for key state files such as `brain`, `session`, `preferences`, and Notebook package manifests. More governance files should gain schemas over time.

### `templates/`

`templates/` contains example policy and state files, including continuation policy, unsafe zones, locked decisions, knowledge gaps, grounding queue, assumptions, hypotheses, validation backlog, acceptance requests, and deliberation runs.

Templates are important because ABW should bootstrap missing state explicitly rather than inventing hidden state.

### `tests/`

`tests/` covers command surface parity, runtime loader behavior, continuation gates, continuation execution, acceptance, routing, multi-workspace registry, API normalization, gap handling, ingestion, recovery, provider behavior, and anti-fake-proof checks.

The v1.1.0 release note reports `673 passed, 7 warnings`. This audit did not rerun the test suite; it inspected repository structure and implementation state.

## Adaptive Router

`/abw-ask` is the main adaptive entrypoint. Its role is to route user intent and execute through the governed runtime, not to act as a loose router.

ABW currently defines these strategic paths:

### Tier 1: `ask` / `query`

Use for simple questions and precise lookups when the answer should already exist in `wiki/`.

Rules:

- perform fast wiki-first retrieval;
- cite supporting notes and provenance;
- do not hallucinate missing answers;
- log missing information to `.brain/knowledge_gaps.json`;
- advise ingestion when sources are absent.

### Tier 2: `query-deep`

Use for comparison, root cause analysis, architectural tradeoffs, contradictions, stale notes, and high-accuracy requests.

Rules:

- decompose the question;
- assemble evidence;
- ground or skip grounding honestly;
- self-critique and score the answer;
- repair if evidence improves;
- stop through a circuit breaker when no new evidence appears.

### Tier 3: `bootstrap`

Use for greenfield projects or undefined ideas where `raw/` and `wiki/` do not contain source knowledge.

Rules:

- do not compile unsupported facts;
- switch to hypothesis-driven mode;
- write reasoning state under `.brain/bootstrap/`;
- produce assumptions, hypotheses, decision log, and validation backlog.

### Tier 4: `resume`

Use for interrupted projects with existing `.brain/` state.

Rules:

- reconstruct project state;
- select one safe next step;
- pass the Continuation Kernel gate;
- stop for approval if required;
- record outcomes after execution.

## Continuation Kernel

The Continuation Kernel governs what an agent may do next. It is the action side of ABW.

The key question is not "can the model do this?" The key question is "is this the next bounded, reversible, policy-compliant action?"

### Gate Inputs

The gate reads:

- `.brain/resume_state.json`
- `.brain/continuation_backlog.json`
- `.brain/locked_decisions.json`
- `.brain/unsafe_zones.json`
- `.brain/continuation_policy.json`
- `.brain/knowledge_gaps.json`
- `.brain/step_history.jsonl`
- `.brain/handover_log.jsonl`

### Unsafe Zones

Unsafe zones define protected areas.

- `user_declared + high`: hard block until the user unlocks it.
- `historical + high`: requires approval and audit.
- `heuristic_suspected`: warning, not sovereign authority.

### Locked Decisions

Locked decisions prevent silent reversals of architecture or policy. A step that changes a locked decision must include explicit `affects_decision_ids`, evidence delta refs, and approval when required.

### Knowledge Gaps

Blocking gaps stop dependent work. Advisory gaps warn. Non-blocking gaps pass. The gate must not allow a step that depends on missing critical knowledge.

### Effective Budget

`effective_budget` limits file count and line-change size. Failed steps shrink future budget; repeated successful accepted steps may increase it within policy maximums.

### Rollback Contract

Every writable step needs a rollback contract:

- method,
- cost,
- confidence.

High-cost, low-confidence, or non-rollbackable steps require approval. A small step is not safe unless it is also reversible enough.

### Approval Gate

If the gate returns `blocked` or `approval_required`, the agent must stop and ask for explicit user intervention. Approval cannot be inferred from vague language.

## No-Fake-Success Constitution

ABW's highest-value invariant is honesty under uncertainty.

### No Fake Grounding

If NotebookLM MCP, `nlm`, or any grounding backend is unavailable, ABW must degrade to draft, pending grounding, partial answer, or gap logged. It must not claim grounded status.

### No Fake Retrieval

If `wiki/` does not contain the answer, ABW should say so, log the gap, and suggest ingestion. It must not produce a polished answer without evidence.

### No Fake Acceptance

A completion report is not acceptance. Acceptance requires evidence: tests, artifact presence, diff inspection, human review where appropriate, and claim-to-evidence mapping.

### Citation and Provenance

Grounded answers should cite wiki notes and, where possible, trace back through `processed/manifest.jsonl` to `raw/`.

### Contradictions

Contradictory notes should be surfaced as disputed evidence, not averaged into a false consensus.

### Gap Logging

Open questions belong in `.brain/knowledge_gaps.json`. Repeated unresolved questions should affect routing and prioritization.

## Runtime and API Surface

### CLI

Quick start from this repository:

```powershell
cd D:\Sandbox\skill-Anti-brain-wiki_note
.\abw.bat init
.\abw.bat ask "what you want to do"
.\abw.bat ingest raw\<file>
.\abw.bat review
.\abw.bat doctor
.\abw.bat version
.\abw.bat migrate
```

Installed package mode:

```powershell
py -m pip install -U abw-skill
abw init
abw ask "dashboard"
```

The one-command rule remains:

```powershell
abw ask "..."
```

### Local API

`src/abw/api.py` exposes a local service surface through FastAPI when available, with Starlette fallback.

Current endpoints include:

- `GET /health`
- `POST /inspect`
- `POST /gaps`
- `POST /recover-plan`
- `POST /recover-verify`
- `POST /trend`
- `POST /improve`
- `POST /apply`
- `POST /ask`
- `POST /workspace-intel`
- `POST /workspace-fix`
- `POST /promote-drafts`
- `POST /route-query`
- `GET /list-workspaces`
- `POST /register-workspace`
- `POST /disable-workspace`

This API is the natural second integration layer for product shells after a CLI bridge is stable.

## Integration With NVIDIA Agent Runtime

NVIDIA Agent Runtime, located outside this workspace at `D:\Sandbox\Nvidia`, should be treated as an integration target only.

As of this audit, ABW should not claim that it is already integrated with NVIDIA. No running bridge was verified in this pass.

Recommended boundary:

- ABW remains the canonical governance engine.
- NVIDIA remains the product shell and active agent runtime.
- NVIDIA may call ABW to route, inspect, ask, detect gaps, evaluate readiness, and enforce continuation gates.
- ABW should not import NVIDIA source or depend on NVIDIA internals.
- NVIDIA should not mechanically merge ABW source into its app shell.

### Phase 1: CLI Bridge First

The first integration should be a thin CLI bridge from NVIDIA to ABW.

Example responsibilities:

- call `abw version` and `abw doctor` for health;
- call `abw ask "..."` for governed user requests;
- call `abw inspect`, `abw gaps`, and `abw recover-plan` for workspace state;
- call continuation gate scripts only through a documented interface;
- capture stdout, exit code, and structured JSON when available;
- treat non-zero exit codes and approval-required statuses as stops, not soft warnings.

This phase is easier to debug and avoids coupling two codebases too early.

### Phase 2: Local Service / FastAPI Bridge

After the CLI bridge is stable, NVIDIA can call ABW's local API.

Recommended contract:

- NVIDIA starts or connects to an ABW local service.
- NVIDIA registers workspaces with `/register-workspace`.
- NVIDIA uses `/route-query` before `/ask` for multi-workspace ambiguity.
- NVIDIA displays `trust_score`, `retrieval_status`, `sources`, and `warnings`.
- NVIDIA treats `no_match`, `wrong_workspace`, `ambiguous`, and `no_confident_workspace` as user-visible states.
- NVIDIA does not hide low trust behind confident UI.

### Phase 3: Event and Governance Contract

Later, ABW and NVIDIA can share a richer event contract:

- selected workspace,
- route decision,
- evidence sources,
- continuation gate result,
- approval requirements,
- accepted completion artifact,
- handover record.

This should be a protocol boundary, not a source merge.

## Technical Boundaries

ABW owns:

- governance semantics;
- evidence status;
- gap logging;
- route decisions;
- continuation policy;
- acceptance/evaluation policy;
- workspace registry and ABW workspace health;
- release discipline for the ABW engine.

Product shells own:

- user interface;
- chat/session UX;
- active agent orchestration;
- editor/terminal/tool embedding;
- app-specific permissions;
- product-specific telemetry and settings.

Shared boundary:

- CLI command contract;
- local API contract;
- structured outputs;
- documented exit statuses;
- workspace paths and registry entries.

Forbidden boundary crossing:

- ABW must not silently write into unrelated repositories.
- Product shells must not bypass ABW gates while presenting work as governed.
- Neither side should mechanically merge source trees.

## What ABW Is Not

ABW is not:

- an inference provider;
- a product command center;
- a replacement for an IDE;
- a replacement for human approval;
- a source of truth without citations;
- a task runner that may execute arbitrary work without governance;
- a generic knowledge base that stores guesses in `wiki/`;
- a product shell like NVIDIA Agent IDE;
- a reason to merge unrelated repositories into one codebase.

ABW is a constitutional governance layer.

## Current Architecture Assessment

### Strengths

- The repo already separates package CLI, workflow docs, skills, scripts, templates, schemas, examples, and tests.
- The Continuation Kernel is specified and implemented through a machine gate.
- The package runtime has a clear dev-mode vs packaged fallback story.
- The local API is already broad enough for future UI and shell integration.
- Multi-workspace route-then-ask exists through `.brain/workspaces.json`, `/route-query`, and `/ask`.
- Tests explicitly cover fake proof rejection, continuation gates, router behavior, API behavior, workspace registry, and CLI parity.
- Release notes for `v1.1.0` identify trust/retrieval and workspace routing hardening.

### Weaknesses

- README currently undersells ABW as a small CLI rather than the full governance layer present in the repo.
- Some workflow and skill files show mojibake in Vietnamese text. This creates documentation trust risk and should be fixed without changing policy meaning.
- The local API is present but not yet described as a formal integration contract.
- Changelog and release notes are not fully converged. `CHANGELOG.md` trails many release tags while `docs/releases/v1.1.0.md` carries newer truth.
- There is still a visible dual-runtime burden: canonical `scripts/` in dev mode and `_legacy/` packaged fallback. Mirror drift tests exist, but the boundary remains maintenance-heavy.
- Schemas cover some state files, but many governance-critical files still rely on templates and tests rather than formal JSON schemas.

## Roadmap

### Short Term

- Adopt this README after human review by replacing `README.md` only if approved.
- Add a concise integration contract document for CLI bridge callers.
- Add API response examples for `/ask`, `/route-query`, `/inspect`, `/gaps`, and continuation gate results.
- Fix mojibake in workflow and skill docs using a controlled encoding audit.
- Align `CHANGELOG.md`, `VERSION`, `pyproject.toml`, release notes, and git tags.
- Add schemas for continuation policy, backlog, unsafe zones, locked decisions, knowledge gaps, and acceptance requests.
- Document exit codes and blocking states for CLI bridge use.

### Medium Term

- Stabilize an ABW local service mode for product shells.
- Add contract tests that verify CLI and API return equivalent governance states.
- Formalize route decisions: `route`, `ambiguous`, `wrong_workspace`, `no_match`, `no_confident_workspace`.
- Reduce dev/package mirror burden by making runtime source selection and mirror drift reports more explicit.
- Build first-class workspace backup/export guidance for GitHub and local snapshots.
- Add integration smoke tests using a mock external product shell.
- Extend grounding backend abstraction beyond NotebookLM while preserving no-fake-grounding semantics.

### Long Term

- Treat ABW as a versioned governance protocol.
- Keep product shells thin at the governance boundary.
- Support multiple app shells calling the same ABW workspace safely.
- Build a stable event stream for route decisions, gate decisions, gaps, acceptance, handovers, and release metadata.
- Make governance files fully schema-validated and migration-aware.
- Provide signed or reproducible release artifacts for the ABW engine.

## Open Architecture Decisions

- What is the stable CLI JSON contract for external shells?
- Should local API endpoints expose continuation gate and acceptance gate directly, or only through existing workflow/CLI wrappers?
- Which `.brain/` files should be versioned, sanitized, ignored, or backed up by default?
- Should `scripts/` remain canonical in dev mode long term, or should runtime code converge into `src/abw/` with scripts as thin wrappers?
- How should ABW represent grounding backends after NotebookLM: provider abstraction, plugin system, or explicit backend adapters?
- What exact permissions should product shells have when invoking ABW against another repository?
- How should ABW expose approval-required states to UI without encouraging users to click through them?
- What is the minimum evidence contract NVIDIA must show before marking work as accepted?

## Risks

- Documentation drift: workflow docs, README, release notes, and runtime behavior can diverge.
- Encoding drift: mojibake in policy files can weaken operator understanding and automated matching.
- Source merge temptation: merging ABW into a product shell would blur governance and application concerns.
- Fake integration risk: UI may call ABW health endpoints but bypass gates for actual actions.
- Overconfident retrieval: low-source answers must stay visibly low trust.
- Grounding dependency: NotebookLM-first implementation needs honest degraded mode when MCP or auth is unavailable.
- Runtime mirror drift: packaged fallback must keep matching canonical behavior.
- `.brain/` noise: append-only logs and nonces can grow large and should be backed up or ignored intentionally.

## GitHub Backup / Release Discipline

Canonical ABW repository:

```text
D:\Sandbox\skill-Anti-brain-wiki_note
https://github.com/Nakazasen/skill-Anti-brain-wiki_note
```

NVIDIA integration target:

```text
D:\Sandbox\Nvidia
https://github.com/Nakazasen/nvidia-server
```

Release discipline should include:

1. Keep `VERSION`, `pyproject.toml`, `src/abw/__init__.py`, release notes, and git tags aligned.
2. Run baseline tests before release.
3. Record release verification in `docs/releases/`.
4. Build wheel artifacts under `dist/`.
5. Keep migration and rollback notes for each release.
6. Push ABW releases to the canonical ABW repository.
7. Do not use the NVIDIA repository as backup storage for ABW source.
8. For integration work, commit bridge code in the product shell and governance code in ABW.
9. Use explicit tags for ABW versions consumed by external shells.
10. Never present an unverified local integration as a released bridge.

## Development Rules

- Do not delete old content without a reviewed migration path.
- Do not overwrite `README.md` with this file until a human reviews and approves it.
- Do not write ABW guesses into `wiki/`.
- Do not claim grounded status without provenance.
- Do not execute continuation work without passing the gate.
- Do not silently reverse locked decisions.
- Do not write outside the intended workspace.
- Do not merge ABW source mechanically into product shells.

## Conclusion

ABW should continue as the canonical governance engine: grounded memory, reality checking, routing, continuation control, and acceptance discipline. NVIDIA should continue as the product shell and active agent runtime. Their integration should be contractual, first through a CLI bridge and later through the local API, without collapsing the two repositories into one source tree.
