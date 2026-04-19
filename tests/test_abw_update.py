import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_update  # noqa: E402


class AbwUpdateTests(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "scripts").mkdir(parents=True)
        (root / "tests").mkdir(parents=True)
        (root / "scripts" / "abw_runner.py").write_text("print('runner')\n", encoding="utf-8")
        (root / "scripts" / "abw_proof.py").write_text("print('proof')\n", encoding="utf-8")
        (root / "scripts" / "abw_output.py").write_text("print('output')\n", encoding="utf-8")
        return tmp, root

    def test_initialize_runtime_creates_version_file(self):
        tmp, root = self.make_repo()
        with tmp, patch("abw_update.git_rev_parse", return_value="abc123"):
            state = abw_update.initialize_runtime(root)
            self.assertEqual(state["version"]["commit"], "abc123")
            self.assertEqual(state["version"]["status"], "stable")
            self.assertTrue((root / ".abw_version.json").exists())

    def test_verify_runtime_integrity_reports_changed_hash(self):
        tmp, root = self.make_repo()
        with tmp:
            abw_update._RUNTIME_BASELINE[str(root.resolve())] = abw_update.current_integrity_snapshot(root)
            (root / "scripts" / "abw_runner.py").write_text("print('changed')\n", encoding="utf-8")
            result = abw_update.verify_runtime_integrity(root)

        self.assertEqual(result["state"], "integrity_compromised")
        self.assertIn("scripts/abw_runner.py", result["changed"])

    def test_perform_update_writes_version_and_log(self):
        tmp, root = self.make_repo()
        with tmp, patch("abw_update.acquire_update_lock"), patch("abw_update.release_update_lock"), patch(
            "abw_update.git_rev_parse",
            side_effect=["old111", "old111", "new222"],
        ), patch("abw_update.require_git_success"), patch(
            "abw_update.resolve_target",
            return_value=("origin/main", "new222"),
        ), patch("abw_update.prepare_staging_worktree", return_value=root), patch(
            "abw_update.verify_staging_integrity",
            return_value={"ran": True, "returncode": 0},
        ), patch("abw_update.create_backup_dir", return_value=root / ".abw_backup" / "ts"), patch(
            "abw_update.move_live_to_backup"
        ), patch("abw_update.move_staging_to_live"), patch("abw_update.cleanup_staging"), patch(
            "abw_update.finalize_git_state"
        ), patch("abw_update.reload_system_modules", return_value=["abw_runner"]):
            result = abw_update.perform_update(workspace=root)

            version_payload = json.loads((root / ".abw_version.json").read_text(encoding="utf-8"))
            update_log = (root / ".brain" / "update_log.jsonl").read_text(encoding="utf-8")

        self.assertEqual(result["task"], "/abw-update")
        self.assertEqual(result["current_state"], "verified")
        self.assertEqual(result["update"]["current_version"], "old111")
        self.assertEqual(result["update"]["target_version"], "new222")
        self.assertEqual(result["update"]["update_result"], "success")
        self.assertEqual(version_payload["commit"], "new222")
        self.assertEqual(version_payload["status"], "stable")
        self.assertIn('"status": "success"', update_log)

    def test_perform_update_rolls_back_on_failure(self):
        tmp, root = self.make_repo()
        backup_dir = root / ".abw_backup" / "ts"
        (backup_dir / "live").mkdir(parents=True, exist_ok=True)
        with tmp, patch("abw_update.acquire_update_lock"), patch("abw_update.release_update_lock"), patch(
            "abw_update.git_rev_parse",
            side_effect=["old111"],
        ), patch("abw_update.require_git_success"), patch(
            "abw_update.resolve_target",
            return_value=("origin/main", "new222"),
        ), patch("abw_update.prepare_staging_worktree", return_value=root), patch(
            "abw_update.verify_staging_integrity",
            side_effect=RuntimeError("staging tests failed"),
        ), patch("abw_update.create_backup_dir", return_value=backup_dir), patch(
            "abw_update.restore_backup"
        ), patch("abw_update.finalize_git_state"), patch("abw_update.cleanup_staging"):
            result = abw_update.perform_update(workspace=root)
            update_log = (root / ".brain" / "update_log.jsonl").read_text(encoding="utf-8")

        self.assertEqual(result["current_state"], "blocked")
        self.assertIn(result["update"]["update_result"], {"rollback", "failed"})
        self.assertIn('"status": "failed"', update_log)

    def test_perform_rollback_restores_last_backup(self):
        tmp, root = self.make_repo()
        backup_dir = root / ".abw_backup" / "2026-04-19T22-00-00Z"
        (backup_dir / "live").mkdir(parents=True, exist_ok=True)
        (backup_dir / "manifest.json").write_text(
            json.dumps({"from_commit": "old111", "to_commit": "new222"}, ensure_ascii=False),
            encoding="utf-8",
        )
        with tmp, patch("abw_update.acquire_update_lock"), patch("abw_update.release_update_lock"), patch(
            "abw_update.git_rev_parse",
            return_value="new222",
        ), patch("abw_update.restore_backup"), patch("abw_update.finalize_git_state"), patch(
            "abw_update.reload_system_modules",
            return_value=["abw_runner"],
        ):
            result = abw_update.perform_rollback(workspace=root)

        self.assertEqual(result["task"], "/abw-rollback")
        self.assertEqual(result["current_state"], "verified")
        self.assertEqual(result["update"]["target_version"], "old111")
        self.assertEqual(result["update"]["update_result"], "rollback")

    def test_prepare_staging_worktree_and_cleanup_use_real_git_worktree(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        with tmp:
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
            (root / "scripts").mkdir(parents=True)
            (root / "scripts" / "abw_runner.py").write_text("print('v1')\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            (root / "scripts" / "abw_runner.py").write_text("print('v2')\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "v2"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            target_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            stage = abw_update.prepare_staging_worktree(root, target_commit)
            self.assertTrue(stage.exists())
            self.assertEqual(
                (stage / "scripts" / "abw_runner.py").read_text(encoding="utf-8").strip(),
                "print('v2')",
            )

            abw_update.cleanup_staging(root)
            self.assertFalse(stage.exists())


if __name__ == "__main__":
    unittest.main()
