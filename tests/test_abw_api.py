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
from scripts import abw_ingest, abw_review  # noqa: E402
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

    def test_ask_marks_raw_only_sources_as_weak_evidence(self):
        result = {
            "answer": "Raw note says AGV dispatch uses MQTT.",
            "confidence": "high",
            "knowledge_evidence_tier": "E1_fallback",
            "knowledge_output": {
                "retrieval_status": "fuzzy_match",
                "source_summary": "raw_source",
            },
            "citations": [{"path": "raw/agv.md"}],
        }
        with tempfile.TemporaryDirectory() as tmp, patch("abw.api.run_ask", return_value=result):
            raw_file = Path(tmp) / "raw" / "agv.md"
            raw_file.parent.mkdir(parents=True)
            raw_file.write_text("AGV dispatch uses MQTT.", encoding="utf-8")
            response = self.client.post("/ask", json={"workspace": tmp, "query": "AGV dispatch"})
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["retrieval_status"], "raw_or_draft_only")
        self.assertLess(payload["data"]["trust_score"], 50)
        self.assertIn("raw or draft material", " ".join(payload["data"]["warnings"]))

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

    def test_specific_term_overlap_blocks_supplier_contract_overmatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki_file = root / "wiki" / "agv.md"
            wiki_file.parent.mkdir(parents=True)
            wiki_file.write_text(
                "# AGV Communication\nstatus: grounded\n\nAGV dispatch messages use MQTT.\nHeartbeat interval is 5 seconds.\n",
                encoding="utf-8",
            )

            protocol_matches = _search_wiki_contexts(
                "What protocol does the AGV use for dispatch messages?",
                workspace=root,
                limit=3,
            )
            supplier_matches = _search_wiki_contexts(
                "Who approved the AGV supplier contract?",
                workspace=root,
                limit=3,
            )

        self.assertEqual(protocol_matches[0]["path"], "wiki\\agv.md")
        self.assertEqual(protocol_matches[0]["retrieval_status"], "grounded")
        self.assertEqual(supplier_matches, [])

    def test_fact_specific_query_requires_multiple_fact_terms_for_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki_file = root / "wiki" / "agv.md"
            wiki_file.parent.mkdir(parents=True)
            wiki_file.write_text(
                "# AGV Vendor Note\nstatus: grounded\n\nAGV vendor onboarding uses MQTT dispatch integration.\n",
                encoding="utf-8",
            )

            matches = _search_wiki_contexts(
                "Who approved the AGV supplier contract?",
                workspace=root,
                limit=3,
            )

        self.assertEqual(matches, [])

    def test_draft_boilerplate_approval_words_do_not_trigger_fact_query_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft_file = root / "drafts" / "agv-manual_draft.md"
            draft_file.parent.mkdir(parents=True)
            draft_file.write_text(
                "# Draft Knowledge: agv_manual\n\n"
                "## Business Summary\n"
                "AGV communication uses MQTT for dispatch messages. "
                "The emergency stop signal must be verified before restart.\n\n"
                "## Trust Notice\n"
                "This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.\n",
                encoding="utf-8",
            )

            supplier_matches = _search_wiki_contexts(
                "Who approved the AGV supplier contract?",
                workspace=root,
                limit=3,
            )
            restart_matches = _search_wiki_contexts(
                "What signal must be verified before restart?",
                workspace=root,
                limit=3,
            )

        self.assertEqual(supplier_matches, [])
        self.assertEqual(restart_matches[0]["path"], "drafts\\agv-manual_draft.md")
        self.assertEqual(restart_matches[0]["source"], "draft_metadata")
        self.assertIn(restart_matches[0]["retrieval_status"], {"fuzzy_match", "exact_match"})

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

    def test_missing_source_control_question_does_not_match_control_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_file = root / "raw" / "missing_source_controls.md"
            raw_file.parent.mkdir(parents=True)
            raw_file.write_text(
                "# Missing Source Controls\n\n"
                "The following questions are intentionally absent from this corpus and must not be answered as grounded facts.\n\n"
                "## Absent controls\n"
                "- What is the internal IP for the pilot server?\n"
                "- What is the customer ticket ID for the forklift outage?\n\n"
                "## Expected behavior\n"
                "- Return no-match or unknown\n",
                encoding="utf-8",
            )

            matches = _search_wiki_contexts(
                "What is the internal IP for the pilot server?",
                workspace=root,
                limit=3,
            )

        self.assertEqual(matches, [])

    def test_explicit_unsupported_filename_blocks_unrelated_fallback_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir(parents=True)
            (raw / "troubleshooting_sync_warning.md").write_text(
                "# Troubleshooting Sync Warning\n\nAnswer shows weak evidence only.\n",
                encoding="utf-8",
            )
            brain = root / ".brain"
            brain.mkdir(parents=True)
            (brain / "ingest_report.json").write_text(
                '{\n'
                '  "unsupported_files": [{"path": "raw/unsupported_marker.xyz", "reason": "skipped_unsupported_extension"}],\n'
                '  "parse_errors": []\n'
                '}\n',
                encoding="utf-8",
            )

            matches = _search_wiki_contexts(
                "What does unsupported_marker.xyz say?",
                workspace=root,
                limit=3,
            )

        self.assertEqual(matches, [])

    def test_explicit_parse_error_filename_blocks_unrelated_fallback_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir(parents=True)
            (raw / "procedure_publish_checklist.md").write_text(
                "# Procedure Publish Checklist\n\nPrepare a sanitized pilot package.\n",
                encoding="utf-8",
            )
            brain = root / ".brain"
            brain.mkdir(parents=True)
            (brain / "ingest_report.json").write_text(
                '{\n'
                '  "unsupported_files": [],\n'
                '  "parse_errors": [{"path": "raw/malformed_placeholder.docx", "reason": "skipped_parse_error"}]\n'
                '}\n',
                encoding="utf-8",
            )

            matches = _search_wiki_contexts(
                "What procedure is stored in malformed_placeholder.docx?",
                workspace=root,
                limit=3,
            )

        self.assertEqual(matches, [])

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

    def test_approve_draft_endpoint_returns_preview_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "ops.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("# Ops\nQueue depth affects latency.\n", encoding="utf-8")
            ingest_result = abw_ingest.run("ingest raw/ops.md", str(workspace))
            draft_path = ingest_result["draft_file"]
            draft_hash = abw_review.compute_draft_hash(workspace / draft_path)

            response = self.client.post(
                "/approve-draft",
                json={
                    "workspace": tmp,
                    "draft_path": draft_path,
                    "draft_id": abw_review.draft_id_from_relpath(draft_path),
                    "expected_draft_hash": draft_hash,
                    "expected_queue_status": "review_needed",
                    "dry_run": True,
                },
            )
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "approve-draft")
        self.assertEqual(payload["data"]["status"], "preview_ready")
        self.assertEqual(payload["data"]["target_wiki_path"], "wiki/ops.md")
        self.assertFalse(payload["data"]["promotionPerformed"])

    def test_approve_draft_endpoint_apply_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "ops.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("# Ops\nQueue depth affects latency.\n", encoding="utf-8")
            ingest_result = abw_ingest.run("ingest raw/ops.md", str(workspace))
            draft_path = ingest_result["draft_file"]
            draft_hash = abw_review.compute_draft_hash(workspace / draft_path)
            draft_id = abw_review.draft_id_from_relpath(draft_path)

            response = self.client.post(
                "/approve-draft",
                json={
                    "workspace": tmp,
                    "draft_path": draft_path,
                    "draft_id": draft_id,
                    "expected_draft_hash": draft_hash,
                    "expected_queue_status": "review_needed",
                    "confirm": {
                        "user_confirmed": True,
                        "confirmation_token": abw_review.confirmation_token_for(draft_id, draft_hash),
                        "confirmation_text": abw_review.APPROVE_CONFIRMATION_TEXT,
                    },
                    "dry_run": False,
                },
            )
            payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["status"], "approved")
        self.assertTrue(payload["data"]["approved"])
        self.assertTrue(payload["data"]["promotionPerformed"])


if __name__ == "__main__":
    unittest.main()
