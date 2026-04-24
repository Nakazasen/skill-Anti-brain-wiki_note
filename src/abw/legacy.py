"""Loader for the existing ABW runtime modules.

The runtime modules are kept byte-for-byte compatible under ``abw._legacy`` so
the package CLI can use them without changing runner or proof behavior.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


LEGACY_DIR = Path(__file__).resolve().parent / "_legacy"
RUNTIME_SOURCE_PACKAGED = "packaged_legacy"


def ensure_legacy_path() -> None:
    path = str(LEGACY_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


def runtime_source_details() -> dict:
    return {
        "runtime_source": RUNTIME_SOURCE_PACKAGED,
        "runtime_source_path": str(LEGACY_DIR),
    }


def load(name: str):
    ensure_legacy_path()
    return importlib.import_module(name)
