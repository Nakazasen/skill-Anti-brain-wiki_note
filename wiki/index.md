# Hybrid Anti-Brain-Wiki -- Knowledge Index

> **Auto-generated index.** Updated by `ingest-wiki` and `lint-wiki` skills.  
> Last updated: 2026-04-11T23:58:00+07:00

---

## How This Wiki Works

```
raw/  ->  processed/  ->  NotebookLM grounding  ->  wiki/  ->  index update  ->  .brain/ log
```

- **Never** write directly from `raw/` to `wiki/`.
- Every note follows [`wiki/_schemas/note.schema.md`](./_schemas/note.schema.md).
- Every processed source has a line in [`processed/manifest.jsonl`](../processed/manifest.jsonl).

---

## Entities

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- ENTITY_INDEX_START -->

_No entities yet. Run `ingest-wiki` to populate._

<!-- ENTITY_INDEX_END -->

---

## Concepts

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- CONCEPT_INDEX_START -->

| ID | Title | Status | Confidence | Updated |
|----|-------|--------|------------|--------|
| `postgresql-selection-rationale` | [PostgreSQL Selection Rationale](concepts/postgresql-selection-rationale.md) | grounded | medium | 2026-04-11 |
| `mongodb-evaluation` | [MongoDB Evaluation](concepts/mongodb-evaluation.md) | disputed | low | 2026-04-11 |

<!-- CONCEPT_INDEX_END -->

---

## Timelines

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- TIMELINE_INDEX_START -->

_No timelines yet. Run `ingest-wiki` to populate._

<!-- TIMELINE_INDEX_END -->

---

## Sources

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- SOURCE_INDEX_START -->

_No sources yet. Run `ingest-wiki` to populate._

<!-- SOURCE_INDEX_END -->

---

## Knowledge Health

| Metric | Count |
|--------|-------|
| Total notes | 2 |
| Grounded | 1 |
| Draft | 0 |
| Stale | 0 |
| Disputed | 1 |
| Open gaps | See [`.brain/knowledge_gaps.json`](../.brain/knowledge_gaps.json) |
| Pending grounding | See [`.brain/grounding_queue.json`](../.brain/grounding_queue.json) |

---

## Cross-Reference Map

_Empty -- will be populated as notes with `related` fields are added._

---

## Quick Commands

| Command | What it does |
|---------|-------------|
| `abw-ingest` | Process raw sources -> grounding -> wiki notes |
| `abw-query` | Search wiki, fallback to NotebookLM, log gaps |
| `abw-query-deep` | Bounded thinking loop for complex queries (TTC) |
| `abw-lint` | Audit structure, grounding, TTC health (12 checks) |
| `abw-status` | Quick health check for MCP connection and Queue |
| `abw-setup` | Interactive wizard for NotebookLM connection setup |

---

*Schema: [`wiki/_schemas/note.schema.md`](./_schemas/note.schema.md)*  
*Manifest: [`processed/manifest.jsonl`](../processed/manifest.jsonl)*
