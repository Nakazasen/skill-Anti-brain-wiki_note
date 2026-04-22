import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_ai_runner(script_path, payload=None, env=None):
    merged_env = os.environ.copy()
    merged_env["ABW_DEV_ENTRY"] = "1"
    merged_env["PYTHONIOENCODING"] = "utf-8"
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(payload or {"task": "dashboard"}),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=str(REPO_ROOT),
        env=merged_env,
    )


class AiRunnerTests(unittest.TestCase):
    def assert_agent_output(self, stdout):
        self.assertIn("### ABW Dashboard", stdout)
        self.assertIn("Raw files:", stdout)
        self.assertIn("Wiki files:", stdout)
        self.assertIn("Coverage:", stdout)
        self.assertNotIn("binding_status", stdout)
        self.assertNotIn("validation_proof", stdout)
        self.assertNotIn("runtime_id", stdout)
        self.assertNotIn("Finalization", stdout)
        self.assertNotIn("commit:", stdout)
        self.assertNotIn("modules:", stdout)
        self.assertNotIn("lanes:", stdout)

    def test_scripts_ai_runner_renders_agent_ui(self):
        completed = run_ai_runner(REPO_ROOT / "scripts" / "ai_runner.py")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_agent_output(completed.stdout)

    def test_scripts_ai_runner_overrides_cli_mode(self):
        completed = run_ai_runner(
            REPO_ROOT / "scripts" / "ai_runner.py",
            env={"ABW_CLI_MODE": "1", "ABW_USER_LEVEL": "expert"},
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_agent_output(completed.stdout)
        self.assertIn("Level: expert", completed.stdout)

    def test_scripts_ai_runner_ignores_invalid_debug_level(self):
        completed = run_ai_runner(
            REPO_ROOT / "scripts" / "ai_runner.py",
            payload={"task": "dashboard", "level": "debug"},
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_agent_output(completed.stdout)
        self.assertNotIn('"binding_status"', completed.stdout)
        self.assertNotIn("[ABW]", completed.stdout)

    def test_root_ai_runner_wrapper_uses_scripts_runner(self):
        completed = run_ai_runner(REPO_ROOT / "ai_runner.py")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assert_agent_output(completed.stdout)

    def test_agent_mode_blocks_direct_entry_bypass(self):
        env = os.environ.copy()
        env["ABW_DEV_ENTRY"] = "1"
        env["ABW_AGENT_MODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys,json; "
                    "sys.path.insert(0,'scripts'); "
                    "import abw_entry as e; "
                    "res=e.final_output(e.execute_command('/abw-ask', task='dashboard')); "
                    "print(json.dumps(res, indent=2))"
                ),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Forbidden: Agent must use ai_runner.py", completed.stderr)
        self.assertNotIn("validation_proof", completed.stdout)

    def test_inline_python_direct_entry_bypass_is_blocked_without_agent_mode(self):
        env = os.environ.copy()
        env["ABW_DEV_ENTRY"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("ABW_AGENT_MODE", None)
        env.pop("ABW_EXECUTION_PATH", None)
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys,json; "
                    "sys.path.insert(0,'scripts'); "
                    "import abw_entry as e; "
                    "res=e.final_output(e.execute_command('/abw-ask', task='dashboard')); "
                    "print(json.dumps(res, indent=2))"
                ),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Forbidden: Agent must use ai_runner.py", completed.stderr)
        self.assertNotIn("validation_proof", completed.stdout)

    def test_inline_python_direct_runner_bypass_is_blocked(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("ABW_AGENT_MODE", None)
        env.pop("ABW_EXECUTION_PATH", None)
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys,json; "
                    "sys.path.insert(0,'scripts'); "
                    "import abw_runner as r; "
                    "res=r.dispatch_request(task='dashboard', task_kind='execution'); "
                    "print(json.dumps(res, indent=2))"
                ),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Forbidden: Agent must use ai_runner.py", completed.stderr)
        self.assertNotIn("validation_proof", completed.stdout)


if __name__ == "__main__":
    unittest.main()
