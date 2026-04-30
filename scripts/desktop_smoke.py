from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [sys.executable, str(ROOT / "ui" / "run_abw_desktop.py"), "--smoke"]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip())
    print(f"desktop_smoke: {'PASS' if completed.returncode == 0 else 'FAIL'}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
