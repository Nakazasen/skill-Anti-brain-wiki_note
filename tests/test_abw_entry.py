import json
import os
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


def dev_entry_env():
    env = os.environ.copy()
    env["ABW_DEV_ENTRY"] = "1"
    return env


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
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=dev_entry_env(),
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("ABW", completed.stdout)
        self.assertIn("hello world", completed.stdout)
        self.assertIn("Actions", completed.stdout)
        self.assertNotIn("binding_status", completed.stdout)
        self.assertNotIn("validation_proof", completed.stdout)

    def test_ask_help_cli_uses_clean_output(self):
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_entry.py"), "/abw-ask", "--task", "help"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=dev_entry_env(),
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("ABW Help", completed.stdout)
        self.assertIn("- Raw files:", completed.stdout)
        self.assertIn("- ingest raw/<file>", completed.stdout)
        self.assertNotIn("{", completed.stdout)
        self.assertNotIn("binding_status", completed.stdout)
        self.assertNotIn("validation_proof", completed.stdout)

    def test_ask_debug_dev_entry_returns_full_json(self):
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_entry.py"), "/abw-ask", "--task", "help", "--debug"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=dev_entry_env(),
        )

        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn(payload["binding_status"], {"runner_checked", "runner_enforced"})
        self.assertTrue(payload["validation_proof"])

    def test_ask_debug_dev_entry_with_raw_json_env_returns_full_json(self):
        env = dev_entry_env()
        env["ABW_RAW_JSON"] = "1"
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_entry.py"), "/abw-ask", "--task", "help", "--debug"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )

        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn(payload["binding_status"], {"runner_checked", "runner_enforced"})
        self.assertTrue(payload["validation_proof"])

    def test_agent_mode_blocks_direct_entry_level_bypass(self):
        env = dev_entry_env()
        env["ABW_AGENT_MODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "abw_entry.py"),
                "/abw-ask",
                "--task",
                "help",
                "--level",
                "expert",
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

    def test_task_text_debug_does_not_enable_json(self):
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_entry.py"), "/abw-ask", "--task", "help --debug"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=dev_entry_env(),
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("ABW Help", completed.stdout)
        self.assertNotIn("binding_status", completed.stdout)
        self.assertNotIn("validation_proof", completed.stdout)

    def test_direct_entry_without_cli_or_dev_is_blocked(self):
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_entry.py"), "/abw-ask", "--task", "help"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("Do not run abw_entry directly. Use 'abw' CLI.", completed.stderr)

    def test_direct_return_without_runner_is_rejected(self):
        trusted = abw_entry.final_output("plain raw answer")
        rendered = abw_runner.render_with_visibility_lock(trusted)
        self.assertEqual(trusted["binding_status"], "rejected")
        self.assertEqual(trusted["reason"], "output not produced by runner")
        self.assertIn("### ABW", rendered)
        self.assertIn("state: blocked", rendered)
        self.assertIn("output not produced by runner", rendered)
        self.assertNotIn("binding=rejected", rendered)

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
        self.assertIn("### ABW", rendered)
        self.assertIn("state: blocked", rendered)
        self.assertIn("output not produced by runner", rendered)
        self.assertNotIn("binding=rejected", rendered)

    def test_real_runner_payload_passes(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            workspace=".",
            task_kind="execution",
            binding_source="cli",
        )
        rendered = abw_entry.render_final_output(result)
        self.assertIn("ABW", rendered)
        self.assertIn("hello world", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("finalization_block", rendered)

    def test_render_final_output_uses_agent_safe_dashboard_view(self):
        result = abw_runner.dispatch_request(
            task="dashboard",
            workspace=".",
            task_kind="execution",
            binding_source="cli",
        )
        rendered = abw_entry.render_final_output(result)
        self.assertIn("ABW Dashboard", rendered)
        self.assertIn("Raw files:", rendered)
        self.assertIn("Wiki files:", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("Finalization", rendered)
        self.assertNotIn("commit:", rendered)
        self.assertNotIn("binding=", rendered)
        self.assertNotIn("Modules:", rendered)
        self.assertNotIn("Lanes:", rendered)

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
                encoding="utf-8",
                capture_output=True,
                check=False,
                cwd=str(REPO_ROOT),
                env=dev_entry_env(),
            )

            self.assertEqual(completed.returncode, 0)
            self.assertIn("ABW", completed.stdout)
            self.assertIn("ABW health audit completed.", completed.stdout)
            self.assertNotIn("binding_status", completed.stdout)
            self.assertNotIn("validation_proof", completed.stdout)

    def test_doctor_and_legacy_status_alias_route_to_health_audit(self):
        fake = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "health ok",
        }
        for command in ("/abw-doctor", "/abw-health", "/abw-status"):
            with self.subTest(command=command), patch("abw_entry.abw_health.run_health", return_value=fake) as health_mock:
                result = abw_entry.execute_command(command, workspace=".")

            health_mock.assert_called_once()
            self.assertEqual(health_mock.call_args.kwargs["mode"], "audit")
            self.assertEqual(result["answer"], "health ok")

    def test_doctor_adds_self_check_hint_when_stale_install_suspected(self):
        fake = {
            "binding_status": "runner_enforced",
            "binding_source": "cli",
            "current_state": "verified",
            "runner_status": "completed",
            "runtime_id": "123",
            "nonce": "a" * 32,
            "finalization_block": "## Finalization\n- current_state: verified\n- evidence: ok\n- gaps_or_limitations: none\n- next_steps: none",
        }
        fake["answer"] = "ABW health audit completed.\n\n" + fake["finalization_block"]
        with patch("abw_entry.abw_health.run_health", return_value=fake), patch(
            "abw_entry.build_version_report",
            return_value={"release_match_state": "mismatched"},
        ), patch("abw_entry.stale_install_suspected", return_value=True):
            result = abw_entry.execute_command("/abw-doctor", workspace=".")
        self.assertIn("abw self-check", result["answer"])

    def test_version_command_returns_structured_report_result(self):
        version_report = {"package_version": "0.2.4"}
        with patch("abw_entry.build_version_report", return_value=version_report) as build_mock, patch(
            "abw_entry.render_version_report",
            return_value="ABW Version\n- package_version: 0.2.4",
        ) as render_mock:
            result = abw_entry.execute_command("/abw-version", workspace=".")

        build_mock.assert_called_once_with(".")
        render_mock.assert_called_once_with(version_report)
        self.assertEqual(result["task"], "/abw-version")
        self.assertEqual(result["binding_status"], "runner_enforced")
        self.assertIn("ABW Version", result["answer"])

    def test_migrate_command_returns_structured_report_result(self):
        migration_report = {"status": "already_compatible"}
        with patch("abw_entry.build_migration_report", return_value=migration_report) as build_mock, patch(
            "abw_entry.render_migration_report",
            return_value="ABW Migrate\n- result: already_compatible",
        ) as render_mock:
            result = abw_entry.execute_command("/abw-migrate", workspace=".")

        build_mock.assert_called_once_with(".")
        render_mock.assert_called_once_with(migration_report)
        self.assertEqual(result["task"], "/abw-migrate")
        self.assertEqual(result["binding_status"], "runner_enforced")
        self.assertIn("ABW Migrate", result["answer"])

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
                encoding="utf-8",
                capture_output=True,
                check=False,
                cwd=str(REPO_ROOT),
                env=dev_entry_env(),
            )

            self.assertEqual(completed.returncode, 0)
            self.assertIn("ABW", completed.stdout)
            self.assertIn("ABW health repair completed.", completed.stdout)
            self.assertNotIn("binding_status", completed.stdout)
            self.assertNotIn("validation_proof", completed.stdout)

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

    def test_alias_command_rewrites_through_ask_path(self):
        fake = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "dashboard",
        }
        with patch("abw_entry.abw_runner.dispatch_request", return_value=fake) as dispatch_mock:
            result = abw_entry.execute_command("/abw-dashboard", workspace=".")

        dispatch_mock.assert_called_once()
        self.assertEqual(dispatch_mock.call_args.kwargs["task"], "show dashboard")
        self.assertEqual(result["answer"], "dashboard")

    def test_alias_task_rewrites_without_changing_ask_behavior(self):
        fake = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "query",
        }
        with patch("abw_entry.abw_runner.dispatch_request", return_value=fake) as dispatch_mock:
            result = abw_entry.execute_command("/abw-ask", task='/abw-query "abc"', workspace=".")

        dispatch_mock.assert_called_once()
        self.assertEqual(dispatch_mock.call_args.kwargs["task"], 'ask "abc"')
        self.assertEqual(result["answer"], "query")

    def test_unknown_abw_alias_falls_back_to_ask_safely(self):
        fake = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "fallback",
        }
        with patch("abw_entry.abw_runner.dispatch_request", return_value=fake) as dispatch_mock:
            result = abw_entry.execute_command("/abw-unknown", task="arg", workspace=".")

        dispatch_mock.assert_called_once()
        self.assertEqual(dispatch_mock.call_args.kwargs["task"], "/abw-unknown arg")
        self.assertEqual(result["answer"], "fallback")
