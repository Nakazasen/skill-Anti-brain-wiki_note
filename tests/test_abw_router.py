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

    def test_router_selects_help_intent(self):
        route = abw_router.route_request("help", workspace=".")

        self.assertEqual(route["lane"], "help")
        self.assertEqual(route["intent"], "help")

    def test_router_selects_dashboard_intent(self):
        route = abw_router.route_request("dashboard", workspace=".")

        self.assertEqual(route["lane"], "dashboard")
        self.assertEqual(route["intent"], "dashboard")

    def test_router_matches_vietnamese_help_without_exact_ascii(self):
        route = abw_router.route_request("trợ giúp", workspace=".")

        self.assertEqual(route["lane"], "help")
        self.assertEqual(route["intent"], "help")

    def test_router_selects_list_drafts_for_pending_drafts_intent(self):
        route = abw_router.route_request("list drafts", workspace=".")

        self.assertEqual(route["lane"], "list_drafts")
        self.assertEqual(route["intent"], "list_drafts")

    def test_router_selects_review_drafts_for_batch_review_intent(self):
        route = abw_router.route_request("review drafts", workspace=".")

        self.assertEqual(route["lane"], "review_drafts")
        self.assertEqual(route["intent"], "review_drafts")

    def test_router_selects_approve_draft_only_when_path_is_present(self):
        route = abw_router.route_request("approve draft drafts/example_draft.md", workspace=".")

        self.assertEqual(route["lane"], "approve_draft")
        self.assertEqual(route["intent"], "approve_draft")
        self.assertEqual(route["params"]["draft_path"], "drafts/example_draft.md")

    def test_router_selects_explain_draft_only_when_path_is_present(self):
        route = abw_router.route_request("explain draft drafts/example_draft.md", workspace=".")

        self.assertEqual(route["lane"], "explain_draft")
        self.assertEqual(route["intent"], "explain_draft")
        self.assertEqual(route["params"]["draft_path"], "drafts/example_draft.md")

    def test_router_falls_back_when_approve_draft_has_no_path(self):
        route = abw_router.route_request("approve draft", workspace=".")

        self.assertNotEqual(route["lane"], "approve_draft")
        self.assertEqual(route["lane"], "legacy_execution")

    def test_router_falls_back_when_explain_draft_has_no_path(self):
        route = abw_router.route_request("explain draft", workspace=".")

        self.assertNotEqual(route["lane"], "explain_draft")
        self.assertEqual(route["lane"], "query")

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
