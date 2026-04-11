---
id: "mongodb-evaluation"
title: "MongoDB Evaluation"
type: concept
aliases: ["mongo eval", "mongodb comparison"]
status: disputed
sources:
  - ref: "processed/manifest.jsonl#line-2"
    type: text
    title: "MongoDB Technical Assessment"
    accessed_at: "2026-04-11T23:00:00+07:00"
grounding:
  engine: manual
  notebook_id: ""
  query_used: "What were the findings from the MongoDB evaluation?"
  grounded_at: "2026-04-11T23:00:00+07:00"
  confidence_note: "Partial -- cost analysis disputed by DevOps team"
confidence: low
created_at: "2026-04-11T23:00:00+07:00"
updated_at: "2026-04-11T23:00:00+07:00"
tags: ["database", "mongodb", "architecture-decision"]
related:
  - "wiki/concepts/postgresql-selection-rationale.md"
contradictions:
  - claim: "MongoDB is more expensive at scale due to Atlas pricing"
    counter_claim: "MongoDB self-hosted on k8s is cheaper than managed PostgreSQL"
    source_a: "processed/manifest.jsonl#line-2"
    source_b: "processed/manifest.jsonl#line-3"
    resolution: pending
    resolved_by: ""
---

## Summary

MongoDB was evaluated as an alternative to PostgreSQL for the analytics service. It was rejected for ACID concerns but the cost comparison remains disputed [src:manifest-line-2].

## Details

MongoDB strengths identified:
1. Native document model fits event log ingestion
2. Horizontal scaling simpler than PostgreSQL sharding
3. Atlas provides managed HA out of the box

MongoDB concerns:
1. Multi-document ACID transactions added in 4.0 but not as mature as PostgreSQL
2. Cost comparison disputed between managed Atlas and self-hosted k8s deployment
3. Team lacked deep MongoDB operational experience

## Evidence

- [OK] Grounded via manual review: technical assessment doc reviewed
- [!] Disputed: cost comparison -- engineering says Atlas is expensive, DevOps says self-hosted Mongo is cheaper

## Related

- [[wiki/concepts/postgresql-selection-rationale]]

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-11 | Created from technical assessment | ingest-wiki |
