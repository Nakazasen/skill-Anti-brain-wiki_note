---
id: "postgresql-selection-rationale"
title: "PostgreSQL Selection Rationale"
type: concept
aliases: ["postgres choice", "db selection"]
status: grounded
sources:
  - ref: "processed/manifest.jsonl#line-1"
    type: text
    title: "Architecture Decision Record - Database Selection"
    accessed_at: "2026-04-11T23:00:00+07:00"
grounding:
  engine: manual
  notebook_id: ""
  query_used: "Why was PostgreSQL selected for the analytics service?"
  grounded_at: "2026-04-11T23:00:00+07:00"
  confidence_note: "Confirmed by engineering team lead"
confidence: medium
created_at: "2026-04-11T23:00:00+07:00"
updated_at: "2026-04-11T23:00:00+07:00"
tags: ["database", "postgresql", "architecture-decision"]
related:
  - "wiki/concepts/mongodb-evaluation.md"
contradictions: []
---

## Summary

PostgreSQL was selected for the analytics service due to its strong ACID compliance, advanced indexing, and mature support for complex queries [src:manifest-line-1].

## Details

The team evaluated PostgreSQL, MongoDB, and CockroachDB. PostgreSQL won because:
1. ACID compliance required for financial analytics
2. JSONB support covers document-style needs without sacrificing relational integrity
3. Mature ecosystem with proven HA solutions (Patroni, pgBouncer)
4. Team expertise already existed

MongoDB was rejected primarily due to consistency concerns in multi-document transactions.

## Evidence

- [OK] Grounded via manual confirmation: engineering lead confirmed rationale
- [!] Gap: cost comparison data between PostgreSQL and MongoDB not quantified

## Related

- [[wiki/concepts/mongodb-evaluation]]

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-11 | Created from ADR review | ingest-wiki |
