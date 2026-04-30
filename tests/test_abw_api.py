import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from abw.api import app  # noqa: E402
from scripts.abw_knowledge import _search_wiki_contexts  # noqa: E402


EXPECTED_VERSION = "1.1.0"


class AbwApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_stable_envelope(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "health")
        self.assertEqual(payload["version"], EXPECTED_VERSION)
        self.assertEqual(payload["data"]["status"], "ok")

    def test_report_endpoints_return_stable_envelope(self):
        endpoints = {
            "/inspect": ("inspect", "build_inspect_report"),
            "/gaps": ("gaps", "build_gap_report"),
            "/recover-plan": ("recover-plan", "build_recovery_report"),
            "/recover-verify": ("recover-verify", "build_verify_report"),
            "/trend": ("trend", "build_trend_report"),
            "/improve": ("improve", "build_improvement_plan"),
            "/workspace-intel": ("workspace-intel", "build_workspace_intel_report"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for endpoint, (command, builder_name) in endpoints.items():
                with self.subTest(endpoint=endpoint), patch(f"abw.api.{builder_name}", return_value={"marker": command}):
                    response = self.client.post(endpoint, json={"workspace": tmp})
                    payload = response.json()

                self.assertEqual(response.status_code, 200)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["command"], command)
                self.assertEqual(payload["version"], EXPECTED_VERSION)
                self.assertEqual(payload["data"], {"marker": command})

    def test_ask_returns_normalized_native_response(self):
        result = {
            "answer": "AGV issue summary",
            "route": {"lane": "query"},
            "confidence": "high",
            "evidence": ["wiki/agv.md"],
            "warnings": ["grounded locally"],
        }
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.run_ask", return_value=result) as ask_mock:
            wiki_file = Path(tmp) / "wiki" / "agv.md"
            wiki_file.parent.mkdir(parents=True)
            wiki_file.write_text("# AGV\nstatus: grounded\n\nAGV issue summary", encoding="utf-8")
            response = self.client.post("/ask", json={"workspace": tmp, "query": "AGV communication issue"})
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "ask")
        self.assertEqual(payload["version"], EXPECTED_VERSION)
        self.assertEqual(payload["data"]["answer"], "AGV issue summary")
        self.assertEqual(payload["data"]["retrieval_status"], "fuzzy_match")
        self.assertEqual(
            payload["data"]["sources"],
            [{"path": "wiki/agv.md", "title": "agv", "snippet": "", "confidence": 65}],
        )
        self.assertGreaterEqual(payload["data"]["trust_score"], 70)
        self.assertEqual(payload["data"]["warnings"], ["grounded locally"])
        self.assertEqual(payload["data"]["logs"], ["grounded locally"])
        self.assertEqual(payload["data"]["meta"]["route"], {"lane": "query"})
        ask_mock.assert_called_once_with("AGV communication issue", workspace=str(Path(tmp).resolve()))

    def test_ask_marks_no_sources_as_low_confidence(self):
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.run_ask", return_value={"answer": "Maybe", "confidence": "high"}):
            response = self.client.post("/ask", json={"workspace": tmp, "query": "unknown"})
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["sources"], [])
        self.assertEqual(payload["data"]["retrieval_status"], "no_match")
        self.assertEqual(payload["data"]["trust_score"], 0)
        self.assertTrue(payload["data"]["answer"])
        self.assertIn("No supporting sources", " ".join(payload["data"]["warnings"]))

    def test_ask_filters_synthetic_sources_and_guards_no_match_answer(self):
        result = {
            "answer": "noise",
            "confidence": 0,
            "retrieval_status": "no_match",
            "sources": [
                {"path": "router", "title": "router"},
                {"path": "trusted", "title": "trusted"},
                {"path": "none", "title": "none"},
                {"path": "wiki/agv.md", "title": "agv"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.run_ask", return_value=result):
            wiki_file = Path(tmp) / "wiki" / "agv.md"
            wiki_file.parent.mkdir(parents=True)
            wiki_file.write_text("# AGV\nstatus: grounded\n\nAGV issue summary", encoding="utf-8")
            response = self.client.post("/ask", json={"workspace": tmp, "query": "AGV lﾃ gﾃｬ?"})
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["retrieval_status"], "no_match")
        self.assertEqual(payload["data"]["trust_score"], 0)
        self.assertEqual(
            payload["data"]["sources"],
            [{"path": "wiki/agv.md", "title": "agv", "snippet": "", "confidence": 65}],
        )

    def test_root_level_wiki_file_is_retrievable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki_file = root / "wiki" / "agv.md"
            wiki_file.parent.mkdir(parents=True)
            wiki_file.write_text("# AGV Communication\nstatus: grounded\n\nAGV communication protocol over UDP.", encoding="utf-8")

            matches = _search_wiki_contexts("AGV communication protocol", workspace=root, limit=3)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["path"], "wiki\\agv.md")

    def test_missing_non_wiki_sources_do_not_get_medium_trust(self):
        result = {
            "answer": "noise",
            "sources": [
                {"path": "raw/missing.txt"},
                {"path": "drafts/missing.md"},
                {"path": "processed/missing.md"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.run_ask", return_value=result):
            response = self.client.post("/ask", json={"workspace": tmp, "query": "AGV communication issue"})
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["sources"], [])
        self.assertEqual(payload["data"]["retrieval_status"], "no_match")
        self.assertEqual(payload["data"]["trust_score"], 0)

    def test_quarantine_source_is_filtered(self):
        result = {
            "answer": "noise",
            "sources": [{"path": "processed/quarantine/bad.md"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            quarantine_file = Path(tmp) / "processed" / "quarantine" / "bad.md"
            quarantine_file.parent.mkdir(parents=True)
            quarantine_file.write_text("bad", encoding="utf-8")
            with patch("abw.api.run_ask", return_value=result):
                response = self.client.post("/ask", json={"workspace": tmp, "query": "AGV communication issue"})
                payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["sources"], [])
        self.assertEqual(payload["data"]["retrieval_status"], "no_match")

    def test_ask_requires_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = self.client.post("/ask", json={"workspace": tmp})

        self.assertEqual(response.status_code, 400)
        self.assertIn("query is required", response.text)

    def test_workspace_fix_previews_auto_fix(self):
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.run_workspace_fix", return_value={"issue_type": "stale_drafts", "dry_run": True}) as fix_mock:
            response = self.client.post("/workspace-fix", json={"workspace": tmp, "issue_type": "stale_drafts", "dry_run": True})
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "workspace-fix")
        self.assertEqual(payload["version"], EXPECTED_VERSION)
        self.assertEqual(payload["data"], {"issue_type": "stale_drafts", "dry_run": True})
        fix_mock.assert_called_once_with(Path(tmp).resolve(), "stale_drafts", dry_run=True)

    def test_workspace_fix_requires_issue_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = self.client.post("/workspace-fix", json={"workspace": tmp})

        self.assertEqual(response.status_code, 400)
        self.assertIn("issue_type is required", response.text)

    def test_apply_defaults_to_safe_dry_run_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = root / "drafts" / "note.md"
            draft.parent.mkdir(parents=True)
            draft.write_text("draft", encoding="utf-8")

            response = self.client.post("/apply", json={"workspace": tmp})
            payload = response.json()

            self.assertEqual(response.status_code, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["command"], "apply")
            self.assertEqual(payload["version"], EXPECTED_VERSION)
            self.assertEqual(payload["data"]["action"], "cleanup-drafts")
            self.assertEqual(payload["data"]["mode"], "dry-run")
            self.assertTrue(draft.exists())

    def test_missing_workspace_returns_400(self):
        response = self.client.post("/inspect", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("workspace is required", response.text)

    def test_internal_error_returns_500(self):
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.build_inspect_report", side_effect=RuntimeError("boom")):
            response = self.client.post("/inspect", json={"workspace": tmp})

        self.assertEqual(response.status_code, 500)
        self.assertIn("boom", response.text)

    def test_unknown_apply_action_returns_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = self.client.post("/apply", json={"workspace": tmp, "action": "unknown"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("unknown apply action", response.text)


if __name__ == "__main__":
    unittest.main()
