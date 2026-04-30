import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_cli  # noqa: E402
import abw_entry  # noqa: E402


class CommandSurfaceParityTests(unittest.TestCase):
    def test_cli_exposes_all_canonical_verbs(self):
        for command, argv in {
            "ask": ["ask", "ping"],
            "review": ["review"],
            "doctor": ["doctor"],
            "gaps": ["gaps"],
            "version": ["version"],
            "migrate": ["migrate"],
            "apply": ["apply", "--dry-run", "cleanup-drafts"],
        }.items():
            with self.subTest(command=command):
                parsed = abw_cli.parse_args(argv)
                self.assertEqual(parsed.command, command)

    def test_canonical_slash_commands_route(self):
        fake_runner = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "ok",
        }
        with patch("abw_entry.abw_runner.dispatch_request", return_value=fake_runner) as dispatch_mock:
            result = abw_entry.execute_command("/abw-ask", task="ping", workspace=".")
        self.assertEqual(result["answer"], "ok")
        self.assertEqual(dispatch_mock.call_args.kwargs["task"], "ping")

        with patch("abw_entry.abw_runner.dispatch_request", return_value=fake_runner) as dispatch_mock:
            result = abw_entry.execute_command("/abw-review", workspace=".")
        self.assertEqual(result["answer"], "ok")
        self.assertEqual(dispatch_mock.call_args.kwargs["task"], "review drafts")

        with patch("abw_entry.abw_health.run_health", return_value=fake_runner) as health_mock:
            result = abw_entry.execute_command("/abw-doctor", workspace=".")
        self.assertEqual(result["answer"], "ok")
        self.assertEqual(health_mock.call_args.kwargs["mode"], "audit")

        with patch("abw_entry.build_version_report", return_value={"package_version": "0.2.4"}), patch(
            "abw_entry.render_version_report",
            return_value="ABW Version\n- package_version: 0.2.4",
        ):
            result = abw_entry.execute_command("/abw-version", workspace=".")
        self.assertEqual(result["task"], "/abw-version")
        self.assertEqual(result["binding_status"], "runner_enforced")

        with patch("abw_entry.build_migration_report", return_value={"status": "already_compatible"}), patch(
            "abw_entry.render_migration_report",
            return_value="ABW Migrate\n- result: already_compatible",
        ):
            result = abw_entry.execute_command("/abw-migrate", workspace=".")
        self.assertEqual(result["task"], "/abw-migrate")
        self.assertEqual(result["binding_status"], "runner_enforced")

    def test_legacy_health_aliases_resolve_to_doctor(self):
        fake = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "ok",
        }
        for command in ("/abw-health", "/abw-status"):
            with self.subTest(command=command), patch("abw_entry.abw_health.run_health", return_value=fake) as health_mock:
                result = abw_entry.execute_command(command, workspace=".")
            self.assertEqual(result["answer"], "ok")
            self.assertEqual(health_mock.call_args.kwargs["mode"], "audit")


if __name__ == "__main__":
    unittest.main()
