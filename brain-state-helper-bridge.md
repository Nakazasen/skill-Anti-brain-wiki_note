# Brain-State Helper Bridge

> **Version:** 1.0.0
> **Purpose:** Bridge rules between `.brain/` (operational memory) and `wiki/` (persistent knowledge)
> **Required by:** PROMPT_V2.hybrid-abw.md line 47
> **Last Updated:** 2026-04-11T22:38:00+07:00

---

## Why This Bridge Exists

`.brain/` and `wiki/` serve fundamentally different purposes. Without explicit bridge rules,
data leaks between layers: operational state pollutes knowledge, or knowledge gets trapped
in session files. This document defines **when, how, and what** flows between them.

---

## 1. Data Flow Rules

### 1.1 From `.brain/` TO `wiki/` (Promotion)

Data moves from operational memory to persistent knowledge **only** when:

| Condition | Source | Target | Trigger |
|-----------|--------|--------|---------|
| Knowledge gap resolved | `.brain/knowledge_gaps.json` | `wiki/<type>/<note>.md` | `ingest-wiki` processes new source that fills the gap |
| Grounding queue completed | `.brain/grounding_queue.json` | `wiki/<type>/<note>.md` (status upgrade) | `ingest-wiki` Stage 3 succeeds |
| Session decision becomes pattern | `.brain/session.json` -> `decisions_made` | `wiki/concepts/<pattern>.md` | User explicitly promotes via `ingest-wiki` |

#### Promotion Rules
```
1. NEVER auto-promote .brain/ data to wiki/ without processed/ intermediary
2. ALL promotions MUST go through: .brain/ -> raw/ (export) -> processed/ -> wiki/
3. A session decision is NOT knowledge until it has been:
   a. Extracted as a claim
   b. Added to manifest.jsonl
   c. Optionally grounded
   d. Compiled as a wiki note
```

### 1.2 From `wiki/` TO `.brain/` (Reference)

Wiki data flows to operational memory **only** as read-only references:

| Condition | Source | Target | Trigger |
|-----------|--------|--------|---------|
| Query finds wiki answer | `wiki/<note>.md` | Console output (NOT .brain/) | `query-wiki` Layer 2 |
| Lint detects issues | `wiki/index.md`, notes | Console output + optional `.brain/session_log.txt` delta | `lint-wiki` |
| Session recap needs context | `wiki/` search results | `.brain/` recap supplement (read-only) | `query-wiki` Layer 1 |

#### Reference Rules
```
1. .brain/ NEVER stores copies of wiki content
2. .brain/ MAY store references (paths, IDs) to wiki notes
3. References are ephemeral -- they don't survive session snapshots
4. wiki/ is the authoritative source; .brain/ only points to it
```

### 1.3 Forbidden Flows

| Flow | Why Forbidden | What To Do Instead |
|------|--------------|-------------------|
| `.brain/session.json` -> `wiki/` directly | Bypasses processed/ layer, no provenance | Export to raw/ first, then ingest |
| `wiki/` -> `.brain/brain.json` | Mixes knowledge into operational state | Use wiki/ as query-time reference only |
| `.brain/knowledge_gaps.json` -> `wiki/` without source | Creates ungrounded knowledge from a question | Find source material first, then ingest |
| `wiki/` deletion -> `.brain/` cleanup skip | Orphaned references in .brain/ | lint-wiki checks for orphan references |

---

## 2. Shared State Contract

### 2.1 Files `.brain/` Owns (ABW writes)

| File | Written By | Read By | Purpose |
|------|-----------|---------|---------|
| `grounding_queue.json` | `ingest-wiki` (fallback) | `ingest-wiki` (recovery), `lint-wiki` (check 9) | Pending grounding operations |
| `knowledge_gaps.json` | `query-wiki` (Layer 4) | `query-wiki` (duplicate check), `lint-wiki` | Unresolved knowledge holes |

### 2.2 Files `.brain/` Owns (AWF writes, ABW reads only)

| File | Written By | ABW Access | Boundary |
|------|-----------|------------|----------|
| `brain.json` | AWF `/save-brain` | READ ONLY | ABW never modifies project knowledge |
| `session.json` | AWF auto-save | READ ONLY | ABW reads `working_on` for Layer 1 context |
| `session_log.txt` | AWF auto-save | APPEND ONLY | ABW appends `[ingest-wiki]`, `[query-wiki]`, `[lint-wiki]` deltas |
| `snapshots/` | AWF save-brain | NO ACCESS | ABW ignores historical snapshots |
| `summaries/` | AWF save-brain | READ ONLY | ABW may read for recap but never writes |

### 2.3 Files `wiki/` Owns

| File | Written By | .brain/ Access | Boundary |
|------|-----------|----------------|----------|
| `wiki/**/*.md` | `ingest-wiki` only | Reference paths only | .brain/ never stores note content |
| `wiki/index.md` | `ingest-wiki`, `lint-wiki` | Read for query routing | .brain/ never modifies index |
| `wiki/_schemas/note.schema.md` | System (immutable) | Read for validation | Never modified at runtime |

---

## 3. Lifecycle Bridges

### 3.1 Grounding Queue Lifecycle

```
ingest-wiki (Stage 3 fallback)
    |
    +-- Creates queue entry in .brain/grounding_queue.json
    |   status: "pending"
    |
    +-- Creates wiki note with status: "draft"
    |   (wiki/ has the note, .brain/ has the queue entry)
    |
    +-- When MCP restored:
        |
        +-- ingest-wiki processes queue
        |   status: "pending" -> "in_progress" -> "completed"
        |
        +-- Updates wiki note: status: "draft" -> "grounded"
        |   (wiki/ upgraded, .brain/ queue entry resolved)
        |
        +-- Removes completed entry from queue
            (.brain/ cleaned up, wiki/ is authoritative)
```

### 3.2 Knowledge Gap Lifecycle

```
query-wiki (Layer 4)
    |
    +-- Logs gap in .brain/knowledge_gaps.json
    |   status: "open"
    |
    +-- User provides source material later:
        |
        +-- ingest-wiki processes source
        |   -> Creates wiki note
        |
        +-- query-wiki finds wiki note that fills gap
        |   -> Updates gap: status: "open" -> "resolved"
        |   -> Records resolution_path: "wiki/<type>/<note>.md"
        |
        +-- Gap stays in .brain/ as resolved record
            (not deleted -- serves as audit trail)
```

### 3.3 Session-to-Wiki Promotion Flow

```
Developer makes architecture decision in session
    |
    v
.brain/session.json -> decisions_made[]
    |
    | (User says: "Save this decision to wiki")
    |
    v
Export decision text to raw/decisions/<slug>.md
    |
    v
ingest-wiki processes:
    raw/ -> processed/manifest.jsonl -> grounding -> wiki/concepts/<slug>.md
    |
    v
Wiki note exists with full provenance chain
    |
    +-- .brain/session.json decision is now REDUNDANT
        (wiki/ is the authoritative record)
```

---

## 4. Conflict Resolution

### When .brain/ and wiki/ Disagree

| Scenario | Resolution | Authority |
|----------|-----------|-----------|
| `.brain/` says task done, `wiki/` note missing | wiki/ is truth -- task not complete until note exists | `wiki/` |
| `.brain/` gap says "open", wiki note exists | Gap is resolved -- update .brain/ | `wiki/` |
| `.brain/` queue says "completed", wiki note still "draft" | Queue lied or update failed -- re-process | `wiki/` (re-trigger Stage 4) |
| `wiki/` note exists, no manifest entry | Orphan note -- flag via lint-wiki Check 8 | `processed/manifest.jsonl` |

### Rule
> **When `.brain/` and `wiki/` conflict, `wiki/` wins.** `.brain/` is ephemeral coordination;
> `wiki/` is the persistent, citable record.

---

## 5. AWF Command Compatibility

| AWF Command | ABW Impact | Safe? |
|-------------|-----------|-------|
| `/save-brain` | Saves `.brain/brain.json`, `.brain/session.json` -- does NOT touch ABW files | YES |
| `/recap` | Reads `.brain/session.json` -- ABW supplements with wiki context (Layer 1) | YES |
| `/init` | Creates `.brain/` directory -- ABW files will be created on first ingest | YES |
| `/review` | Reads project state -- ABW has no impact | YES |
| `/debug` | May modify code -- ABW tracks via session_log deltas only | YES |

### Invariant
> ABW files (`grounding_queue.json`, `knowledge_gaps.json`) are INVISIBLE to AWF commands.
> AWF commands NEVER read, write, or delete ABW files. The two systems coexist without interference.

---

## 6. Quick Decision Table

**"Where does this data go?"**

| Data Type | Goes To | NOT To | Why |
|-----------|---------|--------|-----|
| "We chose React over Vue" (session decision) | `.brain/session.json` | `wiki/` | Operational -- promote explicitly later |
| "React uses virtual DOM for efficient updates" (fact) | `wiki/concepts/` via ingest | `.brain/` | Knowledge -- belongs in wiki |
| "NotebookLM confirmed React's reconciliation algorithm" (grounding result) | `wiki/` note frontmatter + `processed/manifest.jsonl` | `.brain/` | Evidence -- stays with the note |
| "Q: How does React handle concurrent rendering?" (unanswered question) | `.brain/knowledge_gaps.json` | `wiki/` | Gap -- not knowledge until answered |
| "3 items pending grounding" (queue status) | `.brain/grounding_queue.json` | `wiki/` | Operational state -- not knowledge |

---

*Bridge v1.0.0 | Hybrid ABW | Compatible with AWF 4.1*
