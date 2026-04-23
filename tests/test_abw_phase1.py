import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.overview import build_overview  # noqa: E402
from abw.save import save_candidate  # noqa: E402


class AbwPhase1Tests(unittest.TestCase):
    def test_overview_works_on_empty_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_overview(tmp)

            self.assertEqual(result["relative_path"], "wiki/overview.md")
            overview_path = Path(tmp) / "wiki" / "overview.md"
            self.assertTrue(overview_path.exists())
            content = overview_path.read_text(encoding="utf-8")
            self.assertIn("# ABW Overview", content)
            self.assertIn("Trusted wiki file count: 0", content)
            self.assertIn("Raw file count: 0", content)
            self.assertIn("Suggested next actions", content)
            self.assertNotIn("validation_proof", content)
            self.assertNotIn("runtime_id", content)
            self.assertNotIn("nonce", content)

    def test_overview_reports_existing_workspace_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "wiki").mkdir(parents=True, exist_ok=True)
            (workspace / "wiki" / "printer.md").write_text("Printer module overview.\n", encoding="utf-8")
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            (workspace / "raw" / "notes.md").write_text("Raw notes.\n", encoding="utf-8")
            (workspace / "drafts").mkdir(parents=True, exist_ok=True)
            (workspace / "drafts" / "notes_draft.md").write_text("# Draft\n", encoding="utf-8")
            (workspace / ".brain").mkdir(parents=True, exist_ok=True)
            (workspace / ".brain" / "ingest_queue.json").write_text(
                '{"items": [{"status": "review_needed"}]}\n',
                encoding="utf-8",
            )

            result = build_overview(workspace)

            self.assertEqual(result["trusted_wiki_files"], 1)
            self.assertEqual(result["raw_files"], 1)
            self.assertEqual(result["draft_files"], 1)
            self.assertEqual(result["pending_reviews"], 1)

    def test_save_writes_candidate_note_without_touching_wiki(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "wiki").mkdir(parents=True, exist_ok=True)
            (workspace / "wiki" / "trusted.md").write_text("Trusted wiki stays unchanged.\n", encoding="utf-8")

            result = save_candidate("Remember the service owner list.", workspace)

            saved_path = workspace / result["relative_path"]
            self.assertTrue(saved_path.exists())
            content = saved_path.read_text(encoding="utf-8")
            self.assertIn("# Captured Note", content)
            self.assertIn("manual_save", content)
            self.assertIn("candidate_only", content)
            self.assertEqual((workspace / "wiki" / "trusted.md").read_text(encoding="utf-8"), "Trusted wiki stays unchanged.\n")


if __name__ == "__main__":
    unittest.main()
