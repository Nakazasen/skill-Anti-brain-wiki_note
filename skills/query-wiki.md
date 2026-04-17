# Skill: query-wiki

> **Version:** 1.0.0  
> **Trigger:** User asks a knowledge question, requests citation, or says "query wiki", "search wiki"  
> **Dependencies:** `wiki/`, `.brain/`, `processed/manifest.jsonl`, `.brain/knowledge_gaps.json`  
> **MCP:** `notebooklm` (optional -- degrades gracefully)

---

## Purpose

Answer user questions with **cited, verifiable evidence** by searching the wiki knowledge base first, escalating to NotebookLM for deep grounding when needed, and honestly logging gaps when knowledge is insufficient.

---

## Routing Gate (v1.1.0)

Before entering the 4-layer pipeline, classify the query:

```
+-----------------+
|  User Query     |
+--------+--------+
         |
         v
+------------------+
|  CLASSIFY QUERY  |
+--------+---------+
         |
    +----+----+
    |         |
    v         v
  FAST    DELIBERATIVE
  PATH    PATH
    |         |
    v         v
  (below)   query-wiki-deliberative.md
```

### Fast Path (use this skill's 4-layer pipeline)
Query meets ALL of these:
- Fact lookup, definition, or simple recall
- Likely answered by a single wiki note
- No contradictions or stale notes expected
- User did not request high accuracy or deep analysis

### Deliberative Path (delegate to `query-wiki-deliberative.md`)
Query meets ANY of these:
- "Why" / "compare" / "which should we" / "root cause" / "design decision"
- Requires synthesis across multiple wiki notes
- Known contradictions exist on the topic
- Stale notes flagged on the topic
- User explicitly says "think carefully", "be thorough", "I need high accuracy"
- Topic involves risk, security, or architecture decisions

**Handoff rule:** If classified as DELIBERATIVE, **STOP this skill immediately**.
Do NOT continue into the 4-layer pipeline below. Instead, invoke
`query-wiki-deliberative.md` and return its result as the final answer.
This skill's 4-layer pipeline is ONLY for fast-path queries.

### Classification Examples
```
FAST:       "What is the Gemini Flash context window limit?"
FAST:       "Who wrote the Q3 API review?"
DELIBERATE: "Why did we choose PostgreSQL over MongoDB?"
DELIBERATE: "Compare our rate limiting approaches across services"
DELIBERATE: "What is the root cause of the latency spike?"
DELIBERATE: "Should we migrate to a microservices architecture?"
```

---

## Query Routing Logic

```
+--------------+
|  User Query   |
+------+-------+
       |
       v
+--------------+     found     +-----------------+
|  LAYER 1     |-------------->|  Answer with     |
|  .brain/     |               |  citations       |
|  Recap Check |               |  from wiki/      |
+------+-------+               +-----------------+
       | not found                      ^
       v                                |
+--------------+     found              |
|  LAYER 2     |------------------------+
|  wiki/       |
|  Search      |
+------+-------+
       | insufficient
       v
+------------------+   grounded   +-----------------+
|  LAYER 3         |------------->|  Compile answer  |
|  NotebookLM MCP  |              |  + update wiki/  |
|  Deep Grounding  |              +-----------------+
+------+-----------+
       | unavailable OR insufficient
       v
+------------------+
|  LAYER 4         |
|  Gap Logging     |
|  Partial Answer  |
+------------------+
```

---

## Layer 1: .brain/ Recap Check

### Purpose
Quick context check -- has this topic been discussed recently?

### Actions
1. Check `.brain/session.json` (if exists) for `working_on` or recent `conversation_summary` mentioning the query topic
2. Check `.brain/brain.json` (if exists) for `knowledge_items.patterns` or `knowledge_items.gotchas` matching the query
3. Check `.brain/knowledge_gaps.json` for any `status: "resolved"` gap matching the query

### Decision
- If relevant context found in `.brain/` -> use as **supplementary context** (not primary answer)
- Always proceed to Layer 2 for authoritative answers
- `.brain/` data is operational, NOT knowledge -- never cite `.brain/` as a primary source

---

## Layer 2: Wiki Search

### Actions
1. **Keyword extraction**: Parse user query into search terms
2. **Index scan**: Search `wiki/index.md` for matching entries
3. **Full-text scan**: Search across wiki note files:
   - `wiki/entities/*.md` -- entity names, aliases
   - `wiki/concepts/*.md` -- concept titles, tags
   - `wiki/timelines/*.md` -- date ranges, event names
   - `wiki/sources/*.md` -- source titles
4. **Frontmatter filter**: For each match, read YAML frontmatter:
   - Prefer `status: verified` > `grounded` > `draft`
   - Prefer `confidence: high` > `medium` > `low`
   - Flag `status: stale` notes with a warning
   - Flag `status: disputed` notes with contradiction details
5. **Compile answer**: Build response with inline citations:
   ```
   [Answer text] [src:wiki/concepts/topic.md, confidence:high, grounded:2026-04-10]
   ```

### Decision Tree
```
IF exact match with confidence >= medium AND status in {grounded, verified}:
    -> Return answer with citations
    -> STOP (success)

IF match found but confidence = low OR status = draft:
    -> Return partial answer with caveat
    -> Proceed to Layer 3 for verification

IF match found but status = stale:
    -> Return answer with [!] STALE warning
    -> Suggest re-grounding

IF match found but status = disputed:
    -> Return BOTH sides of contradiction
    -> Cite both sources

IF no match:
    -> Proceed to Layer 3
```

### Citation Format
All wiki-sourced answers must include:
```markdown
**Sources:**
- [1] wiki/concepts/topic.md (confidence: high, grounded: 2026-04-10)
- [2] wiki/entities/entity.md (confidence: medium, status: draft)

**Provenance:**
- [1] <- processed/manifest.jsonl#line-42 <- raw/original-doc.pdf
```

### Finalization Rule
Append the terminal block from `workflows/finalization.md` to every answer.
- Use `verified` only when the answer has explicit provenance and the cited chain is checkable.
- Use `partially_verified` when the answer is source-backed but still incomplete or caveated.
- Use `blocked` when the wiki cannot support the answer and no safe fallback exists.

---

## Layer 3: NotebookLM Deep Grounding

### Pre-check
```
IF NotebookLM MCP available:
    -> Proceed
ELSE:
    -> Skip to Layer 4 with note: "NotebookLM unavailable for deep grounding"
```

### Actions (MCP Available)
1. List available notebooks via `notebook_list`
2. Identify notebook(s) most likely to contain relevant sources:
   - Match by notebook title keywords
   - If unsure, query the most recently updated notebook
3. Execute query:
   ```
   notebook_query(notebook_id=<id>, query=<user_query>)
   ```
4. Evaluate response:
   - If response contains substantive answer with citations -> **USE IT**
   - If response is generic/unhelpful -> proceed to Layer 4
5. If substantive answer received:
   - Compile into wiki note format (follow `note.schema.md`)
   - Add to appropriate `wiki/<type>/` directory
   - Update `wiki/index.md`
   - Update manifest (new processed entry)
   - Return answer with full citation chain

### Answer Format (from NotebookLM)
```markdown
[Answer compiled from NotebookLM grounding]

**Sources:**
- [1] NotebookLM notebook "<name>" -- query: "<query_used>"
- [2] Source within notebook: "<source_title>"

**Action taken:**
- Created wiki/concepts/new-note.md (status: grounded, confidence: medium)

**Provenance:**
- Grounded via NotebookLM MCP at <timestamp>
- Compiled into wiki for future local retrieval
```

---

## Layer 4: Gap Logging & Partial Answer

### Trigger Conditions
- No wiki match found AND NotebookLM unavailable
- No wiki match found AND NotebookLM returned insufficient answer
- Wiki match found but `confidence: low` and no grounding possible

### Actions
1. **Check existing gaps**: Search `.brain/knowledge_gaps.json` for similar query
   - If found with `status: "open"` -> increment priority, add new context
   - If found with `status: "resolved"` -> use resolution info
2. **Log new gap** (if not already logged):
   ```json
   {
     "id": "gap-<YYYYMMDD>-<XXXX>",
     "query": "<original user query>",
     "context": "<why we couldn't answer>",
     "searched_locations": ["wiki/concepts/", "wiki/entities/", ...],
     "notebooklm_checked": <true|false>,
     "notebooklm_notebook_id": "<id or null>",
     "reason": "<specific reason for gap>",
     "priority": "<critical|high|medium|low>",
     "status": "open",
     "created_at": "<ISO 8601>",
     "resolved_at": null,
     "resolution_path": null,
     "suggested_sources": ["<URL or description of where to find info>"]
   }
   ```
3. Update `.brain/knowledge_gaps.json` stats
4. **Return honest partial answer**:

### Partial Answer Format
```markdown
[!] **Incomplete Answer -- Knowledge Gap Detected**

**What I know:**
[Any partial information from wiki/ or .brain/ context]

**What I don't know:**
[Specific aspects that couldn't be answered]

**Gap logged:** `.brain/knowledge_gaps.json` -> gap-<id>
**Suggested next steps:**
1. Add source material to `raw/` and run `ingest-wiki`
2. [Specific source suggestions if available]

**Priority:** <medium>
```

After the answer body, append the `Finalization` block from `workflows/finalization.md`.
- Do not collapse partial support into `verified`.
- Do not use `done` as a substitute for evidence.

---

## Priority Assignment for Gaps

| Condition | Priority |
|-----------|----------|
| User explicitly needs answer now | `critical` |
| Query relates to active project work (from `.brain/session.json`) | `high` |
| General knowledge question | `medium` |
| Nice-to-have, curiosity | `low` |

---

## Post-Query Actions

After every query (regardless of which layer answered):

1. **If Layer 2 answered**: No additional action needed
2. **If Layer 3 answered**: New wiki note was created -> verify with `lint-wiki` later
3. **If Layer 4 triggered**: Gap logged -> suggest `ingest-wiki` with relevant sources
4. **Always**: If `status: stale` notes were encountered, suggest re-grounding

---

## Usage Examples

### Successful Wiki Answer
```
User: What are the limitations of Gemini Flash context window?
-> Layer 1: Check .brain/ -- found recent session context
-> Layer 2: Found wiki/concepts/gemini-flash-context-limits.md
   status: grounded, confidence: high
-> Return: "Gemini Flash 2.5 has a 1M token window [src:wiki/concepts/...]"
-> STOP (success)
```

### NotebookLM Escalation
```
User: What did the Q3 review say about API latency?
-> Layer 1: No .brain/ context
-> Layer 2: No matching wiki note
-> Layer 3: Found relevant notebook, queried, got answer
-> Created wiki/sources/q3-review-api-latency.md
-> Return answer with full citation chain
```

### Gap Logging
```
User: What's our competitor's pricing model?
-> Layer 1: No context
-> Layer 2: No wiki match
-> Layer 3: No relevant notebook / MCP unavailable
-> Layer 4: Logged gap-20260411-0001
-> Return: "[!] Knowledge gap -- suggest adding competitive analysis docs to raw/"
```

---

## Error Handling

| Error | Response |
|-------|----------|
| `.brain/` files missing | Skip Layer 1, proceed to Layer 2 |
| `wiki/index.md` missing | Scan wiki directories directly |
| NotebookLM MCP timeout | Log error, proceed to Layer 4 |
| NotebookLM auth failure | Log error, proceed to Layer 4, suggest `nlm login` |
| Contradictory wiki notes found | Present both sides, flag for `lint-wiki` |
| `knowledge_gaps.json` write fails | Log to console, still return partial answer |
