from __future__ import annotations


def ask(text: str, *, workspace: str):
    from .runner import run_task

    return run_task(text, workspace=workspace)


def dashboard(*, workspace: str):
    from .runner import run_task

    return run_task("dashboard", workspace=workspace)
