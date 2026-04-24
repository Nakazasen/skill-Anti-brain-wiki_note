from __future__ import annotations

import json
import os
from pathlib import Path

from . import __version__


CONFIG_FILENAME = "abw_config.json"
REQUIRED_DIRS = ("raw", "wiki", "drafts")
WORKSPACE_SCHEMA = 1


def resolve_workspace(value: str | os.PathLike[str] | None = None) -> Path:
    raw = value or os.environ.get("ABW_WORKSPACE") or os.getcwd()
    return Path(raw).expanduser().resolve()


def config_path(workspace: str | os.PathLike[str] | None = None) -> Path:
    return resolve_workspace(workspace) / CONFIG_FILENAME


def default_config(root: Path) -> dict:
    return {
        "project_name": root.name,
        "workspace_schema": WORKSPACE_SCHEMA,
        "abw_version": __version__,
        "raw_dir": "raw",
        "wiki_dir": "wiki",
        "drafts_dir": "drafts",
    }


def read_workspace_config(workspace: str | os.PathLike[str] | None = None) -> tuple[dict | None, str]:
    path = config_path(workspace)
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None, "invalid"
    if not isinstance(payload, dict):
        return None, "invalid"
    return payload, "ok"


def write_workspace_config(root: Path, payload: dict) -> Path:
    path = root / CONFIG_FILENAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def ensure_workspace(workspace: str | os.PathLike[str] | None = None) -> dict:
    root = resolve_workspace(workspace)
    root.mkdir(parents=True, exist_ok=True)

    created_dirs = []
    for name in REQUIRED_DIRS:
        directory = root / name
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(name)

    config, config_status = read_workspace_config(root)
    config_created = False
    config_updated = False
    if config_status == "missing":
        config = default_config(root)
        write_workspace_config(root, config)
        config_created = True
        config_status = "created"
    elif config_status == "ok":
        merged = dict(config)
        for key, value in default_config(root).items():
            if key not in merged or merged.get(key) in {None, ""}:
                merged[key] = value
                config_updated = True
        if merged.get("workspace_schema") != WORKSPACE_SCHEMA:
            merged["workspace_schema"] = WORKSPACE_SCHEMA
            config_updated = True
        merged["abw_version"] = __version__
        if merged != config:
            write_workspace_config(root, merged)
            config = merged
            config_status = "updated"
        else:
            config_status = "ok"
    return {
        "root": root,
        "created_dirs": created_dirs,
        "config_status": config_status,
        "config_created": config_created,
        "config_updated": config_updated,
        "config": config,
        "config_path": root / CONFIG_FILENAME,
    }


def init_workspace(workspace: str | os.PathLike[str] | None = None) -> Path:
    return ensure_workspace(workspace)["root"]
