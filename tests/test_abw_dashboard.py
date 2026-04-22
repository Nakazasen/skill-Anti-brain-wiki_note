import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_dashboard  # noqa: E402
import abw_version  # noqa: E402


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
            write(
                workspace / ".abw_version.json",
                json.dumps(
                    {
                        "commit": "file123",
                        "status": "stable",
                        "updated_at": "2026-04-21T00:00:00Z",
                    }
                ),
            )

            with patch.object(abw_version, "get_git_commit", return_value="file123"):
                result = abw_dashboard.run_dashboard(tmp)

            self.assertEqual(result["header"]["title"], "ABW Dashboard")
            self.assertEqual(result["version"]["commit"], "file123")
            self.assertEqual(result["version"]["deploy_status"], "ok")
            self.assertEqual(result["deploy"]["status"], "ok")
            self.assertEqual(result["knowledge"]["raw_files"], 1)
            self.assertEqual(result["knowledge"]["draft_files"], 1)
            self.assertEqual(result["knowledge"]["wiki_files"], 1)
            self.assertEqual(result["knowledge"]["pending_drafts"], 1)
            self.assertEqual(result["knowledge"]["coverage_ratio"], 0.5)
            self.assertEqual(result["top_gaps"], ["printer firmware", "network timeout"])
            self.assertEqual(result["next_actions"][0]["command"], "review drafts")
            self.assertIn("ABW Dashboard", result["rendered"])
            self.assertIn("Version:", result["rendered"])
            self.assertIn("deploy_status: ok", result["rendered"])
            self.assertIn("Next actions:", result["rendered"])
            self.assertIn("Guided wizard: wizard", result["rendered"])
            self.assertEqual(result["wizard"]["command"], "wizard")

    def test_dashboard_agent_mode_renders_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write(workspace / "wiki" / "source.md", "# Wiki\n")

            with patch.dict(os.environ, {"ABW_AGENT_MODE": "1"}):
                result = abw_dashboard.run_dashboard(tmp)

            self.assertIn("### ABW Dashboard", result["rendered"])
            self.assertIn("### Summary", result["rendered"])
            self.assertIn("### Answer", result["rendered"])
            self.assertIn("### Next Actions", result["rendered"])
            self.assertIn("- Raw files:", result["rendered"])
            self.assertIn("- Wiki files:", result["rendered"])
            self.assertIn("- wizard", result["rendered"])
            self.assertNotIn("Version:", result["rendered"])
            self.assertNotIn("deploy_status:", result["rendered"])
            self.assertNotIn("modules:", result["rendered"])
            self.assertNotIn("lanes:", result["rendered"])

    def test_dashboard_with_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_dashboard.run_dashboard(tmp)

            self.assertEqual(result["health"]["modules"], 0)
            self.assertEqual(result["health"]["lanes"], 0)
            self.assertEqual(result["knowledge"]["raw_files"], 0)
            self.assertEqual(result["knowledge"]["draft_files"], 0)
            self.assertEqual(result["knowledge"]["wiki_files"], 0)
            self.assertIn("version", result)
            self.assertIn(result["version"]["deploy_status"], {"unknown", "out_of_sync"})
            self.assertEqual([action["command"] for action in result["next_actions"]], ["help", "audit system"])
            self.assertEqual(result["top_gaps"], [])


if __name__ == "__main__":
    unittest.main()
