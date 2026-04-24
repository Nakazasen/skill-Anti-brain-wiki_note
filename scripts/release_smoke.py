from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def smoke_commands(workspace: Path) -> list[list[str]]:
    return [
        ["abw", "--help"],
        ["abw", "help"],
        ["abw", "init"],
        ["abw", "version"],
        ["abw", "doctor"],
        ["abw", "ask", "dashboard"],
    ]


def wheel_command(output_dir: Path) -> list[str]:
    return [sys.executable, "-m", "pip", "wheel", ".", "-w", str(output_dir)]


def run_smoke(*, include_wheel: bool = False) -> tuple[int, list[dict]]:
    if shutil.which("abw") is None:
        return 1, [{"command": "abw", "returncode": 1, "stdout": "", "stderr": "`abw` is not on PATH"}]

    rows: list[dict] = []
    env = dict(os.environ)
    env.pop("ABW_WORKSPACE", None)
    env.pop("ABW_AGENT_MODE", None)

    with tempfile.TemporaryDirectory(prefix="abw-smoke-") as tmp:
        workspace = Path(tmp)
        for command in smoke_commands(workspace):
            row = run_command(command, cwd=workspace, env=env)
            rows.append(row)
            if row["returncode"] != 0:
                return row["returncode"], rows

        if include_wheel:
            wheel_out = workspace / "wheelhouse"
            wheel_out.mkdir(parents=True, exist_ok=True)
            row = run_command(wheel_command(wheel_out), cwd=ROOT, env=env)
            rows.append(row)
            if row["returncode"] != 0:
                return row["returncode"], rows

    return 0, rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run ABW release smoke checks.")
    parser.add_argument("--wheel", action="store_true", help="Also build a wheel into a temporary directory.")
    args = parser.parse_args(argv)

    exit_code, rows = run_smoke(include_wheel=args.wheel)
    for row in rows:
        status = "PASS" if row["returncode"] == 0 else "FAIL"
        print(f"{status}: {row['command']}")
        if row["returncode"] != 0:
            if row["stdout"]:
                print(row["stdout"])
            if row["stderr"]:
                print(row["stderr"])
    print(f"release_smoke: {'PASS' if exit_code == 0 else 'FAIL'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
