from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from functools import lru_cache


WINDOWS_TESSERACT_CANDIDATES = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)


def resolve_tesseract_executable() -> str | None:
    for env_name in ("ABW_TESSERACT_CMD", "TESSERACT_CMD", "TESSERACT_EXE"):
        configured = os.environ.get(env_name)
        if configured and Path(configured).exists():
            return str(Path(configured))

    path_match = shutil.which("tesseract")
    if path_match:
        return path_match

    local_appdata = os.environ.get("LOCALAPPDATA")
    candidates = list(WINDOWS_TESSERACT_CANDIDATES)
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / "Tesseract-OCR" / "tesseract.exe")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def tesseract_status() -> dict:
    executable = resolve_tesseract_executable()
    if not executable:
        return {"provider": "tesseract", "status": "unavailable", "reason": "tesseract executable not found"}
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        return {"provider": "tesseract", "status": "failed", "path": executable, "reason": str(exc)}

    first_line = (completed.stdout or completed.stderr).splitlines()[0] if (completed.stdout or completed.stderr) else "unknown"
    if completed.returncode != 0:
        return {"provider": "tesseract", "status": "failed", "path": executable, "reason": first_line}
    return {"provider": "tesseract", "status": "available", "path": executable, "version": first_line}


@lru_cache(maxsize=8)
def available_tesseract_languages(executable: str | None = None) -> tuple[str, ...]:
    executable = executable or resolve_tesseract_executable()
    if not executable:
        return ()
    try:
        completed = subprocess.run(
            [executable, "--list-langs"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception:  # noqa: BLE001
        return ()
    if completed.returncode != 0:
        return ()
    languages = []
    for line in (completed.stdout or "").splitlines():
        value = line.strip()
        if not value or value.lower().startswith("list of available languages"):
            continue
        languages.append(value)
    return tuple(languages)


def preferred_tesseract_language(executable: str | None = None) -> str:
    languages = set(available_tesseract_languages(executable))
    if {"eng", "jpn"}.issubset(languages):
        return "eng+jpn"
    if "jpn" in languages:
        return "jpn"
    return "eng"
