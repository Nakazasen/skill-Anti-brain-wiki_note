import json
import os
from pathlib import Path
from typing import Any


def _has_workspace_indicators(root: Path) -> bool:
    indicators = (
        root / "raw",
        root / "wiki",
        root / "drafts",
        root / ".brain",
        root / "pyproject.toml",
        root / "README.md",
        root / "README.txt",
    )
    return any(path.exists() for path in indicators)

def get_registry_path() -> Path:
    # Use a default location if not specified, but usually within the repo root .brain
    root = Path(os.environ.get("ABW_ROOT", ".")).expanduser().resolve()
    brain_dir = root / ".brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    return brain_dir / "workspaces.json"

def load_workspaces() -> list[dict[str, Any]]:
    path = get_registry_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_workspaces(workspaces: list[dict[str, Any]]) -> None:
    path = get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workspaces, f, indent=2, ensure_ascii=False)

def list_enabled_workspaces() -> list[str]:
    workspaces = load_workspaces()
    return [w["path"] for w in workspaces if w.get("enabled", True)]

def register_workspace(path: str, name: str | None = None) -> dict[str, Any]:
    workspaces = load_workspaces()
    abs_path = str(Path(path).expanduser().resolve())
    resolved = Path(abs_path)
    if not resolved.exists():
        raise ValueError(f"workspace path does not exist: {abs_path}")
    if not _has_workspace_indicators(resolved):
        raise ValueError(f"workspace path is missing workspace indicators: {abs_path}")
    
    # Check if already exists
    for w in workspaces:
        if w["path"] == abs_path:
            w["enabled"] = True # Re-enable if exists
            if name:
                w["name"] = name
            save_workspaces(workspaces)
            return w
            
    new_ws = {
        "path": abs_path,
        "name": name or Path(abs_path).name,
        "enabled": True
    }
    workspaces.append(new_ws)
    save_workspaces(workspaces)
    return new_ws

def disable_workspace(path: str) -> bool:
    workspaces = load_workspaces()
    abs_path = str(Path(path).expanduser().resolve())
    found = False
    for w in workspaces:
        if w["path"] == abs_path:
            w["enabled"] = False
            found = True
            break
    if found:
        save_workspaces(workspaces)
    return found
