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
from abw import migrate as migrate_module  # noqa: E402
from abw.migrate import build_migration_report, render_migration_report  # noqa: E402
from abw.upgrade import build_upgrade_report, render_upgrade_report  # noqa: E402
from abw.version import build_version_report, render_version_report  # noqa: E402
from abw.version import release_match_state  # noqa: E402
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
            self.assertIn("release_match_state", report)
            self.assertIn("runtime_source", report)
            self.assertIn("runtime_source_path", report)
            self.assertIn("version_runtime_path", report)
            self.assertIn("mirror_status", report)
            self.assertIn("ABW Version", rendered)
            self.assertIn("release_match:", rendered)
            self.assertIn("version_runtime_path:", rendered)
            self.assertIn("runtime_source:", rendered)
            self.assertIn("mirror_status:", rendered)
            self.assertNotIn("validation_proof", rendered)

    def test_version_report_adds_self_check_hint_when_stale_install_suspected(self):
        report = {
            "package_version": "0.2.5",
            "git_tag": "unknown",
            "git_commit": "unknown",
            "release_match_state": "mismatched",
            "workspace": "D:/w",
            "install_mode": "pip package",
            "workspace_schema": "unknown",
            "python": "3.13",
            "runtime_source": "packaged_legacy",
            "runtime_source_path": "site-packages/abw/_legacy",
            "mirror_status": "mismatch",
            "mirror_mismatches": ["abw_entry.py"],
            "note": "Package version does not match the current tagged source.",
            "stale_install_suspected": True,
            "self_check_hint": "Run `abw self-check` to diagnose stale install/runtime path issues.",
        }
        rendered = render_version_report(report)
        self.assertIn("abw self-check", rendered)
        self.assertIn("py -m pip install -U .", rendered)

    def test_wheel_unknown_release_match_is_not_stale_by_default(self):
        report = {
            "package_version": "0.4.0",
            "git_tag": "unknown",
            "git_commit": "unknown",
            "release_match_state": "unknown",
            "release_verification_status": "unverified_wheel_release",
            "workspace": "D:/w",
            "install_mode": "pip package",
            "workspace_schema": "unknown",
            "python": "3.13",
            "runtime_source": "packaged_legacy",
            "runtime_source_path": "site-packages/abw/_legacy",
            "mirror_status": "not_checked",
            "mirror_mismatches": [],
            "note": "Wheel install detected. Package version is primary truth; git tag verification is unavailable.",
            "stale_install_suspected": False,
        }
        rendered = render_version_report(report)
        self.assertIn("release_verification: unverified_wheel_release", rendered)
        self.assertNotIn("abw self-check", rendered)

    def test_release_match_state_is_explicit(self):
        self.assertEqual(release_match_state("0.2.2", "v0.2.2"), "matched")
        self.assertEqual(release_match_state("0.2.2", "v0.2.1"), "mismatched")
        self.assertEqual(release_match_state("0.2.2", None), "unknown")

    def test_doctor_detects_missing_folders_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_doctor_report(tmp)
            rendered = render_doctor_report(report)

            self.assertEqual(report["overall"], "WARN")
            self.assertEqual(report["workspace_health"], "WARN")
            messages = [item["message"] for item in report["checks"]]
            self.assertIn("missing raw/", messages)
            self.assertIn("missing abw_config.json", messages)
            self.assertIn("ABW Doctor", rendered)
            self.assertIn("Workspace checks:", rendered)
            self.assertIn("Engine checks:", rendered)
            self.assertIn("runtime mirror status", rendered)
            self.assertNotIn("validation_proof", rendered)

    def test_doctor_reports_partial_supported_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ensure_workspace(root)
            (root / "raw" / "budget.xlsx").write_bytes(b"PK\x03\x04")
            (root / "raw" / "notes.docx").write_bytes(b"PK\x03\x04")

            report = build_doctor_report(root)
            rendered = render_doctor_report(report)

            self.assertEqual(report["corpus"]["classification"], "partial_supported_corpus")
            self.assertEqual(report["corpus"]["supported_source_counts"], {"xlsx": 1})
            self.assertEqual(report["corpus"]["unsupported_source_counts"], {"docx": 1})
            self.assertIn("corpus_readiness: partial_supported_corpus", rendered)
            self.assertIn("visible_extension_counts:", rendered)

    def test_doctor_detects_legacy_local_abw_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)
            (Path(tmp) / "abw").mkdir(parents=True, exist_ok=True)

            report = build_doctor_report(tmp)

            messages = [item["message"] for item in report["checks"]]
            self.assertIn("local legacy ABW engine detected at ./abw", messages)

    def test_doctor_runtime_mirror_clean_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)
            with patch("abw.doctor.build_version_report") as mock_version:
                mock_version.return_value = {
                    "package_version": "0.2.2",
                    "install_mode": "editable/dev",
                    "release_match_state": "matched",
                    "runtime_source": "packaged_legacy",
                    "runtime_source_path": "d:/x/src/abw/_legacy",
                    "mirror_status": "matched",
                    "mirror_mismatches": [],
                }
                report = build_doctor_report(tmp)
            self.assertIn(
                "runtime mirror status matched",
                [item["message"] for item in report["engine_checks"]],
            )

    def test_doctor_runtime_mirror_mismatch_is_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)
            with patch("abw.doctor.build_version_report") as mock_version:
                mock_version.return_value = {
                    "package_version": "0.2.2",
                    "install_mode": "editable/dev",
                    "release_match_state": "matched",
                    "runtime_source": "packaged_legacy",
                    "runtime_source_path": "d:/x/src/abw/_legacy",
                    "mirror_status": "mismatch",
                    "mirror_mismatches": ["abw_help.py"],
                    "stale_install_suspected": False,
                }
                report = build_doctor_report(tmp)
            self.assertIn(
                "runtime mirror mismatch: abw_help.py",
                [item["message"] for item in report["engine_checks"]],
            )

    def test_doctor_suggests_self_check_when_stale_install_suspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_workspace(tmp)
            with patch("abw.doctor.build_version_report") as mock_version:
                mock_version.return_value = {
                    "package_version": "0.2.5",
                    "install_mode": "pip package",
                    "release_match_state": "mismatched",
                    "runtime_source": "packaged_legacy",
                    "runtime_source_path": "site-packages/abw/_legacy",
                    "mirror_status": "mismatch",
                    "mirror_mismatches": ["abw_entry.py"],
                    "stale_install_suspected": True,
                }
                report = build_doctor_report(tmp)
            self.assertIn("run `abw self-check`", report["next_steps"])

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
            self.assertIn("git", report)
            self.assertIn("adoption_commit_scope", report)
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

    def test_migrate_warns_when_unrelated_dirty_files_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                migrate_module,
                "_git_status_summary",
                return_value={
                    "available": True,
                    "branch": "main",
                    "dirty_files": ["main.py", ".gitignore", "abw_config.json"],
                    "migration_scope_files": [".gitignore", "abw_config.json"],
                    "unrelated_dirty_files": ["main.py"],
                },
            ):
                report = build_migration_report(tmp)
                rendered = render_migration_report(report)
        self.assertIn("Repository has unrelated dirty files. Keep migration commit isolated.", report["warnings"])
        self.assertTrue(
            any("create branch `chore/abw-package-migration`" in step for step in report["next_steps"])
        )
        self.assertIn("commit only `.gitignore` and `abw_config.json`", report["next_steps"])
        self.assertIn("unrelated_dirty_files: main.py", rendered)

    def test_upgrade_gives_mode_specific_guidance(self):
        with patch(
            "abw.upgrade.install_mode_details",
            return_value={"install_mode": "editable/dev", "source_path": "D:/src/abw", "direct_url": {}},
        ), patch(
            "abw.upgrade.build_version_report",
            return_value={
                "workspace": "D:/work",
                "package_version": "0.2.2",
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
