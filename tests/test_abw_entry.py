import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_entry  # noqa: E402
import abw_proof  # noqa: E402
import abw_runner  # noqa: E402


class AbwEntryTests(unittest.TestCase):
    def make_layout(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        workspace = root / "workspace"
        runtime = root / "runtime"
        (workspace / "scripts").mkdir(parents=True)
        (workspace / "workflows").mkdir(parents=True)
        (runtime / "scripts").mkdir(parents=True)
        (runtime / "global_workflows").mkdir(parents=True)
        return tmp, workspace, runtime

    def make_clean_pair(self, workspace, runtime):
        (workspace / "scripts" / "abw_runner.py").write_text("print('ok')\n", encoding="utf-8")
        (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
        (runtime / "scripts" / "abw_runner.py").write_text("print('ok')\n", encoding="utf-8")
        (runtime / "global_workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")

    def test_trusted_cli_output_path_works(self):
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_entry.py"), "/abw-ask", "--task", "print hello world"],
            text=True,
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("[ABW] binding=runner_enforced | validation_proof=", completed.stdout)
        self.assertIn("hello world", completed.stdout)

    def test_direct_return_without_runner_is_rejected(self):
        trusted = abw_entry.final_output("plain raw answer")
        rendered = abw_runner.render_with_visibility_lock(trusted)
        self.assertEqual(trusted["binding_status"], "rejected")
        self.assertEqual(trusted["reason"], "output not produced by runner")
        self.assertIn("[UNVERIFIED OUTPUT - DO NOT TRUST]", rendered)

    def test_fake_runner_payload_is_rejected(self):
        fake = {
            "binding_status": "runner_checked",
            "validation_proof": abw_proof.generate_proof("forged", "## Finalization\n- current_state: verified", "123"),
            "current_state": "verified",
            "answer": "forged",
            "finalization_block": "## Finalization\n- current_state: verified",
            "runtime_id": "123",
        }
        trusted = abw_entry.final_output(fake)
        rendered = abw_runner.render_with_visibility_lock(trusted)
        self.assertEqual(trusted["binding_status"], "rejected")
        self.assertIn(
            trusted["reason"],
            {"output not produced by runner", "raw draft answer is not allowed"},
        )
        self.assertIn("[UNVERIFIED OUTPUT - DO NOT TRUST]", rendered)

    def test_real_runner_payload_passes(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            workspace=".",
            task_kind="execution",
            binding_source="cli",
        )
        rendered = abw_entry.render_final_output(result)
        self.assertIn("[ABW] binding=runner_enforced | validation_proof=", rendered)

    def test_health_cli_path_works(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "abw_entry.py"),
                    "/abw-health",
                    "--workspace",
                    str(workspace),
                    "--runtime-root",
                    str(runtime),
                ],
                text=True,
                capture_output=True,
                check=False,
                cwd=str(REPO_ROOT),
            )

            self.assertEqual(completed.returncode, 0)
            self.assertIn("[ABW] binding=runner_enforced | validation_proof=", completed.stdout)
            self.assertIn("ABW health audit completed.", completed.stdout)

    def test_repair_cli_path_works(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "abw_runner.py").write_text("print('workspace')\n", encoding="utf-8")
            (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
            (runtime / "scripts" / "abw_runner.py").write_text("print('runtime')\n", encoding="utf-8")
            (runtime / "global_workflows" / "abw-ask.md").write_text("# stale\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "abw_entry.py"),
                    "/abw-repair",
                    "--workspace",
                    str(workspace),
                    "--runtime-root",
                    str(runtime),
                ],
                text=True,
                capture_output=True,
                check=False,
                cwd=str(REPO_ROOT),
            )

            self.assertEqual(completed.returncode, 0)
            self.assertIn("[ABW] binding=runner_enforced | validation_proof=", completed.stdout)
            self.assertIn("ABW health repair completed.", completed.stdout)
