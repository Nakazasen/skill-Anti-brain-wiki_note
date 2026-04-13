# hello-abw

This is the minimal example workspace for Hybrid ABW.

## Goal

Show the smallest useful path:

1. `/abw-ingest`
2. `/abw-ask`
3. `/abw-pack`
4. `/abw-sync` dry-run
5. `/abw-eval`
6. `/abw-wrap`

## Contents

- `raw/`
- `processed/manifest.jsonl`
- `wiki/`

## Note

On a clean clone without `processed/manifest.jsonl`, `/abw-pack` should be expected to land in `needs_review`.
