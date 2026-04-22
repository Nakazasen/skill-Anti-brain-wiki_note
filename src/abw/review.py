from __future__ import annotations

from .runner import run_task


def review_drafts(*, workspace: str):
    return run_task("review drafts", workspace=workspace)


def approve_draft(path: str, *, workspace: str):
    return run_task(f"approve draft {path}", workspace=workspace)
