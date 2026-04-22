from __future__ import annotations

from .runner import run_task


def ask(text: str, *, workspace: str):
    return run_task(text, workspace=workspace)


def dashboard(*, workspace: str):
    return run_task("dashboard", workspace=workspace)
