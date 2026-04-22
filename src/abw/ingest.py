from __future__ import annotations

from .runner import run_task


def ingest(path: str, *, workspace: str):
    return run_task(f"ingest {path}", workspace=workspace)
