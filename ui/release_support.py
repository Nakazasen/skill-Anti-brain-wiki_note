from __future__ import annotations

import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_VERSION = "1.1.0"
APP_NAME = "ABW Admin Desktop"
BUILD_INFO = os.environ.get("ABW_BUILD_INFO", "internal")
DEFAULT_API_PORT = 8000
MAX_RECENT_WORKSPACES = 8


def log_dir() -> Path:
    return Path(os.environ.get("ABW_LOG_DIR", "logs")).expanduser().resolve()


def feedback_dir() -> Path:
    return Path(os.environ.get("ABW_FEEDBACK_DIR", "feedback")).expanduser().resolve()


def diagnostics_dir() -> Path:
    return Path(os.environ.get("ABW_DIAGNOSTICS_DIR", "diagnostics")).expanduser().resolve()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def configure_file_logger(name: str, filename: str) -> logging.Logger:
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_path = directory / filename
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path for handler in logger.handlers):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger


def settings_path() -> Path:
    configured = os.environ.get("ABW_ADMIN_SETTINGS")
    if configured:
        return Path(configured).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "ABW-Admin" / "settings.json"
    return Path.home() / ".abw-admin" / "settings.json"


class AdminSettings:
    def __init__(self, path: Path | None = None):
        self.path = path or settings_path()
        self.data: dict[str, Any] = {
            "last_workspace_path": "",
            "last_api_port": DEFAULT_API_PORT,
            "window_size": {"width": 1100, "height": 750},
            "recent_workspaces": [],
            "welcome_seen_versions": [],
        }
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
        except Exception:
            # Startup must remain recoverable even if the settings file is corrupt.
            self.data["settings_load_error"] = True

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def remember_workspace(self, workspace: str) -> None:
        workspace = workspace.strip()
        if not workspace:
            return
        self.data["last_workspace_path"] = workspace
        recent = [item for item in self.recent_workspaces() if item != workspace]
        recent.insert(0, workspace)
        self.data["recent_workspaces"] = recent[:MAX_RECENT_WORKSPACES]

    def recent_workspaces(self) -> list[str]:
        recent = self.data.get("recent_workspaces", [])
        if not isinstance(recent, list):
            return []
        return [str(item) for item in recent if str(item).strip()]

    def last_api_port(self) -> int:
        try:
            port = int(self.data.get("last_api_port", DEFAULT_API_PORT))
        except (TypeError, ValueError):
            return DEFAULT_API_PORT
        return port if 1 <= port <= 65535 else DEFAULT_API_PORT

    def set_window_size(self, width: int, height: int) -> None:
        self.data["window_size"] = {"width": max(width, 640), "height": max(height, 480)}

    def welcome_seen(self, version: str = APP_VERSION) -> bool:
        seen = self.data.get("welcome_seen_versions", [])
        return isinstance(seen, list) and version in seen

    def mark_welcome_seen(self, version: str = APP_VERSION) -> None:
        seen = self.data.get("welcome_seen_versions", [])
        if not isinstance(seen, list):
            seen = []
        if version not in seen:
            seen.append(version)
        self.data["welcome_seen_versions"] = seen


def save_feedback(category: str, message: str, workspace: str | None = None) -> Path:
    directory = feedback_dir()
    directory.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "timestamp": utc_timestamp(),
        "app_version": APP_VERSION,
        "category": category,
        "message": message,
    }
    if workspace:
        payload["workspace"] = workspace
    path = directory / f"feedback_{timestamp_slug()}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def runtime_manifest_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "app_version": APP_VERSION,
        "build_info": BUILD_INFO,
    }
    try:
        from abw.runtime_manifest import (
            CANONICAL_RUNTIME_DIR,
            CRITICAL_RUNTIME_MODULES,
            MIRRORED_RUNTIME_MODULES,
            PACKAGE_ONLY_MODULES,
            PACKAGED_FALLBACK_DIR,
            SCRIPT_ONLY_MODULES,
        )

        snapshot.update(
            {
                "canonical_runtime_dir": CANONICAL_RUNTIME_DIR,
                "packaged_fallback_dir": PACKAGED_FALLBACK_DIR,
                "critical_runtime_modules": list(CRITICAL_RUNTIME_MODULES),
                "mirrored_runtime_modules": list(MIRRORED_RUNTIME_MODULES),
                "script_only_modules": list(SCRIPT_ONLY_MODULES),
                "package_only_modules": list(PACKAGE_ONLY_MODULES),
            }
        )
    except Exception as exc:
        snapshot["runtime_manifest_error"] = str(exc)
    return snapshot


def export_diagnostics(settings: AdminSettings) -> Path:
    directory = diagnostics_dir()
    directory.mkdir(parents=True, exist_ok=True)
    zip_path = directory / f"abw_diagnostics_{timestamp_slug()}.zip"
    manifest_text = json.dumps(runtime_manifest_snapshot(), indent=2)
    settings_text = json.dumps(settings.data, indent=2)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("runtime_manifest.json", manifest_text)
        archive.writestr("settings_snapshot.json", settings_text)
        if settings.path.exists():
            archive.write(settings.path, "settings.json")
        logs = log_dir()
        if logs.exists():
            for path in logs.glob("*.log"):
                if path.is_file():
                    archive.write(path, f"logs/{path.name}")
    return zip_path
