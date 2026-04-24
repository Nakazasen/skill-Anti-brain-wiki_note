import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_runner  # noqa: E402
import abw_proof  # noqa: E402
import abw_wizard  # noqa: E402


def make_proof(answer, finalization_block, runtime_id="123", nonce=None, binding_source="mcp"):
    nonce = nonce or ("a" * 32)
    return abw_proof.generate_proof(answer, finalization_block, runtime_id, nonce, binding_source)


def action_commands(actions):
    return [action["command"] if isinstance(action, dict) else action for action in actions]


class AbwRunnerBindingTests(unittest.TestCase):
    def test_render_with_visibility_lock_verified_output(self):
        rendered = abw_runner.render_with_visibility_lock(
            {
                "answer": "Verified answer.\n\n## Finalization\n- current_state: verified",
                "binding_status": "runner_checked",
                "validation_proof": "proof",
                "current_state": "verified",
                "runtime_id": "123",
            }
        )

        self.assertIn("### ABW", rendered)
        self.assertIn("Verified answer.", rendered)
        self.assertNotIn("binding=runner_checked", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("Finalization", rendered)

    def test_render_with_visibility_lock_missing_validation_proof_is_checked(self):
        rendered = abw_runner.render_with_visibility_lock(
            {
                "answer": "Some answer.\n\n## Finalization\n- current_state: verified",
                "binding_status": "runner_checked",
                "current_state": "verified",
            }
        )

        self.assertIn("### ABW", rendered)
        self.assertIn("Some answer.", rendered)
        self.assertNotIn("binding=runner_checked", rendered)
        self.assertNotIn("UNVERIFIED OUTPUT", rendered)

    def test_render_with_visibility_lock_non_structured_output_is_blocked(self):
        rendered = abw_runner.render_with_visibility_lock("plain string output")

        self.assertIn("### ABW", rendered)
        self.assertIn("state: blocked", rendered)
        self.assertIn("plain string output", rendered)
        self.assertNotIn("UNVERIFIED OUTPUT", rendered)

    def test_render_with_visibility_lock_is_pure_view_for_verified_payload(self):
        rendered = abw_runner.render_with_visibility_lock(
            {
                "answer": "Verified answer without finalization.",
                "binding_status": "runner_enforced",
                "validation_proof": "proof",
                "current_state": "verified",
                "runtime_id": "123",
            }
        )

        self.assertIn("Verified answer without finalization.", rendered)
        self.assertNotIn("binding=runner_enforced", rendered)
        self.assertNotIn("validation_proof", rendered)

    def test_resolve_trust_label_maps_help_to_informational(self):
        self.assertEqual(
            abw_runner.resolve_trust_label(
                {
                    "binding_status": "runner_checked",
                    "current_state": "checked_only",
                    "runner_status": "completed",
                    "route": {"lane": "help"},
                }
            ),
            "informational",
        )

    def test_resolve_trust_label_maps_explain_to_checked(self):
        self.assertEqual(
            abw_runner.resolve_trust_label(
                {
                    "binding_status": "runner_checked",
                    "current_state": "checked_only",
                    "runner_status": "completed",
                    "route": {"lane": "explain_draft"},
                }
            ),
            "checked",
        )

    def test_resolve_trust_label_maps_query_to_checked(self):
        self.assertEqual(
            abw_runner.resolve_trust_label(
                {
                    "binding_status": "runner_checked",
                    "current_state": "knowledge_answered",
                    "runner_status": "completed",
                    "route": {"lane": "query"},
                }
            ),
            "checked",
        )

    def test_resolve_trust_label_maps_invalid_approve_to_blocked(self):
        self.assertEqual(
            abw_runner.resolve_trust_label(
                {
                    "binding_status": "runner_checked",
                    "current_state": "blocked",
                    "runner_status": "blocked",
                    "route": {"lane": "approve_draft"},
                }
            ),
            "blocked",
        )

    def test_direct_runner_cli_is_blocked(self):
        payload = {
            "task": "explain ABW",
            "task_kind": "validation",
            "candidate_answer": (
                "Draft explanation.\n\n"
                "## Finalization\n"
                "- current_state: knowledge_answered\n"
                "- evidence: AGENTS.md describes the Adaptive Reasoning Policy\n"
                "- gaps_or_limitations: derived from docs rather than wiki\n"
                "- next_steps: inspect specific workflows if needed\n"
            ),
            "binding_mode": "STRICT",
            "binding_source": "fallback",
        }

        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_runner.py"), "--json-input"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Do not run abw_runner directly. Use 'abw' CLI.", completed.stderr)

    def test_draft_answer_without_runner_validation_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "This is still just a draft answer.",
                "binding_status": "runner_checked",
                "current_state": "verified",
                "task": "explain ABW",
            },
            mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["reason"], "raw draft answer is not allowed")

    def test_negative_memory_logs_rejected_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="just answer this now",
                task_kind="validation",
                candidate_answer="",
                binding_mode="STRICT",
                workspace=tmp,
            )

            self.assertEqual(result["binding_status"], "runner_checked")
            self.assertEqual(result["current_state"], "blocked")
            memory_path = Path(tmp) / ".brain" / "negative_memory.jsonl"
            self.assertTrue(memory_path.exists())
            rows = abw_runner.load_memory(tmp)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["pattern"], "skip_validation")
            self.assertEqual(rows[0]["failure"], "runner_checked")

    def test_negative_memory_dedups_and_increments_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(2):
                abw_runner.dispatch_request(
                    task="just answer this now",
                    task_kind="validation",
                    candidate_answer="",
                    binding_mode="STRICT",
                    workspace=tmp,
                )

            rows = abw_runner.load_memory(tmp)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["pattern"], "skip_validation")
            self.assertEqual(rows[0]["count"], 2)

    def test_negative_memory_warning_is_attached_on_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_runner.log_negative_memory(
                workspace=tmp,
                pattern="skip_validation",
                failure="missing required field: binding_status",
                context="blocked",
                fix_hint="Use the runner path instead of prompt-only output.",
            )

            result = abw_runner.dispatch_request(
                task="just answer this now",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertIn("memory_warning", result)
            self.assertEqual(result["memory_warning"]["pattern"], "skip_validation")
            self.assertEqual(result["binding_status"], "runner_checked")

    def test_missing_finalization_block_is_forced_blocked(self):
        result = abw_runner.run_finalization_gate("plain model output without a final block")

        self.assertEqual(result["report"]["decision"], "blocked")
        self.assertEqual(result["report"]["checked_state"], "blocked")
        self.assertIn("current_state: blocked", result["block"])
        self.assertIn("Finalization block missing", result["block"])

    def test_downgrade_updates_current_state(self):
        output = """Body.

## Finalization
- current_state: verified
- evidence: smoke test ran one case
- gaps_or_limitations: broader suite not checked
- next_steps: run full test suite
"""

        result = abw_runner.run_finalization_gate(output, task_kind="fix")

        self.assertEqual(result["report"]["decision"], "downgrade")
        self.assertEqual(result["report"]["checked_state"], "runs_one_case")
        self.assertIn("current_state: runs_one_case", result["block"])

    def test_runtime_evidence_passes(self):
        output = """Body.

## Finalization
- current_state: verified
- evidence: terminal output showed tests passed with exit code 0
- gaps_or_limitations: no known gaps
- next_steps: commit the verified change
"""

        result = abw_runner.run_finalization_gate(output, task_kind="fix")

        self.assertEqual(result["report"]["decision"], "pass")
        self.assertEqual(result["report"]["checked_state"], "verified")
        self.assertIn("current_state: verified", result["block"])

    def test_mcp_execution_path_sets_runner_enforced(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            task_kind="execution",
            binding_source="mcp",
        )

        self.assertEqual(result["runner_status"], "completed")
        self.assertEqual(result["binding_status"], "runner_enforced")
        self.assertEqual(result["evaluation"]["verdict"], "pass")
        self.assertTrue(result["evaluation"]["accepted"])
        self.assertTrue(result["artifact_path"].startswith(".brain/runner_artifacts/"))
        self.assertTrue(result["acceptance_request"].startswith(".brain/acceptance_requests/"))
        self.assertEqual(
            result["validation_proof"],
            abw_proof.generate_proof(
                result["answer"],
                result["finalization_block"],
                result["runtime_id"],
                result["nonce"],
                result["binding_source"],
            ),
        )
        self.assertEqual(result["current_state"], "verified")
        self.assertIn("hello world", result["answer"])
        self.assertIn("## Finalization", result["answer"])

    def test_abw_accept_failure_downgrades_binding_status(self):
        with patch(
            "abw_runner.abw_accept.evaluate_file",
            return_value={
                "status": "evaluated",
                "verdict": "fail",
                "accepted": False,
                "fail_reasons": ["runtime_marker_missing_or_invalid"],
            },
        ):
            result = abw_runner.dispatch_request(
                task="print hello world",
                task_kind="execution",
                binding_source="mcp",
            )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["evaluation"]["verdict"], "fail")

    def test_abw_accept_requires_accepted_true_for_runner_enforced(self):
        with patch(
            "abw_runner.abw_accept.evaluate_file",
            return_value={
                "status": "evaluated",
                "verdict": "pass",
                "accepted": False,
                "fail_reasons": [],
            },
        ):
            result = abw_runner.dispatch_request(
                task="print hello world",
                task_kind="execution",
                binding_source="mcp",
            )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["evaluation"]["verdict"], "pass")
        self.assertFalse(result["evaluation"]["accepted"])

    def test_execution_preserves_binding_source_from_caller(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            task_kind="execution",
            binding_source="cli",
        )

        self.assertEqual(result["binding_source"], "cli")

    def test_fallback_validation_sets_runner_checked(self):
        candidate = "Tentative answer.\n\n## Finalization\n- current_state: verified\n- evidence: terminal output showed tests passed with exit code 0\n- gaps_or_limitations: no known gaps\n- next_steps: commit the change"
        result = abw_runner.dispatch_request(
            task="print hello world",
            task_kind="validation",
            candidate_answer=candidate,
            binding_mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["runner_status"], "completed")
        self.assertEqual(result["current_state"], "checked_only")
        self.assertEqual(result["answer"], result["validated_answer"])
        self.assertIn("Tentative answer.", result["answer"])
        self.assertIn("## Finalization", result["answer"])

    def test_validated_answer_passes_acceptance(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            task_kind="validation",
            candidate_answer="Draft answer.\n\n## Finalization\n- current_state: verified\n- evidence: terminal output showed tests passed with exit code 0\n- gaps_or_limitations: no known gaps\n- next_steps: commit the change",
            binding_mode="STRICT",
        )

        self.assertIn(result["binding_status"], {"runner_checked", "runner_enforced"})
        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertIn("## Finalization", result["answer"])

    def test_bypass_attempt_is_forced_through_validation(self):
        raw_answer = """Direct model answer: fixed and verified.

## Finalization
- current_state: verified
- evidence: static reasoning only; model says it is verified
- gaps_or_limitations: not tested and no runtime proof
- next_steps: ship it
"""
        result = abw_runner.dispatch_request(
            task="fix bug",
            task_kind="validation",
            candidate_answer=raw_answer,
            binding_mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["current_state"], "code_changed_only")
        self.assertIn("Validated result: completion claim was downgraded", result["answer"])
        self.assertIn("current_state: code_changed_only", result["answer"])
        self.assertNotEqual(result["answer"].strip(), raw_answer.strip())
        self.assertNotIn("ship it\n", result["answer"])

    def test_validation_mode_rewrites_overclaim_to_runner_checked(self):
        raw_answer = """Direct model answer: fixed and verified.

## Finalization
- current_state: verified
- evidence: static reasoning only; model says it is verified
- gaps_or_limitations: not tested and no runtime proof
- next_steps: ship it
"""
        result = abw_runner.dispatch_request(
            task="fix bug",
            task_kind="validation",
            candidate_answer=raw_answer,
            binding_mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["current_state"], "code_changed_only")

    def test_knowledge_execution_exposes_binding_and_tier(self):
        result = abw_runner.dispatch_request(
            task="explain PostgreSQL selection rationale",
            task_kind="execution",
            binding_source="mcp",
        )

        self.assertEqual(result["runner_status"], "completed")
        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["current_state"], "knowledge_answered")
        self.assertEqual(result["knowledge_evidence_tier"], "E2_wiki")
        self.assertGreaterEqual(result["knowledge_source_score"], 1)
        self.assertEqual(result["knowledge"]["tier"], "E2_wiki")
        self.assertEqual(result["knowledge"]["source_summary"], "local_wiki")
        self.assertEqual(result["knowledge"]["source"], "wiki")
        self.assertIn("PostgreSQL was selected", result["answer"])
        self.assertIn("knowledge_evidence_tier: E2_wiki", result["answer"])

    def test_unknown_knowledge_topic_stays_visible(self):
        result = abw_runner.dispatch_request(
            task="unknown topic",
            task_kind="execution",
            route={"intent": "knowledge"},
            binding_source="mcp",
        )

        self.assertEqual(result["runner_status"], "completed")
        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["current_state"], "knowledge_gap_logged")
        self.assertEqual(result["knowledge"]["tier"], "E0_unknown")
        self.assertTrue(result["knowledge"]["gap_logged"])
        self.assertEqual(result["knowledge"]["source"], "none")
        self.assertIn("binding_status", result)

    def test_unimplemented_execution_path_stays_runner_checked(self):
        result = abw_runner.dispatch_request(
            task="do something unsupported",
            task_kind="execution",
            binding_source="mcp",
        )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["runner_status"], "blocked")
        self.assertEqual(result["current_state"], "blocked")

    def test_prompt_only_soft_mode_is_explicit(self):
        result = abw_runner.validate_candidate_answer(
            task="explain PostgreSQL selection rationale",
            candidate_answer="",
            route={"intent": "knowledge"},
            binding_mode="SOFT",
        )

        self.assertEqual(result["binding_status"], "prompt_only")
        self.assertEqual(result["runner_status"], "not_run")
        self.assertIn("knowledge", result)
        self.assertEqual(result["knowledge"]["tier"], "E2_wiki")

    def test_missing_binding_status_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "x",
                "current_state": "verified",
            },
            mode="STRICT",
        )

        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["reason"], "output not produced by runner")

    def test_fake_validated_output_without_proof_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "Validated looking output.\n\n## Finalization\n- current_state: verified",
                "binding_status": "runner_checked",
                "current_state": "verified",
                "finalization_block": "## Finalization\n- current_state: verified",
                "binding_source": "mcp",
                "nonce": "a" * 32,
                "runtime_id": "123",
                "task": "print hello world",
            },
            mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["reason"], "output not produced by runner")

    def test_corrupted_validation_proof_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "Validated looking output.\n\n## Finalization\n- current_state: verified",
                "binding_status": "runner_checked",
                "validation_proof": "fake",
                "binding_source": "mcp",
                "current_state": "verified",
                "finalization_block": "## Finalization\n- current_state: verified",
                "nonce": "a" * 32,
                "runtime_id": "123",
                "task": "print hello world",
            },
            mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["reason"], "output not produced by runner")

    def test_rewrite_after_runner_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": (
                    "Rewritten summary.\n\n"
                    "## Finalization\n"
                    "- current_state: verified"
                ),
                "validated_answer": (
                    "Original runner answer.\n\n"
                    "## Finalization\n"
                    "- current_state: verified"
                ),
                "finalization_block": "## Finalization\n- current_state: verified",
                "binding_status": "runner_checked",
                "binding_source": "mcp",
                "validation_proof": make_proof(
                    "Rewritten summary.\n\n## Finalization\n- current_state: verified",
                    "## Finalization\n- current_state: verified",
                    "123",
                ),
                "current_state": "verified",
                "nonce": "a" * 32,
                "runtime_id": "123",
                "task": "print hello world",
            },
            mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["reason"], "output not produced by runner")

    def test_strict_mode_prompt_only_is_blocked(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "draft",
                "binding_status": "prompt_only",
                "current_state": "unknown",
                "task": "explain ABW",
                "runner_status": "not_run",
            },
            mode="STRICT",
        )

        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["reason"], "STRICT mode requires runner usage")

    def test_knowledge_missing_tier_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "knowledge answer",
                "binding_status": "runner_checked",
                "current_state": "knowledge_answered",
                "intent": "knowledge",
                "validation_proof": "fake",
                "binding_source": "mcp",
                "finalization_block": "## Finalization\n- current_state: knowledge_answered",
                "nonce": "a" * 32,
                "runtime_id": "123",
                "knowledge": {
                    "score": 1,
                    "source_summary": "general_knowledge",
                },
            },
            mode="STRICT",
        )

        self.assertEqual(result["current_state"], "blocked")
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["reason"], "missing knowledge.tier")

    def test_blocked_knowledge_state_is_semantically_reclassified(self):
        result = {
            "current_state": "blocked",
            "evidence": "wiki retrieval matched wiki/concepts/postgresql-selection-rationale.md",
            "knowledge_context": {
                "source": "wiki",
                "content": "PostgreSQL was selected for the analytics service.",
                "confidence": 0.8,
            },
        }

        abw_runner.apply_knowledge_semantics(result, "what is ABW")

        self.assertEqual(result["current_state"], "knowledge_answered")
        self.assertTrue(result["semantic_fix_applied"])
        self.assertEqual(result["knowledge_evidence_tier"], "E2_wiki")

    def test_explicit_local_source_is_grounded(self):
        result = abw_runner.dispatch_request(
            task="explain wiki/concepts/postgresql-selection-rationale.md",
            task_kind="execution",
            route={"intent": "knowledge"},
            binding_source="mcp",
        )

        self.assertEqual(result["current_state"], "knowledge_answered")
        self.assertEqual(result["knowledge_evidence_tier"], "E3_grounded")
        self.assertEqual(result["knowledge"]["source"], "local")
        self.assertEqual(result["knowledge"]["source_summary"], "explicit_local")

    def test_missing_source_logs_knowledge_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="explain ABW",
                task_kind="execution",
                route={"intent": "knowledge"},
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["current_state"], "knowledge_gap_logged")
            gap_path = Path(tmp) / ".brain" / "knowledge_gaps.json"
            self.assertTrue(gap_path.exists())
            payload = json.loads(gap_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["gaps"][0]["query"], "explain ABW")

    def test_knowledge_state_without_evidence_does_not_hard_block(self):
        output = """Body.

## Finalization
- current_state: knowledge_answered
- evidence:
- gaps_or_limitations: no known gaps
- next_steps: no further action
"""

        result = abw_runner.run_finalization_gate(output, task_kind="knowledge")

        self.assertEqual(result["report"]["decision"], "pass")
        self.assertEqual(result["report"]["checked_state"], "knowledge_answered")

    def test_fake_proof_is_rejected(self):
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "Verified answer.\n\n## Finalization\n- current_state: verified",
                "validated_answer": "Verified answer.\n\n## Finalization\n- current_state: verified",
                "finalization_block": "## Finalization\n- current_state: verified",
                "binding_status": "runner_checked",
                "validation_proof": "fake",
                "binding_source": "mcp",
                "current_state": "verified",
                "nonce": "a" * 32,
                "runtime_id": "123",
                "task": "print hello world",
            },
            mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")

    def test_validation_knowledge_tier_ignores_answer_wording(self):
        result = abw_runner.dispatch_request(
            task="explain ABW",
            task_kind="validation",
            candidate_answer=(
                "Theo wiki va sources, day la cau tra loi.\n\n"
                "## Finalization\n"
                "- current_state: knowledge_answered\n"
                "- evidence: cited from wiki wording only\n"
                "- gaps_or_limitations: none\n"
                "- next_steps: none\n"
            ),
            route={"intent": "knowledge"},
            binding_mode="STRICT",
            workspace=".",
        )

        self.assertEqual(result["binding_status"], "runner_checked")
        self.assertEqual(result["current_state"], "knowledge_gap_logged")
        self.assertEqual(result["knowledge"]["tier"], "E0_unknown")

    def test_modified_answer_is_rejected_when_proof_was_for_original_answer(self):
        finalization_block = "## Finalization\n- current_state: verified"
        result = abw_runner.enforce_output_acceptance(
            {
                "answer": "Modified answer.\n\n## Finalization\n- current_state: verified",
                "validated_answer": "Modified answer.\n\n## Finalization\n- current_state: verified",
                "finalization_block": finalization_block,
                "binding_status": "runner_checked",
                "binding_source": "mcp",
                "validation_proof": make_proof(
                    "Original answer.\n\n## Finalization\n- current_state: verified",
                    finalization_block,
                    "123",
                ),
                "current_state": "verified",
                "nonce": "a" * 32,
                "runtime_id": "123",
                "task": "print hello world",
            },
            mode="STRICT",
        )

        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")

    def test_real_runner_output_passes_with_real_proof(self):
        result = abw_runner.dispatch_request(
            task="print hello world",
            task_kind="execution",
            binding_source="mcp",
        )

        accepted = abw_runner.enforce_output_acceptance(dict(result), mode="STRICT")
        self.assertEqual(accepted["binding_status"], "runner_enforced")
        self.assertEqual(
            accepted["validation_proof"],
            abw_proof.generate_proof(
                accepted["answer"],
                accepted["finalization_block"],
                accepted["runtime_id"],
                accepted["nonce"],
                accepted["binding_source"],
            ),
        )

    def test_negative_memory_does_not_change_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_runner.log_negative_memory(
                workspace=tmp,
                pattern="generic_failure",
                failure="old failure",
                context="blocked",
                fix_hint="Use a valid runner shape.",
            )

            result = abw_runner.dispatch_request(
                task="print hello world",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["binding_status"], "runner_enforced")
            self.assertEqual(result["current_state"], "verified")
            self.assertNotIn("memory_warning", result)

    def test_generic_failure_is_ignored_in_read_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_runner.log_negative_memory(
                workspace=tmp,
                pattern="generic_failure",
                failure="blocked",
                context="blocked",
                fix_hint="Do not trust generic failures for routing.",
            )

            warning = abw_runner.check_negative_memory(
                task="some unrelated task",
                workspace=tmp,
            )

            self.assertIsNone(warning)

    def test_derive_failure_label_falls_back_when_reason_missing(self):
        label = abw_runner.derive_failure_label(
            {
                "binding_status": "runner_checked",
                "current_state": "blocked",
            }
        )

        self.assertEqual(label, "runner_checked")

    def test_derive_failure_label_never_returns_empty(self):
        label = abw_runner.derive_failure_label({})

        self.assertEqual(label, "unknown_rejection_reason")

    def test_negative_memory_global_scope_uses_global_path(self):
        with tempfile.TemporaryDirectory() as home_tmp:
            with patch("abw_runner.Path.home", return_value=Path(home_tmp)):
                abw_runner.log_negative_memory(
                    workspace="ignored-workspace",
                    pattern="skip_validation",
                    failure="runner_checked",
                    context="blocked",
                    fix_hint="Use the runner path instead of prompt-only output.",
                    memory_scope="global",
                )

                global_path = Path(home_tmp) / ".gemini" / "antigravity" / "negative_memory.jsonl"
                self.assertTrue(global_path.exists())

                rows = abw_runner.load_memory(
                    workspace="other-workspace",
                    memory_scope="global",
                )
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["pattern"], "skip_validation")

    def test_query_and_query_deep_routes_are_visible_in_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            shallow = abw_runner.dispatch_request(
                task="What is PostgreSQL selection rationale?",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )
            deep = abw_runner.dispatch_request(
                task="Compare PostgreSQL versus MongoDB tradeoffs for this architecture",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(shallow["route"]["lane"], "query")
            self.assertEqual(deep["route"]["lane"], "query_deep")
            self.assertEqual(deep["binding_status"], "runner_checked")
            self.assertEqual(deep["strategy_trace"]["mode"], "bounded_wiki_reasoning_loop")
            self.assertIn("reasoning_steps", deep)
            self.assertIn("evaluation", shallow)
            self.assertIn("artifact_path", shallow)
            self.assertTrue((Path(tmp) / ".brain" / "used_nonces.json").exists())

    def test_replayed_runner_payload_is_rejected_for_reused_nonce(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="print hello world",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            replayed = dict(result)
            replayed.pop("_nonce_validated", None)
            rejected = abw_runner.enforce_output_acceptance(replayed, mode="STRICT")

            self.assertEqual(rejected["binding_status"], "rejected")
            self.assertEqual(rejected["current_state"], "blocked")
            self.assertEqual(rejected["reason"], "nonce already used")

    def test_resume_lane_falls_back_to_query_when_no_safe_step_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="resume prior work",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "query")
            self.assertEqual(result["route"]["fallback_from"], "resume")
            self.assertEqual(result["current_state"], "knowledge_gap_logged")
            route_log = Path(tmp) / ".brain" / "route_log.jsonl"
            self.assertTrue(route_log.exists())
            self.assertEqual(len(route_log.read_text(encoding="utf-8").splitlines()), 2)

    def test_bootstrap_lane_is_controlled_and_does_not_write_bootstrap_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="bootstrap this greenfield idea",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "bootstrap")
            self.assertIn("bootstrap_proposal", result)
            self.assertFalse((Path(tmp) / ".brain" / "bootstrap").exists())
            self.assertEqual(result["binding_status"], "runner_checked")

    def test_ingest_lane_creates_draft_queue_without_trusted_wiki_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "sample.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("# Sample\n", encoding="utf-8")

            result = abw_runner.dispatch_request(
                task="ingest raw/sample.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "ingest")
            self.assertIn("ingest_draft", result)
            self.assertFalse(result["ingest_draft"]["trusted_wiki_written"])
            self.assertTrue((Path(tmp) / ".brain" / "ingest_queue.json").exists())
            self.assertEqual(list((Path(tmp) / "wiki").rglob("*.md")) if (Path(tmp) / "wiki").exists() else [], [])

    def test_list_drafts_returns_empty_when_no_queue_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="list drafts",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "list_drafts")
            self.assertEqual(result["pending_drafts"], [])
            self.assertIn("No pending drafts.", result["answer"])

    def test_approve_valid_draft_succeeds_via_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "sample.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("# Sample\n", encoding="utf-8")
            abw_runner.dispatch_request(
                task="ingest raw/sample.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            result = abw_runner.dispatch_request(
                task="approve draft drafts/sample_draft.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "approve_draft")
            self.assertEqual(result["review_status"], "approved")
            self.assertEqual(result["runner_status"], "completed")
            self.assertTrue((Path(tmp) / "wiki" / "sample.md").exists())
            self.assertFalse((Path(tmp) / "drafts" / "sample_draft.md").exists())

    def test_approve_invalid_draft_is_rejected_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="approve draft drafts/missing_draft.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "approve_draft")
            self.assertEqual(result["review_status"], "blocked")
            self.assertEqual(result["runner_status"], "blocked")
            self.assertEqual(result["current_state"], "blocked")
            self.assertIn("blocked", result["answer"].lower())

    def test_approve_without_path_falls_back_in_router(self):
        result = abw_runner.dispatch_request(
            task="approve draft",
            task_kind="execution",
            binding_source="mcp",
            workspace=".",
        )

        self.assertNotEqual(result["route"]["lane"], "approve_draft")
        self.assertEqual(result["route"]["lane"], "legacy_execution")

    def test_explain_valid_draft_returns_review_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "sample.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                "# Orders Table\n\n"
                "This draft explains the orders table.\n\n"
                "- column order_id identifies the row\n"
                "- example query helps analyze timeout error\n\n"
                "SELECT order_id FROM orders WHERE status = 'FAILED';\n",
                encoding="utf-8",
            )
            abw_runner.dispatch_request(
                task="ingest raw/sample.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            result = abw_runner.dispatch_request(
                task="explain draft drafts/sample_draft.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "explain_draft")
            self.assertEqual(result["explain_status"], "ok")
            self.assertEqual(result["runner_status"], "completed")
            self.assertIn("Draft overview:", result["answer"])
            self.assertIn(result["draft_explanation"]["confidence"], {"medium", "high"})

    def test_explain_invalid_draft_is_rejected_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="explain draft drafts/missing_draft.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "explain_draft")
            self.assertEqual(result["explain_status"], "blocked")
            self.assertEqual(result["runner_status"], "blocked")
            self.assertEqual(result["current_state"], "blocked")

    def test_explain_empty_draft_returns_low_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "empty.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("", encoding="utf-8")
            abw_runner.dispatch_request(
                task="ingest raw/empty.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            result = abw_runner.dispatch_request(
                task="explain draft drafts/empty_draft.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "explain_draft")
            self.assertEqual(result["draft_explanation"]["confidence"], "low")

    def test_review_drafts_returns_multiple_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for name, content in {
                "orders.md": "# Orders\n\n- example\nSELECT * FROM orders;\n",
                "errors.md": "# Errors\n\n- timeout error details\n",
            }.items():
                raw_path = workspace / "raw" / name
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(content, encoding="utf-8")
                abw_runner.dispatch_request(
                    task=f"ingest raw/{name} into wiki",
                    task_kind="execution",
                    binding_source="mcp",
                    workspace=tmp,
                )

            result = abw_runner.dispatch_request(
                task="review drafts",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "review_drafts")
            self.assertEqual(len(result["draft_batch_review"]["items"]), 2)
            self.assertIn("Draft batch review:", result["answer"])

    def test_review_drafts_handles_empty_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "empty.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("", encoding="utf-8")
            abw_runner.dispatch_request(
                task="ingest raw/empty.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            result = abw_runner.dispatch_request(
                task="review drafts",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "review_drafts")
            self.assertEqual(result["draft_batch_review"]["items"][0]["confidence"], "low")
            self.assertEqual(result["draft_batch_review"]["items"][0]["suggestion"], "improve")

    def test_review_drafts_limits_to_top_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for index in range(6):
                raw_path = workspace / "raw" / f"draft-{index}.md"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(f"# Draft {index}\n\n- sample example\n", encoding="utf-8")
                abw_runner.dispatch_request(
                    task=f"ingest raw/draft-{index}.md into wiki",
                    task_kind="execution",
                    binding_source="mcp",
                    workspace=tmp,
                )

            result = abw_runner.dispatch_request(
                task="review drafts",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "review_drafts")
            self.assertEqual(len(result["draft_batch_review"]["items"]), 5)

    def test_help_command_returns_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="help",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "help")
            self.assertEqual(result["message"], "You can continue from the current state:")
            self.assertEqual(len(result["sections"]), 5)
            self.assertEqual(result["sections"][0]["title"], "Overview")
            self.assertIn(
                'Dashboard: natural: "show dashboard"; command: /abw-dashboard',
                result["sections"][4]["items"],
            )
            self.assertEqual(result["state_snapshot"]["raw_files"], 0)
            self.assertEqual(action_commands(result["next_actions"]), ["help", "audit system"])
            return

        self.assertEqual(result["route"]["lane"], "help")
        self.assertEqual(result["message"], "Bạn có thể làm:")
        self.assertEqual(len(result["sections"]), 5)
        self.assertEqual(result["sections"][0]["title"], "📥 Nạp tài liệu")

    def test_dashboard_lane_returns_structured_ui_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="dashboard",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "dashboard")
            self.assertEqual(result["header"]["title"], "ABW Dashboard")
            self.assertIn("health", result)
            self.assertIn("knowledge", result)
            self.assertIn("top_gaps", result)
            self.assertTrue(result["next_actions"])
            self.assertIn("ABW Dashboard", result["answer"])

    def test_wizard_lane_returns_options_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="wizard",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "wizard")
            self.assertEqual(result["wizard_status"], "menu")
            self.assertEqual(result["wizard_state"]["step"], "choose_action")
            self.assertFalse(result["should_execute"])
            self.assertIn("ABW Wizard", result["answer"])
            self.assertIn("wizard_options", result)

    def test_wizard_selection_runs_guided_flow_without_auto_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_runner.dispatch_request(
                task="wizard",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )
            result = abw_runner.dispatch_request(
                task="wizard 1",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "wizard")
            self.assertEqual(result["wizard_status"], "flow_completed")
            self.assertEqual(result["wizard"]["flow"], abw_wizard.INGEST_FLOW)
            self.assertFalse(result["should_execute"])
            self.assertTrue(any(item["step"] == "USER_APPROVE" for item in result["wizard"]["history"]))
            self.assertIn("ABW Wizard Auto-Flow", result["answer"])

    def test_system_trend_lane_captures_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="system trend",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "system_trend")
            self.assertEqual(result["snapshot_count"], 1)
            self.assertEqual(result["monitor_status"], "insufficient_history")
            self.assertTrue((Path(tmp) / ".brain" / "system_snapshots.jsonl").exists())
            self.assertIn("ABW System Trend", result["answer"])

    def test_ingest_lane_exposes_state_based_next_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "sample.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("# Sample\n", encoding="utf-8")

            result = abw_runner.dispatch_request(
                task="ingest raw/sample.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "ingest")
            self.assertEqual(action_commands(result["next_actions"]), ["review drafts"])
            self.assertTrue(result["guidance"])

    def test_ingest_raw_directory_shortcut_does_not_fallback_to_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "raw" / "a.md").parent.mkdir(parents=True, exist_ok=True)
            (Path(tmp) / "raw" / "a.md").write_text("# A\n", encoding="utf-8")
            (Path(tmp) / "raw" / "nested" / "b.txt").parent.mkdir(parents=True, exist_ok=True)
            (Path(tmp) / "raw" / "nested" / "b.txt").write_text("B\n", encoding="utf-8")

            result = abw_runner.dispatch_request(
                task="ingest raw",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "ingest")
            self.assertNotIn("fallback_from", result["route"])
            self.assertEqual(result.get("runner_status"), "completed")
            self.assertGreaterEqual(result.get("ingest_result", {}).get("ingested_count", 0), 2)

    def test_ingest_missing_path_is_blocked_without_query_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="ingest raw/missing.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "ingest")
            self.assertNotIn("fallback_from", result["route"])
            self.assertEqual(result.get("runner_status"), "blocked")
            self.assertIn("Use: ingest raw/<file> or ingest raw/", result["answer"])

    def test_list_drafts_lane_uses_state_based_next_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "sample.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("# Sample\n", encoding="utf-8")
            abw_runner.dispatch_request(
                task="ingest raw/sample.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            result = abw_runner.dispatch_request(
                task="list drafts",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(action_commands(result["next_actions"]), ["review drafts"])
            self.assertTrue(result["guidance"])

    def test_explain_draft_lane_uses_state_based_next_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "sample.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("# Sample\n\n- example\n", encoding="utf-8")
            abw_runner.dispatch_request(
                task="ingest raw/sample.md into wiki",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            result = abw_runner.dispatch_request(
                task="explain draft drafts/sample_draft.md",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(action_commands(result["next_actions"]), ["review drafts"])
            self.assertTrue(result["guidance"])

    def test_query_lane_uses_fallback_next_actions_when_no_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="What is PostgreSQL selection rationale?",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(result["route"]["lane"], "query")
            self.assertEqual(action_commands(result["next_actions"]), ["help", "audit system"])
            self.assertTrue(result["guidance"])

    def test_next_actions_menu_displays_indexed_actions(self):
        menu = abw_runner.render_action_menu(["help", {"label": "Tự audit", "command": "audit system"}])

        self.assertIn("1. Show help (help)", menu)
        self.assertIn("2. Tự audit (audit system)", menu)

    def test_valid_next_action_selection_returns_command(self):
        command = abw_runner.interactive_next_action_command(
            ["help", "audit system"],
            input_func=lambda _prompt: "2",
            output_func=lambda _text: None,
        )

        self.assertEqual(command, "audit system")

    def test_invalid_next_action_selection_is_ignored(self):
        messages = []
        command = abw_runner.interactive_next_action_command(
            ["help"],
            input_func=lambda _prompt: "9",
            output_func=messages.append,
        )

        self.assertIsNone(command)
        self.assertTrue(any("không hợp lệ" in message for message in messages))

    def test_cli_next_action_loop_executes_valid_selection(self):
        initial = {
            "next_actions": [{"label": "Xem hướng dẫn", "command": "help"}],
            "runner_status": "completed",
        }
        executed = {
            "answer": "ok",
            "binding_status": "runner_enforced",
            "validation_proof": "proof",
            "current_state": "checked_only",
            "runner_status": "completed",
            "next_actions": [],
        }

        with patch.object(abw_runner, "dispatch_request", return_value=executed) as mocked:
            result = abw_runner.run_cli_next_action_loop(
                initial,
                workspace=".",
                binding_mode="STRICT",
                binding_source="cli",
                input_func=lambda _prompt: "1",
                output_func=lambda _text: None,
                max_steps=1,
            )

        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["task"], "help")
        self.assertIs(result, executed)

    def test_help_command_has_guidance_and_english_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_runner.dispatch_request(
                task="help",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertTrue(result["guidance"])
            self.assertTrue(result["next_actions"])
            self.assertIn("You can continue from the current state:", result["answer"])
            self.assertIn("Situational guidance", result["answer"])
            return

        result = abw_runner.dispatch_request(
            task="help",
            task_kind="execution",
            binding_source="mcp",
            workspace=".",
        )

        self.assertEqual(result["guidance"], "Tôi đang gợi ý các bước bạn có thể làm tiếp theo.")
        self.assertTrue(result["next_actions"])
        self.assertIn("Bạn có thể làm:", result["answer"])
        self.assertIn("📋 Duyệt tri thức", result["answer"])

    def test_set_language_vi_updates_help_and_trust_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_result = abw_runner.dispatch_request(
                task="set language vi",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )

            self.assertEqual(set_result["language"], "vi")
            self.assertEqual(set_result["runner_status"], "completed")

            help_result = abw_runner.dispatch_request(
                task="help",
                task_kind="execution",
                binding_source="mcp",
                workspace=tmp,
            )
            rendered = abw_runner.render_with_visibility_lock(help_result, workspace=tmp)

            self.assertIn("Ban co the tiep tuc dua tren trang thai hien tai:", help_result["answer"])
            self.assertIn("### ABW Help", rendered)
            self.assertNotIn("muc_tin_cay", rendered)
            self.assertNotIn("validation_proof", rendered)
            self.assertEqual(help_result["next_actions"][0]["command"], "help")


if __name__ == "__main__":
    unittest.main()
