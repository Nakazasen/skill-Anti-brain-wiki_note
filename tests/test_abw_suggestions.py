import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_suggestions  # noqa: E402


def commands(actions):
    return [action["command"] for action in actions]


class AbwSuggestionsTests(unittest.TestCase):
    def test_drafts_exist_suggest_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / ".brain"
            brain.mkdir(parents=True, exist_ok=True)
            (brain / "ingest_queue.json").write_text(
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

            actions = abw_suggestions.suggest_next_actions(tmp)

            self.assertEqual(commands(actions), ["review drafts"])
            self.assertEqual(actions[0]["label"], "Duyệt các bản nháp")

    def test_low_coverage_suggests_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / ".brain"
            brain.mkdir(parents=True, exist_ok=True)
            (brain / "coverage_report.json").write_text(
                json.dumps({"coverage_ratio": 0.4}),
                encoding="utf-8",
            )

            actions = abw_suggestions.suggest_next_actions(tmp)

            self.assertEqual(commands(actions), ["ingest more knowledge"])

    def test_no_data_suggests_help_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            actions = abw_suggestions.suggest_next_actions(tmp)

            self.assertEqual(commands(actions), ["help", "audit system"])

    def test_raw_exists_without_drafts_suggests_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "sample.md").write_text("# Raw\n", encoding="utf-8")

            actions = abw_suggestions.suggest_next_actions(tmp)

            self.assertEqual(commands(actions), ["ingest raw/<file>"])

    def test_high_fail_rate_suggests_knowledge_improvement(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp) / ".brain"
            brain.mkdir(parents=True, exist_ok=True)
            rows = [
                {"result": {"status": "insufficient_evidence"}},
                {"result": {"status": "insufficient_evidence"}},
                {"result": {"status": "ok"}},
            ]
            (brain / "query_deep_runs.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )

            actions = abw_suggestions.suggest_next_actions(tmp)

            self.assertEqual(commands(actions), ["improve knowledge base"])

    def test_string_actions_remain_compatible(self):
        actions = abw_suggestions.normalize_next_actions(["help", {"command": "audit system"}])

        self.assertEqual(
            actions,
            [
                {"label": "Xem hướng dẫn", "command": "help"},
                {"label": "Audit hệ thống", "command": "audit system"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
