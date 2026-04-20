import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_audit  # noqa: E402


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_jsonl(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class AbwAuditTests(unittest.TestCase):
    def make_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        write(
            workspace / "scripts" / "abw_runner.py",
            """
def execute_lane(task, workspace=".", route=None, binding_source="mcp"):
    handlers = {
        "query": lambda: None,
        "ingest": lambda: None,
        "review_drafts": lambda: None,
    }
    return handlers
""".strip(),
        )
        write(
            workspace / "scripts" / "abw_router.py",
            """
def route_request(task, workspace=".", route=None):
    if "help" in str(task or "").lower():
        return {"intent": "help", "lane": "help", "reason": "help", "fallback_allowed": True}
    if "review drafts" in str(task or "").lower():
        return {"intent": "review_drafts", "lane": "review_drafts", "reason": "batch", "fallback_allowed": True}
    return {"intent": "query", "lane": "query", "reason": "default", "fallback_allowed": True}
""".strip(),
        )
        write(
            workspace / "scripts" / "intent_matcher.py",
            """
INTENT_PATTERNS = [
    {"intent": "help", "lane": "help", "reason": "help"},
    {"intent": "review_drafts", "lane": "review_drafts", "reason": "batch"},
]
""".strip(),
        )
        write(workspace / "scripts" / "abw_ingest.py", "def run(task, workspace):\n    return {}\n")
        write(workspace / "scripts" / "abw_review.py", "def run(task, workspace):\n    return {}\n")
        return tmp, workspace

    def test_system_with_missing_modules(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            system_map = abw_audit.discover_system(str(workspace))

            self.assertIn("abw_runner.py", system_map["modules"])
            self.assertIn("query", system_map["lanes"])
            self.assertEqual(system_map["logs"], [])

    def test_system_with_new_lane_added(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            write(
                workspace / "scripts" / "abw_runner.py",
                """
def execute_lane(task, workspace=".", route=None, binding_source="mcp"):
    handlers = {
        "query": lambda: None,
        "audit": lambda: None,
        "ingest": lambda: None,
    }
    return handlers
""".strip(),
            )

            system_map = abw_audit.discover_system(str(workspace))

            self.assertIn("audit", system_map["lanes"])

    def test_system_with_partial_logs(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            append_jsonl(workspace / ".brain" / "route_log.jsonl", {"route": {"lane": "query"}})
            append_jsonl(
                workspace / ".brain" / "query_deep_runs.jsonl",
                {"result": {"status": "insufficient_evidence"}},
            )
            queue = {
                "items": [
                    {"draft": "drafts/a_draft.md", "status": "review_needed"},
                    {"draft": "drafts/b_draft.md", "status": "review_needed"},
                    {"draft": "drafts/c_draft.md", "status": "review_needed"},
                ]
            }
            write(workspace / ".brain" / "ingest_queue.json", json.dumps(queue, ensure_ascii=False))
            write(workspace / "raw" / ".gitkeep", "")
            write(workspace / "drafts" / "a_draft.md", "# A\n")

            system_map = abw_audit.discover_system(str(workspace))
            analysis = abw_audit.analyze_system(system_map, workspace=str(workspace))
            report = abw_audit.render_report(system_map, analysis)

            self.assertTrue(any(item["type"] == "review_bottleneck" for item in analysis["bottlenecks"]))
            self.assertTrue(any(item["type"] == "knowledge_gap" for item in analysis["bottlenecks"]))
            self.assertIn("📋 Audit toàn hệ ABW", report)
            self.assertIn("⚠️ Điểm nghẽn:", report)

    def test_discover_system_reads_intent_matcher_module(self):
        tmp, workspace = self.make_workspace()
        with tmp:
            system_map = abw_audit.discover_system(str(workspace))

            intents = {(item["lane"], item["intent"]) for item in system_map["intent_mapping"]}
            self.assertIn(("help", "help"), intents)
            self.assertIn(("review_drafts", "review_drafts"), intents)


if __name__ == "__main__":
    unittest.main()
