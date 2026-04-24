from __future__ import annotations

import subprocess
from pathlib import Path

from .workspace import CONFIG_FILENAME, REQUIRED_DIRS, ensure_workspace, read_workspace_config, resolve_workspace


def _file_count(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file())


def _run_git(root: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _git_status_summary(root: Path) -> dict:
    in_repo = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if in_repo != "true":
        return {
            "available": False,
            "branch": "unknown",
            "dirty_files": [],
            "migration_scope_files": [],
            "unrelated_dirty_files": [],
        }

    branch = _run_git(root, ["branch", "--show-current"]) or "unknown"
    porcelain = _run_git(root, ["status", "--porcelain"]) or ""
    dirty_files = []
    for line in porcelain.splitlines():
        candidate = line[3:] if len(line) >= 4 else line
        path_text = candidate.strip()
        if path_text:
            dirty_files.append(path_text)

    migration_scope = {".gitignore", CONFIG_FILENAME}
    migration_scope_files = [item for item in dirty_files if item in migration_scope]
    unrelated_dirty_files = [item for item in dirty_files if item not in migration_scope]

    return {
        "available": True,
        "branch": branch,
        "dirty_files": dirty_files,
        "migration_scope_files": migration_scope_files,
        "unrelated_dirty_files": unrelated_dirty_files,
    }


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
    git_status = _git_status_summary(root)

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

    if git_status["available"] and git_status["unrelated_dirty_files"]:
        warnings.append("Repository has unrelated dirty files. Keep migration commit isolated.")
        next_steps.append("create branch `chore/abw-package-migration` for migration-only commit")
        next_steps.append("commit only `.gitignore` and `abw_config.json`")

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
        "git": git_status,
        "adoption_commit_scope": [".gitignore", CONFIG_FILENAME],
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
    git_status = report.get("git", {})
    if git_status.get("available"):
        lines.extend(
            [
                f"- git_branch: {git_status.get('branch', 'unknown')}",
                f"- git_dirty_files: {len(git_status.get('dirty_files', []))}",
                f"- migration_scope_files: {', '.join(git_status.get('migration_scope_files', [])) or 'none'}",
            ]
        )
        unrelated = git_status.get("unrelated_dirty_files", [])
        if unrelated:
            lines.append(f"- WARN: unrelated_dirty_files: {', '.join(unrelated)}")
            lines.append("- WARN: keep migration commit scoped to .gitignore + abw_config.json")
    if report.get("workspace_schema") is not None:
        lines.append(f"- workspace_schema: {report['workspace_schema']}")
    for warning in report["warnings"]:
        lines.append(f"- WARN: {warning}")
    for step in report["next_steps"]:
        lines.append(f"- NEXT: {step}")
    return "\n".join(lines)
