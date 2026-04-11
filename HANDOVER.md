# Hybrid Anti-Brain-Wiki -- Handover Report

> **Builder:** Claude Opus 4.6 (Lead System Architect)
> **Runtime Operator:** Gemini Flash (via Antigravity IDE)
> **Handover Date:** 2026-04-11T22:41:00+07:00
> **ABW Version:** 1.0.1 (post-review fixes applied)
> **AWF Compatibility:** 4.1 (Eternal Context Design)
> **Review Score:** 6.5/10 -> fixes applied for all 5 findings

---

## 1. What Was Built

### 1.1 Folder Structure

```
skill-Anti-brain-wiki_note/
|
+-- raw/                          # Immutable source files
+-- processed/                    # Normalized evidence layer
|   +-- manifest.jsonl            # EMPTY at init (runtime-populated, .gitignored)
|
+-- wiki/                         # Persistent knowledge base
|   +-- entities/
|   +-- concepts/
|   +-- timelines/
|   +-- sources/
|   +-- _indexes/
|   +-- _schemas/
|   |   +-- note.schema.md        # Schema contract
|   +-- index.md                  # Central index
|
+-- .brain/                       # Operational memory (AWF-compatible)
|   +-- grounding_queue.json      # EMPTY at init (runtime-populated, .gitignored)
|   +-- knowledge_gaps.json       # EMPTY at init (runtime-populated, .gitignored)
|   +-- snapshots/
|   +-- summaries/
|   +-- cache/
|
+-- notebooks/                    # NotebookLM workspace refs
+-- skills/
|   +-- ingest-wiki.md            # 6-stage pipeline
|   +-- query-wiki.md             # 4-layer routing
|   +-- lint-wiki.md              # 9-check audit
|   +-- notebooklm-mcp-bridge.md  # MCP stub (FALLBACK MODE)
|
+-- templates/                    # Example data (NOT live state)
|   +-- manifest.example.jsonl
|   +-- grounding_queue.example.json
|   +-- knowledge_gaps.example.json
|   +-- brain.example.json        # (pre-existing AWF)
|   +-- session.example.json      # (pre-existing AWF)
|   +-- preferences.example.json  # (pre-existing AWF)
|
+-- AGENTS.md                     # System architecture (10 sections)
+-- brain-state-helper-bridge.md  # Bridge rules .brain/ <-> wiki/
+-- HANDOVER.md                   # This file
+-- .gitignore                    # Runtime state exclusion policy
```

### 1.2 State Separation Policy

| File | Committed? | Populated By | Notes |
|------|-----------|-------------|-------|
| `processed/manifest.jsonl` | NO (.gitignored) | `ingest-wiki` at runtime | Starts empty, examples in `templates/` |
| `.brain/grounding_queue.json` | NO (.gitignored) | `ingest-wiki` fallback | Starts empty, examples in `templates/` |
| `.brain/knowledge_gaps.json` | NO (.gitignored) | `query-wiki` Layer 4 | Starts empty, examples in `templates/` |
| `wiki/_schemas/note.schema.md` | YES | System (immutable) | Schema contract |
| `wiki/index.md` | YES | `ingest-wiki`, `lint-wiki` | Auto-updated |
| `AGENTS.md` | YES | System | Architecture doc |
| `brain-state-helper-bridge.md` | YES | System | Bridge rules |
| `.gitignore` | YES | System | State exclusion |
| `skills/*.md` | YES | System | Skill definitions |
| `templates/*.example.*` | YES | System | Reference formats |

---

## 2. Active vs Pending Capabilities

### Active Now (no MCP needed)

| Capability | Status |
|------------|--------|
| Folder structure | Ready |
| Schema validation (`note.schema.md`) | Ready |
| Manifest tracking (append-only JSONL) | Ready |
| Manifest status lifecycle: `extracted -> pending_grounding -> grounded -> compiled` | Ready |
| Idempotency via SHA-256 checksum | Ready |
| Knowledge gap logging | Ready |
| Grounding queue management | Ready |
| Wiki index with auto-gen markers | Ready |
| ingest-wiki Stages 1-2, 4-6 | Ready |
| query-wiki Layers 1-2, 4 | Ready |
| lint-wiki Checks 1-8 | Ready |
| Brain-state bridge rules | Ready |
| AWF coexistence (zero breaking changes) | Ready |
| .gitignore (runtime state excluded) | Ready |

### Pending (needs NotebookLM MCP)

| Capability | Blocked By |
|------------|-----------|
| ingest-wiki Stage 3 (grounding) | MCP auth: run `nlm login` |
| query-wiki Layer 3 (deep grounding) | MCP auth |
| lint-wiki Check 9 (notebook health) | MCP auth |
| Status upgrade: draft -> grounded | Grounding engine required |
| Confidence upgrade: low -> medium/high | Grounding result required |

---

## 3. Manifest Status Enum (Definitive)

The manifest (`processed/manifest.jsonl`) uses a strict 5-value enum:

```
extracted  -->  pending_grounding  -->  grounded  -->  compiled
    \                                                     |
     +------------>  failed  <----------------------------+
```

| Status | Set At | Meaning | Idempotent? |
|--------|--------|---------|-------------|
| `extracted` | Stage 2 | Raw processed, manifest entry created | No -- resumes Stage 3 |
| `pending_grounding` | Stage 3 fallback | MCP unavailable, queued | No -- resumes Stage 3 |
| `grounded` | Stage 3 success | Claims verified by engine | Yes -- skips |
| `compiled` | Stage 6 | Full pipeline complete | Yes -- skips |
| `failed` | Any stage | Unrecoverable error | No -- retries Stage 2 |

The grounding queue (`.brain/grounding_queue.json`) uses a separate lifecycle:

```
pending  -->  in_progress  -->  completed | failed
```

These are DISTINCT enums. Manifest tracks the source. Queue tracks the grounding task.

---

## 4. Usage Guide

### Add a source to wiki

```
User: "Ingest this PDF about Kubernetes networking"

Pipeline:
  Stage 1: Copy to raw/
  Stage 2: Extract claims, append manifest (status: extracted)
  Stage 3: Ground via MCP (or queue if unavailable)
  Stage 4: Create wiki/concepts/kubernetes-networking.md
  Stage 5: Update wiki/index.md
  Stage 6: Set manifest status: compiled, log to .brain/
```

### Search for knowledge

```
User: "What do we know about API rate limits?"

Routing:
  Layer 1: Check .brain/ session context
  Layer 2: Search wiki/ -- return if confidence >= medium
  Layer 3: (if MCP available) Query NotebookLM
  Layer 4: Log gap if insufficient
```

### Audit wiki health

```
User: "Lint wiki"

Checks: orphans, dead links, duplicates, contradictions,
        ungrounded, stale, schema, manifest, MCP health
Output: Formatted report with errors/warnings/info
```

---

## 5. Architecture Invariants

```
1. NO direct raw/ -> wiki/ writes (must go through processed/)
2. NO status: grounded without grounding engine verification
3. NO long-term knowledge in .brain/ (use wiki/)
4. NO gap-skipping when answers are insufficient
5. NO overwriting verified notes (merge evidence instead)
6. NO fake NotebookLM results when MCP unavailable
7. NO skipping index update after wiki note compile
8. NO wiki notes missing required frontmatter fields
```

---

## 6. Fixes Applied (post-review v1.0.1)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | High | `brain-state-helper-bridge.md` missing | Created: 6 sections, data flow rules, conflict resolution, AWF compatibility |
| 2 | High | Example data in live state files | Moved examples to `templates/`, state files start EMPTY |
| 3 | Medium | Idempotency enum mismatch | Defined 5-value enum (extracted/pending_grounding/grounded/compiled/failed), fixed check logic |
| 4 | Medium | Missing `.gitignore` | Created with AWF-aligned policy, runtime state excluded |
| 5 | Medium | Encoding concern | Verified: UTF-8 no BOM, LF endings, all Unicode chars valid. Display issues are terminal-side |

---

## 7. File Quick Reference

```
Schema reference    -> wiki/_schemas/note.schema.md
Wiki overview       -> wiki/index.md
Provenance tracking -> processed/manifest.jsonl (runtime)
Grounding queue     -> .brain/grounding_queue.json (runtime)
Knowledge gaps      -> .brain/knowledge_gaps.json (runtime)
Architecture        -> AGENTS.md
Bridge rules        -> brain-state-helper-bridge.md
MCP setup           -> skills/notebooklm-mcp-bridge.md
Ingest pipeline     -> skills/ingest-wiki.md
Query routing       -> skills/query-wiki.md
Audit system        -> skills/lint-wiki.md
Format examples     -> templates/*.example.*
```

---

## 8. Handover

```
Builder:   Claude Opus 4.6  -- COMPLETE
Operator:  Gemini Flash     -- READY

Next steps:
  1. Drop first file into raw/
  2. Run ingest-wiki
  3. See wiki note appear
  4. (Optional) nlm login to enable grounding
```

---

*Hybrid ABW v1.0.1 | Post-review fixes applied*
*"A cited answer beats a confident guess. A logged gap beats a fake answer."*
