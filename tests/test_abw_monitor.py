import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_monitor  # noqa: E402


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class AbwMonitorTests(unittest.TestCase):
    def test_capture_snapshot_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write(workspace / "raw" / "source.md", "# Raw\n")
            write(
                workspace / ".brain" / "coverage_report.json",
                json.dumps({"coverage_ratio": 0.5, "fail": 2}),
            )
            write(
                workspace / ".brain" / "ingest_queue.json",
                json.dumps({"items": [{"status": "review_needed", "draft": "drafts/a.md"}]}),
            )

            with patch("abw_version.get_git_commit", return_value="git123"):
                snapshot = abw_monitor.capture_snapshot(tmp)

            self.assertEqual(snapshot["version"]["commit"], "git123")
            self.assertEqual(snapshot["files"]["raw"], 1)
            self.assertEqual(snapshot["coverage"]["coverage_ratio"], 0.5)
            self.assertEqual(snapshot["ingest"]["pending_drafts"], 1)
            rows = abw_monitor.read_snapshots(tmp)
            self.assertEqual(len(rows), 1)

    def test_trend_marks_coverage_up_and_fail_down_good(self):
        snapshots = [
            {
                "timestamp": "t1",
                "coverage": {"coverage_ratio": 0.4, "fail": 3},
                "ingest": {"pending_drafts": 2},
            },
            {
                "timestamp": "t2",
                "coverage": {"coverage_ratio": 0.7, "fail": 1},
                "ingest": {"pending_drafts": 2},
            },
        ]

        trend = abw_monitor.build_trend(snapshots)

        states = {item["metric"]: item["state"] for item in trend["changes"]}
        self.assertEqual(states["coverage_ratio"], "good")
        self.assertEqual(states["fail"], "good")
        self.assertEqual(trend["status"], "ok")

    def test_trend_marks_draft_increase_as_bottleneck(self):
        snapshots = [
            {
                "timestamp": "t1",
                "coverage": {"coverage_ratio": 0.5, "fail": 1},
                "ingest": {"pending_drafts": 1},
            },
            {
                "timestamp": "t2",
                "coverage": {"coverage_ratio": 0.5, "fail": 1},
                "ingest": {"pending_drafts": 4},
            },
        ]

        trend = abw_monitor.build_trend(snapshots)

        states = {item["metric"]: item["state"] for item in trend["changes"]}
        self.assertEqual(states["pending_drafts"], "warning")
        self.assertEqual(trend["status"], "watch")
        self.assertTrue(any("nghẽn review" in finding for finding in trend["findings"]))

    def test_run_trend_handles_insufficient_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("abw_version.get_git_commit", return_value=None):
                trend = abw_monitor.run_trend(tmp)

            self.assertEqual(trend["status"], "insufficient_history")
            self.assertEqual(trend["snapshot_count"], 1)
            self.assertIn("Need at least 2 snapshots", trend["summary"])


if __name__ == "__main__":
    unittest.main()
