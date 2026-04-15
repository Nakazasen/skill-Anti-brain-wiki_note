import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_accept  # noqa: E402


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def base_request(**overrides):
    request = {
        "scope": "Test artifact",
        "artifact": {"id": "artifact-1", "path": "out.txt", "type": "doc"},
        "candidate_files": ["out.txt"],
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
                    "ref": "tests/logs/pytest.txt",
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


class AbwAcceptTests(unittest.TestCase):
    def make_workspace(self, request):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        (workspace / "out.txt").write_text("ok\n", encoding="utf-8")
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
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "pass")
            self.assertTrue(result["accepted"])


if __name__ == "__main__":
    unittest.main()
