# Grounding Backend Contract

Hybrid ABW currently ships with NotebookLM as the first real grounding backend.

## Current Backend

- NotebookLM MCP
- `nlm` CLI

## Required Capabilities

Any future backend should support:

1. health check
2. explicit auth or connection state
3. source ingestion or synchronization
4. reproducible retrieval
5. honest degraded mode

## Required ABW Semantics

- no fake grounding
- clear fallback when grounding is unavailable
- traceability back to source or logged gap
- explicit operator approval before expensive or destructive sync steps

## Status

- implemented today: NotebookLM
- future direction: pluggable grounding backend contract
