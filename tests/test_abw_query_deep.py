import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_query_deep  # noqa: E402


class AbwQueryDeepTests(unittest.TestCase):
    def test_run_returns_wiki_backed_answer_and_logs_run(self):
        result = abw_query_deep.run(
            "Compare PostgreSQL selection rationale and PostgreSQL evaluation",
            workspace=str(REPO_ROOT),
        )

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["sources"])
        self.assertTrue(result["evidence"])
        self.assertLessEqual(len(result["reasoning_steps"][0]["subquestions"]), 5)
        log_path = REPO_ROOT / ".brain" / "query_deep_runs.jsonl"
        self.assertTrue(log_path.exists())
        last_row = log_path.read_text(encoding="utf-8").splitlines()[-1]
        payload = json.loads(last_row)
        self.assertEqual(payload["result"]["status"], "ok")

    def test_run_reports_insufficient_evidence_when_wiki_has_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "wiki" / "concepts").mkdir(parents=True)
            result = abw_query_deep.run(
                "unknown impossible topic for deep reasoning",
                workspace=str(workspace),
            )

            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertEqual(result["sources"], [])
            self.assertEqual(result["confidence"], "low")
            self.assertFalse(result["deep_run_log_suppressed"])
            self.assertTrue((workspace / ".brain" / "query_deep_runs.jsonl").exists())

    def test_read_only_query_mode_suppresses_deep_run_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "wiki" / "concepts").mkdir(parents=True)

            with patch.dict(os.environ, {"ABW_READ_ONLY_QUERY": "1"}, clear=False):
                result = abw_query_deep.run(
                    "unknown impossible topic for deep reasoning",
                    workspace=str(workspace),
                )

            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertTrue(result["deep_run_log_suppressed"])
            self.assertFalse((workspace / ".brain" / "query_deep_runs.jsonl").exists())

    def test_read_only_query_mode_does_not_change_existing_deep_run_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            brain = workspace / ".brain"
            brain.mkdir(parents=True)
            log_path = brain / "query_deep_runs.jsonl"
            original = json.dumps({"existing": True}, sort_keys=True) + "\n"
            log_path.write_text(original, encoding="utf-8")
            (workspace / "wiki" / "concepts").mkdir(parents=True)

            with patch.dict(os.environ, {"ABW_READ_ONLY_QUERY": "1"}, clear=False):
                result = abw_query_deep.run(
                    "unknown impossible topic for deep reasoning",
                    workspace=str(workspace),
                )

            self.assertTrue(result["deep_run_log_suppressed"])
            self.assertEqual(log_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
