import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_dashboard  # noqa: E402


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class AbwDashboardTests(unittest.TestCase):
    def test_dashboard_with_full_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write(workspace / "scripts" / "abw_runner.py", "def execute_lane():\n    handlers = {'query': None}\n")
            write(workspace / "scripts" / "abw_router.py", "def route_request():\n    return {}\n")
            write(workspace / "raw" / "source.md", "# Raw\n")
            write(workspace / "drafts" / "source_draft.md", "# Draft\n")
            write(workspace / "wiki" / "source.md", "# Wiki\n")
            write(
                workspace / ".brain" / "ingest_queue.json",
                json.dumps(
                    {
                        "items": [
                            {
                                "draft": "drafts/source_draft.md",
                                "status": "review_needed",
                            }
                        ]
                    }
                ),
            )
            write(
                workspace / ".brain" / "coverage_report.json",
                json.dumps(
                    {
                        "coverage_ratio": 0.5,
                        "total_questions": 3,
                        "success": 1,
                        "weak": 1,
                        "fail": 1,
                        "top_gaps": ["printer firmware", "network timeout"],
                    }
                ),
            )

            result = abw_dashboard.run_dashboard(tmp)

            self.assertEqual(result["header"]["title"], "ABW Dashboard")
            self.assertEqual(result["knowledge"]["raw_files"], 1)
            self.assertEqual(result["knowledge"]["draft_files"], 1)
            self.assertEqual(result["knowledge"]["wiki_files"], 1)
            self.assertEqual(result["knowledge"]["pending_drafts"], 1)
            self.assertEqual(result["knowledge"]["coverage_ratio"], 0.5)
            self.assertEqual(result["top_gaps"], ["printer firmware", "network timeout"])
            self.assertEqual(result["next_actions"][0]["command"], "review drafts")
            self.assertIn("ABW Dashboard", result["rendered"])
            self.assertIn("Next actions:", result["rendered"])

    def test_dashboard_with_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_dashboard.run_dashboard(tmp)

            self.assertEqual(result["health"]["modules"], 0)
            self.assertEqual(result["health"]["lanes"], 0)
            self.assertEqual(result["knowledge"]["raw_files"], 0)
            self.assertEqual(result["knowledge"]["draft_files"], 0)
            self.assertEqual(result["knowledge"]["wiki_files"], 0)
            self.assertEqual([action["command"] for action in result["next_actions"]], ["help", "audit system"])
            self.assertEqual(result["top_gaps"], [])


if __name__ == "__main__":
    unittest.main()
