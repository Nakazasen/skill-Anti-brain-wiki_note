"""Loader for ABW runtime modules with canonical scripts + packaged fallback."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from .runtime_manifest import MIRRORED_RUNTIME_MODULES

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
LEGACY_DIR = Path(__file__).resolve().parent / "_legacy"
RUNTIME_SOURCE_PACKAGED = "packaged_legacy"
RUNTIME_SOURCE_SCRIPTS = "scripts"
_ENV_RUNTIME_SOURCE = "ABW_RUNTIME_SOURCE"
_RUNTIME_SOURCE_AUTO = "auto"
_RUNTIME_SOURCE_SCRIPTS = "scripts"
_RUNTIME_SOURCE_PACKAGED = "packaged"

_RUNTIME_MODULE_NAMES = tuple(Path(name).stem for name in MIRRORED_RUNTIME_MODULES)


def _scripts_runtime_available() -> bool:
    return (SCRIPTS_DIR / "abw_runner.py").exists()


def _safe_resolve_path(path_value: str | Path) -> Path | None:
    try:
        return Path(path_value).resolve()
    except Exception:  # noqa: BLE001
        return None


def _resolve_override_value() -> str:
    override = str(os.environ.get(_ENV_RUNTIME_SOURCE, "") or "").strip().lower()
    if override in {"", _RUNTIME_SOURCE_AUTO, _RUNTIME_SOURCE_SCRIPTS, _RUNTIME_SOURCE_PACKAGED}:
        return override or _RUNTIME_SOURCE_AUTO
    raise ValueError(f"ABW_RUNTIME_SOURCE must be one of: {_RUNTIME_SOURCE_AUTO}, {_RUNTIME_SOURCE_SCRIPTS}, {_RUNTIME_SOURCE_PACKAGED}")


def _select_runtime_source() -> dict:
    override = _resolve_override_value()
    if override == _RUNTIME_SOURCE_AUTO:
        if _scripts_runtime_available():
            return {"runtime_source": RUNTIME_SOURCE_SCRIPTS, "runtime_source_path": str(SCRIPTS_DIR)}
        return {"runtime_source": RUNTIME_SOURCE_PACKAGED, "runtime_source_path": str(LEGACY_DIR)}
    if override == _RUNTIME_SOURCE_SCRIPTS:
        scripts_runner = SCRIPTS_DIR / "abw_runner.py"
        if not _scripts_runtime_available():
            raise RuntimeError(f"ABW_RUNTIME_SOURCE=scripts but runtime file is missing: {scripts_runner}")
        return {"runtime_source": RUNTIME_SOURCE_SCRIPTS, "runtime_source_path": str(SCRIPTS_DIR)}
    if override == _RUNTIME_SOURCE_PACKAGED:
        return {"runtime_source": RUNTIME_SOURCE_PACKAGED, "runtime_source_path": str(LEGACY_DIR)}
    raise RuntimeError(f"Unexpected runtime override value: {override}")


def _remove_conflicting_modules(selected_root: Path) -> None:
    module_names = set(_RUNTIME_MODULE_NAMES)
    for loaded_name in list(sys.modules):
        stem = loaded_name.split(".")[-1]
        if stem not in module_names:
            continue
        loaded_module = sys.modules.get(loaded_name)
        module_file = getattr(loaded_module, "__file__", None)
        if not loaded_module or not module_file:
            continue
        file_path = Path(module_file).resolve()
        if selected_root in file_path.parents or file_path == selected_root:
            continue
        sys.modules.pop(loaded_name, None)


def _set_runtime_path(selected_root: Path) -> None:
    resolved_selected = selected_root.resolve()
    selected = str(resolved_selected)
    other_roots = {str(SCRIPTS_DIR.resolve()), str(LEGACY_DIR.resolve())}
    other_roots.discard(selected)
    filtered_entries = []
    for entry in sys.path:
        resolved_entry = _safe_resolve_path(entry)
        if resolved_entry and str(resolved_entry) in other_roots:
            continue
        filtered_entries.append(entry)
    sys.path[:] = filtered_entries
    if selected not in sys.path:
        sys.path.insert(0, selected)


def runtime_source_details() -> dict:
    try:
        return _select_runtime_source()
    except Exception:
        return {
            "runtime_source": "unknown",
            "runtime_source_path": "unknown",
        }


def ensure_legacy_path() -> None:
    info = _select_runtime_source()
    selected_root = Path(info["runtime_source_path"]).resolve()
    _set_runtime_path(selected_root)
    _remove_conflicting_modules(selected_root)


def selected_runtime_source() -> dict:
    return _select_runtime_source()


def load(name: str):
    info = _select_runtime_source()
    selected_root = Path(info["runtime_source_path"]).resolve()
    _set_runtime_path(selected_root)
    _remove_conflicting_modules(selected_root)
    return importlib.import_module(name)


def current_runtime_search_paths() -> tuple[str, ...]:
    normalized_paths = set()
    for entry in sys.path:
        if not entry:
            continue
        resolved_entry = _safe_resolve_path(entry)
        if resolved_entry:
            normalized_paths.add(str(resolved_entry))
    return tuple(
        sorted(
            normalized_paths
        )
    )
