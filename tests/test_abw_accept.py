import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_accept  # noqa: E402


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def base_request(**overrides):
    request = {
        "step_id": "step-test",
        "scope": "Test artifact",
        "artifact": {"id": "artifact-1", "path": "out.txt", "type": "doc"},
        "candidate_files": ["out.txt", "tests/logs/pytest.txt"],
        "rubric": [
            {
                "id": "scope",
                "description": "Scope satisfied.",
                "required": True,
                "passed": True,
                "evidence": {
                    "type": "scope_diff",
                    "ref": "out.txt",
                    "status": "passed",
                    "machine_checkable": False,
                    "strength": "allowed_human",
                    "claim_id": "rubric:scope",
                    "proves": "The artifact path stays inside the accepted scope.",
                    "mechanism": "human_review",
                    "result": "passed",
                    "details": "Reviewed artifact path against candidate_files.",
                },
            },
        ],
        "checks": [
            {
                "id": "validation",
                "type": "test_result",
                "subject": "artifact-1",
                "status": "passed",
                "expected": "pass",
                "required": True,
                "description": "Validation passed.",
                "evidence": {
                    "type": "test_output",
                    "ref": f"{sys.executable} -c pass",
                    "ref_type": "command",
                    "ref_check": "exit_code:0",
                    "source": "trusted",
                    "context_id": "step-test",
                    "runtime_id": "OPTIONAL_RUNTIME_ID",
                    "status": "passed",
                    "machine_checkable": True,
                    "strength": "required_machine",
                    "claim_id": "check:validation",
                    "proves": "The validation check passed.",
                    "mechanism": "test_result",
                    "result": "passed",
                    "details": "1 passed",
                },
            }
        ],
    }
    request.update(overrides)
    return request


def command_request(command, ref_check="exit_code:0", result="passed", source=None, runtime_reflection=None):
    evidence = {
        "type": "command_result",
        "ref": command,
        "ref_type": "command",
        "ref_check": ref_check,
        "runtime_id": "OPTIONAL_RUNTIME_ID",
        "status": result,
        "machine_checkable": True,
        "strength": "required_machine",
        "claim_id": "check:command-check",
        "proves": "The command exited with the expected code.",
        "mechanism": "test_result",
        "result": result,
        "details": "Exit code only.",
    }
    if source is not None:
        evidence["source"] = source
    if runtime_reflection is not None:
        evidence["runtime_reflection"] = runtime_reflection
    return base_request(
        checks=[
            {
                "id": "command-check",
                "type": "command_exit_code",
                "subject": "command",
                "status": result,
                "expected": "pass",
                "required": True,
                "description": "Command exited with expected status.",
                "evidence": evidence,
            }
        ]
    )


def file_request(**evidence_overrides):
    evidence = {
        "type": "test_output",
        "ref": "tests/logs/pytest.txt",
        "ref_type": "file",
        "ref_check": "contains: passed",
        "source": "trusted",
        "context_id": "step-test",
        "runtime_id": "1234567",
        "status": "passed",
        "machine_checkable": True,
        "strength": "required_machine",
        "claim_id": "check:unit-tests",
        "proves": "The unit test command passed.",
        "mechanism": "test_result",
        "result": "passed",
        "details": "1 passed",
    }
    evidence.update(evidence_overrides)
    return base_request(
        checks=[
            {
                "id": "unit-tests",
                "type": "test_result",
                "subject": "artifact-1",
                "status": "passed",
                "expected": "pass",
                "required": True,
                "description": "Tests passed.",
                "evidence": evidence,
            }
        ]
    )


class AbwAcceptTests(unittest.TestCase):
    def make_workspace(self, request):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "out.txt").write_text("ok\n", encoding="utf-8")
        (workspace / "tests" / "logs").mkdir(parents=True)
        (workspace / "tests" / "logs" / "pytest.txt").write_text("1 passed\n", encoding="utf-8")
        request_path = workspace / "acceptance_request.json"
        write_json(request_path, request)
        return tmp, workspace, request_path

    def test_acceptance_pass_appends_log(self):
        tmp, workspace, request_path = self.make_workspace(base_request())
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])
            log_path = workspace / ".brain" / "acceptance_log.jsonl"
            self.assertTrue(log_path.exists())
            self.assertIn('"verdict": "pass"', log_path.read_text(encoding="utf-8"))

    def test_missing_artifact_blocks_acceptance(self):
        request = base_request(artifact={"id": "artifact-1", "path": "missing.txt", "type": "doc"})
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "blocked")
            self.assertFalse(result["accepted"])
            self.assertTrue(result["block_reasons"])

    def test_failed_required_check_is_partial_when_some_evidence_passes(self):
        request = base_request(
            checks=[
                {
                    "id": "validation",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "failed",
                    "expected": "pass",
                    "required": True,
                    "description": "Validation failed.",
                    "evidence": {
                        "type": "test_output",
                        "ref": "tests/logs/pytest.txt",
                        "status": "failed",
                        "machine_checkable": True,
                        "strength": "required_machine",
                        "claim_id": "check:validation",
                        "proves": "The validation check failed.",
                        "mechanism": "test_result",
                        "result": "failed",
                        "details": "1 failed",
                    },
                },
                {
                    "id": "artifact-exists",
                    "type": "file_exists",
                    "subject": "out.txt",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Artifact exists.",
                    "evidence": {
                        "type": "filesystem_probe",
                        "ref": "out.txt",
                        "status": "passed",
                        "machine_checkable": True,
                        "strength": "required_machine",
                        "claim_id": "check:artifact-exists",
                        "proves": "The expected artifact exists.",
                        "mechanism": "artifact_presence",
                        "result": "passed",
                        "details": "Path exists in workspace.",
                    },
                },
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "partial")
            self.assertFalse(result["accepted"])
            self.assertTrue(result["fail_reasons"])

    def test_required_check_missing_evidence_rejects_acceptance(self):
        request = base_request(
            checks=[
                {
                    "id": "validation",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Validation passed without evidence.",
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertIn(result["verdict"], {"fail", "partial"})
            self.assertFalse(result["accepted"])
            self.assertTrue(any("Missing evidence" in reason for reason in result["fail_reasons"]))

    def test_passed_machine_check_with_narrative_only_evidence_rejects_acceptance(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "summary",
                        "ref": "final-answer",
                        "status": "passed",
                        "machine_checkable": False,
                        "strength": "allowed_human",
                        "claim_id": "check:unit-tests",
                        "proves": "The tests were claimed as passed.",
                        "mechanism": "human_review",
                        "result": "passed",
                        "details": "I ran the tests and they passed.",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertIn(result["verdict"], {"fail", "partial"})
            self.assertFalse(result["accepted"])
            self.assertTrue(any("Machine-checkable evidence" in reason for reason in result["fail_reasons"]))

    def test_contradictory_evidence_rejects_acceptance(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "test_output",
                        "ref": "tests/logs/pytest.txt",
                        "status": "failed",
                        "machine_checkable": True,
                        "strength": "required_machine",
                        "claim_id": "check:unit-tests",
                        "proves": "The tests failed.",
                        "mechanism": "test_result",
                        "result": "failed",
                        "details": "1 failed",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertIn(result["verdict"], {"fail", "partial"})
            self.assertFalse(result["accepted"])
            self.assertTrue(any("contradicts" in reason for reason in result["fail_reasons"]))

    def test_optional_missing_evidence_is_partial(self):
        request = base_request(
            checks=[
                base_request()["checks"][0],
                {
                    "id": "optional-doc-review",
                    "type": "manual_review",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": False,
                    "description": "Optional docs review was claimed without evidence.",
                },
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "partial")
            self.assertFalse(result["accepted"])
            self.assertTrue(result["warnings"])

    def test_artifact_outside_candidate_files_rejects_acceptance(self):
        request = base_request(
            artifact={"id": "artifact-1", "path": "out.txt", "type": "doc"},
            candidate_files=["allowed.txt"],
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertIn(result["verdict"], {"fail", "partial"})
            self.assertFalse(result["accepted"])
            self.assertTrue(any("outside candidate_files" in reason for reason in result["fail_reasons"]))

    def test_machine_checkable_claim_with_only_allowed_human_evidence_rejects_acceptance(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "review_note",
                        "ref": "review.md#tests",
                        "status": "passed",
                        "machine_checkable": False,
                        "strength": "allowed_human",
                        "claim_id": "check:unit-tests",
                        "proves": "A human says tests passed.",
                        "mechanism": "human_review",
                        "result": "passed",
                        "details": "Reviewer says it looks fine.",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("required_machine" in reason for reason in result["fail_reasons"]))

    def test_supporting_only_evidence_cannot_pass_required_claim(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "summary",
                        "ref": "notes.md#summary",
                        "status": "passed",
                        "machine_checkable": True,
                        "strength": "supporting_only",
                        "claim_id": "check:unit-tests",
                        "proves": "A summary mentions tests.",
                        "mechanism": "consistency_check",
                        "result": "passed",
                        "details": "Summary only.",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("supporting_only" in reason for reason in result["fail_reasons"]))

    def test_evidence_mapped_to_wrong_claim_id_rejects_acceptance(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "test_output",
                        "ref": "tests/logs/pytest.txt",
                        "status": "passed",
                        "machine_checkable": True,
                        "strength": "required_machine",
                        "claim_id": "check:scope-diff",
                        "proves": "The wrong claim passed.",
                        "mechanism": "test_result",
                        "result": "passed",
                        "details": "Mapped to the wrong claim.",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("claim_id" in reason for reason in result["fail_reasons"]))

    def test_inconclusive_evidence_cannot_pass_required_claim(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "test_output",
                        "ref": "tests/logs/pytest.txt",
                        "status": "inconclusive",
                        "machine_checkable": True,
                        "strength": "required_machine",
                        "claim_id": "check:unit-tests",
                        "proves": "The test result is unknown.",
                        "mechanism": "test_result",
                        "result": "inconclusive",
                        "details": "Test log did not produce a clear pass/fail.",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("Inconclusive evidence" in reason for reason in result["fail_reasons"]))

    def test_required_machine_evidence_mapped_to_claim_can_pass(self):
        request = base_request(
            checks=[
                {
                    "id": "unit-tests",
                    "type": "test_result",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Tests passed.",
                    "evidence": {
                        "type": "test_output",
                        "ref": "tests/logs/pytest.txt",
                        "ref_type": "file",
                        "ref_check": "contains: passed",
                        "source": "trusted",
                        "context_id": "step-test",
                        "runtime_id": "1234567",
                        "status": "passed",
                        "machine_checkable": True,
                        "strength": "required_machine",
                        "claim_id": "check:unit-tests",
                        "proves": "The unit test command passed.",
                        "mechanism": "test_result",
                        "result": "passed",
                        "details": "1 passed",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_file_ref_inside_candidate_files_can_pass(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_file_ref_inside_artifact_paths_can_pass(self):
        request = file_request(ref="out.txt", ref_check="contains: passed")
        request["candidate_files"] = []
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "out.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_file_ref_outside_scope_rejects_acceptance(self):
        request = file_request(ref="outside/pytest.txt")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "outside").mkdir()
            (workspace / "outside" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("evidence_ref_outside_scope" in reason for reason in result["fail_reasons"]))

    def test_required_machine_missing_file_ref_rejects_acceptance(self):
        request = file_request(ref="tests/logs/missing.txt")
        request["candidate_files"].append("tests/logs/missing.txt")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("file_not_found" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_content_mismatch_rejects_acceptance(self):
        request = file_request(ref_check="contains: 2 passed")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("content_mismatch" in reason for reason in result["fail_reasons"]))

    def test_required_machine_valid_file_match_can_pass(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_declared_pass_with_real_fail_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text(
                "runtime_id: 1234567\n3 failed, 10 passed\n",
                encoding="utf-8",
            )
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(
                any("observed_result_contradicts_declared_pass" in reason for reason in result["fail_reasons"])
            )

    def test_mixed_failed_and_passed_log_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text(
                "runtime_id: 1234567\n3 failed, 10 passed\n",
                encoding="utf-8",
            )
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(
                any("observed_result_contradicts_declared_pass" in reason for reason in result["fail_reasons"])
            )

    def test_no_failure_text_does_not_count_as_failed(self):
        self.assertIsNone(abw_accept.observed_result_from_text("no failure detected\n"))
        self.assertIsNone(abw_accept.observed_result_from_text("error handling improved\n"))

    def test_contains_check_uses_word_boundary(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text(
                "runtime_id: 1234567\nbypassed checks\n",
                encoding="utf-8",
            )
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("content_mismatch" in reason for reason in result["fail_reasons"]))

    def test_required_machine_empty_file_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("empty_file" in reason for reason in result["fail_reasons"]))

    def test_required_machine_unknown_result_rejects_acceptance(self):
        request = file_request(ref_check=None, details="No pass/fail token.")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text(
                "runtime_id: 1234567\ncollection finished\n",
                encoding="utf-8",
            )
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("observed_result_unknown" in reason for reason in result["fail_reasons"]))

    def test_required_machine_command_success_can_pass(self):
        request = command_request(f"{sys.executable} -c pass")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_command_runtime_reflection_stdout_can_pass(self):
        command = (
            f"{sys.executable} -c "
            "__import__('sys').stdout.write('runtime_id:'+chr(32)+__import__('os').environ.get('ABW_RUNTIME_ID',''))"
        )
        request = command_request(command, runtime_reflection="stdout")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_command_runtime_reflection_missing_rejects_acceptance(self):
        request = command_request(f"{sys.executable} -c pass", runtime_reflection="stdout")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(
                any("runtime_marker_missing_or_invalid_in_stdout" in reason for reason in result["fail_reasons"])
            )

    def test_required_machine_command_loose_runtime_stdout_rejects_acceptance(self):
        command = (
            f"{sys.executable} -c "
            "__import__('sys').stdout.write(__import__('os').environ.get('ABW_RUNTIME_ID',''))"
        )
        request = command_request(command, runtime_reflection="stdout")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(
                any("runtime_marker_missing_or_invalid_in_stdout" in reason for reason in result["fail_reasons"])
            )

    def test_required_machine_command_wrong_runtime_marker_rejects_acceptance(self):
        command = f"{sys.executable} -c __import__('sys').stdout.write('runtime_id:'+chr(32)+'wrong')"
        request = command_request(command, runtime_reflection="stdout")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(
                any("runtime_marker_missing_or_invalid_in_stdout" in reason for reason in result["fail_reasons"])
            )

    def test_required_machine_command_fail_rejects_acceptance(self):
        request = command_request(f"{sys.executable} -c 1/0")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(
                any("command_exit_code_contradicts_declared_pass" in reason for reason in result["fail_reasons"])
            )

    def test_required_machine_invalid_command_rejects_acceptance(self):
        request = command_request("definitely-not-a-real-abw-command")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("command_run_failed" in reason for reason in result["fail_reasons"]))

    def test_required_machine_dangerous_command_rejects_acceptance(self):
        for command in ["rm temp.txt", "git reset --hard"]:
            request = command_request(command)
            tmp, workspace, request_path = self.make_workspace(request)
            with tmp:
                result = abw_accept.evaluate_file(workspace, request_path)
                self.assertFalse(result["accepted"])
                self.assertTrue(any("dangerous_command" in reason for reason in result["fail_reasons"]))

    def test_required_machine_command_missing_ref_check_rejects_acceptance(self):
        request = command_request(f"{sys.executable} -c pass", ref_check=None)
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("missing_ref_check" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_without_source_rejects_acceptance(self):
        request = file_request()
        request["checks"][0]["evidence"].pop("source")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("trusted source" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_untrusted_source_rejects_acceptance(self):
        request = file_request()
        request["checks"][0]["evidence"]["source"] = "untrusted"
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("trusted source" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_trusted_source_can_pass(self):
        request = file_request()
        request["checks"][0]["evidence"]["source"] = "trusted"
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_command_without_source_defaults_trusted(self):
        request = command_request(f"{sys.executable} -c pass")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_command_untrusted_source_rejects_acceptance(self):
        request = command_request(f"{sys.executable} -c pass", source="untrusted", runtime_reflection="stdout")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("trusted source" in reason for reason in result["fail_reasons"]))
            self.assertFalse(
                any("runtime_marker_missing_or_invalid_in_stdout" in reason for reason in result["fail_reasons"])
            )

    def test_required_machine_stale_file_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            stale_time = 1
            evidence_path = workspace / "tests" / "logs" / "pytest.txt"
            evidence_path.write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            os.utime(evidence_path, (stale_time, stale_time))
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("stale_evidence" in reason for reason in result["fail_reasons"]))

    def test_required_machine_fresh_file_can_pass(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_context_id_mismatch_rejects_acceptance(self):
        request = file_request()
        request["checks"][0]["evidence"]["context_id"] = "other-step"
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("context_mismatch" in reason for reason in result["fail_reasons"]))

    def test_required_machine_missing_context_id_rejects_acceptance(self):
        request = file_request()
        request["checks"][0]["evidence"].pop("context_id")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("context_mismatch" in reason for reason in result["fail_reasons"]))

    def test_required_machine_command_without_context_id_still_passes(self):
        request = command_request(f"{sys.executable} -c pass")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_required_machine_missing_runtime_id_rejects_acceptance(self):
        request = file_request()
        request["checks"][0]["evidence"].pop("runtime_id")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("runtime_mismatch" in reason for reason in result["fail_reasons"]))

    def test_required_machine_runtime_id_mismatch_rejects_acceptance(self):
        request = file_request(runtime_id="wrong-runtime")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("runtime_mismatch" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_missing_runtime_marker_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("runtime_marker_missing_or_invalid" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_loose_runtime_substring_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("run 1234567 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("runtime_marker_missing_or_invalid" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_wrong_runtime_marker_rejects_acceptance(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: wrong\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("runtime_marker_missing_or_invalid" in reason for reason in result["fail_reasons"]))

    def test_required_machine_file_missing_runtime_marker_passes_without_runtime_id(self):
        request = file_request()
        request["checks"][0]["evidence"].pop("runtime_id")
        request["checks"][0]["evidence"]["source"] = "untrusted"
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertFalse(any("runtime_mismatch" in reason for reason in result["fail_reasons"]))
            self.assertFalse(any("runtime_not_found_in_artifact" in reason for reason in result["fail_reasons"]))
            self.assertFalse(any("runtime_marker_missing_or_invalid" in reason for reason in result["fail_reasons"]))

    def test_allowed_human_file_evidence_does_not_require_runtime_id(self):
        request = base_request(
            checks=[
                {
                    "id": "human-review",
                    "type": "manual_review",
                    "subject": "artifact-1",
                    "status": "passed",
                    "expected": "pass",
                    "required": True,
                    "description": "Manual review passed.",
                    "evidence": {
                        "type": "review_note",
                        "ref": "tests/logs/pytest.txt",
                        "ref_type": "file",
                        "ref_check": "contains: passed",
                        "source": "untrusted",
                        "status": "passed",
                        "machine_checkable": False,
                        "strength": "allowed_human",
                        "claim_id": "check:human-review",
                        "proves": "A manual review passed.",
                        "mechanism": "human_review",
                        "result": "passed",
                        "details": "Reviewed by a human.",
                    },
                }
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_command_execution_receives_runtime_env(self):
        request = command_request(f"{sys.executable} -c pass")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            completed = type("Completed", (), {"returncode": 0})()
            with patch("abw_accept.time.time", return_value=1234.567):
                with patch("abw_accept.subprocess.run", return_value=completed) as run:
                    result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertEqual(run.call_args.kwargs["env"]["ABW_RUNTIME_ID"], "1234567")

    def test_required_machine_command_timeout_rejects_acceptance(self):
        request = command_request(f"{sys.executable} -c __import__('time').sleep(3)")
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertFalse(result["accepted"])
            self.assertTrue(any("command_timeout" in reason for reason in result["fail_reasons"]))

    def test_large_file_passes_when_marker_is_in_first_chunk(self):
        request = file_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            content = "runtime_id: 1234567\n1 passed\n" + ("x" * 10000)
            (workspace / "tests" / "logs" / "pytest.txt").write_text(content, encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])

    def test_repeated_evidence_is_checked_once(self):
        request = file_request()
        duplicate = json.loads(json.dumps(request["checks"][0]))
        duplicate["id"] = "unit-tests-repeat"
        duplicate["evidence"]["claim_id"] = "check:unit-tests-repeat"
        request["checks"].append(duplicate)
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            (workspace / "tests" / "logs" / "pytest.txt").write_text("runtime_id: 1234567\n1 passed\n", encoding="utf-8")
            with patch("abw_accept.time.time", return_value=1234.567):
                with patch("abw_accept.check_evidence_ref", wraps=abw_accept.check_evidence_ref) as check_ref:
                    result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])
            self.assertEqual(check_ref.call_count, 1)

    def test_evaluation_timeout_triggers_fail(self):
        request = base_request()
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            with patch("abw_accept.time.time", side_effect=[1000.0, 1003.1]):
                result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "fail")
            self.assertFalse(result["accepted"])
            self.assertIn("evaluation_timeout", result["fail_reasons"])


if __name__ == "__main__":
    unittest.main()
