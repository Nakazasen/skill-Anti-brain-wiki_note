# ABW v1.2 Ingest Acceptance Criteria (Sprint 21-22 Target)

## Scope

This document defines testable acceptance criteria for hardening work after Sprint 20 baseline mapping.
It is a target contract for Sprint 21-22 implementation, not a claim that current ABW ingest already satisfies all items.

## Current Baseline Reminder

Current audit evidence:
- ingest core tests: `48/48` pass (`tests/test_abw_ingest.py`)
- supporting suite: `29 pass, 2 fail` (`tests/test_abw_health.py`, `tests/test_abw_inspect.py`, `tests/test_abw_gaps.py`, `tests/test_promotion_engine.py`)
- known fails are pre-existing and must be tracked explicitly

## Acceptance Criteria

### AC1. One-command ingest remains stable

Required proof:
- `abw ingest raw/` and `abw ingest raw/<file>` execute successfully in supported scenarios.
- Ingest result includes `scanned_count`, `changed_count`, `ingested_count`, `skipped_count`.
- Skipped entries include path + reason + action.

### AC2. Draft + manifest + queue artifacts remain consistent

Required proof:
- draft files generated for ingested sources.
- `processed/manifest.jsonl` updated with source identity fields.
- `.brain/ingest_queue.json` updated with queue entries.
- rename/delete lineage is preserved without duplicate logical source identity.

### AC3. No blind auto-promote in manual mode

Required proof:
- a config mode (for example `promotion_mode: manual`) blocks auto-promotion paths.
- with manual mode active, no wiki write occurs without explicit review/approve action.
- tests explicitly verify confidence-threshold logic does not bypass manual mode.

### AC4. Domain/workspace contamination guard exists

Required proof:
- ingest checks workspace/domain profile compatibility before promotion-sensitive transitions.
- mismatched domain signals are flagged or quarantined.
- contamination tests exist and pass.

### AC5. Ingest-bound machine-readable gap output exists

Required proof:
- post-ingest output contains machine-readable summary for ingest risks/gaps.
- output includes skipped/failed breakdown and actionable categories.
- output is generated from ingest reality, not only eval-only context.

### AC6. No grounded claim without valid source

Required proof:
- trust status language in outputs is explicit and conservative.
- auto-promoted content (if enabled) is clearly labeled and separated from trusted canonical knowledge.
- missing evidence paths remain visible as gaps.

### AC7. Regression safety

Required proof:
- `tests/test_abw_ingest.py` remains all-pass.
- known pre-existing failures are either fixed in scoped sprint or explicitly tracked as unresolved with rationale.
- no silent degradation in health/inspect/gaps/promotion suites.

## Required Negative Tests

1. parse error isolation in batch ingest
2. unsupported extension skip with explicit reason
3. empty file skip with explicit reason
4. re-run dedup safety (no duplicate logical draft identity)
5. domain contamination detection path
6. manual-mode auto-promote block
7. conflict path does not silently promote

## Forbidden Behaviors

- blind auto-promote when manual mode is configured
- silent wiki writes without traceable review/approval path
- cross-domain ingestion without warning/quarantine behavior
- grounded/trusted claim without valid source evidence

## Non-Claims

This acceptance contract does not claim:
- production-ready
- Cognitive OS achieved
- VS Code parity
- Cursor parity
- enterprise-grade security
- full NVIDIA<->ABW bridge
- self-growing wiki
- autonomous self-learning
- mature self-ingesting knowledge system
- fully solved ingest pipeline

## Exit Condition for Opening Bridge Phase 1

Bridge Phase 1 should remain blocked until:
- contamination guard is implemented and tested
- manual-mode no-blind-auto-promote invariant is verified
- ingest-bound machine-readable gap output exists
- validation evidence is audited and accepted
