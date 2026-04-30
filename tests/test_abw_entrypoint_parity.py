import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_entrypoint(command, *, cwd):
    env = dict(os.environ)
    env.pop("ABW_WORKSPACE", None)
    env.pop("ABW_AGENT_MODE", None)
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class AbwEntrypointParityTests(unittest.TestCase):
    def entrypoints(self):
        commands = [
            ["abw"],
            [sys.executable, "-m", "abw.cli"],
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_cli.py")],
        ]
        if (REPO_ROOT / "abw.bat").exists():
            commands.append([str(REPO_ROOT / "abw.bat")])
        return commands

    def test_supported_entrypoints_expose_same_public_help(self):
        expected = ["init", "ask", "ingest", "review", "doctor", "gaps", "version", "migrate", "help"]
        hidden = ["dashboard", "coverage", "wizard", "approve"]
        with tempfile.TemporaryDirectory() as tmp:
            for base in self.entrypoints():
                with self.subTest(entrypoint=base[0]):
                    completed = run_entrypoint([*base, "--help"], cwd=Path(tmp))
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    for command in expected:
                        self.assertIn(command, completed.stdout)
                    for command in hidden:
                        self.assertNotIn(command, completed.stdout)

    def test_supported_entrypoints_run_core_smoke_commands(self):
        cases = [
            (["help"], "ABW Help"),
            (["version"], "ABW Version"),
            (["doctor"], ("ABW Doctor", "ABW health audit completed.")),
            (["ask", "dashboard"], "ABW Dashboard"),
        ]
        for base in self.entrypoints():
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                init = run_entrypoint([*base, "init"], cwd=workspace)
                self.assertEqual(init.returncode, 0, init.stderr)
                for args, marker in cases:
                    with self.subTest(entrypoint=base[0], args=args):
                        completed = run_entrypoint([*base, *args], cwd=workspace)
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        if isinstance(marker, tuple):
                            self.assertTrue(any(candidate in completed.stdout for candidate in marker))
                        else:
                            self.assertIn(marker, completed.stdout)


class AbwReleaseSmokeTests(unittest.TestCase):
    def test_release_smoke_script_passes(self):
        if shutil.which("abw") is None:
            self.skipTest("abw console script is not on PATH")
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "release_smoke.py")],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("release_smoke: PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
