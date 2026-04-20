import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_router  # noqa: E402


class AbwRouterTests(unittest.TestCase):
    def test_router_defaults_question_to_query(self):
        route = abw_router.route_request("What is ABW?", workspace=".")

        self.assertEqual(route["lane"], "query")
        self.assertEqual(route["intent"], "query")
        self.assertTrue(route["fallback_allowed"])

    def test_router_selects_query_deep_for_analysis_style_question(self):
        route = abw_router.route_request(
            "Compare PostgreSQL versus MongoDB tradeoffs for this architecture",
            workspace=".",
        )

        self.assertEqual(route["lane"], "query_deep")
        self.assertEqual(route["intent"], "query_deep")

    def test_router_preserves_legacy_execution_for_non_question_task(self):
        route = abw_router.route_request("print hello world", workspace=".")

        self.assertEqual(route["lane"], "legacy_execution")
        self.assertEqual(route["intent"], "legacy_execution")

    def test_router_selects_coverage_for_gap_report_intent(self):
        route = abw_router.route_request("show coverage report and top gaps", workspace=".")

        self.assertEqual(route["lane"], "coverage")
        self.assertEqual(route["intent"], "coverage")

    def test_router_uses_bootstrap_only_for_explicit_intent_or_repeated_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            route = abw_router.route_request("how does this work?", workspace=tmp)
            self.assertEqual(route["lane"], "query")

            gap_path = Path(tmp) / ".brain" / "knowledge_gaps.json"
            gap_path.parent.mkdir(parents=True, exist_ok=True)
            gap_path.write_text(
                json.dumps(
                    {
                        "gaps": [
                            {"id": "gap-1", "status": "open", "query": "how does this work?"},
                            {"id": "gap-2", "status": "open", "query": "how does this work?"},
                            {"id": "gap-3", "status": "open", "query": "other query"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            repeated_gap_route = abw_router.route_request("how does this work?", workspace=tmp)
            self.assertEqual(repeated_gap_route["lane"], "bootstrap")

    def test_route_logging_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            route = abw_router.route_request("What is ABW?", workspace=tmp)
            abw_router.log_route_decision(tmp, "What is ABW?", route)

            log_path = Path(tmp) / ".brain" / "route_log.jsonl"
            self.assertTrue(log_path.exists())
            rows = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 1)
            payload = json.loads(rows[0])
            self.assertEqual(payload["route"]["lane"], "query")


if __name__ == "__main__":
    unittest.main()
