# Core System Invariants & Reasoning Policy
> Version: 1.3.1

Hybrid ABW (Anti-Brain-Wiki) is an operating discipline for AI work that enforces strict governance on how information is processed and actions are executed. It operates on a **4-Tier Adaptive Reasoning Policy**.

## The Adaptive Router (`/abw-ask`)

**Role:** The single entry point for all user questions.
**Policy:**

- Automatically scans `wiki/` and `raw/` to detect if the project is Greenfield or Knowledgeable.
- Evaluates query complexity and dynamically dispatches execution to Tier 1, Tier 2, or Tier 3 logic.

## Tier 1: Fast Path (`/abw-query`)

**Use Case:** Simple queries, definitions, precise procedural questions.
**Condition:** Data MUST exist in `wiki/`.
**Policy:**

- 1-pass retrieval. No Test-Time Compute (TTC) loop.
- If the answer is not in the wiki, DO NOT hallucinate.
- Log the missing information into `.brain/knowledge_gaps.json`.
- Advise the user to ingest raw sources using `/abw-ingest`.

## Tier 2: Deliberative Path (`/abw-query-deep`)

**Use Case:** Architecture comparison, RCA, tradeoff analysis, resolving contradictions.
**Condition:** Complex questions requiring deep reasoning over existing `wiki/` and `raw/` data.
**Policy:**

- Executes 3-5 passes of bounded Test-Time Compute (Decomposition -> Evidence Assembly -> Grounding -> Self-Critique -> Repair).
- Must pass the exit gate score (e.g., >8/10) to return a final answer.
- If 2 consecutive critique loops yield no new evidence delta, trigger the Circuit Breaker and stop.

## Tier 3: Bootstrap Path (`/abw-bootstrap`)

**Use Case:** Greenfield projects, brand new ideas, undefined scope, missing data.
**Condition:** NO data exists in `raw/` or `wiki/`.
**Policy:**

- **DO NOT fake knowledge.** Shift from "grounded knowledge mode" to "hypothesis-driven mode".
- The model is only allowed to compile **reasoning state** (uncertainty), not facts.
- Must output 4 specific artifacts to `.brain/bootstrap/`:
  1. `assumptions.json`: What beliefs are currently guiding the thought process?
  2. `hypotheses.json`: What are the competing approaches?
  3. `decision_log.jsonl`: Provisional or final decisions.
  4. `validation_backlog.json`: The absolute cheapest next experiments to verify assumptions.

## Tier 4: Governed Action Path (`/abw-resume`)

**Use Case:** Continuing an interrupted project while maintaining continuity and safety.
**Condition:** Complex project in motion with existing state in `.brain/`.
**Policy:**

- **Action Governance:** Every writable action must pass the **Continuation Kernel v1 Gate**.
- **Constraint Gate:** Validates the next step against:
  1. `unsafe_zones.json`: Hard blocks (user-declared) or audit requirements (historical).
  2. `locked_decisions.json`: Blocks silent reversals of established architectural choices.
  3. `effective_budget`: Enforces both file count and line-change limits.
  4. `knowledge_gaps.json`: Blocks steps dependent on missing critical info.
- **Outcome Recording:** All execution outcomes must be recorded to `.brain/step_history.jsonl` and `.brain/handover_log.jsonl` to adjust future budgets.
- If the gate returns `blocked` or `approval_required`, the Agent must STOP and request explicit user intervention.

---

## Strict "No Fake Success" Rule

- If NotebookLM MCP (Grounding engine) is down, gracefully degrade to `draft` or `pending_grounding`. Never fake `grounded` status.
- If a user asks to build an app but provides no context, fallback to Tier 3 (Bootstrap) to extract constraints instead of blindly writing code.
