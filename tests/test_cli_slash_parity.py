import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").strip().split("\n"))


def run_cli(args, *, cwd: Path):
    env = dict(os.environ)
    env.pop("ABW_WORKSPACE", None)
    env.pop("ABW_AGENT_MODE", None)
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "abw_cli.py"), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def run_slash(command: str, *, cwd: Path, workspace: Path, task: str | None = None):
    env = dict(os.environ)
    env["ABW_DEV_ENTRY"] = "1"
    env.pop("ABW_AGENT_MODE", None)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "abw_entry.py"),
        command,
        "--workspace",
        str(workspace),
    ]
    if task is not None:
        cmd.extend(["--task", task])
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class CliSlashParityTests(unittest.TestCase):
    def _assert_pair(self, cli_args, slash_command, *, workspace: Path, task: str | None = None):
        cli = run_cli(cli_args, cwd=workspace)
        slash = run_slash(slash_command, cwd=workspace, workspace=workspace, task=task)
        self.assertEqual(cli.returncode, slash.returncode, f"CLI={cli.stderr}\nSLASH={slash.stderr}")
        self.assertEqual(_normalize(cli.stdout), _normalize(slash.stdout))
        self.assertIn("ABW", cli.stdout)

    def test_canonical_pairs_have_output_and_exit_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            init = run_cli(["init"], cwd=workspace)
            self.assertEqual(init.returncode, 0, init.stderr)

            # Force migrate warnings/next-step hints to validate parity in warning paths too.
            (workspace / "abw").mkdir(exist_ok=True)

            self._assert_pair(["doctor"], "/abw-doctor", workspace=workspace)
            self._assert_pair(["version"], "/abw-version", workspace=workspace)
            self._assert_pair(["ask", "print hello world"], "/abw-ask", workspace=workspace, task="print hello world")
            self._assert_pair(["review"], "/abw-review", workspace=workspace)
            self._assert_pair(["migrate"], "/abw-migrate", workspace=workspace)

    def test_workspace_resolution_matches_with_explicit_workspace_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)

            init = run_cli(["init"], cwd=workspace)
            self.assertEqual(init.returncode, 0, init.stderr)

            module_cli = subprocess.run(
                [sys.executable, "-m", "abw.cli", "--workspace", str(workspace), "doctor"],
                cwd=str(root),
                env={
                    **os.environ,
                    "ABW_ENTRY_CALLER": "abw_cli",
                    "PYTHONPATH": str(REPO_ROOT / "src") + os.pathsep + str(os.environ.get("PYTHONPATH", "")),
                },
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if module_cli.returncode == 1 and "No module named abw.cli" in (module_cli.stderr or ""):
                self.skipTest("abw package module is not available in this test environment")

            slash = run_slash("/abw-doctor", cwd=root, workspace=workspace)
            self.assertEqual(module_cli.returncode, slash.returncode, module_cli.stderr + "\n" + slash.stderr)
            self.assertEqual(_normalize(module_cli.stdout), _normalize(slash.stdout))


if __name__ == "__main__":
    unittest.main()
