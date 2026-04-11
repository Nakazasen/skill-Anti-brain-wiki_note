# Skill: lint-wiki

> **Version:** 1.0.0  
> **Trigger:** User says "lint wiki", "audit wiki", "check wiki health", or scheduled periodic check  
> **Dependencies:** `wiki/`, `processed/manifest.jsonl`, `.brain/grounding_queue.json`, `.brain/knowledge_gaps.json`  
> **MCP:** `notebooklm` (optional -- health check only)

---

## Purpose

Audit the structural integrity, knowledge quality, and grounding health of the entire wiki. Detect problems **before** they cause incorrect answers in `query-wiki`.

---

## Audit Categories

```
+-------------------------------------------------------------+
|                    lint-wiki Audit Report                     |
+-------------------------------------------------------------+
|  [ERR] ERRORS    -- Must fix: broken structure, missing fields   |
|  [WARN] WARNINGS  -- Should fix: quality/grounding issues         |
|  [INFO] INFO      -- Suggestions for improvement                  |
+-------------------------------------------------------------+
```

---

## Check 1: Orphan Notes

> **Severity:** [WARN] WARNING  
> **Description:** Notes that exist in wiki/ but are not referenced in `wiki/index.md`

### Algorithm
```
FOR EACH file in wiki/entities/, wiki/concepts/, wiki/timelines/, wiki/sources/:
    slug = filename without .md
    IF slug NOT FOUND in wiki/index.md between appropriate markers:
        REPORT: "Orphan note: wiki/<type>/<slug>.md -- not in index"
```

### Auto-fix Suggestion
```
Add to wiki/index.md under the appropriate section:
- [<title>](<type>/<slug>.md) -- `<status>` | confidence: `<confidence>`
```

---

## Check 2: Dead Links

> **Severity:** [ERR] ERROR  
> **Description:** Cross-references in `related` fields or body links that point to non-existent files

### Algorithm
```
FOR EACH note in wiki/**/*.md:
    Parse YAML frontmatter -> extract `related` array
    FOR EACH path in `related`:
        IF file at path does NOT exist:
            REPORT: "Dead link in <note>: related path '<path>' does not exist"

    Parse body content -> extract [[wiki/...]] or [text](wiki/...) links
    FOR EACH link:
        IF target file does NOT exist:
            REPORT: "Dead link in <note>: body link to '<target>' does not exist"
```

### Auto-fix Suggestion
```
Option A: Create stub note at the dead link target
Option B: Remove the dead link from `related` array
```

---

## Check 3: Duplicate Entities

> **Severity:** [WARN] WARNING  
> **Description:** Multiple notes that appear to describe the same entity/concept

### Algorithm
```
COLLECT all notes -> extract (id, title, aliases) tuples

FOR EACH pair of notes (A, B):
    IF A.title == B.title OR A.title IN B.aliases OR B.title IN A.aliases:
        REPORT: "Potential duplicate: <A.path> and <B.path> -- title/alias overlap"
    
    IF A.id == B.id:
        REPORT: "[ERR] ERROR: Duplicate ID '<A.id>' in <A.path> and <B.path>"

    IF similarity(A.title, B.title) > 0.85:  # Fuzzy match
        REPORT: "Possible duplicate: '<A.title>' ~= '<B.title>'"
```

### Auto-fix Suggestion
```
Option A: Merge notes (keep the one with higher confidence/more sources)
Option B: Add distinguishing context to titles/IDs
Option C: Add one as alias of the other
```

---

## Check 4: Contradiction Candidates

> **Severity:** [WARN] WARNING  
> **Description:** Notes that make conflicting claims about the same subject

### Algorithm
```
FOR EACH note with non-empty `contradictions` field:
    FOR EACH contradiction entry:
        IF contradiction.resolution == "pending":
            REPORT: "Unresolved contradiction in <note>:
                     Claim: '<claim>'
                     Counter: '<counter_claim>'
                     Sources: <source_a> vs <source_b>"

# Cross-note contradiction detection (heuristic)
GROUP notes by overlapping tags or related links
FOR EACH group:
    EXTRACT key claims from Summary sections
    IF claims appear contradictory (e.g., "X supports Y" vs "X does not support Y"):
        REPORT: "Potential contradiction between <note_A> and <note_B>:
                 <note_A> claims: '...'
                 <note_B> claims: '...'"
```

### Auto-fix Suggestion
```
1. Add `contradictions` entry to both notes
2. Set status: "disputed" on the less-sourced note
3. Queue both for re-grounding via NotebookLM
```

---

## Check 5: Ungrounded Notes

> **Severity:** [WARN] WARNING  
> **Description:** Notes with `grounding.engine: none` or `status: draft` that should be grounded

### Algorithm
```
FOR EACH note in wiki/**/*.md:
    Parse YAML frontmatter
    IF status == "draft" AND grounding.engine == "none":
        age = NOW - created_at
        IF age > 24 hours:
            REPORT: "Ungrounded note (>24h old): <path>
                     -- consider running ingest-wiki or manual grounding"
    
    IF status == "grounded" AND grounding.engine == "none":
        REPORT: "[ERR] ERROR: Inconsistent metadata in <path>
                 -- status is 'grounded' but grounding.engine is 'none'"
```

### Auto-fix Suggestion
```
Option A: Queue for grounding via .brain/grounding_queue.json
Option B: Update status to 'draft' if grounding.engine is 'none'
```

---

## Check 6: Stale Notes

> **Severity:** [INFO] INFO  
> **Description:** Notes that haven't been updated in >30 days

### Algorithm
```
THRESHOLD = 30 days (configurable)

FOR EACH note in wiki/**/*.md:
    Parse YAML frontmatter -> extract `updated_at`
    age = NOW - updated_at
    IF age > THRESHOLD:
        REPORT: "Stale note (<age> days old): <path>
                 -- last updated: <updated_at>
                 -- suggest re-grounding or marking as stale"
    
    IF status != "stale" AND age > THRESHOLD:
        SUGGEST: "Update status to 'stale' in <path>"
```

### Auto-fix Suggestion
```
Set status: "stale" in frontmatter
Queue for re-grounding
```

---

## Check 7: Schema Compliance

> **Severity:** [ERR] ERROR  
> **Description:** Notes missing required frontmatter fields per `note.schema.md`

### Algorithm
```
REQUIRED_FIELDS = [id, title, type, status, sources, grounding, confidence, created_at, updated_at]

FOR EACH note in wiki/**/*.md:
    Parse YAML frontmatter
    FOR EACH field in REQUIRED_FIELDS:
        IF field MISSING or EMPTY:
            REPORT: "Missing required field '<field>' in <path>"
    
    # Type validation
    IF status NOT IN [draft, grounded, verified, stale, disputed]:
        REPORT: "Invalid status '<status>' in <path>"
    IF confidence NOT IN [high, medium, low, unverified]:
        REPORT: "Invalid confidence '<confidence>' in <path>"
    IF type NOT IN [entity, concept, timeline, source]:
        REPORT: "Invalid type '<type>' in <path>"
    
    # Type-path consistency
    IF type == "entity" AND path NOT STARTS WITH "wiki/entities/":
        REPORT: "Type-path mismatch: type is 'entity' but file is in <dir>"
```

---

## Check 8: Manifest Integrity

> **Severity:** [ERR] ERROR  
> **Description:** Broken references between `processed/manifest.jsonl` and wiki notes

### Algorithm
```
FOR EACH line in manifest.jsonl:
    IF status == "compiled":
        FOR EACH target in wiki_targets:
            IF file at target does NOT exist:
                REPORT: "Manifest line <N> references non-existent wiki note: <target>"

FOR EACH note in wiki/**/*.md:
    FOR EACH source in sources:
        IF source.ref starts with "processed/manifest.jsonl#line-":
            line_num = extract line number
            IF manifest.jsonl has no such line:
                REPORT: "Note <path> references non-existent manifest line: <line_num>"
```

---

## Check 9: Notebook Grounding Health

> **Severity:** [INFO] INFO  
> **Description:** Status of NotebookLM grounding infrastructure

### Pre-check
```
IF NotebookLM MCP available:
    -> Run health checks
ELSE:
    -> REPORT: "[!] NotebookLM MCP unavailable -- cannot verify grounding health"
    -> Report count of items in grounding_queue.json with status: "pending"
```

### Actions (MCP Available)
1. List notebooks via `notebook_list`
2. For each notebook referenced in wiki notes:
   - Verify notebook still exists
   - Check source count vs expected sources
3. Report grounding queue status:
   ```
   Grounding Queue: <N> pending, <M> completed, <K> failed
   ```

### Actions (MCP Unavailable)
```
REPORT:
  "NotebookLM MCP Status: UNAVAILABLE
   Grounding queue: <N> items pending
   Last successful grounding: <timestamp or 'never'>
   Action: Run 'nlm login' to restore MCP connection"
```

---

## Check 10: Gate Exit Failures (TTC)

> **Severity:** [WARN] WARNING
> **Description:** Deliberation runs that hit the circuit breaker or scored below threshold
> **Requires:** `.brain/deliberation_runs.jsonl`

### Algorithm
```
IF .brain/deliberation_runs.jsonl does NOT exist or is empty:
    SKIP (no deliberation history)

FOR EACH run in deliberation_runs.jsonl:
    IF run.circuit_breaker_triggered == true:
        REPORT: "Circuit breaker triggered for query: '<query>'
                 Reason: <exit_reason>
                 Score: <exit_score>/10
                 Suggestion: Add sources to raw/ for this topic"

    IF run.exit_score < 5:
        REPORT: "Low-quality deliberation for query: '<query>'
                 Score: <exit_score>/10
                 Gaps logged: <gaps_logged count>
                 Suggestion: Review .brain/knowledge_gaps.json"
```

---

## Check 11: Stale-but-High-Priority Notes (TTC)

> **Severity:** [WARN] WARNING
> **Description:** Notes referenced by recent deliberation runs that have gone stale
> **Requires:** `.brain/deliberation_runs.jsonl`, `wiki/`

### Algorithm
```
IF .brain/deliberation_runs.jsonl does NOT exist or is empty:
    SKIP

COLLECT all wiki note paths from recent deliberation runs (last 30 days)
FOR EACH note_path in collected:
    IF note exists AND note.status == "stale":
        REPORT: "Stale note used in recent deliberation: <note_path>
                 Last updated: <updated_at>
                 Used by run: <run_id>
                 Suggestion: Re-ground this note -- it affects deliberation quality"
```

---

## Check 12: Contradiction Clusters (TTC)

> **Severity:** [WARN] WARNING
> **Description:** Groups of 3+ notes with unresolved contradictions forming a cluster
> **Requires:** `wiki/`

### Algorithm
```
BUILD contradiction graph:
    FOR EACH note with non-empty contradictions (resolution == "pending"):
        Add edges between contradicting notes

FIND clusters (connected components with >= 3 nodes)
FOR EACH cluster:
    REPORT: "Contradiction cluster detected:
             Notes: <list of note paths>
             Unresolved contradictions: <count>
             Suggestion: Prioritize grounding for this cluster --
                          deliberation quality degrades with unresolved conflicts"
```

---

## Output: Lint Report

### Format
```markdown
# [SCAN] Wiki Lint Report
> Generated: <ISO 8601>
> Wiki path: wiki/
> Total notes scanned: <N>

## Summary
| Category | [ERR] Error | [WARN] Warning | [INFO] Info |
|----------|----------|------------|---------|
| Orphan Notes | 0 | <n> | 0 |
| Dead Links | <n> | 0 | 0 |
| Duplicate Entities | 0 | <n> | 0 |
| Contradictions | 0 | <n> | 0 |
| Ungrounded Notes | <n> | <n> | 0 |
| Stale Notes | 0 | 0 | <n> |
| Schema Compliance | <n> | 0 | 0 |
| Manifest Integrity | <n> | 0 | 0 |
| Grounding Health | 0 | 0 | <n> |
| Gate Exit Failures | 0 | <n> | 0 |
| Stale High-Priority | 0 | <n> | 0 |
| Contradiction Clusters | 0 | <n> | 0 |
| **TOTAL** | **<total>** | **<total>** | **<total>** |

## [ERR] Errors (Must Fix)
1. [error details...]

## [WARN] Warnings (Should Fix)
1. [warning details...]

## [INFO] Info (Suggestions)
1. [info details...]

## Recommended Actions
1. Fix all [ERR] errors first
2. Address [WARN] warnings by priority
3. Consider [INFO] suggestions for improvement
```

### Report Destination
- Print to console (always)
- Optionally save to `wiki/_indexes/lint-report-<date>.md`

---

## Usage Examples

### Full Audit
```
User: lint wiki
-> Run all 12 checks
-> Output formatted report
-> Suggest priority fixes
```

### Quick Health Check (Grounding Only)
```
User: How healthy is the wiki?
-> Run checks 5-9 only (grounding-focused, excludes TTC checks 10-12)
-> Output summary table
-> Suggest: "Run checks 10-12 separately for TTC health"
```

### TTC Health Check
```
User: How is deliberation quality?
-> Run checks 10-12 only (TTC-focused)
-> Report gate failures, stale high-priority notes, contradiction clusters
```

### After Ingest
```
User: (after running ingest-wiki) Check the new notes
-> Run checks 1, 2, 7 on recently created notes only
-> Verify schema compliance and links
```

---

## Error Handling

| Error | Response |
|-------|----------|
| `wiki/` directory empty | Report "Wiki is empty -- run ingest-wiki first" |
| YAML parse failure in note | Report as [ERR] ERROR with file path and parse error |
| `manifest.jsonl` missing | Report as [ERR] ERROR, suggest running ingest-wiki |
| Excessive errors (>50) | Truncate report, suggest fixing top 10 first |
