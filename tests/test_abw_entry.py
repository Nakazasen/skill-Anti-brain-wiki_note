import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_entry  # noqa: E402
import abw_proof  # noqa: E402
import abw_runner  # noqa: E402
import abw_update  # noqa: E402


def make_proof(answer, finalization_block, runtime_id="123", nonce=None, binding_source="mcp"):
    nonce = nonce or ("a" * 32)
    return abw_proof.generate_proof(answer, finalization_block, runtime_id, nonce, binding_source)


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
        self.assertIn("[ABW] trust=enforced | binding=runner_enforced | state=verified | validation_proof=", completed.stdout)
        self.assertIn("hello world", completed.stdout)

    def test_direct_return_without_runner_is_rejected(self):
        trusted = abw_entry.final_output("plain raw answer")
        rendered = abw_runner.render_with_visibility_lock(trusted)
        self.assertEqual(trusted["binding_status"], "rejected")
        self.assertEqual(trusted["reason"], "output not produced by runner")
        self.assertIn("[ABW] trust=blocked | binding=rejected | state=blocked", rendered)

    def test_fake_runner_payload_is_rejected(self):
        finalization_block = "## Finalization\n- current_state: verified"
        fake = {
            "binding_status": "runner_checked",
            "binding_source": "mcp",
            "validation_proof": make_proof("forged", finalization_block),
            "current_state": "verified",
            "answer": "forged",
            "finalization_block": finalization_block,
            "nonce": "a" * 32,
            "runtime_id": "123",
        }
        trusted = abw_entry.final_output(fake)
        rendered = abw_runner.render_with_visibility_lock(trusted)
        self.assertEqual(trusted["binding_status"], "rejected")
        self.assertIn(
            trusted["reason"],
            {"output not produced by runner", "raw draft answer is not allowed"},
        )
        self.assertIn("[ABW] trust=blocked | binding=rejected | state=blocked", rendered)

    def test_real_runner_payload_passes(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            workspace=".",
            task_kind="execution",
            binding_source="cli",
        )
        rendered = abw_entry.render_final_output(result)
        self.assertIn("[ABW] trust=enforced | binding=runner_enforced | state=verified | validation_proof=", rendered)

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
            self.assertIn("[ABW] trust=enforced | binding=runner_enforced | state=verified | validation_proof=", completed.stdout)
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
            self.assertIn("[ABW] trust=enforced | binding=runner_enforced | state=verified | validation_proof=", completed.stdout)
            self.assertIn("ABW health repair completed.", completed.stdout)

    def test_update_command_routes_to_update_module(self):
        fake = abw_update.build_result(
            binding_source="cli",
            binding_status="runner_enforced",
            current_state="verified",
            runner_status="completed",
            task="/abw-update",
            body="ABW update completed.",
            evidence="repo synced",
            gaps_or_limitations="none",
            next_steps="none",
            details={"changed": False},
        )
        with patch("abw_entry.abw_update.perform_update", return_value=fake) as update_mock:
            result = abw_entry.execute_command("/abw-update", task="abc123", workspace=".")

        update_mock.assert_called_once_with(workspace=".", target_ref="abc123")
        self.assertEqual(result["task"], "/abw-update")
        self.assertEqual(result["binding_status"], "runner_enforced")

    def test_rollback_command_routes_to_update_module(self):
        fake = abw_update.build_result(
            binding_source="cli",
            binding_status="runner_enforced",
            current_state="verified",
            runner_status="completed",
            task="/abw-rollback",
            body="ABW rollback completed.",
            evidence="repo restored",
            gaps_or_limitations="none",
            next_steps="none",
            details={"update_result": "rollback"},
        )
        with patch("abw_entry.abw_update.perform_rollback", return_value=fake) as rollback_mock:
            result = abw_entry.execute_command("/abw-rollback", workspace=".")

        rollback_mock.assert_called_once_with(workspace=".")
        self.assertEqual(result["task"], "/abw-rollback")
        self.assertEqual(result["binding_status"], "runner_enforced")
