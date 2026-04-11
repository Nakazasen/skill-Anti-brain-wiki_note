# Skill: ingest-wiki

> **Version:** 1.0.0  
> **Trigger:** User says "ingest", "add to wiki", "process source", or drops files into `raw/`  
> **Dependencies:** `wiki/_schemas/note.schema.md`, `processed/manifest.jsonl`, `.brain/grounding_queue.json`  
> **MCP:** `notebooklm` (optional -- degrades gracefully)

---

## Purpose

Transform raw source material into grounded, citable wiki notes through a strict 6-stage pipeline. **No stage may be skipped.**

---

## Pipeline Overview

```
+---------+    +--------------+    +-----------------+    +--------------+    +--------------+    +------------+
|  STAGE 1 |--->|   STAGE 2    |--->|    STAGE 3      |--->|   STAGE 4    |--->|   STAGE 5    |--->|  STAGE 6   |
|  Receive |    |  Extract &   |    |  NotebookLM     |    |  Wiki Note   |    |  Index &     |    |  .brain    |
|  raw/    |    |  Process     |    |  Grounding      |    |  Compile     |    |  Link Update |    |  Log       |
+---------+    +--------------+    +-----------------+    +--------------+    +--------------+    +------------+
```

---

## Stage 1: Receive Source

### Input
- User provides: file path, URL, pasted text, or Google Drive link
- Accepted formats: `.pdf`, `.md`, `.txt`, `.docx`, `.html`, URLs, YouTube links

### Actions
1. Identify source type and format
2. If file: copy or move to `raw/` with descriptive filename
3. If URL: save metadata to `raw/` as `<slug>.url.md` with content:
   ```markdown
   ---
   url: "https://example.com/article"
   fetched_at: "2026-04-11T22:00:00+07:00"
   ---
   [Pasted or fetched content here]
   ```
4. Generate a unique `source_id` (format: `SRC-YYYYMMDD-XXXX`)

### Output
- File exists in `raw/`
- `source_id` assigned

### Failure Mode
- If file format unsupported -> STOP, inform user, do not proceed
- If file empty -> STOP, inform user

---

## Stage 2: Extract & Process

### Actions
1. Read the raw source
2. Extract structured information:
   - **Key claims** (factual statements that can be verified)
   - **Entities** (people, orgs, tools, products mentioned)
   - **Concepts** (abstract ideas, methodologies, patterns)
   - **Temporal markers** (dates, versions, timelines)
   - **Relationships** (entity-to-entity, concept-to-concept)
3. Compute SHA-256 checksum of raw file for idempotency
4. **Append** a new line to `processed/manifest.jsonl`:

### Manifest Status Enum (Definitive)

| Status | Set At | Meaning |
|--------|--------|--------|
| `extracted` | Stage 2 | Raw source processed, manifest entry created |
| `pending_grounding` | Stage 3 (fallback) | MCP unavailable, queued for later grounding |
| `grounded` | Stage 3 (success) | Claims verified by grounding engine |
| `compiled` | Stage 6 | Wiki note created, index updated, pipeline complete |
| `failed` | Any stage | Unrecoverable error during processing |

```json
{
  "line": <next_line_number>,
  "source_id": "SRC-20260411-0001",
  "source_type": "pdf",
  "title": "Descriptive title of the source",
  "origin_path": "raw/filename.pdf",
  "processed_at": "2026-04-11T22:00:00+07:00",
  "checksum_sha256": "abc123...",
  "extraction_method": "gemini-flash",
  "status": "extracted",
  "grounding_result": null,
  "wiki_targets": [],
  "notes": ""
}
```

### Idempotency Check
- Before processing, check `manifest.jsonl` for matching `checksum_sha256`
- If found with `status` IN (`grounded`, `compiled`) -> SKIP, inform user "Already ingested"
- If found with `status: "extracted"` or `"pending_grounding"` -> resume from Stage 3
- If found with `status: "failed"` -> allow re-processing from Stage 2

### Output
- Manifest entry appended
- Structured extraction ready for grounding

---

## Stage 3: NotebookLM Grounding

### Pre-check
```
IF NotebookLM MCP is available:
    -> Proceed with grounding
ELSE:
    -> FALLBACK MODE (see below)
```

### Actions (MCP Available)
1. Check if a relevant notebook exists (via `notebook_list`)
2. If not: create notebook via `notebook_create` with title matching the source domain
3. Add source to notebook:
   - URL -> `source_add(source_type="url", url=...)`
   - Text -> `source_add(source_type="text", text=..., title=...)`
   - File -> `source_add(source_type="file", file_path=...)`
4. Wait for source processing to complete (`wait=True`)
5. Query the notebook to verify key claims:
   ```
   notebook_query(notebook_id=..., query="Summarize the key claims and evidence from [source title]")
   ```
6. Record grounding result:
   - Update manifest entry: `status: "grounded"`, `grounding_result: { ... }`

### Actions (FALLBACK -- MCP Unavailable)
1. Log to console: `"[!] NotebookLM MCP NOT AVAILABLE -- entering fallback mode"`
2. Set manifest entry: `status: "pending_grounding"`
3. Add item to `.brain/grounding_queue.json`:
   ```json
   {
     "id": "gq-<source_id>",
     "manifest_ref": "processed/manifest.jsonl#line-<N>",
     "source_title": "...",
     "query": "Verify key claims from [source]",
     "priority": "high",
     "status": "pending",
     "created_at": "<now>",
     "grounding_engine": "notebooklm",
     "notebook_id": null,
     "result_summary": null,
     "target_wiki_path": null,
     "error": "MCP_UNAVAILABLE"
   }
   ```
4. Proceed to Stage 4 with `status: draft` (NOT `grounded`)
5. **DO NOT fake grounding success**

### Output
- Grounding result recorded (or queue entry created)
- Manifest updated

---

## Stage 4: Wiki Note Compile

### Actions
1. Determine note type: `entity`, `concept`, `timeline`, or `source`
2. Determine target path: `wiki/<type>/<slug>.md`
3. Check if note already exists:
   - If exists with `status: verified` -> do NOT overwrite, append new evidence only
   - If exists with `status: draft` -> merge and upgrade
   - If not exists -> create new
4. Generate note content following `wiki/_schemas/note.schema.md`:

```yaml
---
id: "<slug>"
title: "<descriptive title>"
type: <entity|concept|timeline|source>
aliases: []
status: <grounded|draft>  # Based on Stage 3 result
sources:
  - ref: "processed/manifest.jsonl#line-<N>"
    type: <pdf|url|text|drive|notebooklm>
    title: "<source title>"
    accessed_at: "<ISO 8601>"
grounding:
  engine: <notebooklm|none>
  notebook_id: "<UUID or empty>"
  query_used: "<query or empty>"
  grounded_at: "<ISO 8601 or empty>"
  confidence_note: "<note>"
confidence: <high|medium|low|unverified>
created_at: "<ISO 8601>"
updated_at: "<ISO 8601>"
tags: []
related: []
contradictions: []
---

## Summary
...

## Details
...

## Evidence
...

## Change Log
| Date | Change | By |
|------|--------|----|
| <today> | Created from <source_id> | ingest-wiki |
```

### Confidence Assignment Rules
| Condition | Confidence |
|-----------|------------|
| >=2 sources agree + grounded | `high` |
| 1 source + grounded | `medium` |
| 1 source + NOT grounded | `low` |
| No grounding attempted | `unverified` |

### Output
- Wiki note file created/updated at `wiki/<type>/<slug>.md`

---

## Stage 5: Index & Link Update

### Actions
1. Open `wiki/index.md`
2. Find the appropriate section marker (e.g., `<!-- ENTITY_INDEX_START -->`)
3. Add or update the entry:
   ```markdown
   - [<title>](entities/<slug>.md) -- `<status>` | confidence: `<confidence>` | updated: <date>
   ```
4. Scan the new note's `related` field:
   - For each referenced note, verify it exists
   - If it exists, check if it already has a back-link to the new note
   - If not, add the back-link to its `related` field
5. Update `wiki/index.md` Knowledge Health table counts

### Output
- `wiki/index.md` updated
- Cross-links established bidirectionally

---

## Stage 6: .brain Log Update

### Actions
1. **Update manifest status to `compiled`**:
   - Set `status: "compiled"` in `processed/manifest.jsonl` for this entry
   - Set `wiki_targets: ["wiki/<type>/<slug>.md"]`
   - This is the FINAL status -- idempotency check uses this value
2. Update `.brain/grounding_queue.json`:
   - If the item was successfully grounded: remove from queue or set `status: "completed"`
   - Update `updated_at` timestamp
3. If wiki note was created as `draft` (fallback mode):
   - Ensure queue entry remains with `status: "pending"`
   - Manifest stays at `pending_grounding` (NOT `compiled`) until grounding resolves
4. Log a delta entry (for AWF session tracking):
   ```
   [ingest-wiki] Ingested <source_id> -> wiki/<type>/<slug>.md (status: <status>, confidence: <confidence>)
   ```

### Manifest Status at End of Pipeline
| Pipeline Outcome | Manifest Status | Idempotent? |
|-----------------|----------------|-------------|
| Full pipeline (grounded) | `compiled` | Yes -- re-ingest skips |
| Fallback (draft note created) | `pending_grounding` | No -- re-ingest resumes from Stage 3 |
| Error at any stage | `failed` | No -- re-ingest retries from Stage 2 |

### Output
- `.brain/` state consistent with wiki state
- Manifest status reflects actual pipeline outcome
- Pipeline complete

---

## Usage Examples

### Basic Ingest
```
User: Ingest this PDF about Kubernetes networking
-> Copy PDF to raw/
-> Extract claims, entities (K8s, CNI, Calico...)
-> Ground via NotebookLM
-> Create wiki/concepts/kubernetes-networking.md
-> Update index
-> Log to .brain/
```

### Ingest with MCP Down
```
User: Add this article to wiki
-> Copy to raw/
-> Extract and process
-> [!] MCP unavailable -- queue grounding
-> Create wiki/concepts/article-topic.md with status: draft
-> Update index (marked as draft)
-> Queue entry in .brain/grounding_queue.json
```

### Re-ingest (Idempotent)
```
User: Process raw/same-file.pdf again
-> Checksum matches manifest entry with status: compiled
-> "Already ingested. Use lint-wiki to check freshness."
-> STOP (no duplicate)
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Unsupported file format | STOP, inform user |
| Empty file | STOP, inform user |
| Manifest write failure | Retry once, then STOP with error |
| NotebookLM MCP timeout | Fallback mode, queue grounding |
| NotebookLM auth expired | Log error, fallback mode |
| Wiki note path conflict | Merge strategy (see Stage 4) |
| SHA-256 collision | Compare content, create with `-v2` suffix if different |
