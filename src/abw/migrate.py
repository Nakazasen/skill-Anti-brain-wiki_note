from __future__ import annotations

from pathlib import Path

from .workspace import CONFIG_FILENAME, REQUIRED_DIRS, ensure_workspace, read_workspace_config, resolve_workspace


def _file_count(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file())


def build_migration_report(workspace: str | Path = ".") -> dict:
    root = resolve_workspace(workspace)
    before = {
        "raw": _file_count(root / "raw"),
        "wiki": _file_count(root / "wiki"),
        "drafts": _file_count(root / "drafts"),
    }
    config_before, config_status_before = read_workspace_config(root)
    ensured = ensure_workspace(root)
    config_after, config_status_after = read_workspace_config(root)

    warnings = []
    next_steps = []
    legacy_folder = root / "abw"
    if legacy_folder.exists() and legacy_folder.is_dir():
        warnings.append("Legacy local ABW engine detected at ./abw")
        next_steps.append("Remove or archive ./abw manually after confirming package-based ABW works.")

    if config_status_before == "invalid":
        warnings.append(f"Existing {CONFIG_FILENAME} is invalid and was preserved for manual review.")
        next_steps.append("Fix or replace the invalid abw_config.json manually.")

    if config_status_after in {"missing", "invalid"}:
        status = "manual_attention_required"
    elif warnings:
        status = "partially_migrated"
    elif ensured["created_dirs"] or ensured["config_created"] or ensured["config_updated"]:
        status = "migrated"
    else:
        status = "already_compatible"

    if not next_steps:
        next_steps = ["run `abw doctor`", 'run `abw ask "dashboard"`']

    return {
        "workspace": str(root),
        "status": status,
        "created_dirs": ensured["created_dirs"],
        "config_status": ensured["config_status"],
        "before": before,
        "after": {
            "raw": _file_count(root / "raw"),
            "wiki": _file_count(root / "wiki"),
            "drafts": _file_count(root / "drafts"),
        },
        "warnings": warnings,
        "next_steps": next_steps,
        "workspace_schema": (config_after or {}).get("workspace_schema") if isinstance(config_after, dict) else None,
        "config_before": config_before,
    }


def render_migration_report(report: dict) -> str:
    lines = [
        "ABW Migrate",
        f"- workspace: {report['workspace']}",
        f"- result: {report['status']}",
        f"- created_dirs: {', '.join(report['created_dirs']) if report['created_dirs'] else 'none'}",
        f"- config_status: {report['config_status']}",
        f"- preserved_raw_files: {report['after']['raw']}",
        f"- preserved_wiki_files: {report['after']['wiki']}",
        f"- preserved_draft_files: {report['after']['drafts']}",
    ]
    if report.get("workspace_schema") is not None:
        lines.append(f"- workspace_schema: {report['workspace_schema']}")
    for warning in report["warnings"]:
        lines.append(f"- WARN: {warning}")
    for step in report["next_steps"]:
        lines.append(f"- NEXT: {step}")
    return "\n".join(lines)
