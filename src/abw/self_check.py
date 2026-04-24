from __future__ import annotations

import shutil
from pathlib import Path

from .version import REPO_URL, build_version_report
from .workspace import resolve_workspace


def build_self_check_report(workspace: str | Path = ".") -> dict:
    root = resolve_workspace(workspace)
    version = build_version_report(root)
    cli_path = shutil.which("abw") or "not found"
    suspected = bool(version.get("stale_install_suspected"))
    next_steps = []
    if suspected:
        next_steps.extend(
            [
                "run `py -m pip install -U .` from this repository",
                f"or run `py -m pip install -U git+{REPO_URL}`",
                "then run `abw version` and `abw doctor` again",
            ]
        )
    else:
        next_steps.append("no stale install signal detected")
    return {
        "workspace": str(root),
        "cli_path": cli_path,
        "package_version": version["package_version"],
        "install_mode": version["install_mode"],
        "runtime_source": version["runtime_source"],
        "runtime_source_path": version["runtime_source_path"],
        "release_match_state": version["release_match_state"],
        "mirror_status": version["mirror_status"],
        "stale_install_suspected": suspected,
        "next_steps": next_steps,
    }


def render_self_check_report(report: dict) -> str:
    lines = [
        "ABW Self Check",
        f"- workspace: {report['workspace']}",
        f"- cli_path: {report['cli_path']}",
        f"- package_version: {report['package_version']}",
        f"- install_mode: {report['install_mode']}",
        f"- runtime_source: {report['runtime_source']}",
        f"- runtime_source_path: {report['runtime_source_path']}",
        f"- release_match: {report['release_match_state']}",
        f"- mirror_status: {report['mirror_status']}",
        f"- stale_install_suspected: {report['stale_install_suspected']}",
    ]
    for step in report.get("next_steps", []):
        lines.append(f"- NEXT: {step}")
    return "\n".join(lines)
