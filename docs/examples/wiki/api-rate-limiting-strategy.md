---
id: "api-rate-limiting-strategy"
title: "API Rate Limiting Strategy"
type: concept
aliases: ["rate limiting", "token bucket", "API throttling"]
status: draft
sources:
  - ref: "processed/manifest.jsonl#line-4"
    type: text
    title: "API Rate Limiting Strategy"
    accessed_at: "2026-04-11T23:57:00+07:00"
grounding:
  engine: none
  notebook_id: ""
  query_used: ""
  grounded_at: ""
  confidence_note: "MCP unavailable at ingest time -- queued for grounding"
confidence: low
created_at: "2026-04-11T23:57:00+07:00"
updated_at: "2026-04-11T23:57:00+07:00"
tags: ["api", "rate-limiting", "token-bucket", "infrastructure"]
related: []
contradictions: []
---

## Summary

The platform uses a tiered rate limiting strategy (Free/Pro/Enterprise) implemented via token bucket algorithm at the API Gateway level [src:manifest-line-4].

## Details

### Tier Structure
- Free tier: 100 req/min, 10,000 req/day
- Pro tier: 1,000 req/min, 100,000 req/day
- Enterprise tier: Custom limits per contract

### Token Bucket Implementation
- Bucket size = burst limit (allows short spikes)
- Refill rate = sustained request rate
- Overflow returns HTTP 429 Too Many Requests with Retry-After header

### Monitoring
Rate limit hits tracked via Prometheus:
- `api_rate_limit_hits_total{tier, endpoint}` -- counter of 429 responses
- `api_rate_limit_remaining{api_key}` -- gauge of remaining tokens

### Known Issues
1. Enterprise customers hit limits during batch imports despite "unlimited" contracts
2. Token bucket does not distinguish read vs write operations

### Decision Timeline
- 2025-11-15: Adopted token bucket over fixed window
- 2026-01-20: Added per-endpoint granularity
- 2026-03-10: Enterprise tier review pending (read/write separation)

## Evidence

- [!] Draft: MCP unavailable at ingest time -- not grounded
- [!] Gap: Enterprise tier actual usage patterns not quantified
- [!] Gap: Read/write separation design not documented

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-11 | Created from SRC-20260412-0001 | ingest-wiki |
