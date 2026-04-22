from __future__ import annotations

import json
import os
from pathlib import Path


CONFIG_FILENAME = "abw_config.json"


def resolve_workspace(value: str | os.PathLike[str] | None = None) -> Path:
    raw = value or os.environ.get("ABW_WORKSPACE") or os.getcwd()
    return Path(raw).expanduser().resolve()


def init_workspace(workspace: str | os.PathLike[str] | None = None) -> Path:
    root = resolve_workspace(workspace)
    root.mkdir(parents=True, exist_ok=True)
    for name in ("raw", "wiki", "drafts"):
        (root / name).mkdir(parents=True, exist_ok=True)

    config_path = root / CONFIG_FILENAME
    if not config_path.exists():
        payload = {
            "workspace_version": 1,
            "raw_dir": "raw",
            "wiki_dir": "wiki",
            "drafts_dir": "drafts",
        }
        config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root
