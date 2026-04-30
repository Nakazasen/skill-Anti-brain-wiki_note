import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.apply import run_apply, run_rollback


class AbwApplyTests(unittest.TestCase):
    def test_cleanup_drafts_dry_run_logs_plan_without_archiving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = root / "drafts" / "note.md"
            draft.parent.mkdir(parents=True)
            draft.write_text("draft", encoding="utf-8")

            report = run_apply(root, "cleanup-drafts")

            self.assertEqual(report["mode"], "dry-run")
            self.assertEqual(report["files_affected_count"], 1)
            self.assertEqual(report["risk_level"], "low")
            self.assertTrue(report["rollback_possible"])
            self.assertTrue(draft.exists())
            self.assertTrue(Path(report["log_path"]).exists())
            self.assertEqual(json.loads(Path(report["log_path"]).read_text(encoding="utf-8"))["action"], "cleanup-drafts")

    def test_cleanup_drafts_apply_archives_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = root / "drafts" / "note.md"
            draft.parent.mkdir(parents=True)
            draft.write_text("draft", encoding="utf-8")

            report = run_apply(root, "cleanup-drafts", yes=True)

            self.assertFalse(draft.exists())
            archived = root / report["changes_applied"][0]["target"]
            self.assertTrue(archived.exists())
            self.assertEqual(archived.read_text(encoding="utf-8"), "draft")
            self.assertIn("rollback", report["rollback_command"])

            rollback = run_rollback(root, report["action_id"], yes=True)

            self.assertEqual(rollback["changes_applied_count"], 1)
            self.assertTrue(draft.exists())
            self.assertEqual(draft.read_text(encoding="utf-8"), "draft")

    def test_rebuild_wiki_backs_up_existing_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "source.txt"
            raw.parent.mkdir(parents=True)
            raw.write_text("source", encoding="utf-8")
            index = root / "wiki" / "_abw_source_index.md"
            index.parent.mkdir(parents=True)
            index.write_text("old index", encoding="utf-8")

            report = run_apply(root, "rebuild-wiki", yes=True)

            self.assertIn("raw/source.txt", index.read_text(encoding="utf-8"))
            backup = root / report["changes_applied"][0]["backup"]
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), "old index")

            run_rollback(root, report["action_id"], yes=True)
            self.assertEqual(index.read_text(encoding="utf-8"), "old index")

    def test_archive_stale_only_moves_old_processed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_file = root / "processed" / "old.txt"
            new_file = root / "processed" / "new.txt"
            old_file.parent.mkdir(parents=True)
            old_file.write_text("old", encoding="utf-8")
            new_file.write_text("new", encoding="utf-8")
            old_time = time.time() - 31 * 24 * 60 * 60
            old_file.touch()
            new_file.touch()
            os.utime(old_file, (old_time, old_time))

            report = run_apply(root, "archive-stale", yes=True)

            self.assertEqual(report["files_affected"], ["processed/old.txt"])
            self.assertFalse(old_file.exists())
            self.assertTrue(new_file.exists())
            self.assertTrue((root / report["changes_applied"][0]["target"]).exists())


if __name__ == "__main__":
    unittest.main()
