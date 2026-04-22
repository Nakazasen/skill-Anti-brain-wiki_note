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
        self.assertEqual(run_mock.call_args.kwargs["env"]["ABW_ENTRY_CALLER"], "abw_cli")

    def test_ask_routes_text_through_entry(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["ask", "MOM la gi"])

        self.assertEqual(run_mock.call_args.args[0][4], "MOM la gi")

    def test_command_mappings(self):
        cases = [
            (["ingest", "raw/file.pdf"], "ingest raw/file.pdf"),
            (["review"], "review drafts"),
            (["approve", "drafts/file.md"], "approve draft drafts/file.md"),
            (["coverage"], "coverage"),
            (["dashboard"], "dashboard"),
            (["wizard"], "wizard"),
        ]

        for argv, task in cases:
            with self.subTest(argv=argv), patch(
                "abw_cli.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run_mock:
                abw_cli.main(argv)

            self.assertEqual(run_mock.call_args.args[0][4], task)

    def test_debug_after_subcommand_is_forwarded(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["help", "--debug"])

        self.assertIn("--debug", run_mock.call_args.args[0])

    def test_level_after_subcommand_is_forwarded(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["help", "--level", "expert"])

        self.assertIn("--level", run_mock.call_args.args[0])
        self.assertIn("expert", run_mock.call_args.args[0])

    def test_health_routes_to_health_entry_command(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["health"])

        self.assertEqual(run_mock.call_args.args[0][2], "/abw-health")
        self.assertNotIn("--task", run_mock.call_args.args[0])

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

    def test_global_debug_before_subcommand_is_forwarded(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["--debug", "help"])

        self.assertIn("--debug", run_mock.call_args.args[0])

    def test_global_level_before_subcommand_is_forwarded(self):
        with patch("abw_cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            abw_cli.main(["--level", "beginner", "help"])

        self.assertIn("--level", run_mock.call_args.args[0])
        self.assertIn("beginner", run_mock.call_args.args[0])

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
