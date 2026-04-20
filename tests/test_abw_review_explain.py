import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_ingest  # noqa: E402
import abw_review_explain  # noqa: E402


class AbwReviewExplainTests(unittest.TestCase):
    def make_workspace_with_draft(self, content):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        raw_file = workspace / "raw" / "orders.md"
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text(content, encoding="utf-8")
        ingest_result = abw_ingest.run("ingest raw/orders.md", str(workspace))
        return tmp, workspace, ingest_result

    def test_valid_draft_returns_explanation(self):
        content = """# Orders Table

This draft explains the orders table and the related troubleshooting query.

- table stores order events
- column order_id is the primary identifier
- example query helps triage timeout error

Example:
SELECT order_id FROM orders WHERE status = 'FAILED';
"""
        tmp, workspace, ingest_result = self.make_workspace_with_draft(content)
        with tmp:
            result = abw_review_explain.explain_draft(ingest_result["draft_file"], str(workspace))

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["draft"], ingest_result["draft_file"])
            self.assertIn("Draft overview:", result["summary"])
            self.assertIn("query", result["key_elements"])
            self.assertIn("error", result["key_elements"])
            self.assertEqual(result["domain"], "database")

    def test_invalid_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_review_explain.explain_draft("drafts/missing_draft.md", tmp)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("does not exist", result["reason"])

    def test_empty_draft_returns_low_confidence(self):
        tmp, workspace, ingest_result = self.make_workspace_with_draft("")
        with tmp:
            result = abw_review_explain.explain_draft(ingest_result["draft_file"], str(workspace))

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["confidence"], "low")
            self.assertIn("insufficient detail", result["missing"])

    def test_review_drafts_returns_multiple_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for name, content in {
                "orders.md": "# Orders\n\n- example\nSELECT * FROM orders;\n",
                "errors.md": "# Errors\n\n- timeout error details\n",
            }.items():
                raw_file = workspace / "raw" / name
                raw_file.parent.mkdir(parents=True, exist_ok=True)
                raw_file.write_text(content, encoding="utf-8")
                abw_ingest.run(f"ingest raw/{name}", str(workspace))

            result = abw_review_explain.review_drafts(str(workspace))

            self.assertEqual(len(result["items"]), 2)
            self.assertEqual({item["draft"] for item in result["items"]}, {"drafts/orders_draft.md", "drafts/errors_draft.md"})

    def test_review_drafts_handles_empty_drafts(self):
        tmp, workspace, _ = self.make_workspace_with_draft("")
        with tmp:
            result = abw_review_explain.review_drafts(str(workspace))

            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["items"][0]["confidence"], "low")
            self.assertEqual(result["items"][0]["suggestion"], "improve")

    def test_review_drafts_limits_to_top_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for index in range(6):
                name = f"draft-{index}.md"
                raw_file = workspace / "raw" / name
                raw_file.parent.mkdir(parents=True, exist_ok=True)
                raw_file.write_text(f"# Draft {index}\n\n- sample example\n", encoding="utf-8")
                abw_ingest.run(f"ingest raw/{name}", str(workspace))

            result = abw_review_explain.review_drafts(str(workspace))

            self.assertEqual(len(result["items"]), 5)

    def test_troubleshooting_domain_adds_resolution_gap(self):
        content = """# Printer Error

Timeout error appears during startup.

- error code E42
- failure repeats after reboot
"""
        tmp, workspace, ingest_result = self.make_workspace_with_draft(content)
        with tmp:
            result = abw_review_explain.explain_draft(ingest_result["draft_file"], str(workspace))

            self.assertEqual(result["domain"], "troubleshooting")
            self.assertIn("missing resolution step", result["missing"])


if __name__ == "__main__":
    unittest.main()
