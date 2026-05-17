from __future__ import annotations


def review_drafts(*, workspace: str):
    from .runner import run_task

    return run_task("review drafts", workspace=workspace)


def approve_draft(path: str, *, workspace: str):
    from .runner import run_task

    return run_task(f"approve draft {path}", workspace=workspace)


def approve_draft_contract(
    *,
    workspace: str,
    draft_path: str,
    draft_id: str | None = None,
    expected_draft_hash: str | None = None,
    expected_queue_status: str = "review_needed",
    confirm: dict | None = None,
    operator_note: str | None = None,
    dry_run: bool = True,
):
    from scripts.abw_review import APPROVE_SCHEMA_VERSION, approve_draft_request

    return approve_draft_request(
        {
            "schema_version": APPROVE_SCHEMA_VERSION,
            "workspace": str(workspace),
            "draft_path": draft_path,
            "draft_id": draft_id,
            "expected_draft_hash": expected_draft_hash,
            "expected_queue_status": expected_queue_status,
            "confirm": confirm or {},
            "operator_note": operator_note,
            "dry_run": bool(dry_run),
        }
    )
