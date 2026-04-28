from __future__ import annotations


def ingest(path: str, *, workspace: str):
    from .runner import run_task

    return run_task(f"ingest {path}", workspace=workspace)
