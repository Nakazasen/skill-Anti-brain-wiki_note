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
        "rubric": [
            {"id": "scope", "description": "Scope satisfied.", "required": True, "passed": True},
        ],
        "checks": [
            {
                "type": "test_result",
                "subject": "artifact-1",
                "result": "pass",
                "expected": "pass",
                "required": True,
                "description": "Validation passed.",
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
                    "type": "test_result",
                    "subject": "artifact-1",
                    "result": "fail",
                    "expected": "pass",
                    "required": True,
                    "description": "Validation failed.",
                },
                {
                    "type": "file_exists",
                    "subject": "out.txt",
                    "result": "pass",
                    "expected": "pass",
                    "required": True,
                    "description": "Artifact exists.",
                },
            ]
        )
        tmp, workspace, request_path = self.make_workspace(request)
        with tmp:
            result = abw_accept.evaluate_file(workspace, request_path)
            self.assertEqual(result["verdict"], "partial")
            self.assertFalse(result["accepted"])
            self.assertTrue(result["fail_reasons"])


if __name__ == "__main__":
    unittest.main()
