from __future__ import annotations

from .legacy import load


def _legacy_runner():
    return load("abw_runner")


def _legacy_output():
    return load("abw_output")


def run_task(task: str, *, workspace: str, task_kind: str = "execution"):
    legacy_runner = _legacy_runner()
    result = legacy_runner.dispatch_request(
        task=task,
        workspace=workspace,
        task_kind=task_kind,
        binding_mode="STRICT",
        binding_source="cli",
    )
    if isinstance(result, dict):
        result.setdefault("workspace", workspace)
    return finalize(result, workspace=workspace)


def finalize(result, *, workspace: str):
    legacy_runner = _legacy_runner()
    if isinstance(result, dict) and result.get("evaluation") is None:
        result = legacy_runner.apply_acceptance_validation(result, workspace=workspace)
    result = _legacy_output().enforce_runner_output(result)
    return legacy_runner.enforce_output_acceptance(result, mode="STRICT")
