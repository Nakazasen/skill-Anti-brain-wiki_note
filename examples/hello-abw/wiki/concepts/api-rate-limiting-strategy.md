---
id: "api-rate-limiting-strategy"
title: "API Rate Limiting Strategy"
type: concept
status: grounded
sources:
  - ref: "processed/manifest.jsonl#line-1"
    type: text
    title: "API Rate Limiting Strategy"
    accessed_at: "2026-04-13T22:00:00+07:00"
grounding:
  engine: manual
  notebook_id: ""
  query_used: "What is the current API rate limiting strategy?"
  grounded_at: "2026-04-13T22:00:00+07:00"
confidence: medium
created_at: "2026-04-13T22:00:00+07:00"
updated_at: "2026-04-13T22:00:00+07:00"
tags: ["api", "rate-limit"]
related: []
contradictions: []
---

## Summary

The service uses token-bucket rate limiting at the API gateway with a burst allowance and a steady refill rate [src:manifest-line-1].

## Details

- burst limit: 100 requests
- steady rate: 20 requests per second
- authenticated users receive higher burst limits
