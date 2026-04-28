import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw import upgrade as upgrade_module  # noqa: E402


class AbwUpgradeCommandTests(unittest.TestCase):
    def _create_workspace(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for dirname in ("raw", "wiki", "drafts", "processed", ".brain"):
            (root / dirname).mkdir(parents=True, exist_ok=True)
            (root / dirname / "seed.txt").write_text(f"{dirname}\n", encoding="utf-8")
        (root / "abw_config.json").write_text(
            json.dumps({"workspace_schema": 1, "project_name": "demo"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return root

    def test_upgrade_preserves_workspace_files(self):
        workspace = self._create_workspace()
        with patch.object(
            upgrade_module,
            "_resolve_target",
            return_value={
                "status": "ok",
                "target_version": "0.3.0",
                "install_spec": "abw-skill==0.3.0",
                "source": "release",
                "local_wheels": [],
            },
        ), patch.object(
            upgrade_module,
            "_install_package",
            return_value={"args": [], "returncode": 0, "stdout": "ok", "stderr": ""},
        ), patch.object(
            upgrade_module,
            "_run_health_checks",
            return_value=[
                {"command": "abw version", "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
                {"command": "abw doctor", "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
                {"command": 'abw ask "dashboard"', "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
            ],
        ), patch.object(upgrade_module, "_installed_distribution_version", side_effect=["0.2.9", "0.3.0"]):
            result = upgrade_module.perform_upgrade(workspace, channel="stable")

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["data_preserved"])
        self.assertTrue((workspace / "raw" / "seed.txt").exists())
        self.assertTrue((workspace / "wiki" / "seed.txt").exists())
        self.assertTrue((workspace / "drafts" / "seed.txt").exists())
        self.assertTrue((workspace / "processed" / "seed.txt").exists())
        self.assertTrue((workspace / ".brain" / "seed.txt").exists())

    def test_upgrade_rollback_uses_last_backup(self):
        workspace = self._create_workspace()
        backup_dir = workspace / ".brain" / "upgrade_backups" / "20260425T070000Z"
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "operation": "upgrade",
                    "previous_version": "0.2.8",
                    "target_version": "0.2.9",
                    "install_spec": "abw-skill==0.2.9",
                    "rollback_spec": "abw-skill==0.2.8",
                    "channel": "stable",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (workspace / ".brain" / "upgrade_backups" / "latest.json").write_text(
            json.dumps({"backup_dir": str(backup_dir)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with patch.object(
            upgrade_module,
            "_install_package",
            return_value={"args": [], "returncode": 0, "stdout": "ok", "stderr": ""},
        ) as install_mock, patch.object(
            upgrade_module,
            "_run_health_checks",
            return_value=[
                {"command": "abw version", "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
                {"command": "abw doctor", "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
                {"command": 'abw ask "dashboard"', "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
            ],
        ), patch.object(upgrade_module, "_installed_distribution_version", side_effect=["0.2.9", "0.2.8"]):
            result = upgrade_module.perform_upgrade(workspace, rollback=True, channel="stable")

        self.assertEqual(result["operation"], "rollback")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["target_version"], "0.2.8")
        install_mock.assert_called_once()
        self.assertEqual(install_mock.call_args.kwargs["channel"], "stable")

    def test_upgrade_reports_version_change(self):
        workspace = self._create_workspace()
        with patch.object(
            upgrade_module,
            "_resolve_target",
            return_value={
                "status": "ok",
                "target_version": "0.3.0",
                "install_spec": "abw-skill==0.3.0",
                "source": "release",
                "local_wheels": [],
            },
        ), patch.object(
            upgrade_module,
            "_install_package",
            return_value={"args": [], "returncode": 0, "stdout": "ok", "stderr": ""},
        ), patch.object(
            upgrade_module,
            "_run_health_checks",
            return_value=[
                {"command": "abw version", "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
                {"command": "abw doctor", "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
                {"command": 'abw ask "dashboard"', "returncode": 0, "ok": True, "stdout": "", "stderr": ""},
            ],
        ), patch.object(upgrade_module, "_installed_distribution_version", side_effect=["0.2.9", "0.3.0"]):
            result = upgrade_module.perform_upgrade(workspace, channel="stable")

        self.assertEqual(result["package_version_before"], "0.2.9")
        self.assertEqual(result["package_version_after"], "0.3.0")
        self.assertTrue(result["installed_change"])
        metadata = json.loads((workspace / ".brain" / "release_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["package_version"], "0.3.0")
        self.assertEqual(metadata["previous_version"], "0.2.9")
        self.assertIn("install_timestamp", metadata)


if __name__ == "__main__":
    unittest.main()
