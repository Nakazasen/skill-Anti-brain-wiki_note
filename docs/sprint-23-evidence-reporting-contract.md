# Sprint 23: Evidence Reporting Contract

## Why Sprint 23 Exists

Sprint 20 identified a missing machine-readable gap/report contract in the ABW
ingest flow. The existing gaps pipeline (src/abw/gaps.py) serves eval/inspect
orientations but does not produce a stable, versioned, run-correlated evidence
pair per ingest run.

Sprint 23 creates the minimal machine-readable contract artifacts required for
future read-only/evidence-only bridge consumption without inventing truth or
claiming bridge readiness.

## Gate Context

Gate review selected: C. INSERT_EVIDENCE_REPORTING_SPRINT

Bridge Phase 1: NOT AUTHORIZED.

Safety baseline after Sprint 20-22 is adequate, but bridge-facing evidence/
reporting contract was not sufficiently explicit/stable. Sprint 23 addresses
this gate blocker.

## Artifact Paths

Both artifacts are written under `.brain/` alongside existing ingest metadata:

| Artifact | Path |
|---|---|
| Ingest Report | `.brain/ingest_report.json` |
| Ingest Gaps | `.brain/ingest_gaps.json` |

These paths align with existing conventions:
- `.brain/ingest_runs.jsonl` (append-only ingest run log)
- `.brain/ingest_queue.json` (pending review items)
- `.brain/ingest_state.json` (fingerprint/delta state)
- `processed/manifest.jsonl` (source manifest)

## Schema Versions

| Artifact | Schema Version |
|---|---|
| ingest_report.json | `abw.ingest_report.v1` |
| ingest_gaps.json | `abw.ingest_gaps.v1` |

## Run Correlation

Both artifacts share:
- Same `run_id` (format: `run-{workspace_name}-{YYYYMMDDThhmmss}`)
- Same `created_at` (ISO 8601 UTC)
- Same `workspace` (absolute path)

This ensures a future bridge can correlate the report and gap output for a
single ingest run without ambiguity.

## ingest_report.json Field Definitions

### Top-level

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"abw.ingest_report.v1"` |
| `run_id` | string | Unique ingest run identifier |
| `created_at` | string | ISO 8601 UTC timestamp |
| `workspace` | string | Absolute workspace path |
| `command` | string | Ingest command string (e.g. "ingest raw/test.md") |
| `summary` | object | Aggregate counts (see summary fields) |
| `items` | array | Per-source ingest outcome records |
| `safety` | object | Safety/guard state (see safety fields) |
| `limitations` | array | Known limitations of this report |

### summary Fields

| Field | Type | Description |
|---|---|---|
| `ingested_count` | integer | Successfully ingested items |
| `skipped_count` | integer | Skipped files (unchanged, junk, etc.) |
| `failed_count` | integer | Parse errors during ingest |
| `quarantined_count` | integer | Domain-blocked files |
| `draft_count` | integer | Draft files created |
| `manifest_count` | integer | Sources in changed set |
| `queue_count` | integer | Items added to review queue |

### items Fields (per source)

| Field | Type | Description |
|---|---|---|
| `source_path` | string | Relative path in workspace |
| `source_id` | string | Deterministic source identifier |
| `content_hash` | string | Content hash or `"UNKNOWN"` / `"NOT_RECORDED"` |
| `status` | string | `"draft_created"`, `"quarantined"`, `"skipped"`, etc. |
| `draft_path` | string | Draft file path or `"NOT_RECORDED"` |
| `manifest_status` | string | Manifest status or `"UNKNOWN"` |
| `queue_status` | string | Queue status or `"UNKNOWN"` |
| `review_state` | string | Review reason (e.g. `"low_confidence"`, `"conflict_detected"`) |
| `promotion_state` | string | Promotion status or `"NOT_RECORDED"` |
| `domain_check` | object | Full domain check results or `{}` |
| `skip_reason` | string or null | Reason for skip, null for ingested items |
| `failure_reason` | string or null | Failure reason, null for successful items |

### safety Fields

| Field | Type | Description |
|---|---|---|
| `auto_promote_default` | boolean | Always `false` (fail-closed by default) |
| `promotion_mode` | string | `"review_required"`, `"auto"`, or `"NOT_RECORDED"` |
| `domain_guard_active` | boolean | True only when domain_guard is configured with keywords |

**Important**: `domain_guard_active` MUST be `false` when `domain_guard` is
not configured. NOT_CONFIGURED is not active protection.

## ingest_gaps.json Field Definitions

### Top-level

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"abw.ingest_gaps.v1"` |
| `run_id` | string | Same run_id as paired ingest_report.json |
| `created_at` | string | Same timestamp as paired ingest_report.json |
| `workspace` | string | Absolute workspace path |
| `gap_summary` | object | Aggregate gap counts |
| `gaps` | array | Per-source/per-signal gap records |
| `limitations` | array | Known limitations of this gap output |

### gap_summary Fields

| Field | Type | Description |
|---|---|---|
| `total_gaps` | integer | Total gap records |
| `blocking_gaps` | integer | Gaps with severity BLOCKING |
| `warning_gaps` | integer | Gaps with severity WARNING |

### gaps Fields (per gap)

| Field | Type | Description |
|---|---|---|
| `source_path` | string | Source file path or `"N/A"` for workspace-level gaps |
| `source_id` | string | Source identifier or `"N/A"` |
| `gap_type` | string | Gap classification (see below) |
| `severity` | string | `"BLOCKING"`, `"WARNING"`, or `"INFO"` |
| `reason` | string | Human-readable gap reason |
| `evidence_ref` | string | Reference to source evidence field |
| `recommended_action` | string | Suggested next step |

### Gap Types

| Gap Type | Severity | Trigger Condition |
|---|---|---|
| `missing_source_hash` | WARNING | Item has no source_id |
| `quarantined_file` | BLOCKING | File blocked by domain contamination guard |
| `domain_check_warning` | WARNING | Domain check returned WARN |
| `domain_check_error` | BLOCKING | Domain check returned ERROR |
| `domain_guard_not_configured` | INFO | No domain_guard in workspace config |
| `promotion_not_performed` | INFO | Item not yet approved/promoted |
| `review_required` | INFO | Item needs human review |
| `skipped_file` | WARNING | Generic skip with no specific gap type |
| `failed_file` | BLOCKING | Parse error during ingest attempt |

## Relationship Between Report and Gaps

- Both artifacts are generated from the same `run_id` and `created_at`.
- The report provides the complete truth of what happened during ingest.
- The gaps provide actionable signals derived from the report (not independent).
- Gaps are deterministic and minimal; they do not claim semantic coverage.
- The existing eval/inspect gaps pipeline (src/abw/gaps.py) is NOT replaced.

## Integration Point

Both artifacts are generated at the end of `run()` in `scripts/abw_ingest.py`,
before the function returns. Generation is automatic for all ingest runs.

## Examples

### ingest_report.json (basic clean ingest)

```json
{
  "schema_version": "abw.ingest_report.v1",
  "run_id": "run-test-workspace-20260503T120000",
  "created_at": "2026-05-03T12:00:00Z",
  "workspace": "/path/to/workspace",
  "command": "ingest raw/test.md",
  "summary": {
    "ingested_count": 1,
    "skipped_count": 0,
    "failed_count": 0,
    "quarantined_count": 0,
    "draft_count": 1,
    "manifest_count": 1,
    "queue_count": 1
  },
  "items": [{
    "source_path": "raw/test.md",
    "source_id": "ingest-abc123def456",
    "content_hash": "abcdef1234567890",
    "status": "draft_created",
    "draft_path": "drafts/test_draft.md",
    "manifest_status": "review_needed",
    "queue_status": "review_needed",
    "review_state": "low_confidence",
    "promotion_state": "review_needed",
    "domain_check": {
      "domain_check_status": "NOT_CONFIGURED",
      "domain_check_reason": "no domain_guard section in config",
      "matched_keywords": [],
      "blocked_keywords": [],
      "required_markers_missing": [],
      "action": "accept"
    },
    "skip_reason": null,
    "failure_reason": null
  }],
  "safety": {
    "auto_promote_default": false,
    "promotion_mode": "review_required",
    "domain_guard_active": false
  },
  "limitations": [
    "Machine-readable evidence only; not bridge-ready.",
    "content_hash may be NOT_RECORDED for skipped/failed items.",
    "promotion_state reflects ingest-time decision only; final promotion is managed separately."
  ]
}
```

### ingest_gaps.json (with domain guard configured)

```json
{
  "schema_version": "abw.ingest_gaps.v1",
  "run_id": "run-test-workspace-20260503T120000",
  "created_at": "2026-05-03T12:00:00Z",
  "workspace": "/path/to/workspace",
  "gap_summary": {
    "total_gaps": 3,
    "blocking_gaps": 0,
    "warning_gaps": 3
  },
  "gaps": [
    {
      "source_path": "raw/test.md",
      "source_id": "ingest-abc123def456",
      "gap_type": "review_required",
      "severity": "INFO",
      "reason": "review_reason: low_confidence",
      "evidence_ref": "review_reason",
      "recommended_action": "Review ingested content for accuracy and domain relevance before promotion."
    },
    {
      "source_path": "raw/test.md",
      "source_id": "ingest-abc123def456",
      "gap_type": "promotion_not_performed",
      "severity": "INFO",
      "reason": "promotion_state is review_needed; item requires explicit approval.",
      "evidence_ref": "promotion_status",
      "recommended_action": "Review draft and explicitly approve/promote through governed workflow."
    },
    {
      "source_path": "N/A",
      "source_id": "N/A",
      "gap_type": "domain_guard_not_configured",
      "severity": "INFO",
      "reason": "domain_guard is not configured; no domain contamination protection active.",
      "evidence_ref": "workspace_config",
      "recommended_action": "Configure domain_guard in abw_config.json to enable domain contamination protection."
    }
  ],
  "limitations": [
    "Minimal deterministic gap classification; not semantic coverage.",
    "Gap types bounded to ingest-relevant signals only.",
    "Does not replace full eval/inspect gap pipeline.",
    "No bridge-specific gap inference."
  ]
}
```

## Limitations

- Gap classification is minimal and deterministic; does not provide semantic
  coverage analysis.
- Gap types are bounded to ingest-relevant signals only (skipped, failed,
  quarantined, domain check, review, promotion).
- This contract does NOT replace the existing eval/inspect gap pipeline
  (src/abw/gaps.py).
- content_hash may be NOT_RECORDED for items that were skipped or failed
  during ingest.
- promotion_state reflects ingest-time assessment only; final promotion
  decisions are managed by the separate promotion workflow.
- Domain check evidence is included only when domain_guard is configured.
  NOT_CONFIGURED is explicitly reported, not silently treated as active.

## Non-Claims

- NOT bridge-ready.
- NOT bridge implementation.
- No NVIDIA repo modified.
- No control repo modified.
- No self-growing wiki.
- No Cognitive OS claim.
- No ingest pipeline fully solved.
- No enterprise-grade security claim.
- No autonomous self-learning claim.

## Next Gate Review Requirement

After Sprint 23 completes and passes GPT-5.3-Codex / GPT-5.4 / GPT-5.5 audit:
- Review evidence contract stability across multiple ingest runs.
- Assess whether gate C (INSERT_EVIDENCE_REPORTING_SPRINT) is satisfied.
- If satisfied, next gate review may consider Bridge Phase 1 authorization.
- Gate verdict is NOT this document's responsibility; audit determines.
