# API Rate Limiting Strategy

## Overview

Our platform uses a tiered rate limiting approach for API consumers:
- Free tier: 100 requests/minute, 10,000 requests/day
- Pro tier: 1,000 requests/minute, 100,000 requests/day
- Enterprise tier: Custom limits, negotiated per contract

## Implementation

Rate limiting is implemented at the API Gateway level using a token bucket algorithm.
Each API key has an associated bucket that refills at a fixed rate.

### Token Bucket Parameters
- Bucket size = burst limit (allows short spikes)
- Refill rate = sustained request rate
- Overflow = HTTP 429 Too Many Requests with Retry-After header

## Monitoring

Rate limit hits are tracked via Prometheus metrics:
- `api_rate_limit_hits_total{tier, endpoint}` -- counter of 429 responses
- `api_rate_limit_remaining{api_key}` -- gauge of remaining tokens

## Current Issues

1. Enterprise customers occasionally hit rate limits during batch imports despite having "unlimited" contracts.
2. The token bucket does not distinguish between read and write operations -- heavy read clients penalize their own writes.

## Decision Log

- 2025-11-15: Adopted token bucket over fixed window (reduces burst edge cases)
- 2026-01-20: Added per-endpoint granularity (previously was global per API key)
- 2026-03-10: Enterprise tier review pending -- need to separate read/write budgets
