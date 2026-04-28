from __future__ import annotations


def review_drafts(*, workspace: str):
    from .runner import run_task

    return run_task("review drafts", workspace=workspace)


def approve_draft(path: str, *, workspace: str):
    from .runner import run_task

    return run_task(f"approve draft {path}", workspace=workspace)
