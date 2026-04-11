# AGENTS.md -- Hybrid Anti-Brain-Wiki System Architecture

> **Version:** 1.1.0  
> **System:** Hybrid ABW for Antigravity IDE  
> **Purpose:** Upgrade Gemini Flash's grounding capability through structured memory, persistent knowledge, verifiable evidence chains, and bounded deliberation  
> **Last Updated:** 2026-04-11T23:30:00+07:00

---

## 1. System Philosophy

Hybrid ABW does **not** assume the model is smarter. It makes the model **more effective** by providing:

- **Operational memory** that persists across sessions
- **Persistent knowledge** with structure, citations, and grounding status
- **Deep grounding** on private data via NotebookLM
- **Honest gap detection** instead of plausible-sounding hallucinations

### Core Principle
> **"A cited answer beats a confident guess. A logged gap beats a fake answer."**

---

## 2. Memory Layer Separation

The system enforces strict boundaries between three memory layers:

```
+---------------------------------------------------------------------+
|                        Hybrid ABW Architecture                       |
+---------------------------------------------------------------------+
|                                                                       |
|  +--------------+    +--------------+    +----------------------+   |
|  |   .brain/     |    |   wiki/       |    |   NotebookLM MCP     |   |
|  |  OPERATIONAL  |    |  PERSISTENT   |    |   GROUNDING ENGINE   |   |
|  |  MEMORY       |    |  KNOWLEDGE    |    |                      |   |
|  +--------------+    +--------------+    +----------------------+   |
|  | session.json  |    | entities/     |    | Verify claims        |   |
|  | brain.json    |    | concepts/     |    | Synthesize evidence  |   |
|  | grounding_    |    | timelines/    |    | Cross-check sources  |   |
|  |   queue.json  |    | sources/      |    | Deep-query private   |   |
|  | knowledge_    |    | _schemas/     |    |   data               |   |
|  |   gaps.json   |    | _indexes/     |    |                      |   |
|  | session_log   |    | index.md      |    | [!] May be unavail.  |   |
|  +------+-------+    +------+-------+    +----------+-----------+   |
|         |                    |                        |               |
|         |    +---------------+                        |               |
|         |    |    +----------------------------------+               |
|         v    v    v                                                   |
|  +------------------+    +--------------+                           |
|  |   processed/      |    |    raw/       |                           |
|  |  EVIDENCE LAYER   |    |  RAW SOURCE   |                           |
|  |  manifest.jsonl   |    |  (untouched)  |                           |
|  +------------------+    +--------------+                           |
|                                                                       |
+---------------------------------------------------------------------+
```

### Layer Responsibilities

| Layer | What it holds | What it does NOT hold | Lifetime |
|-------|--------------|----------------------|----------|
| `.brain/` | Session state, task progress, blockers, handover, grounding queue, knowledge gaps | Long-form knowledge, prose, compiled facts | Session-scoped (with snapshots) |
| `wiki/` | Compiled, cited, grounded knowledge notes with schema-compliant frontmatter | Session state, pending tasks, operational data | Permanent (with staleness tracking) |
| `processed/` | Normalized evidence with provenance (manifest.jsonl) | Raw files, wiki notes, session data | Permanent (append-only) |
| `raw/` | Original source files, untouched | Anything processed or compiled | Permanent (immutable after intake) |
| `NotebookLM` | Private data for deep grounding queries | Source of truth (it's a verification tool) | External (Google-managed) |

### Invariant Rules

1. **`.brain/` NEVER stores long-term knowledge.** It coordinates; `wiki/` remembers.
2. **`wiki/` is NEVER updated directly from `raw/`.** All data must pass through `processed/` first.
3. **`wiki/` notes ALWAYS have a manifest reference.** No orphan knowledge without provenance.
4. **`raw/` files are NEVER modified.** They are the immutable evidence trail.
5. **`processed/manifest.jsonl` is append-only.** Existing lines are never deleted (status can change).

---

## 3. Grounding Policy

### Definition
"Grounding" means verifying claims against source evidence before committing them to wiki/.

### Grounding Engines

| Engine | When Used | Trust Level |
|--------|-----------|-------------|
| `notebooklm` | Primary -- when MCP is available | High (multi-source synthesis) |
| `manual` | User explicitly confirms a claim | Medium (human judgment) |
| `none` | Fallback -- claim recorded as draft | Low (unverified) |

### Grounding Process
```
1. Extract claims from processed source
2. Formulate verification query
3. Submit to grounding engine:
   a. NotebookLM MCP -> notebook_query with source context
   b. Manual -> present claims to user for confirmation
   c. None -> skip grounding, mark as draft
4. Record grounding result in manifest AND wiki note frontmatter
5. Assign confidence level based on grounding outcome
```

### Confidence Assignment

| Scenario | Confidence | Status |
|----------|------------|--------|
| >=2 independent sources agree, engine verified | `high` | `verified` |
| 1 source, engine verified | `medium` | `grounded` |
| 1 source, no engine verification | `low` | `draft` |
| No source verification attempted | `unverified` | `draft` |
| Sources contradict each other | varies | `disputed` |
| Note older than 30 days, not re-verified | varies | `stale` |

### What Grounding is NOT
- Grounding is NOT asking the model "is this true?" (that's circular)
- Grounding is NOT checking Wikipedia (no external web search)
- Grounding is NOT one-time -- notes can be re-grounded when sources change

---

## 4. Compile Policy

### Definition
"Compiling" means transforming processed evidence into a structured wiki note.

### Pipeline
```
raw/ -> processed/ extraction -> grounding -> wiki/ compile -> index update -> .brain/ log
```

### Compile Rules

1. **Schema compliance**: Every wiki note MUST follow `wiki/_schemas/note.schema.md`
2. **Source attribution**: Every claim MUST have at least one source reference
3. **Idempotency**: Re-ingesting the same source (by SHA-256 checksum) MUST NOT create duplicates
4. **Merge over replace**: If a wiki note already exists, new evidence is MERGED, not overwritten
5. **Cross-linking**: New notes MUST establish bidirectional links with related existing notes
6. **Index update**: `wiki/index.md` MUST be updated after every compile

### Merge Strategy (When Note Exists)

| Existing Status | New Evidence | Action |
|-----------------|-------------|--------|
| `verified` | Agrees | Add source, keep status |
| `verified` | Contradicts | Add contradiction entry, set `disputed` |
| `grounded` | Higher confidence | Upgrade status, add source |
| `draft` | Any grounded | Upgrade to `grounded`, merge content |
| `stale` | Any | Re-compile, update timestamp, re-evaluate status |

---

## 5. Query Policy

### Routing Order (Strict)

```
Layer 1: .brain/ recap     -> Operational context (NOT authoritative)
Layer 2: wiki/ search      -> Persistent knowledge (PRIMARY source)
Layer 3: NotebookLM query  -> Deep grounding (SECONDARY, on-demand)
Layer 4: Gap logging       -> Honest "I don't know" (ALWAYS logged)
```

### Layer Behavior

| Layer | Action | Citable? | Can answer alone? |
|-------|--------|----------|-------------------|
| 1. `.brain/` | Check session context | No (operational only) | No -- supplements only |
| 2. `wiki/` | Search notes by topic | Yes | Yes -- if confidence >= medium |
| 3. `NotebookLM` | Deep query private data | Yes (with notebook ref) | Yes -- then compile to wiki |
| 4. Gap log | Record knowledge gap | N/A | No -- returns partial answer |

### Citation Requirements

All answers MUST include:
```markdown
**Sources:**
- [1] Path to wiki note or NotebookLM reference
- [2] ...

**Provenance:**
- [1] <- manifest line <- raw source path
```

Answers without citations MUST be flagged as `unverified`.

### Answer Quality Hierarchy
```
Best:    Wiki answer, confidence: high, status: verified, full citation chain
Good:    Wiki answer, confidence: medium, status: grounded
OK:      NotebookLM answer, compiled to wiki draft
Poor:    Partial answer + gap logged
Worst:   [X] NEVER: Confident-sounding answer without any citation (FORBIDDEN)
```

---

## 6. Fallback Policy (NotebookLM MCP Unavailable)

### Detection
MCP is considered "unavailable" when:
- `notebook_list` times out or returns an error
- Auth tokens are expired
- `nlm login` has not been run
- Network connectivity issues

### Degradation Strategy

The system MUST degrade **safely and honestly**:

```
+--------------------------------+-------------------------------------+
|  Normal Mode                    |  Fallback Mode                      |
+--------------------------------+-------------------------------------+
|  ingest: raw -> grounded wiki    |  ingest: raw -> draft wiki + QUEUE   |
|  query: wiki + NotebookLM       |  query: wiki only + GAP LOG         |
|  delib: full 5-pass loop        |  delib: wiki-only + budget=0        |
|  lint: full 12-check audit      |  lint: 11 checks + MCP status report|
+--------------------------------+-------------------------------------+
|  Status assignments: grounded   |  Status assignments: draft ONLY     |
|  Confidence: medium-high        |  Confidence: low-unverified ONLY    |
+--------------------------------+-------------------------------------+
|  [OK] Full capability             |  [WARN] Reduced but HONEST capability   |
+--------------------------------+-------------------------------------+
```

### What MUST NOT Happen in Fallback Mode

| Forbidden Action | Why |
|-----------------|-----|
| Set `status: grounded` without engine verification | **Fake success** |
| Set `confidence: high` without grounding | **Misleading** |
| Skip gap logging when answer is insufficient | **Knowledge loss** |
| Retry MCP aggressively (>3 attempts/minute) | **Rate limit risk** |
| Silently drop grounding queue items | **Data loss** |

### Recovery When MCP Restored

```
1. Verify connection: notebook_list
2. Update bridge config: mcp_status -> "active"
3. Count pending grounding queue items
4. Notify user: "[OK] MCP restored! <N> items awaiting grounding."
5. Suggest: "Run ingest-wiki to process the grounding queue."
6. Process queue items one by one (respect rate limits)
```

---

## 7. Deliberation Policy (v1.1.0)

For complex queries (synthesis, comparison, root cause, design decisions), the system uses a **bounded thinking loop** instead of single-pass lookup.

### Routing
```
User Query -> Classify -> FAST (query-wiki 4-layer) or DELIBERATIVE (query-wiki-deliberative 5-pass)
```

### Deliberation Architecture
```
Pass 1: Decomposition     -- break query into sub-problems
Pass 2: Evidence Assembly  -- wiki-first evidence gathering
Pass 3: NotebookLM         -- conditional, budget-controlled (max 2 queries)
Pass 4: Self-Critique      -- score 5 criteria, 0-2 each (max 10)
Pass 5: Repair or Exit     -- fix weaknesses or return best answer
```

### Exit Gate (score-based, not feeling-based)
| Score | Action |
|-------|--------|
| >= 8  | Early exit -- answer is sufficient |
| 5-7   | One more round (unless at max_rounds) |
| < 5   | Partial answer + gap log |

### Circuit Breaker (prevents stuck loops)
Triggers: duplicate NbLM query, no new evidence x2, contradiction stall x2, score plateau x2, max_rounds, token budget.

### Invariant Rules
- Deliberation runs are ALWAYS logged to `.brain/deliberation_runs.jsonl`
- Exit gate is ALWAYS score-based, never "feels done"
- Circuit breaker is ALWAYS active -- no unbounded loops
- Fast path queries NEVER go through deliberation
- NotebookLM calls are ALWAYS budget-controlled

---

## 8. Skill Reference

| Skill | File | Purpose |
|-------|------|---------|
| `abw-ingest` | `skills/ingest-wiki.md` | 6-stage pipeline: raw -> processed -> grounding -> wiki -> index -> .brain |
| `abw-query` | `skills/query-wiki.md` | Routing gate + 4-layer fast lookup: .brain -> wiki -> NotebookLM -> gap log |
| `abw-query-deep` | `skills/query-wiki-deliberative.md` | 5-pass bounded deliberation for complex queries with exit gate and circuit breaker |
| `abw-lint` | `skills/lint-wiki.md` | 12-check audit: structure, grounding, staleness, TTC health |
| `notebooklm-mcp-bridge` | `skills/notebooklm-mcp-bridge.md` | MCP configuration, setup, fallback, and TTC budget tracking |
| `abw-status` | `skills/abw-status.md` | Quick health check for queue and MCP connection |
| `abw-setup` | `skills/abw-setup.md` | Interactive setup wizard for NotebookLM authentication |

---

## 9. File Reference

### Core Artifacts

| File | Purpose | Created By |
|------|---------|------------|
| `processed/manifest.jsonl` | Evidence provenance tracking (status: extracted->pending_grounding->grounded->compiled) | ingest-wiki |
| `.brain/grounding_queue.json` | Pending grounding operations | ingest-wiki (fallback) |
| `.brain/knowledge_gaps.json` | Unresolved knowledge questions | query-wiki |
| `.brain/deliberation_runs.jsonl` | Audit trail for deliberative queries (append-only) | query-wiki-deliberative |
| `.brain/exit_gate_policy.json` | Configurable exit gate thresholds and limits | query-wiki-deliberative |
| `.brain/circuit_breaker.json` | Circuit breaker trigger config | query-wiki-deliberative |
| `wiki/index.md` | Central knowledge index | ingest-wiki, lint-wiki |
| `wiki/_schemas/note.schema.md` | Schema contract for wiki notes | System (immutable) |
| `brain-state-helper-bridge.md` | Bridge rules between `.brain/` and `wiki/` -- data flow, conflict resolution | System (immutable) |
| `.gitignore` | Runtime state exclusion policy (aligned with AWF save_brain.md) | System |

### AWF Compatibility

| AWF File | Relationship to ABW |
|----------|-------------------|
| `.brain/brain.json` | <-> Coexists -- ABW does NOT modify this file |
| `.brain/session.json` | <-> Coexists -- ABW reads for Layer 1 recap, does NOT modify |
| `.brain/session_log.txt` | <-> Coexists -- ABW appends delta entries only |
| `.brain/snapshots/` | <-> Coexists -- ABW does NOT modify these |
| `.brain/summaries/` | <-> Coexists -- ABW may add wiki-related summaries |

---

## 9. Data Flow Diagrams

### Ingest Flow
```
User drops file
       |
       v
   +--------+     +------------+     +-------------+     +-----------+
   |  raw/   |---->| processed/  |---->| NotebookLM   |---->|  wiki/     |
   | (store) |     | (extract+   |     | (grounding)  |     | (compile)  |
   |         |     |  manifest)  |     |              |     |            |
   +--------+     +------------+     +------+-------+     +-----+-----+
                                             |                    |
                                      +------v-------+     +-----v-----+
                                      | grounding_    |     | index.md   |
                                      | queue.json    |     | (update)   |
                                      | (if fallback) |     +-----------+
                                      +--------------+
```

### Query Flow
```
User asks question
       |
       v
+--------------+   found    +--------------+
| L1: .brain/   |---------->| Supplement    |-+
| (context)     |           | context       | |
+------+-------+           +--------------+ |
       | not found                           |
       v                                     |
+--------------+   found    +--------------+ |
| L2: wiki/     |---------->| Answer with   |<+
| (search)      |           | citations     |
+------+-------+           +--------------+
       | insufficient                ^
       v                             |
+--------------+   found             |
| L3: NbookLM   |-------------------+
| (deep ground) |
+------+-------+
       | unavailable/insufficient
       v
+--------------+
| L4: Gap Log   |
| + partial ans |
+--------------+
```

### Lint Flow
```
lint-wiki triggered
       |
       v
+-----------------------------------------+
|  Run 12 checks in sequence:             |
|  1. Orphan notes                         |
|  2. Dead links                           |
|  3. Duplicate entities                   |
|  4. Contradiction candidates             |
|  5. Ungrounded notes                     |
|  6. Stale notes                          |
|  7. Schema compliance                    |
|  8. Manifest integrity                   |
|  9. Notebook grounding health            |
|  10. Gate exit failures (TTC)            |
|  11. Stale-but-high-priority (TTC)       |
|  12. Contradiction clusters (TTC)        |
+--------------+--------------------------+
               |
               v
+--------------------------+
|  Lint Report              |
|  [ERR] Errors | [WARN] Warnings |
|  [INFO] Info   | Actions      |
+--------------------------+
```

---

## 11. Anti-Patterns (What NOT To Do)

| Anti-Pattern | Why It's Dangerous | Correct Approach |
|-------------|-------------------|-----------------|
| Write directly from `raw/` to `wiki/` | No provenance trail | Always go through `processed/` |
| Skip grounding, set status: `grounded` | **Fake success** -- worst violation | Use `draft` if grounding skipped |
| Use `.brain/` to store knowledge | Operational memory != knowledge | Store knowledge in `wiki/` only |
| Ignore knowledge gaps | System appears more capable than it is | Always log gaps honestly |
| Overwrite existing verified notes | Destroys evidence history | Merge new evidence instead |
| Trust NotebookLM as absolute truth | It's a tool, not an oracle | Cross-verify, track confidence |
| Create notes without `updated_at` | Impossible to detect staleness | Schema enforces this field |
| Skip index update after compile | Notes become invisible to query | Always update `wiki/index.md` |
| Run deliberation for simple lookups | Wastes compute, no quality gain | Use fast path via query-wiki |
| Deliberation loop without scoring | No exit criteria = infinite risk | Always score with exit gate |
| Self-critique without evidence check | "Feels done" is not valid | Score tied to citations only |
| Call NotebookLM every deliberation round | Rate limits, diminishing returns | Budget-controlled, max 2 queries |
| Skip deliberation run logging | Cannot debug or tune exit policy | Always append to deliberation_runs |
| No circuit breaker | Risk of stuck loops | Always check breaker after each pass |

---

*Created: 2026-04-11 | Hybrid Anti-Brain-Wiki v1.1.0 | Compatible with AWF 4.1 Eternal Context Design*
