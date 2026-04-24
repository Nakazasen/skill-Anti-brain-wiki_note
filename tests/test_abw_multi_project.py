import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.doctor import build_doctor_report, render_doctor_report  # noqa: E402
from abw.migrate import build_migration_report, render_migration_report  # noqa: E402
from abw.upgrade import build_upgrade_report, render_upgrade_report  # noqa: E402
from abw.version import build_version_report, render_version_report  # noqa: E402
from abw.workspace import ensure_workspace, read_workspace_config  # noqa: E402


class AbwMultiProjectTests(unittest.TestCase):
    def test_init_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = ensure_workspace(tmp)
            config_path = Path(tmp) / "abw_config.json"
            initial = json.loads(config_path.read_text(encoding="utf-8"))

            second = ensure_workspace(tmp)
            repeated = json.loads(config_path.read_text(encoding="utf-8"))

            self.assertEqual(first["root"], second["root"])
            self.assertEqual(initial["workspace_schema"], 1)
            self.assertEqual(repeated["workspace_schema"], 1)
            self.assertEqual(repeated["project_name"], Path(tmp).name)

    def test_version_report_includes_install_and_workspace_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)

            report = build_version_report(tmp)
            rendered = render_version_report(report)

            self.assertIn("package_version", report)
            self.assertEqual(str(Path(tmp).resolve()), report["workspace"])
            self.assertIn("install_mode", report)
            self.assertIn("workspace_schema", report)
            self.assertIn("ABW Version", rendered)
            self.assertNotIn("validation_proof", rendered)

    def test_doctor_detects_missing_folders_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_doctor_report(tmp)
            rendered = render_doctor_report(report)

            self.assertEqual(report["overall"], "WARN")
            messages = [item["message"] for item in report["checks"]]
            self.assertIn("missing raw/", messages)
            self.assertIn("missing abw_config.json", messages)
            self.assertIn("ABW Doctor", rendered)
            self.assertNotIn("validation_proof", rendered)

    def test_doctor_detects_legacy_local_abw_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)
            (Path(tmp) / "abw").mkdir(parents=True, exist_ok=True)

            report = build_doctor_report(tmp)

            messages = [item["message"] for item in report["checks"]]
            self.assertIn("local legacy ABW engine detected at ./abw", messages)

    def test_migrate_preserves_existing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            (root / "raw" / "a.md").write_text("raw\n", encoding="utf-8")
            (root / "wiki").mkdir()
            (root / "wiki" / "b.md").write_text("wiki\n", encoding="utf-8")
            (root / "drafts").mkdir()
            (root / "drafts" / "c.md").write_text("draft\n", encoding="utf-8")

            report = build_migration_report(tmp)
            rendered = render_migration_report(report)

            self.assertEqual(report["after"]["raw"], 1)
            self.assertEqual(report["after"]["wiki"], 1)
            self.assertEqual(report["after"]["drafts"], 1)
            self.assertIn("ABW Migrate", rendered)

    def test_migrate_creates_missing_config_schema_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()

            report = build_migration_report(tmp)
            config, status = read_workspace_config(tmp)

            self.assertIn(report["status"], {"migrated", "partially_migrated", "already_compatible"})
            self.assertEqual(status, "ok")
            self.assertEqual(config["workspace_schema"], 1)

    def test_upgrade_gives_mode_specific_guidance(self):
        with patch(
            "abw.upgrade.install_mode_details",
            return_value={"install_mode": "editable/dev", "source_path": "D:/src/abw", "direct_url": {}},
        ), patch(
            "abw.upgrade.build_version_report",
            return_value={
                "workspace": "D:/work",
                "package_version": "0.2.1",
                "install_mode": "editable/dev",
            },
        ):
            report = build_upgrade_report("D:/work")
            rendered = render_upgrade_report(report)

        self.assertEqual(report["install_mode"], "editable/dev")
        self.assertTrue(any("pip install -e" in command for command in report["commands"]))
        self.assertIn("abw doctor", "\n".join(report["commands"]))
        self.assertIn("ABW Upgrade", rendered)

    def test_workspace_isolation_holds_across_two_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_a = root / "project-a"
            project_b = root / "project-b"

            ensure_workspace(project_a)
            ensure_workspace(project_b)
            (project_a / "raw" / "a.md").write_text("a\n", encoding="utf-8")
            (project_b / "wiki" / "b.md").write_text("b\n", encoding="utf-8")

            doctor_a = build_doctor_report(project_a)
            doctor_b = build_doctor_report(project_b)

            self.assertNotEqual(doctor_a["workspace"], doctor_b["workspace"])
            self.assertEqual((project_a / "wiki").exists(), True)
            self.assertEqual((project_b / "raw").exists(), True)
            self.assertEqual((project_a / "wiki" / "b.md").exists(), False)


if __name__ == "__main__":
    unittest.main()
