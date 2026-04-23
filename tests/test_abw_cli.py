import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_cli  # noqa: E402
import abw_entry  # noqa: E402


class AbwCliTests(unittest.TestCase):
    def test_help_routes_through_entry(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            exit_code = abw_cli.main(["help"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            run_mock.call_args.args[0],
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "abw_entry.py"),
                "/abw-ask",
                "--task",
                "help",
                "--workspace",
                ".",
            ],
        )

    def test_help_advanced_sets_help_env(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["help", "--advanced"])

        self.assertEqual(run_mock.call_args.kwargs["env"]["ABW_HELP_ADVANCED"], "1")

    def test_public_commands_route_through_honest_surface(self):
        cases = [
            (["ask", "MOM la gi"], "/abw-ask", "MOM la gi"),
            (["ingest", "raw/file.pdf"], "/abw-ask", "ingest raw/file.pdf"),
            (["review"], "/abw-ask", "review drafts"),
        ]
        for argv, command, task in cases:
            with self.subTest(argv=argv), patch(
                "abw_cli.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run_mock:
                abw_cli.main(argv)

            self.assertEqual(run_mock.call_args.args[0][2], command)
            self.assertEqual(run_mock.call_args.args[0][4], task)

    def test_doctor_uses_health_entry_command(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["doctor"])

        self.assertEqual(run_mock.call_args.args[0][2], "/abw-health")
        self.assertNotIn("--task", run_mock.call_args.args[0])

    def test_power_commands_route_to_direct_entry_points(self):
        cases = [
            (["upgrade"], "/abw-update"),
            (["rollback"], "/abw-rollback"),
            (["repair"], "/abw-repair"),
        ]
        for argv, command in cases:
            with self.subTest(argv=argv), patch(
                "abw_cli.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run_mock:
                abw_cli.main(argv)

            self.assertEqual(run_mock.call_args.args[0][2], command)

    def test_deprecated_health_alias_prints_migration_hint(self):
        stdout = io.StringIO()
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)), patch("sys.stdout", stdout):
            abw_cli.main(["health"])

        self.assertIn("Deprecated command. Use: abw doctor", stdout.getvalue())

    def test_deprecated_query_alias_prints_migration_hint(self):
        stdout = io.StringIO()
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)), patch("sys.stdout", stdout):
            abw_cli.main(["query", "What is MOM?"])

        self.assertIn("Deprecated command. Use: abw ask", stdout.getvalue())

    def test_research_is_honest_placeholder(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            exit_code = abw_cli.main(["research"])

        self.assertEqual(exit_code, 2)
        self.assertIn("not a separate public runtime command yet", stdout.getvalue())

    def test_menu_command_launches_menu(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            exit_code = abw_cli.main(["menu"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(str(run_mock.call_args.args[0][1]).endswith("abw_menu.py"))

    def test_no_command_launches_menu(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            exit_code = abw_cli.main([])

        self.assertEqual(exit_code, 0)
        self.assertTrue(str(run_mock.call_args.args[0][1]).endswith("abw_menu.py"))

    def test_handle_input_routes_plain_text_through_ask(self):
        fake = {
            "binding_status": "runner_enforced",
            "current_state": "verified",
            "runner_status": "completed",
            "answer": "ok",
        }
        with patch("abw_entry.execute_command", return_value=fake) as execute_mock, patch(
            "abw_entry.final_output",
            side_effect=lambda result: result,
        ):
            result = abw_entry.handle_input("help", workspace=".")

        execute_mock.assert_called_once()
        self.assertEqual(execute_mock.call_args.args[0], "/abw-ask")
        self.assertEqual(execute_mock.call_args.kwargs["task"], "help")
        self.assertEqual(result["answer"], "ok")


if __name__ == "__main__":
    unittest.main()
