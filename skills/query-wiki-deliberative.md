# Skill: query-wiki-deliberative

> **Version:** 1.0.0
> **Trigger:** Routed from `query-wiki` when query classified as "deliberative"
> **Dependencies:** `wiki/`, `.brain/`, `processed/manifest.jsonl`, `.brain/knowledge_gaps.json`
> **Auto-created on first use:** `.brain/exit_gate_policy.json` (from template), `.brain/circuit_breaker.json` (from template)
> **MCP:** `notebooklm` (optional -- degrades gracefully)
> **Output:** `.brain/deliberation_runs.jsonl` (append-only)

---

## Purpose

Handle complex queries (synthesis, comparison, root cause, design decisions) through a **bounded thinking loop** with evidence-backed self-critique and score-based exit detection. This skill is the "slow thinking" complement to `query-wiki`'s "fast lookup."

### When This Skill is Used

This skill is NEVER called directly by the user. It is invoked by `query-wiki.md` when the query meets deliberative routing criteria. See `query-wiki.md` Section "Routing Gate" for the classification logic.

---

## Architecture Overview

```
+------------------+
|  query-wiki      |  <-- entry point
|  (routing gate)  |
+--------+---------+
         |
         | deliberative path
         v
+------------------+     +-------------------+
|  PASS 1          |---->|  PASS 2            |
|  Decomposition   |     |  Evidence Assembly |
+------------------+     +--------+----------+
                                  |
                                  v
                          +-------------------+
                          |  PASS 3            |
                          |  NotebookLM        |
                          |  (conditional)     |
                          +--------+----------+
                                   |
                                   v
                          +-------------------+
                          |  PASS 4            |
                          |  Self-Critique     |
                          |  + Exit Gate Score |
                          +--------+----------+
                                   |
                          +--------v----------+
                          |  EXIT DECISION     |
                          |  score >= 8: exit  |
                          |  score 5-7: loop   |
                          |  score < 5: partial|
                          +-------------------+
                                   |
                               (if loop)
                                   |
                          +--------v----------+
                          |  PASS 5            |
                          |  Repair + Re-score |
                          +-------------------+
```

---

## Initialization

Before starting the deliberation loop:

```
1. Load exit gate policy:
   IF .brain/exit_gate_policy.json does NOT exist:
       -> copy templates/exit_gate_policy.example.json to .brain/exit_gate_policy.json
       -> log: "Created exit gate policy from template"
   THEN:
       -> parse .brain/exit_gate_policy.json
       -> IF parse fails OR required keys missing (scoring_criteria, thresholds, limits):
           -> delete corrupted file
           -> copy templates/exit_gate_policy.example.json to .brain/exit_gate_policy.json
           -> log: "[!] Reset corrupted exit gate policy from template"
       -> validate: thresholds.early_exit, thresholds.continue, limits.max_rounds must exist
       -> policy = parsed result

2. Load circuit breaker config:
   IF .brain/circuit_breaker.json does NOT exist:
       -> copy templates/circuit_breaker.example.json to .brain/circuit_breaker.json
       -> log: "Created circuit breaker config from template"
   THEN:
       -> parse .brain/circuit_breaker.json
       -> IF parse fails OR required keys missing (triggers, on_break):
           -> delete corrupted file
           -> copy templates/circuit_breaker.example.json to .brain/circuit_breaker.json
           -> log: "[!] Reset corrupted circuit breaker config from template"
       -> breaker = parsed result

3. Initialize run record:
   run = {
     run_id: "delib-<YYYYMMDD>-<XXXX>",
     query: <original_query>,
     mode: "deliberative",
     rounds: 0,
     max_rounds: policy.limits.max_rounds,
     passes: [],
     scores: {},
     used_wiki_notes: [],
     used_manifest_refs: [],
     used_notebooklm: false,
     notebooklm_queries: [],
     gaps_logged: [],
     created_at: <ISO 8601>
   }
```

---

## Pass 1: Decomposition

### Purpose
Break the query into structured sub-problems before searching.

### Actions
```
1. Parse the user query into:
   - what_is_asked: core question in one sentence
   - evidence_needed: what wiki notes/sources would answer this
   - known_gaps: what is likely missing based on query complexity
   - verification_needed: what claims must be cross-checked

2. Check .brain/deliberation_runs.jsonl for recent runs on similar query:
   IF similar run found within cooldown window:
       -> return cached result
       -> STOP (no duplicate deliberation)

3. Log pass result to run.passes[]
```

### Output
A structured decomposition object. This guides all subsequent passes.

---

## Pass 2: Evidence Assembly (wiki-first)

### Purpose
Gather all relevant evidence from local wiki before considering external grounding.

### Actions
```
1. Search wiki/index.md for entries matching decomposition keywords
2. Full-text search across wiki/entities/, wiki/concepts/, wiki/timelines/, wiki/sources/
3. For each match:
   - Read YAML frontmatter (status, confidence, grounding)
   - Check for stale flag (updated_at > 30 days)
   - Check for disputed flag
   - Track manifest references (provenance chain)
4. Collect contradictions between matched notes
5. Build evidence inventory:
   - strong_evidence: notes with status in {grounded, verified}, confidence >= medium
   - weak_evidence: notes with status = draft, confidence = low
   - contradictions: pairs of conflicting notes
   - stale_notes: notes needing re-grounding
6. Log pass result to run.passes[]
```

### Decision
```
IF strong_evidence sufficient AND contradictions == 0:
    -> skip Pass 3 (no NotebookLM needed)
    -> proceed to Pass 4
ELSE:
    -> proceed to Pass 3
```

---

## Pass 3: NotebookLM Grounding (Conditional)

### Pre-check
```
IF NotebookLM MCP available AND query_budget > 0:
    -> proceed
ELSE:
    -> skip, note "NotebookLM unavailable" in pass result
    -> proceed to Pass 4 with reduced expectations
```

### Trigger Conditions (any one sufficient)
- Evidence confidence still low after Pass 2
- Contradictions found between wiki notes
- Synthesis required across multiple weak sources
- Query has high-stakes flag (user explicitly needs accuracy)

### Actions
```
1. Formulate targeted query based on decomposition (Pass 1)
   - DO NOT re-ask the raw user query
   - Ask specific gap-filling questions
2. Execute notebook_query(notebook_id=<id>, query=<targeted_query>)
3. Track query in run.notebooklm_queries[]
4. Evaluate response:
   IF substantive -> add to evidence inventory
   IF generic/unhelpful -> note as "NotebookLM insufficient"
5. Decrement query_budget
6. Log pass result to run.passes[]
```

### Budget Control
```
max_notebooklm_queries = policy.limits.max_notebooklm_queries (default: 2)
query_budget starts at max_notebooklm_queries
Each query decrements by 1
When budget = 0: no more NotebookLM calls regardless of need
```

---

## Pass 4: Self-Critique + Exit Gate Scoring

### Purpose
The critical pass. Score the current answer draft against 5 objective criteria.

### Scoring Criteria

| Criterion | 0 | 1 | 2 |
|-----------|---|---|---|
| evidence_coverage | Missing primary source | Has source, incomplete | Sufficient sources |
| citation_integrity | No provenance traceable | Partial chain | Full chain: wiki -> manifest -> raw |
| consistency | Unresolved contradiction | Ambiguity present | Fully consistent |
| grounding_status | All cited notes draft/unverified | Mixed grounded/draft | All grounded/verified |
| answer_completeness | Misses core question | Partial answer | Complete answer |

### Scoring Process
```
1. Draft the answer based on current evidence
2. Score each criterion 0-2
3. Calculate total (max 10)
4. Record scores in run.scores
5. Log pass result with scores to run.passes[]
```

### Exit Decision
```
total = sum of all 5 scores

IF total >= policy.thresholds.early_exit (default: 8):
    -> EXIT with final answer
    -> run.exit_reason = "score_threshold_met"

IF total >= policy.thresholds.continue (default: 5):
    -> proceed to Pass 5 (repair)
    -> IF already at max_rounds:
        -> EXIT with current answer + caveats
        -> run.exit_reason = "max_rounds_reached"

IF total < policy.thresholds.force_partial (default: 5):
    -> IF at max_rounds:
        -> EXIT with partial answer
        -> log gap to .brain/knowledge_gaps.json
        -> run.exit_reason = "insufficient_at_max_rounds"
    -> ELSE:
        -> proceed to Pass 5
```

---

## Pass 5: Repair or Exit

### Purpose
Fix specific weaknesses identified by self-critique, then re-score.

### Actions
```
FOR EACH criterion with score < 2:
    evidence_coverage = 0 or 1:
        -> Search for additional wiki notes (broader terms)
        -> If NotebookLM budget > 0: query for missing evidence
    citation_integrity = 0 or 1:
        -> Trace provenance chain for uncited claims
        -> Remove claims that cannot be traced
    consistency = 0 or 1:
        -> Present both sides of contradiction
        -> Mark answer section as "disputed"
    grounding_status = 0 or 1:
        -> Flag draft notes with caveat
        -> Queue for grounding in .brain/grounding_queue.json
    answer_completeness = 0 or 1:
        -> Re-read decomposition (Pass 1)
        -> Address missed sub-questions

AFTER repairs:
    -> Re-score (return to Pass 4 logic)
    -> Increment run.rounds
    -> Check circuit breaker
```

---

## Circuit Breaker

### Check (runs after every pass)
```
BREAK IF any condition is true:

1. duplicate_notebooklm_query:
   Same query string sent to NotebookLM >= threshold times (default: 2)
   AND score did not increase

2. no_new_evidence:
   >= N consecutive rounds (default: 2) added zero new wiki notes or manifest refs

3. contradiction_stall:
   Contradiction count unchanged after >= N repair passes (default: 2)

4. score_plateau:
   Exit gate score unchanged for >= N consecutive rounds (default: 2)

5. max_rounds_exceeded:
   run.rounds >= policy.limits.max_rounds

6. token_budget_exceeded:
   Cumulative tokens used > policy.limits.max_token_budget
```

### On Break
```
1. Set run.circuit_breaker_triggered = true
2. Set run.exit_reason = <trigger_name>
3. Return best current answer with label:
   "[!] Answer may be incomplete -- circuit breaker triggered: <reason>"
4. IF exit score < policy.on_break.log_gap_if_score_below:
   -> Log gap to .brain/knowledge_gaps.json
5. Append run record to .brain/deliberation_runs.jsonl
```

---

## Run Record (Append to `.brain/deliberation_runs.jsonl`)

After every deliberation (success or break), append one JSON line:

```json
{
  "run_id": "delib-<YYYYMMDD>-<XXXX>",
  "query": "<original user query>",
  "mode": "deliberative",
  "rounds": 3,
  "max_rounds": 4,
  "exit_reason": "score_threshold_met | max_rounds_reached | insufficient_at_max_rounds | circuit_breaker:<trigger>",
  "exit_score": 9,
  "circuit_breaker_triggered": false,
  "scores": {
    "evidence_coverage": 2,
    "citation_integrity": 2,
    "consistency": 1,
    "grounding_status": 2,
    "answer_completeness": 2
  },
  "passes": [
    {"pass": 1, "type": "decomposition", "result": "..."},
    {"pass": 2, "type": "evidence_assembly", "result": "..."},
    {"pass": 3, "type": "self_critique", "result": "score: 9/10"}
  ],
  "used_wiki_notes": ["wiki/concepts/example.md"],
  "used_manifest_refs": ["processed/manifest.jsonl#line-7"],
  "used_notebooklm": false,
  "notebooklm_queries": [],
  "result_status": "grounded | partial | gap_logged",
  "gaps_logged": [],
  "created_at": "<ISO 8601>",
  "duration_ms": 4200
}
```

---

## Answer Format

### Successful Deliberation (score >= 8)
```markdown
[Answer text with inline citations]

**Sources:**
- [1] wiki/concepts/topic.md (confidence: high, grounded: 2026-04-11)
- [2] processed/manifest.jsonl#line-7 <- raw/source-doc.pdf

**Deliberation:**
- Mode: deliberative (3 rounds)
- Exit score: 9/10
- Exit reason: score_threshold_met
```

### Partial Answer (circuit breaker or low score)
```markdown
[!] **Partial Answer -- Deliberation Incomplete**

[Best available answer with caveats]

**What is well-supported:**
[Claims with strong citations]

**What remains uncertain:**
[Claims without sufficient evidence]

**Sources:**
- [1] wiki/concepts/topic.md (confidence: medium, status: draft)

**Deliberation:**
- Mode: deliberative (4 rounds -- max reached)
- Exit score: 6/10
- Exit reason: max_rounds_reached
- Gap logged: .brain/knowledge_gaps.json -> gap-<id>

**Suggested next steps:**
1. Add source material to raw/ and run ingest-wiki
2. [Specific source suggestions]
```

---

## Error Handling

| Error | Response |
|-------|----------|
| exit_gate_policy.json corrupted | Reset from template, log warning |
| circuit_breaker.json corrupted | Reset from template, log warning |
| deliberation_runs.jsonl write failure | Log to console, continue answering |
| NotebookLM timeout during Pass 3 | Skip MCP, note in pass result, continue |
| All passes fail to improve score | Circuit breaker triggers, return partial |
| Same query within cooldown window | Return cached result from previous run |

---

## Anti-Patterns (What NOT To Do)

| Anti-Pattern | Why | Correct Approach |
|-------------|-----|-----------------|
| Run deliberation for simple lookups | Wastes compute, no quality gain | Use fast path in query-wiki |
| Loop without scoring | No exit criteria = infinite loop risk | Always score after each round |
| Self-critique without evidence check | "Feels done" is not a valid exit | Score must be tied to citations |
| Call NotebookLM every round | Rate limits, diminishing returns | Budget-controlled, max 2 queries |
| Skip run record logging | Cannot debug or tune exit policy | Always append to deliberation_runs |
| No circuit breaker | Risk of stuck loops | Always check breaker after each pass |
| Score based on answer length | Length != quality | Score based on evidence and provenance |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-04-11 | Initial -- bounded thinking loop with exit gate and circuit breaker |
