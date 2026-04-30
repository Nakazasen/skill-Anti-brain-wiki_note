from __future__ import annotations


CANONICAL_RUNTIME_DIR = "scripts"
PACKAGED_FALLBACK_DIR = "src/abw/_legacy"

CRITICAL_RUNTIME_MODULES = (
    "abw_entry.py",
    "abw_help.py",
    "abw_output.py",
    "abw_proof.py",
    "abw_runner.py",
    "abw_update.py",
)

MIRRORED_RUNTIME_MODULES = (
    "abw_accept.py",
    "abw_alias.py",
    "abw_audit.py",
    "abw_cli.py",
    "abw_coverage.py",
    "abw_dashboard.py",
    "abw_entry.py",
    "abw_health.py",
    "abw_help.py",
    "abw_i18n.py",
    "abw_ingest.py",
    "abw_knowledge.py",
    "abw_menu.py",
    "abw_monitor.py",
    "abw_output.py",
    "abw_pack.py",
    "abw_proof.py",
    "abw_query_deep.py",
    "abw_review.py",
    "abw_review_explain.py",
    "abw_router.py",
    "abw_runner.py",
    "abw_suggestions.py",
    "abw_sync.py",
    "abw_update.py",
    "abw_version.py",
    "abw_wizard.py",
    "ai_runner.py",
    "continuation_claim.py",
    "continuation_detect_unsafe.py",
    "continuation_execute.py",
    "continuation_gate.py",
    "continuation_rollback.py",
    "continuation_status.py",
    "finalization_check.py",
    "intent_matcher.py",
    "validate_docs.py",
)

SCRIPT_ONLY_MODULES = (
    "desktop_smoke.py",
    "release_smoke.py",
)

PACKAGE_ONLY_MODULES = (
    "__init__.py",
)
