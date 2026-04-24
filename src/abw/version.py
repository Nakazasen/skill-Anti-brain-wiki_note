from __future__ import annotations

import json
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from . import __version__
from .legacy import runtime_source_details
from .runtime_manifest import CRITICAL_RUNTIME_MODULES
from .workspace import read_workspace_config, resolve_workspace


DISTRIBUTION_NAME = "abw-skill"
REPO_URL = "https://github.com/Nakazasen/skill-Anti-brain-wiki_note.git"


def _safe_distribution():
    try:
        return metadata.distribution(DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return None


def package_version() -> str:
    return __version__


def _direct_url_payload(distribution) -> dict | None:
    if distribution is None:
        return None
    try:
        raw = distribution.read_text("direct_url.json")
    except FileNotFoundError:
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root_candidates() -> list[Path]:
    candidates = [package_root()]
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            candidates.append(parent)
            break
    return candidates


def _git_value(args: list[str]) -> str | None:
    for root in _repo_root_candidates():
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *args],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except OSError:
            continue
        value = completed.stdout.strip()
        if completed.returncode == 0 and value:
            return value
    return None


def git_commit() -> str | None:
    return _git_value(["rev-parse", "--short", "HEAD"])


def git_tag() -> str | None:
    return _git_value(["describe", "--tags", "--exact-match"])


def release_match_state(package_version_value: str, git_tag_value: str | None) -> str:
    if not git_tag_value:
        return "unknown"
    if git_tag_value == f"v{package_version_value}":
        return "matched"
    return "mismatched"


def install_mode_details() -> dict:
    distribution = _safe_distribution()
    direct_url = _direct_url_payload(distribution)
    source_path = None

    if direct_url:
        if direct_url.get("dir_info", {}).get("editable"):
            url = str(direct_url.get("url") or "").strip()
            if url.startswith("file://"):
                source_path = url.replace("file:///", "").replace("file://", "")
            return {"install_mode": "editable/dev", "source_path": source_path, "direct_url": direct_url}
        url = str(direct_url.get("url") or "").strip()
        if "github.com" in url or url.endswith(".git"):
            return {"install_mode": "git+pip", "source_path": None, "direct_url": direct_url}

    module_path = Path(__file__).resolve()
    module_text = str(module_path).lower()
    if "site-packages" in module_text or "dist-packages" in module_text:
        return {"install_mode": "pip package", "source_path": None, "direct_url": direct_url}

    repo_root = package_root()
    if (repo_root / ".git").exists() and (repo_root / "pyproject.toml").exists():
        return {"install_mode": "editable/dev", "source_path": str(repo_root), "direct_url": direct_url}

    return {"install_mode": "unknown", "source_path": None, "direct_url": direct_url}


def build_version_report(workspace: str | Path = ".") -> dict:
    root = resolve_workspace(workspace)
    config, config_status = read_workspace_config(root)
    install = install_mode_details()
    current_package_version = package_version()
    current_git_tag = git_tag()
    current_git_commit = git_commit()
    current_release_match_state = release_match_state(current_package_version, current_git_tag)
    runtime = runtime_source_details()
    mirror = runtime_mirror_status()
    workspace_schema = None
    if config_status == "ok" and isinstance(config, dict):
        workspace_schema = config.get("workspace_schema") or config.get("workspace_version")
    if current_release_match_state == "matched":
        note = "Package version matches the current tagged source."
    elif current_release_match_state == "mismatched":
        note = "Package version does not match the current tagged source."
    else:
        note = "Release match could not be verified because the current source is not exactly tagged."
    return {
        "package_version": current_package_version,
        "git_tag": current_git_tag or "unknown",
        "git_commit": current_git_commit or "unknown",
        "release_match_state": current_release_match_state,
        "workspace": str(root),
        "workspace_schema": workspace_schema or "unknown",
        "install_mode": install["install_mode"],
        "source_path": install["source_path"],
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "runtime_source": runtime["runtime_source"],
        "runtime_source_path": runtime["runtime_source_path"],
        "mirror_status": mirror["status"],
        "mirror_mismatches": mirror["mismatches"],
        "note": note,
    }


def render_version_report(report: dict) -> str:
    lines = [
        "ABW Version",
        f"- package_version: {report['package_version']}",
        f"- git_tag: {report['git_tag']}",
        f"- git_commit: {report['git_commit']}",
        f"- release_match: {report['release_match_state']}",
        f"- workspace: {report['workspace']}",
        f"- install_mode: {report['install_mode']}",
        f"- workspace_schema: {report['workspace_schema']}",
        f"- python: {report['python']}",
        f"- runtime_source: {report['runtime_source']}",
        f"- runtime_source_path: {report['runtime_source_path']}",
        f"- mirror_status: {report['mirror_status']}",
    ]
    if report.get("source_path"):
        lines.append(f"- source_path: {report['source_path']}")
    if report.get("mirror_mismatches"):
        lines.append(f"- mirror_mismatches: {', '.join(report['mirror_mismatches'])}")
    lines.append(f"- note: {report['note']}")
    return "\n".join(lines)


def runtime_mirror_status() -> dict:
    repo_root = package_root()
    scripts_dir = repo_root / "scripts"
    legacy_dir = Path(__file__).resolve().parent / "_legacy"
    if not scripts_dir.exists() or not legacy_dir.exists():
        return {"status": "not_checked", "mismatches": []}
    mismatches = []
    for name in CRITICAL_RUNTIME_MODULES:
        scripts_file = scripts_dir / name
        legacy_file = legacy_dir / name
        if not scripts_file.exists() or not legacy_file.exists():
            mismatches.append(name)
            continue
        if scripts_file.read_bytes() != legacy_file.read_bytes():
            mismatches.append(name)
    return {"status": "matched" if not mismatches else "mismatch", "mismatches": mismatches}
