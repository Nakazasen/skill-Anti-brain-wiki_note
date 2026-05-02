# Sprint 20: ABW Ingest Baseline Gap Map

## Verdict

BASELINE_MAPPED

## Executive Summary

ABW ingest currently supports one-command ingest (`abw ingest raw/`), creates drafts, writes manifest entries, updates ingest queue, and records ingest run/state artifacts. Test evidence shows `tests/test_abw_ingest.py` passes `48/48`.

Major governance gaps remain before ABW ingest can be considered mature:
- no domain/workspace contamination guard in ingest flow
- auto-promotion side paths exist (not manual-only by default)
- ingest gap reporting is not integrated as an automatic post-ingest machine-readable output

This is baseline evidence only, not proof of a mature self-ingesting governance runtime.

## One-Command Ingest Reality

- Command surface exists: `abw ingest raw/` and `abw ingest raw/<file>` via `scripts/abw_cli.py` -> runner -> `scripts/abw_ingest.py`.
- Directory ingest supports mixed files, skip reasons, and continues on parse errors for directory mode.
- Evidence: `tests/test_abw_ingest.py::test_raw_folder_shortcut_ingests_raw_directory`, `test_directory_ingest_reports_skipped_files`, `test_invalid_path_returns_explicit_error`, `test_missing_path_returns_clear_help_error`.

## Pipeline Stage Matrix (17 Stages)

| Stage | Status | Evidence | Test Evidence | Risk |
|---|---|---|---|---|
| raw discovery | IMPLEMENTED | `discover_ingest_files` in `scripts/abw_ingest.py` | ingest tests pass | LOW |
| supported type filtering | IMPLEMENTED | `SUPPORTED_EXTENSIONS` and extractors | ingest tests pass | LOW |
| parse/extract | IMPLEMENTED | `_extract_multimodal_content` and format extractors | ingest tests pass | LOW |
| normalization/cleaning | IMPLEMENTED | `_clean_content_for_draft`, `_clean_extracted_lines` | ingest tests pass | LOW |
| draft generation | IMPLEMENTED | `write_draft` path | ingest tests pass | LOW |
| manifest generation | IMPLEMENTED | `append_manifest_entry` | ingest tests pass | LOW |
| source identity/hash | IMPLEMENTED | deterministic ID, source fingerprint/hash/state | ingest tests pass | LOW |
| rename/delete lineage tracking | IMPLEMENTED | state + manifest/queue rename/stale helpers | ingest tests pass | LOW |
| skipped/failed file visibility | IMPLEMENTED | `skipped_files` with reason/action/message | ingest tests pass | LOW |
| ingest run/state persistence | IMPLEMENTED | `.brain/ingest_runs.jsonl`, `.brain/ingest_state.json` updates | ingest tests pass | LOW |
| review queue population | IMPLEMENTED | `update_ingest_queue` to `.brain/ingest_queue.json` | ingest tests pass | LOW |
| explicit review approve path | IMPLEMENTED | `scripts/abw_review.py` approve workflow | code confirmed | LOW |
| no blind auto-promote | PARTIAL | `_review_decision` threshold and `run_promote_drafts` side path | promotion tests confirm auto-promote | HIGH |
| safe promote manual-only invariant | PARTIAL | manual approve exists, but auto side path still writes wiki | promotion tests | HIGH |
| gap report tied to ingest output | PARTIAL | `src/abw/gaps.py` built from eval/inspect, not ingest-run output | gaps tests + code | MEDIUM |
| aggregate ingest report contract | PARTIAL | per-run counters exist in run result, but no dedicated stable report contract | code confirmed | MEDIUM |
| domain/workspace contamination guard | MISSING | no ingest-stage domain-profile enforcement gate | code + missing tests | HIGH |

Status summary from matrix above:
- IMPLEMENTED: 12/17
- PARTIAL: 4/17
- MISSING: 1/17
- UNKNOWN: 0/17

## Critical Gaps

1. Domain/workspace contamination guard is missing in ingest decision path.
2. Auto-promotion side paths exist and can write to wiki without explicit per-item human approval.
3. Gap report generation is not an automatic ingest-bound output contract.
4. No stable machine-readable ingest-gap contract that combines skipped/failed/promote-risk/domain-risk in one post-ingest report.

## Test Evidence Snapshot

Executed in this audit:
- `py -m pytest tests/test_abw_ingest.py -v --tb=short` -> `48 passed`
- `py -m pytest tests/test_abw_health.py tests/test_abw_inspect.py tests/test_abw_gaps.py tests/test_promotion_engine.py -v --tb=short` -> `29 passed, 2 failed`

Observed failures (pre-existing, not introduced by docs-only Sprint 20 output):
- `tests/test_abw_inspect.py::test_inspect_docx_heavy_workspace`
- `tests/test_abw_gaps.py::test_xls_heavy_workspace_reports_format_block`

## Sprint 21-22 Follow-up Direction (Planning Only)

Sprint 21 target:
- enforce domain-profile contamination checks in ingest
- make manual-only promotion mode enforceable by config
- add tests for contamination and no-blind-auto-promote behavior

Sprint 22 target:
- add ingest-bound machine-readable gap report
- unify ingest skipped/failed/risk outputs into stable post-ingest report
- add acceptance tests for ingest-gap integration

## Non-Claims

This Sprint 20 baseline does not claim:
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

## Evidence Scope

Inspected source/tests include:
- `scripts/abw_ingest.py`
- `scripts/abw_review.py`
- `scripts/abw_knowledge.py`
- `src/abw/gaps.py`
- `src/abw/inspect.py`
- `src/abw/conflicts.py`
- `tests/test_abw_ingest.py`
- `tests/test_promotion_engine.py`
- `tests/test_abw_gaps.py`
