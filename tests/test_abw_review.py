import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_ingest  # noqa: E402
import abw_review  # noqa: E402


class AbwReviewTests(unittest.TestCase):
    def make_ingested_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        raw_file = workspace / "raw" / "latency-notes.md"
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text(
            "# Latency Notes\nQueue depth affects API latency.\n",
            encoding="utf-8",
        )
        ingest_result = abw_ingest.run("ingest raw/latency-notes.md", str(workspace))
        return tmp, workspace, ingest_result

    def test_approve_draft_promotes_to_wiki(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            result = abw_review.run(f"review {ingest_result['draft_file']}", str(workspace))

            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["draft"], ingest_result["draft_file"])
            self.assertEqual(result["wiki"], "wiki/latency-notes.md")
            self.assertEqual(result["message"], "Draft promoted to trusted wiki")

    def test_queue_updated_after_review(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            abw_review.run(f"review {ingest_result['draft_file']}", str(workspace))

            queue_path = workspace / ".brain" / "ingest_queue.json"
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["draft"], ingest_result["draft_file"])
            self.assertEqual(payload["items"][0]["status"], "approved")
            self.assertIn("approved_at", payload["items"][0])

    def test_file_moved_from_draft_to_wiki(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            draft_path = workspace / ingest_result["draft_file"]
            self.assertTrue(draft_path.exists())

            result = abw_review.run(f"review {ingest_result['draft_file']}", str(workspace))

            self.assertFalse(draft_path.exists())
            self.assertTrue((workspace / result["wiki"]).exists())

    def test_reject_invalid_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            invalid_draft = workspace / "drafts" / "missing_draft.md"
            invalid_draft.parent.mkdir(parents=True, exist_ok=True)
            invalid_draft.write_text("# Missing\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ingest_queue"):
                abw_review.run("review drafts/missing_draft.md", str(workspace))


if __name__ == "__main__":
    unittest.main()
