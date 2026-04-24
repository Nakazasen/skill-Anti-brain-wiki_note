from __future__ import annotations

import shutil
from pathlib import Path

from .version import build_version_report
from .workspace import CONFIG_FILENAME, REQUIRED_DIRS, read_workspace_config, resolve_workspace


def _status(level: str, message: str) -> dict:
    return {"level": level, "message": message}


def build_doctor_report(workspace: str | Path = ".") -> dict:
    root = resolve_workspace(workspace)
    checks = []
    next_steps = []

    for name in REQUIRED_DIRS:
        path = root / name
        if path.exists() and path.is_dir():
            checks.append(_status("OK", f"{name}/ present"))
        else:
            checks.append(_status("WARN", f"missing {name}/"))
            next_steps.append("run `abw init`")

    config, config_status = read_workspace_config(root)
    if config_status == "ok":
        checks.append(_status("OK", f"{CONFIG_FILENAME} present"))
    elif config_status == "missing":
        checks.append(_status("WARN", f"missing {CONFIG_FILENAME}"))
        next_steps.append("run `abw init`")
    else:
        checks.append(_status("WARN", f"{CONFIG_FILENAME} is invalid JSON"))
        next_steps.append("run `abw migrate`")

    try:
        import abw  # noqa: F401

        checks.append(_status("OK", "package import works"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_status("WARN", f"package import failed: {exc}"))
        next_steps.append("reinstall the package")

    cli_path = shutil.which("abw")
    if cli_path:
        checks.append(_status("OK", f"CLI found at {cli_path}"))
    else:
        checks.append(_status("WARN", "global `abw` command not found on PATH"))
        next_steps.append("reinstall or expose the console script")

    version = build_version_report(root)
    checks.append(_status("OK", f"package version {version['package_version']}"))

    legacy_folder = root / "abw"
    if legacy_folder.exists() and legacy_folder.is_dir():
        checks.append(_status("WARN", "local legacy ABW engine detected at ./abw"))
        next_steps.append("run `abw migrate`")

    if version["install_mode"] == "unknown":
        checks.append(_status("WARN", "install mode could not be determined"))
        next_steps.append("run `abw version` and verify the package source")
    elif version["git_tag"] != f"v{version['package_version']}":
        checks.append(_status("WARN", "package version does not map cleanly to the current tagged source"))
        next_steps.append("run `abw upgrade`")

    overall = "OK"
    if any(item["level"] == "WARN" for item in checks):
        overall = "WARN"

    deduped_steps = []
    seen = set()
    for step in next_steps or ["run `abw ask \"dashboard\"`"]:
        if step in seen:
            continue
        seen.add(step)
        deduped_steps.append(step)

    return {
        "workspace": str(root),
        "overall": overall,
        "checks": checks,
        "next_steps": deduped_steps,
        "version": version,
    }


def render_doctor_report(report: dict) -> str:
    lines = [
        "ABW Doctor",
        f"- workspace: {report['workspace']}",
        f"- status: {report['overall']}",
    ]
    for item in report["checks"]:
        lines.append(f"- {item['level']}: {item['message']}")
    for step in report["next_steps"]:
        lines.append(f"- NEXT: {step}")
    lines.append("- Workspace isolation: current working directory is the default workspace unless ABW_WORKSPACE is set.")
    return "\n".join(lines)
