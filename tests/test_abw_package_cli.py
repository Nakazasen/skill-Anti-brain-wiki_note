import json
import importlib
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


if __name__ == "__main__":
    unittest.main()
