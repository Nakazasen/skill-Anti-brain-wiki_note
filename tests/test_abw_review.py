import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_ingest  # noqa: E402
import abw_review  # noqa: E402


class AbwReviewTests(unittest.TestCase):
    def make_ingested_workspace(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        raw_file = workspace / "raw" / "latency-notes.md"
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text(
            "# Latency Notes\nQueue depth affects API latency.\n",
            encoding="utf-8",
        )
        ingest_result = abw_ingest.run("ingest raw/latency-notes.md", str(workspace))
        return tmp, workspace, ingest_result

    def build_contract_request(self, workspace, ingest_result, **overrides):
        draft_path = ingest_result["draft_file"]
        draft_hash = abw_review.compute_draft_hash(workspace / draft_path)
        draft_id = abw_review.draft_id_from_relpath(draft_path)
        payload = {
            "schema_version": abw_review.APPROVE_SCHEMA_VERSION,
            "workspace": str(workspace),
            "draft_path": draft_path,
            "draft_id": draft_id,
            "expected_draft_hash": draft_hash,
            "expected_queue_status": "review_needed",
            "confirm": {
                "user_confirmed": True,
                "confirmation_token": abw_review.confirmation_token_for(draft_id, draft_hash),
                "confirmation_text": abw_review.APPROVE_CONFIRMATION_TEXT,
            },
            "operator_note": "synthetic approval",
            "dry_run": False,
        }
        payload.update(overrides)
        return payload

    def snapshot_state(self, workspace, ingest_result):
        queue_path = workspace / ".brain" / "ingest_queue.json"
        review_log = workspace / ".brain" / "review_log.jsonl"
        draft_path = workspace / ingest_result["draft_file"]
        wiki_path = workspace / abw_review.wiki_relpath_from_draft(ingest_result["draft_file"])
        return {
            "queue": queue_path.read_text(encoding="utf-8") if queue_path.exists() else "",
            "review_log_exists": review_log.exists(),
            "review_log": review_log.read_text(encoding="utf-8") if review_log.exists() else "",
            "draft_exists": draft_path.exists(),
            "draft_text": draft_path.read_text(encoding="utf-8") if draft_path.exists() else "",
            "wiki_exists": wiki_path.exists(),
            "wiki_text": wiki_path.read_text(encoding="utf-8") if wiki_path.exists() else "",
        }

    def test_approve_draft_promotes_to_wiki(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            result = abw_review.run(f"review {ingest_result['draft_file']}", str(workspace))

            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["draft"], ingest_result["draft_file"])
            self.assertEqual(result["wiki"], "wiki/latency-notes.md")
            self.assertEqual(result["message"], "Draft promoted to trusted wiki")

    def test_list_drafts_returns_empty_when_queue_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_review.list_drafts(tmp)

            self.assertEqual(result, {"pending_drafts": []})

    def test_list_drafts_returns_review_needed_items_only(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            queue_path = workspace / ".brain" / "ingest_queue.json"
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            payload["items"].append(
                {
                    "id": "done-1",
                    "raw": "raw/done.md",
                    "draft": "drafts/done_draft.md",
                    "status": "approved",
                }
            )
            queue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            result = abw_review.list_drafts(str(workspace))

            self.assertEqual(len(result["pending_drafts"]), 1)
            self.assertEqual(result["pending_drafts"][0]["draft"], ingest_result["draft_file"])

    def test_queue_updated_after_review(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            abw_review.run(f"review {ingest_result['draft_file']}", str(workspace))

            queue_path = workspace / ".brain" / "ingest_queue.json"
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["draft"], ingest_result["draft_file"])
            self.assertEqual(payload["items"][0]["status"], "approved")
            self.assertIn("approved_at", payload["items"][0])

    def test_file_moved_from_draft_to_wiki(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            draft_path = workspace / ingest_result["draft_file"]
            self.assertTrue(draft_path.exists())

            result = abw_review.run(f"review {ingest_result['draft_file']}", str(workspace))

            self.assertFalse(draft_path.exists())
            self.assertTrue((workspace / result["wiki"]).exists())

    def test_reject_invalid_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            invalid_draft = workspace / "drafts" / "missing_draft.md"
            invalid_draft.parent.mkdir(parents=True, exist_ok=True)
            invalid_draft.write_text("# Missing\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "ingest_queue"):
                abw_review.run("review drafts/missing_draft.md", str(workspace))

    def test_approve_contract_dry_run_returns_preview_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(workspace, ingest_result, dry_run=True, confirm={})

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "preview_ready")
            self.assertTrue(result["would_approve"])
            self.assertFalse(result["approved"])
            self.assertFalse(result["promotionPerformed"])
            self.assertEqual(result["draft_path"], ingest_result["draft_file"])
            self.assertTrue(result["draft_hash"].startswith("sha256:"))
            self.assertEqual(result["target_wiki_path"], "wiki/latency-notes.md")
            self.assertEqual(result["required_confirmation"]["confirmation_text"], abw_review.APPROVE_CONFIRMATION_TEXT)
            self.assertTrue(result["required_confirmation"]["confirmation_token"].startswith("approve:latency-notes:sha256:"))
            self.assertEqual(before, after)

    def test_approve_contract_apply_success_mutates_only_selected_review_artifacts(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            payload = self.build_contract_request(workspace, ingest_result)

            result = abw_review.approve_draft_request(payload)

            queue_path = workspace / ".brain" / "ingest_queue.json"
            review_log = workspace / ".brain" / "review_log.jsonl"
            draft_path = workspace / ingest_result["draft_file"]
            wiki_path = workspace / "wiki" / "latency-notes.md"
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "approved")
            self.assertTrue(result["approved"])
            self.assertTrue(result["promotionPerformed"])
            self.assertFalse(result["manualReviewRequired"])
            self.assertEqual(result["approved_wiki_path"], "wiki/latency-notes.md")
            self.assertEqual(result["queue_transition"], {"from": "review_needed", "to": "approved"})
            self.assertTrue(result["audit_id"])
            self.assertFalse(draft_path.exists())
            self.assertTrue(wiki_path.exists())
            self.assertEqual(queue["items"][0]["status"], "approved")
            self.assertIn("approved_at", queue["items"][0])
            self.assertTrue(review_log.exists())
            review_lines = [json.loads(line) for line in review_log.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(review_lines[-1]["audit_id"], result["audit_id"])
            self.assertEqual(review_lines[-1]["result"]["approved_wiki_path"], "wiki/latency-notes.md")

    def test_approve_contract_blocks_missing_confirmation_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(
                workspace,
                ingest_result,
                confirm={"user_confirmed": False},
            )

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error_code"], "CONFIRMATION_REQUIRED")
            self.assertTrue(result["manualReviewRequired"])
            self.assertFalse(result["promotionPerformed"])
            self.assertTrue(result["no_mutation_confirmed"])
            self.assertEqual(before, after)

    def test_approve_contract_blocks_stale_hash_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(
                workspace,
                ingest_result,
                expected_draft_hash="sha256:" + ("0" * 64),
            )

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error_code"], "STALE_DRAFT_HASH")
            self.assertEqual(before, after)

    def test_approve_contract_blocks_queue_status_mismatch_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(
                workspace,
                ingest_result,
                expected_queue_status="approved",
            )

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error_code"], "QUEUE_STATUS_MISMATCH")
            self.assertEqual(before, after)

    def test_approve_contract_blocks_existing_target_wiki_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            target = workspace / "wiki" / "latency-notes.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("human trusted content\n", encoding="utf-8")
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(workspace, ingest_result)

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error_code"], "TARGET_WIKI_EXISTS")
            self.assertEqual(before, after)

    def test_approve_contract_blocks_path_traversal_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(
                workspace,
                ingest_result,
                draft_path="../outside.md",
                draft_id="outside",
            )

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error_code"], "PATH_TRAVERSAL_BLOCKED")
            self.assertEqual(before, after)

    def test_approve_contract_blocks_non_draft_path_without_mutation(self):
        tmp, workspace, ingest_result = self.make_ingested_workspace()
        with tmp:
            before = self.snapshot_state(workspace, ingest_result)
            payload = self.build_contract_request(
                workspace,
                ingest_result,
                draft_path="raw/latency-notes.md",
                draft_id="latency-notes",
            )

            result = abw_review.approve_draft_request(payload)

            after = self.snapshot_state(workspace, ingest_result)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error_code"], "INVALID_DRAFT_PATH")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
