import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_ingest  # noqa: E402


class AbwIngestTests(unittest.TestCase):
    def test_raw_file_ingest_creates_draft_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "printer-notes.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "# Printer Notes\nDrum unit handles image transfer.\nToner cartridge feeds toner.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/printer-notes.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertEqual(result["raw_file"], "raw/printer-notes.md")
            self.assertTrue((workspace / result["draft_file"]).exists())
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 1)
            manifest_row = json.loads(manifest[0])
            self.assertEqual(manifest_row["source"], "raw/printer-notes.md")
            self.assertEqual(manifest_row["status"], "processed")

    def test_queue_updated_after_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "api.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("API latency depends on queue depth.\n", encoding="utf-8")

            result = abw_ingest.run("process raw/api.md", str(workspace))

            queue_path = workspace / ".brain" / "ingest_queue.json"
            self.assertTrue(queue_path.exists())
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["raw"], "raw/api.md")
            self.assertEqual(payload["items"][0]["draft"], result["draft_file"])
            self.assertEqual(payload["items"][0]["status"], "review_needed")

    def test_ingest_does_not_write_wiki(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "network.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("Network retry strategy.\n", encoding="utf-8")

            abw_ingest.run("review raw/network.md", str(workspace))

            wiki_root = workspace / "wiki"
            self.assertFalse(wiki_root.exists() and any(wiki_root.rglob("*.md")))

    def test_ingest_with_conflict_creates_conflict_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "feature-flags.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("Feature X is disabled in version 2.\n", encoding="utf-8")
            wiki_file = workspace / "wiki" / "feature-flags.md"
            wiki_file.parent.mkdir(parents=True, exist_ok=True)
            wiki_file.write_text("Feature X is enabled in version 1.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/feature-flags.md", str(workspace))

            self.assertEqual(result["conflict_count"], 1)
            self.assertEqual(len(result["conflict_reports"]), 1)
            report_path = workspace / result["conflict_reports"][0]
            self.assertTrue(report_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Potential Contradiction", report)
            self.assertIn("review_required", report)
            self.assertIn("wiki/feature-flags.md", report)

    def test_ingest_without_conflict_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "printer-notes.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("The printer drum handles image transfer.\n", encoding="utf-8")
            wiki_file = workspace / "wiki" / "device-summary.md"
            wiki_file.parent.mkdir(parents=True, exist_ok=True)
            wiki_file.write_text("The scanner lamp needs calibration.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/printer-notes.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertEqual(result["conflict_count"], 0)
            self.assertEqual(result["conflict_reports"], [])
            self.assertFalse((workspace / "drafts" / "conflicts").exists())


if __name__ == "__main__":
    unittest.main()
