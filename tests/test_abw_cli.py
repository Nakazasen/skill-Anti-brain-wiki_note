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
        stdout = io.StringIO()
        with patch("abw_cli.abw_help.run", return_value={"message": "help", "sections": []}), patch(
            "abw_cli.render_help_report",
            return_value="ABW Help",
        ), patch("sys.stdout", stdout), patch("abw_cli.subprocess.run") as run_mock:
            exit_code = abw_cli.main(["help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ABW Help", stdout.getvalue())
        run_mock.assert_not_called()

    def test_help_advanced_sets_help_env(self):
        with patch("abw_cli.abw_help.run", return_value={"message": "help", "sections": []}) as help_mock, patch(
            "abw_cli.render_help_report",
            return_value="ABW Help",
        ):
            abw_cli.main(["help", "--advanced"])

        self.assertTrue(help_mock.call_args.kwargs["advanced"])

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

    def test_ask_overview_uses_local_overview_facade(self):
        stdout = io.StringIO()
        with patch("abw_cli.build_overview", return_value={"content": "# ABW Overview\n"}), patch(
            "sys.stdout",
            stdout,
        ), patch("abw_cli.subprocess.run") as run_mock:
            exit_code = abw_cli.main(["ask", "overview"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "# ABW Overview\n")
        run_mock.assert_not_called()

    def test_overview_command_prints_generated_overview(self):
        stdout = io.StringIO()
        with patch("abw_cli.build_overview", return_value={"content": "# ABW Overview\n- Draft count: 0\n"}), patch(
            "sys.stdout",
            stdout,
        ):
            exit_code = abw_cli.main(["overview"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ABW Overview", stdout.getvalue())

    def test_save_command_reports_saved_candidate_note(self):
        stdout = io.StringIO()
        with patch(
            "abw_cli.save_candidate",
            return_value={
                "relative_path": "raw/captured_notes/2026-04-23_0930_note.md",
                "next_step": "abw ingest raw/captured_notes/2026-04-23_0930_note.md",
            },
        ), patch("sys.stdout", stdout):
            exit_code = abw_cli.main(["save", "lesson learned"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Saved candidate note:", output)
        self.assertIn("Suggested next step:", output)

    def test_init_command_reports_workspace_state(self):
        stdout = io.StringIO()
        with patch(
            "abw_cli.ensure_workspace",
            return_value={
                "root": Path("D:/tmp/workspace"),
                "created_dirs": ["raw", "wiki"],
                "config_status": "created",
                "config": {"workspace_schema": 1},
            },
        ), patch("sys.stdout", stdout):
            exit_code = abw_cli.main(["init"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("ABW workspace initialized:", output)
        self.assertIn("Workspace schema: 1", output)

    def test_doctor_prints_direct_report(self):
        stdout = io.StringIO()
        with patch("abw_cli.build_doctor_report", return_value={"ok": True}), patch(
            "abw_cli.render_doctor_report",
            return_value="ABW Doctor\n- OK: workspace initialized",
        ), patch("sys.stdout", stdout), patch("abw_cli.subprocess.run") as run_mock:
            exit_code = abw_cli.main(["doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ABW Doctor", stdout.getvalue())
        run_mock.assert_not_called()

    def test_version_prints_direct_report(self):
        stdout = io.StringIO()
        with patch("abw_cli.build_version_report", return_value={"package_version": "0.2.2"}), patch(
            "abw_cli.render_version_report",
            return_value="ABW Version\n- package_version: 0.2.2",
        ), patch("sys.stdout", stdout):
            exit_code = abw_cli.main(["version"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ABW Version", stdout.getvalue())

    def test_migrate_prints_direct_report(self):
        stdout = io.StringIO()
        with patch("abw_cli.build_migration_report", return_value={"status": "migrated"}), patch(
            "abw_cli.render_migration_report",
            return_value="ABW Migrate\n- result: migrated",
        ), patch("sys.stdout", stdout):
            exit_code = abw_cli.main(["migrate"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ABW Migrate", stdout.getvalue())

    def test_upgrade_prints_guidance_report(self):
        stdout = io.StringIO()
        with patch("abw_cli.build_upgrade_report", return_value={"install_mode": "pip package"}), patch(
            "abw_cli.render_upgrade_report",
            return_value="ABW Upgrade\n- RUN: py -m pip install -U abw-skill",
        ), patch("sys.stdout", stdout), patch("abw_cli.subprocess.run") as run_mock:
            exit_code = abw_cli.main(["upgrade"])

        self.assertEqual(exit_code, 0)
        self.assertIn("ABW Upgrade", stdout.getvalue())
        run_mock.assert_not_called()

    def test_power_commands_route_to_direct_entry_points(self):
        cases = [
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
        with patch("abw_cli.build_doctor_report", return_value={"ok": True}), patch(
            "abw_cli.render_doctor_report",
            return_value="ABW Doctor",
        ), patch("sys.stdout", stdout):
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
