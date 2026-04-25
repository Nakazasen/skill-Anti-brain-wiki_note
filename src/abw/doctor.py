from __future__ import annotations

import shutil
from pathlib import Path

from .version import build_version_report
from .workspace import CONFIG_FILENAME, REQUIRED_DIRS, read_workspace_config, resolve_workspace


def _status(level: str, message: str) -> dict:
    return {"level": level, "message": message}


def _load_open_knowledge_gaps(root: Path) -> list[dict]:
    path = root / ".brain" / "knowledge_gaps.json"
    if not path.exists():
        return []
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return []
    gaps = payload.get("gaps", [])
    if not isinstance(gaps, list):
        return []
    return [gap for gap in gaps if isinstance(gap, dict) and gap.get("status") == "open"]


def build_doctor_report(workspace: str | Path = ".") -> dict:
    root = resolve_workspace(workspace)
    workspace_checks = []
    engine_checks = []
    next_steps = []

    for name in REQUIRED_DIRS:
        path = root / name
        if path.exists() and path.is_dir():
            workspace_checks.append(_status("OK", f"{name}/ present"))
        else:
            workspace_checks.append(_status("WARN", f"missing {name}/"))
            next_steps.append("run `abw init`")

    config, config_status = read_workspace_config(root)
    if config_status == "ok":
        workspace_checks.append(_status("OK", f"{CONFIG_FILENAME} present"))
    elif config_status == "missing":
        workspace_checks.append(_status("WARN", f"missing {CONFIG_FILENAME}"))
        next_steps.append("run `abw init`")
    else:
        workspace_checks.append(_status("WARN", f"{CONFIG_FILENAME} is invalid JSON"))
        next_steps.append("run `abw migrate`")

    try:
        import abw  # noqa: F401

        engine_checks.append(_status("OK", "package import works"))
    except Exception as exc:  # noqa: BLE001
        engine_checks.append(_status("WARN", f"package import failed: {exc}"))
        next_steps.append("reinstall the package")

    cli_path = shutil.which("abw")
    if cli_path:
        engine_checks.append(_status("OK", f"CLI found at {cli_path}"))
    else:
        engine_checks.append(_status("WARN", "global `abw` command not found on PATH"))
        next_steps.append("reinstall or expose the console script")

    version = build_version_report(root)
    engine_checks.append(_status("OK", f"package version {version['package_version']}"))
    engine_checks.append(
        _status(
            "OK" if version.get("runtime_source") != "unknown" else "WARN",
            f"runtime source {version.get('runtime_source', 'unknown')} ({version.get('runtime_source_path', 'unknown')})",
        )
    )

    legacy_folder = root / "abw"
    if legacy_folder.exists() and legacy_folder.is_dir():
        workspace_checks.append(_status("WARN", "local legacy ABW engine detected at ./abw"))
        next_steps.append("run `abw migrate`")

    if version["install_mode"] == "unknown":
        engine_checks.append(_status("WARN", "install mode could not be determined"))
        next_steps.append("run `abw version` and verify the package source")
    release_match = version.get("release_match_state", "unknown")
    if release_match == "matched":
        engine_checks.append(_status("OK", "package version matches current git tag"))
    elif release_match == "mismatched":
        engine_checks.append(_status("WARN", "package version does not match current git tag"))
        next_steps.append("run `abw version` and verify the package source")
    else:
        engine_checks.append(_status("WARN", "release match could not be verified from git tag"))
        next_steps.append("run `abw version` and verify the package source")
    mirror_status = version.get("mirror_status", "not_checked")
    if mirror_status == "matched":
        engine_checks.append(_status("OK", "runtime mirror status matched"))
    elif mirror_status == "mismatch":
        mismatch_list = ", ".join(version.get("mirror_mismatches", [])) or "unknown files"
        engine_checks.append(_status("WARN", "runtime mirror status mismatch"))
        engine_checks.append(_status("WARN", f"runtime mirror mismatch: {mismatch_list}"))
        next_steps.append("sync scripts/* and src/abw/_legacy/* critical runtime modules")
    else:
        engine_checks.append(_status("WARN", "runtime mirror status not checked"))
        next_steps.append("run ABW from repository source to verify runtime mirror status")
    if version.get("stale_install_suspected"):
        engine_checks.append(_status("WARN", "stale install may be active"))
        next_steps.append("run `abw self-check`")
        next_steps.append("run `py -m pip install -U .` or `py -m pip install -U git+<repo-url>`")
    provider_mode = str(version.get("provider_ask_mode") or "local")
    provider_default = str(version.get("provider_default") or "unknown")
    provider_healthy_count = int(version.get("provider_healthy_count") or 0)
    engine_checks.append(
        _status(
            "OK" if provider_healthy_count > 0 or provider_mode == "local" else "WARN",
            f"provider state mode={provider_mode} default={provider_default} healthy={provider_healthy_count}",
        )
    )
    if provider_mode in {"ai", "hybrid"} and provider_healthy_count == 0:
        next_steps.append("run `abw provider test`")
        next_steps.append("run `abw provider set-default mock`")
    open_gaps = _load_open_knowledge_gaps(root)
    if open_gaps:
        top_gap = open_gaps[-1].get("query") or open_gaps[-1].get("reason") or "unknown"
        engine_checks.append(_status("WARN", f"coverage gaps open={len(open_gaps)} top_gap={top_gap}"))
        next_steps.append("ingest raw sources or add wiki notes for open knowledge gaps")
    else:
        engine_checks.append(_status("OK", "coverage gaps open=0"))

    overall = "OK"
    checks = workspace_checks + engine_checks
    if any(item["level"] == "WARN" for item in checks):
        overall = "WARN"

    workspace_health = "WARN" if any(item["level"] == "WARN" for item in workspace_checks) else "OK"
    engine_health = "WARN" if any(item["level"] == "WARN" for item in engine_checks) else "OK"

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
        "workspace_health": workspace_health,
        "engine_health": engine_health,
        "workspace_checks": workspace_checks,
        "engine_checks": engine_checks,
        "checks": checks,
        "next_steps": deduped_steps,
        "version": version,
    }


def render_doctor_report(report: dict) -> str:
    lines = [
        "ABW Doctor",
        f"- workspace: {report['workspace']}",
        f"- status: {report['overall']}",
        f"- workspace_health: {report['workspace_health']}",
        f"- engine_health: {report['engine_health']}",
        "Workspace checks:",
    ]
    for item in report["workspace_checks"]:
        lines.append(f"- {item['level']}: {item['message']}")
    lines.append("Engine checks:")
    for item in report["engine_checks"]:
        lines.append(f"- {item['level']}: {item['message']}")
    for step in report["next_steps"]:
        lines.append(f"- NEXT: {step}")
    lines.append("- Workspace isolation: current working directory is the default workspace unless ABW_WORKSPACE is set.")
    return "\n".join(lines)
