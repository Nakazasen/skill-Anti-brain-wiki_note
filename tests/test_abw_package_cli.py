import json
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class AbwPackageCliTests(unittest.TestCase):
    def tearDown(self):
        legacy_root = (Path(__file__).resolve().parents[1] / "src" / "abw" / "_legacy").resolve()
        legacy_path = str(legacy_root)
        sys.path[:] = [item for item in sys.path if str(Path(item).resolve()) != legacy_path]
        for name in list(sys.modules):
            if name == "abw" or name.startswith("abw."):
                sys.modules.pop(name, None)
                continue
            module_file = getattr(sys.modules.get(name), "__file__", None)
            if module_file and legacy_root in Path(module_file).resolve().parents:
                sys.modules.pop(name, None)

    def load_cli(self):
        return importlib.import_module("abw.cli")

    def test_init_creates_workspace_structure(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = cli.main(["--workspace", tmp, "init"])

            self.assertEqual(exit_code, 0)
            root = Path(tmp)
            self.assertTrue((root / "raw").is_dir())
            self.assertTrue((root / "wiki").is_dir())
            self.assertTrue((root / "drafts").is_dir())

            config = json.loads((root / "abw_config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["domain_profile"], "generic")
            self.assertEqual(config["raw_dir"], "raw")
            self.assertEqual(config["wiki_dir"], "wiki")
            self.assertEqual(config["drafts_dir"], "drafts")

    def test_ask_uses_abw_workspace_environment_override(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"ABW_WORKSPACE": tmp}), patch(
                "abw.cli._legacy_entry.execute_command",
                return_value={
                    "binding_status": "runner_enforced",
                    "runner_status": "completed",
                    "answer": "ok",
                },
            ) as execute_mock, patch(
                "abw.cli._legacy_entry.final_output",
                side_effect=lambda result: result,
            ), patch("abw.cli.output.render", return_value="ok"):
                exit_code = cli.main(["ask", "dashboard"])

            self.assertEqual(exit_code, 0)
            execute_mock.assert_called_once_with("/abw-ask", task="dashboard", workspace=str(Path(tmp).resolve()))

    def test_workspace_argument_overrides_environment(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as env_tmp, tempfile.TemporaryDirectory() as arg_tmp:
            with patch.dict("os.environ", {"ABW_WORKSPACE": env_tmp}), patch(
                "abw.cli._legacy_entry.execute_command",
                return_value={
                    "binding_status": "runner_enforced",
                    "runner_status": "completed",
                    "answer": "ok",
                },
            ) as execute_mock, patch(
                "abw.cli._legacy_entry.final_output",
                side_effect=lambda result: result,
            ), patch("abw.cli.output.render", return_value="ok"):
                exit_code = cli.main(["--workspace", arg_tmp, "ask", "dashboard"])

            self.assertEqual(exit_code, 0)
            execute_mock.assert_called_once_with("/abw-ask", task="dashboard", workspace=str(Path(arg_tmp).resolve()))

    def test_help_uses_product_facade_without_runner(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            with patch("abw.cli.entry.ask") as ask_mock:
                exit_code = cli.main(["--workspace", tmp, "help"])

            self.assertEqual(exit_code, 0)
            ask_mock.assert_not_called()

    def test_provider_list_command_prints_registry(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch("sys.stdout", output):
                exit_code = cli.main(["--workspace", tmp, "provider", "list"])

            self.assertEqual(exit_code, 0)
            self.assertIn("ABW Providers", output.getvalue())
            self.assertIn("openai", output.getvalue())
            self.assertIn("claude", output.getvalue())

    def test_provider_test_command_prints_health(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch("sys.stdout", output):
                exit_code = cli.main(["--workspace", tmp, "provider", "test"])

            self.assertEqual(exit_code, 0)
            self.assertIn("ABW Provider Health", output.getvalue())

    def test_provider_set_default_updates_workspace_config(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch("sys.stdout", output):
                exit_code = cli.main(["--workspace", tmp, "provider", "set-default", "claude"])

            self.assertEqual(exit_code, 0)
            self.assertIn("default provider set to: claude", output.getvalue())
            config = json.loads((Path(tmp) / "abw_config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["providers"]["default"], "claude")

    def test_provider_route_explain_outputs_selection(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch("sys.stdout", output):
                exit_code = cli.main(
                    [
                        "--workspace",
                        tmp,
                        "provider",
                        "route",
                        "explain",
                        "--task",
                        "analysis",
                        "--sensitivity",
                        "high",
                        "--cost",
                        "low",
                    ]
                )

            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("ABW Provider Route", rendered)
            self.assertIn("selected:", rendered)

    def test_provider_set_mode_updates_workspace_config(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch("sys.stdout", output):
                exit_code = cli.main(["--workspace", tmp, "provider", "set-mode", "hybrid"])

            self.assertEqual(exit_code, 0)
            self.assertIn("ask mode set to: hybrid", output.getvalue())
            config = json.loads((Path(tmp) / "abw_config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["providers"]["ask_mode"], "hybrid")

    def test_ask_uses_local_mode_without_provider_rewrite(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "abw_config.json").write_text(
                json.dumps(
                    {
                        "project_name": "x",
                        "workspace_schema": 1,
                        "abw_version": "0.2.6",
                        "domain_profile": "generic",
                        "raw_dir": "raw",
                        "wiki_dir": "wiki",
                        "drafts_dir": "drafts",
                        "providers": {"ask_mode": "local"},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            with patch("abw.cli._legacy_entry.execute_command", return_value={"answer": "ok"}) as execute_mock, patch(
                "abw.cli._legacy_entry.final_output",
                side_effect=lambda result: result,
            ), patch("abw.cli.output.render", return_value="ok"):
                exit_code = cli.main(["--workspace", tmp, "ask", "hello"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(execute_mock.call_args.kwargs["task"], "hello")

    def test_ask_ai_mode_rewrites_task_with_provider_draft(self):
        cli = self.load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "abw_config.json").write_text(
                json.dumps(
                    {
                        "project_name": "x",
                        "workspace_schema": 1,
                        "abw_version": "0.2.6",
                        "domain_profile": "generic",
                        "raw_dir": "raw",
                        "wiki_dir": "wiki",
                        "drafts_dir": "drafts",
                        "providers": {"ask_mode": "ai", "default": "mock", "fallback_chain": ["mock"]},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            with patch("abw.cli._legacy_entry.execute_command", return_value={"answer": "ok"}) as execute_mock, patch(
                "abw.cli._legacy_entry.final_output",
                side_effect=lambda result: result,
            ), patch("abw.cli.output.render", return_value="ok"):
                exit_code = cli.main(["--workspace", tmp, "ask", "hello"])
            self.assertEqual(exit_code, 0)
            self.assertIn("[provider_draft]", execute_mock.call_args.kwargs["task"])


if __name__ == "__main__":
    unittest.main()
