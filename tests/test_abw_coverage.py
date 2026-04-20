import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_coverage  # noqa: E402


def append_jsonl(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


class AbwCoverageTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
        (workspace / "wiki" / "concepts" / "postgres.md").write_text("# PostgreSQL\n", encoding="utf-8")
        (workspace / "wiki" / "entities").mkdir(parents=True, exist_ok=True)
        (workspace / "wiki" / "entities" / "printer.md").write_text("# Printer\n", encoding="utf-8")
        return tmp, workspace

    def test_log_parsing_and_coverage_ratio(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            log_path = workspace / ".brain" / "query_deep_runs.jsonl"
            append_jsonl(
                log_path,
                {"task": "compare postgres", "result": {"confidence": "high", "status": "ok"}},
            )
            append_jsonl(
                log_path,
                {"task": "compare mongo", "result": {"confidence": "low", "status": "ok"}},
            )
            append_jsonl(
                log_path,
                {"task": "unknown printer firmware", "result": {"confidence": "low", "status": "insufficient_evidence"}},
            )

            report = abw_coverage.run_coverage(str(workspace))

            self.assertEqual(report["total_questions"], 3)
            self.assertEqual(report["success"], 1)
            self.assertEqual(report["weak"], 1)
            self.assertEqual(report["fail"], 1)
            self.assertAlmostEqual(report["coverage_ratio"], 1 / 3, places=4)

    def test_gap_detection_groups_failed_tasks(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            log_path = workspace / ".brain" / "query_deep_runs.jsonl"
            append_jsonl(
                log_path,
                {"task": "unknown printer firmware issue", "result": {"confidence": "low", "status": "insufficient_evidence"}},
            )
            append_jsonl(
                log_path,
                {"task": "unknown printer firmware crash", "result": {"confidence": "low", "status": "insufficient_evidence"}},
            )
            append_jsonl(
                log_path,
                {"task": "unknown network timeout", "result": {"confidence": "low", "status": "insufficient_evidence"}},
            )

            report = abw_coverage.run_coverage(str(workspace))

            self.assertTrue(report["top_gaps"])
            self.assertIn("firmware", report["top_gaps"][0]["topic"])

    def test_report_saved_to_brain(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            report = abw_coverage.run_coverage(str(workspace))
            saved_path = workspace / ".brain" / "coverage_report.json"
            self.assertTrue(saved_path.exists())
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["wiki_topic_count"], report["wiki_topic_count"])


if __name__ == "__main__":
    unittest.main()
