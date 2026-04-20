import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_help  # noqa: E402


def commands(actions):
    return [action["command"] for action in actions]


class AbwHelpTests(unittest.TestCase):
    def test_empty_system_returns_state_based_help(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_help.run(tmp)

            self.assertEqual(result["state_snapshot"]["raw_files"], 0)
            self.assertEqual(result["state_snapshot"]["draft_files"], 0)
            self.assertEqual(result["state_snapshot"]["wiki_files"], 0)
            self.assertEqual(commands(result["next_actions"]), ["help", "audit system"])
            self.assertEqual([section["title"] for section in result["sections"]], [
                "Overview",
                "Next actions",
                "Situational guidance",
                "Minimal commands",
            ])
            self.assertTrue(result["sections"][2]["items"])

    def test_help_with_drafts_suggests_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "drafts").mkdir(parents=True, exist_ok=True)
            (workspace / "drafts" / "sample_draft.md").write_text("# Draft\n", encoding="utf-8")
            (workspace / ".brain").mkdir(parents=True, exist_ok=True)
            (workspace / ".brain" / "ingest_queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "draft": "drafts/sample_draft.md",
                                "status": "review_needed",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = abw_help.run(tmp)

            self.assertEqual(result["state_snapshot"]["draft_files"], 1)
            self.assertEqual(result["state_snapshot"]["pending_drafts"], 1)
            self.assertIn("review drafts", commands(result["next_actions"]))
            self.assertIn("review drafts", commands(result["sections"][1]["items"]))

    def test_help_with_low_coverage_suggests_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".brain").mkdir(parents=True, exist_ok=True)
            (workspace / ".brain" / "coverage_report.json").write_text(
                json.dumps({"coverage_ratio": 0.4}),
                encoding="utf-8",
            )

            result = abw_help.run(tmp)

            self.assertEqual(result["state_snapshot"]["coverage_ratio"], 0.4)
            self.assertIn("ingest more knowledge", commands(result["next_actions"]))
            self.assertTrue(
                any("Coverage" in item or "coverage" in item for item in result["sections"][2]["items"])
            )


if __name__ == "__main__":
    unittest.main()
