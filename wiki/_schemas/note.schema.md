# Wiki Note Schema

> Version: 1.0.0 | Hybrid ABW
> All `.md` files in `wiki/entities/`, `wiki/concepts/`, `wiki/timelines/`, `wiki/sources/` MUST follow this schema.

---

## YAML Frontmatter (Required)

```yaml
---
# === IDENTITY ===
id: "entity-unique-slug"            # kebab-case, unique across wiki/
title: "Display Name"                # Human-readable title
type: entity | concept | timeline | source   # Must match containing directory
aliases: []                          # Alternative names for cross-linking

# === PROVENANCE ===
status: draft | grounded | verified | stale | disputed
  # draft      = just created, not yet grounded
  # grounded   = verified via NotebookLM or processed/ pipeline
  # verified   = cross-checked from >=2 independent sources
  # stale      = needs re-grounding (>30 days or source changed)
  # disputed   = has unresolved contradiction

sources:
  - ref: "processed/manifest.jsonl#line-42"  # Link to manifest entry
    type: pdf | url | text | drive | notebooklm
    title: "Original document name"
    accessed_at: "2026-04-11T22:00:00+07:00"

grounding:
  engine: notebooklm | manual | none
  notebook_id: ""                    # NotebookLM notebook UUID (if applicable)
  query_used: ""                     # Query used for verification
  grounded_at: ""                    # ISO 8601
  confidence_note: ""                # Note about confidence level

# === METADATA ===
confidence: high | medium | low | unverified
  # high       = >=2 sources agree, grounded
  # medium     = 1 source, grounded
  # low        = 1 source, not grounded
  # unverified = has not been through processed/ pipeline

created_at: "2026-04-11T22:00:00+07:00"
updated_at: "2026-04-11T22:00:00+07:00"
tags: []                             # Free-form classification
related:                             # Cross-links to other notes
  - "wiki/concepts/some-concept.md"
  - "wiki/entities/some-entity.md"

# === CONTRADICTION TRACKING ===
contradictions: []
  # - claim: "Source A says X"
  #   counter_claim: "Source B says Y"
  #   source_a: "processed/manifest.jsonl#line-10"
  #   source_b: "processed/manifest.jsonl#line-25"
  #   resolution: pending | resolved
  #   resolved_by: ""
---
```

---

## Body Structure (Recommended)

```markdown
## Summary

2-3 sentence summary of the entity/concept. Should include at least 1 citation.

## Details

Main content with inline citations like `[src:manifest-line-42]`.

## Evidence

- [OK] Grounded: <summary of verified evidence>
- [!] Gaps: <what has not been confirmed>

## Related

- [[wiki/concepts/related-concept]]
- [[wiki/entities/related-entity]]

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-11 | Created | ingest-wiki |
```

---

## Validation Rules

| Rule | Description | Severity |
|------|-------------|----------|
| `id` unique | No duplicate `id` across all of `wiki/` | ERROR |
| `status` required | Must be one of 5 values | ERROR |
| `sources` non-empty | At least 1 source reference | ERROR |
| `confidence` required | Must be one of 4 values | ERROR |
| `updated_at` format | ISO 8601 | ERROR |
| `grounding.engine` sync | If `status=grounded` then `grounding.engine` != `none` | WARNING |
| Cross-link valid | All paths in `related` must exist | WARNING |
| Stale check | `updated_at` > 30 days -> suggest `status: stale` | INFO |

---

## Example: Minimal Valid Note

```yaml
---
id: "gemini-flash-context-limits"
title: "Gemini Flash Context Window Limits"
type: concept
aliases: ["flash context", "context limit"]
status: grounded
sources:
  - ref: "processed/manifest.jsonl#line-1"
    type: url
    title: "Gemini API Documentation"
    accessed_at: "2026-04-11T22:00:00+07:00"
grounding:
  engine: notebooklm
  notebook_id: "abc-123-def"
  query_used: "What is the context window limit of Gemini Flash?"
  grounded_at: "2026-04-11T22:05:00+07:00"
  confidence_note: "Confirmed by official docs"
confidence: high
created_at: "2026-04-11T22:00:00+07:00"
updated_at: "2026-04-11T22:05:00+07:00"
tags: ["gemini", "context-window", "limitations"]
related:
  - "wiki/entities/gemini-flash.md"
contradictions: []
---

## Summary

Gemini Flash 2.5 has a context window of 1M tokens [src:manifest-line-1].

## Details

The effective usable context is approximately 80% of the max due to system prompt overhead.

## Evidence

- [OK] Grounded via NotebookLM: official documentation confirms 1M token limit
- [!] Gap: real-world performance degradation at >500K tokens unverified

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-11 | Created from official docs | ingest-wiki |
```
