import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw import legacy  # noqa: E402
from abw.cli import main  # noqa: E402
from abw.workspace import ensure_workspace  # noqa: E402


class RuntimeLoaderTests(unittest.TestCase):
    def test_auto_selects_scripts_when_runner_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "abw_runner.py").write_text("# test\n", encoding="utf-8")
            legacy_dir = root / "_legacy"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            with patch.object(legacy, "SCRIPTS_DIR", scripts_dir), patch.object(legacy, "LEGACY_DIR", legacy_dir), patch.dict(
                os.environ, {"ABW_RUNTIME_SOURCE": "auto"}
            ):
                selected = legacy.selected_runtime_source()
            self.assertEqual(selected["runtime_source"], "scripts")
            self.assertEqual(selected["runtime_source_path"], str(scripts_dir))

    def test_forced_packaged_selects_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "abw_runner.py").write_text("# test\n", encoding="utf-8")
            legacy_dir = root / "_legacy"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            with patch.object(legacy, "SCRIPTS_DIR", scripts_dir), patch.object(legacy, "LEGACY_DIR", legacy_dir), patch.dict(
                os.environ, {"ABW_RUNTIME_SOURCE": "packaged"}
            ):
                selected = legacy.selected_runtime_source()
            self.assertEqual(selected["runtime_source"], "packaged_legacy")
            self.assertEqual(selected["runtime_source_path"], str(legacy_dir))

    def test_auto_falls_back_to_packaged_when_scripts_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            legacy_dir = root / "_legacy"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            with patch.object(legacy, "SCRIPTS_DIR", scripts_dir), patch.object(legacy, "LEGACY_DIR", legacy_dir), patch.dict(
                os.environ, {"ABW_RUNTIME_SOURCE": "auto"}
            ):
                selected = legacy.selected_runtime_source()
            self.assertEqual(selected["runtime_source"], "packaged_legacy")
            self.assertEqual(selected["runtime_source_path"], str(legacy_dir))

    def test_invalid_override_raises_clear_error(self):
        with patch.dict(os.environ, {"ABW_RUNTIME_SOURCE": "broken"}):
            with self.assertRaisesRegex(ValueError, "ABW_RUNTIME_SOURCE must be one of"):
                legacy.selected_runtime_source()

    def test_ensure_legacy_path_prefers_forced_packaged_without_mixed_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (scripts_dir / "abw_runner.py").write_text("# test\n", encoding="utf-8")
            legacy_dir = root / "_legacy"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            with patch.object(legacy, "SCRIPTS_DIR", scripts_dir), patch.object(legacy, "LEGACY_DIR", legacy_dir), patch.dict(
                os.environ, {"ABW_RUNTIME_SOURCE": "packaged"}
            ):
                with patch.object(sys, "path", [str(scripts_dir), str(legacy_dir), ""]):
                    legacy.ensure_legacy_path()
                    search_paths = legacy.current_runtime_search_paths()
            self.assertIn(str(legacy_dir.resolve()), search_paths)
            self.assertNotIn(str(scripts_dir.resolve()), search_paths)

    def test_cli_commands_still_work_with_auto_runtime_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)
            with patch.dict(os.environ, {"ABW_RUNTIME_SOURCE": "auto"}):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(main(["--workspace", tmp, "ask", "dashboard"]), 0)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["--workspace", tmp, "doctor"]), 0)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["--workspace", tmp, "version"]), 0)


if __name__ == "__main__":
    unittest.main()
