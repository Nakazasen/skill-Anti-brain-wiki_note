# Sprint 22: Domain Contamination Guard v1

## Summary

Sprint 22 implements a bounded v1 Domain Contamination Guard in the ABW ingest path. The guard checks each ingested file against an optional `domain_guard` config section in `abw_config.json` to detect, warn, or block cross-domain data from entering draft/manifest/review/wiki without proper signals.

## What Guard Was Added

A new `check_domain_contamination()` function in `scripts/abw_ingest.py` inspects each ingested file's path and content against configured domain keywords and markers. The guard is integrated into `ingest_single_file()` so every file entering the ingest pipeline is checked before draft/manifest/queue creation.

For blocked (cross-domain) files, no draft is created and the file appears in `skipped_files` with action `quarantined`. For warned files, a draft is created but the warning is recorded in all output artifacts.

## Config / Profile Fields Used

The guard reads optional `domain_guard` section from `abw_config.json`:

```json
{
  "domain_guard": {
    "allowed_keywords": ["agv", "wms", "mom", "station", "warehouse"],
    "blocked_keywords": ["website", "ecommerce", "blog", "social media"],
    "required_markers": ["agv", "wms"]
  }
}
```

| Field | Type | Description |
|---|---|---|
| `allowed_keywords` | list[str] | Keywords expected in domain-relevant content |
| `blocked_keywords` | list[str] | Keywords indicating wrong/non-domain content |
| `required_markers` | list[str] | Keywords that MUST appear; missing triggers WARN |

The guard does NOT use the existing `domain_profile` string value ("generic", "manufacturing") which is reserved for the conflict detection profile system. This separation avoids coupling with the conflict engine.

## Behavior Table

| Scenario | domain_check_status | action | Draft Created? | Manifest/Queue Entry? |
|---|---|---|---|---|
| No `domain_guard` config | NOT_CONFIGURED | accept | Yes | Yes |
| No config at all | NOT_CONFIGURED | accept | Yes | Yes |
| Clean matching domain content | PASS | accept | Yes | Yes |
| Missing required markers | WARN | warn | Yes (with warning) | Yes (with warning) |
| No allowed keywords matched | WARN | warn | Yes (with warning) | Yes (with warning) |
| Blocked keywords found + allowed keywords also found | WARN | warn | Yes (with warning) | Yes (with warning) |
| Blocked keywords found, few allowed | BLOCKED | quarantine | No (skipped) | No |
| Malformed guard config (wrong types) | ERROR | warn | Yes (with warning) | Yes (with warning) |
| Broken config JSON | ERROR | warn | Yes (with warning) | Yes (with warning) |

### Decision Logic

1. If no `domain_guard` section or empty keyword lists -> NOT_CONFIGURED (no disruption)
2. Config parse error -> ERROR with action warn (fail-safe, do not silently pass)
3. Blocked keywords detected with >= 2 blocks and < 2 allowed -> BLOCKED (quarantine)
4. Blocked keywords detected but enough allowed keywords also present -> WARN (hedged)
5. Required markers missing -> WARN
6. No allowed keywords matched (when allowed list is configured) -> WARN
7. All checks pass -> PASS

## Structured Result

Each check returns a structured dict:

```json
{
  "domain_check_status": "PASS" | "WARN" | "BLOCKED" | "NOT_CONFIGURED" | "ERROR",
  "domain_check_reason": "string explanation",
  "matched_keywords": ["list", "of", "matched", "allowed", "keywords"],
  "blocked_keywords": ["list", "of", "matched", "blocked", "keywords"],
  "required_markers_missing": ["list", "of", "missing", "required", "markers"],
  "action": "accept" | "warn" | "quarantine"
}
```

This result is visible in:
- Draft file header (Domain Contamination Guard section)
- Manifest entry (`domain_check` field)
- Ingest queue entry (`domain_check` field)
- Run result (`domain_check` field)
- Skipped files entry (for quarantined files)

## Tests Added

File: `tests/test_abw_domain_contamination.py`

17 tests across 2 classes:

**DomainContaminationUnitTests (10 tests)**
- `test_check_domain_contamination_not_configured_when_no_config` - No guard -> NOT_CONFIGURED
- `test_check_domain_contamination_passes_clean_domain_content` - Clean match -> PASS
- `test_check_domain_contamination_warns_on_missing_required_markers` - Missing marker -> WARN
- `test_check_domain_contamination_blocks_cross_domain_keywords` - Cross-domain -> BLOCKED
- `test_check_domain_contamination_warns_when_blocked_and_allowed_overlap` - Mixed signals -> WARN
- `test_check_domain_contamination_not_configured_when_guard_empty_keywords` - Empty guard -> NOT_CONFIGURED
- `test_check_domain_contamination_error_on_malformed_guard_keywords` - Malformed -> ERROR
- `test_check_domain_contamination_error_on_broken_config_json` - Broken JSON -> ERROR
- `test_check_domain_contamination_not_configured_without_missing_workspace` - Missing workspace -> NOT_CONFIGURED
- `test_check_domain_contamination_warns_on_missing_allowed_keywords` - No allowed match -> WARN

**DomainContaminationIngestTests (7 tests)**
- `test_ingest_passes_clean_domain_file_with_domain_check` - Full ingest with PASS
- `test_ingest_quarantines_blocked_domain_file_no_draft_created` - BLOCKED -> no draft
- `test_ingest_warns_on_warn_domain_check_but_creates_draft` - WARN -> draft with warning
- `test_ingest_not_configured_without_domain_guard_still_creates_draft` - NOT_CONFIGURED -> normal ingest
- `test_ingest_domain_check_appears_in_queue_entry` - Queue carries domain_check
- `test_ingest_does_not_write_wiki_with_domain_check` - No silent wiki write
- `test_ingest_quarantined_directory_mode_continues_processing_other_files` - Batch mode quarantine

## Sprint 21 Invariants Preserved

- No auto-promote path added or modified
- No wiki write path added (ingest never writes wiki, confirmed by test)
- Manual-first promotion invariant preserved
- `promotion_mode: auto` behavior not expanded
- `_review_decision` unchanged (still always returns `review_needed`)

## Limitations

- **Keywords are substring-matched** (case-insensitive). False positives possible on simple keyword overlap. For example, "WMS" could appear in a website domain context. The guard uses keyword count thresholds to mitigate this.
- **No semantic/ML classification** - This is a rule-based keyword guard only. It does not understand document meaning.
- **No bridge integration** - The guard works within ABW ingest only. No NVIDIA-to-ABW cross-repo contamination detection.
- **Domain profile not extended** - The existing `domain_profile` config field ("generic"/"manufacturing") is not used for contamination checking; a separate `domain_guard` section is used.
- **Ingest maturity not fully solved** - This guard addresses one gap (contamination) but does not handle: aggregate gap report, stable ingest-bound output contract, or full pipeline maturity.
- **`domain_guard` config is optional** - Without explicit configuration, the guard reports NOT_CONFIGURED and does not block any ingest. Users must configure it to activate protection.

## Non-Claims

- No bridge implemented
- No self-growing wiki
- Ingest maturity not fully solved
- Aggregate report/gap-output may still be unresolved
- No NVIDIA repo modified
- No control repo modified
- No Sprint 23 work started
- No production/Cognitive OS claim
- No enterprise-grade security claim

## Files Modified / Added

| File | Nature | Lines |
|---|---|---|
| `scripts/abw_ingest.py` | Added `check_domain_contamination()`, integrated into `ingest_single_file()`, `write_draft()`, `append_manifest_entry()`, `update_ingest_queue()`, `run()` | ~120 |
| `tests/test_abw_domain_contamination.py` | New test file: 17 tests | ~340 |
| `docs/sprint-22-domain-contamination-guard.md` | Sprint documentation | This file |
