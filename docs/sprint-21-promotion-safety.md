# Sprint 21: Promotion Safety -- Disable Blind Auto-Promotion

## Summary

Sprint 21 disabled and gated the two blind auto-promotion paths identified in Sprint 20's gap map:

1. **`_review_decision` auto-promote at confidence >= 0.8** -- removed, always returns `review_needed`
2. **`run_promote_drafts` silent wiki writes** -- gated behind `providers.promotion_mode: "auto"` config, disabled by default

## Blind Auto-Promote Paths (Before)

### Path 1: `_review_decision` in `scripts/abw_ingest.py:735`

- **Old behavior**: When `confidence >= AUTO_PROMOTE_THRESHOLD (0.8)`, returned `"candidate_promoted"` with reason `"high_confidence"`, setting `queue_status` to a promoted state without explicit review.
- **Risk**: High-confidence PDF/text files could bypass review queue. While this only set queue status (not a direct wiki write), it signaled that the file was "promoted" with no explicit human action.
- **Triggered by**: Any ingest producing confidence >= 0.8.

### Path 2: `run_promote_drafts` in `scripts/abw_knowledge.py:941`

- **Old behavior**: Scored all drafts in `drafts/` directory, auto-wrote high-scoring drafts to `wiki/auto_promoted/` without requiring explicit approval.
- **Risk**: This was the most dangerous path -- it silently created wiki files from drafts. Only guard was human-wiki collision check (would not overwrite existing wiki).
- **Triggered by**: API call to `/promote-drafts` endpoint, or direct call to `run_promote_drafts()`.

## What Changed

### 1. `_review_decision` (`scripts/abw_ingest.py:735`)

Removed the `candidate_promoted` auto-path. The function now:

- Returns `("review_needed", "conflict_detected")` for conflicts (unchanged)
- Returns `("review_needed", "medium_confidence_enterprise_parse")` for medium-confidence enterprise formats (unchanged reason, but status is now `review_needed` instead of `candidate_ready`)
- Returns `("review_needed", "low_confidence")` for low-confidence (unchanged)
- **NEVER** returns `"candidate_promoted"` regardless of confidence level

The `AUTO_PROMOTE_THRESHOLD = 0.8` constant is no longer referenced by this function and is preserved only for backward reference.

### 2. `run_promote_drafts` (`scripts/abw_knowledge.py:941`)

Added an explicit config gate that checks `abw_config.json` for `providers.promotion_mode`:

- **Default**: Auto-promotion is **disabled**. The function returns `promoted_count: 0` with message: "Auto-promotion is disabled by default. Set providers.promotion_mode=auto in abw_config.json to enable."
- **Enabled when**: User explicitly sets `"providers": {"promotion_mode": "auto"}` in `abw_config.json`.
- **Dry run**: Works as before -- reports what would be promoted without writing files.
- **Human wiki collision**: Still blocked even when auto-promote is enabled (unchanged safety check).

### 3. Existing tests updated

- `test_abw_ingest.py`: 3 assertions updated to expect `review_needed` instead of `candidate_promoted` or `candidate_ready`
- `test_promotion_engine.py`: 3 existing tests updated to include `promotion_mode: auto` config

### 4. New safety tests added

8 new tests in `test_promotion_engine.py` (`TestPromotionSafety` class):

| Test | What It Proves |
|---|---|
| `test_review_decision_never_returns_candidate_promoted` | `_review_decision` never returns promoted status at any confidence |
| `test_review_decision_low_confidence_returns_review_needed` | Low confidence always requires review |
| `test_review_decision_conflict_always_review_needed` | Conflicts always require review, even at high confidence |
| `test_auto_promote_disabled_by_default` | `run_promote_drafts` returns 0 without auto config |
| `test_auto_promote_enabled_with_config` | With `promotion_mode: auto`, promotion still works |
| `test_ingest_high_confidence_does_not_auto_promote` | High-confidence ingest produces review_needed, not auto-promoted |
| `test_ingest_creates_queue_not_wiki` | Ingest creates queue entry, never writes wiki directly |
| `test_explicit_approval_path_still_works` | Draft creation + queue entry works end-to-end |

## Manual-First Invariant

After Sprint 21:

1. **Default behavior is manual-only**: No wiki content is created without explicit review/approval.
2. **Auto-promotion is opt-in**: Users must explicitly set `providers.promotion_mode: "auto"` in `abw_config.json`.
3. **Ingest always produces review queue**: All ingested files get `review_needed` queue status regardless of confidence.
4. **No path writes wiki silently**: Both `_review_decision` and `run_promote_drafts` are gated.

## Explicit Approval Behavior

The existing explicit approval path in `scripts/abw_review.py` is **preserved unchanged**:

- `abw review` lists queued drafts
- `abw approve draft drafts/<name>` explicitly promotes a draft from queue to wiki
- `promote_draft()` moves file from `drafts/` to `wiki/` and updates queue status to `approved`
- This path was already safe -- it requires explicit draft path input and queue entry validation

## Limitations

- **Domain contamination is NOT addressed**: This sprint focused solely on blind auto-promotion. Cross-domain source ingestion without warning is still possible.
- **Auto-promotion can still be enabled**: Setting `promotion_mode: auto` in config restores the `run_promote_drafts` behavior. This is opt-in, not the default.
- **`candidate_ready` status removed entirely**: The medium-confidence enterprise parse path previously set `candidate_ready` (a softer form of auto-promotion). This now goes to `review_needed`. The old behavior can't be restored.
- **API endpoint still works**: `/promote-drafts` API is preserved but returns 0 promoted by default.
- **No bridge integration**: Sprint 21 does not implement any NVIDIA-ABW bridge functionality.

## Non-Claims

- No bridge implemented
- No self-growing wiki claimed
- Ingest maturity not fully solved (domain contamination still unresolved)
- No production/Cognitive OS claim
- No Sprint 22 work started

## Tests Added

File: `tests/test_promotion_engine.py`
- 8 new tests in `TestPromotionSafety` class
- 13 total promotion tests (was 5)
- All 13 passing

## Files Modified

| File | Lines Changed | Nature |
|---|---|---|
| `scripts/abw_ingest.py` | ~10 | Removed auto-promote threshold from `_review_decision` |
| `scripts/abw_knowledge.py` | ~25 | Added `_is_auto_promotion_allowed` gate to `run_promote_drafts` |
| `tests/test_abw_ingest.py` | ~10 | Updated assertions to expect `review_needed` |
| `tests/test_promotion_engine.py` | ~110 | Added 8 safety tests, updated 3 existing tests with config |

No other files modified. No bridge, no NVIDIA repo, no control repo changes.
