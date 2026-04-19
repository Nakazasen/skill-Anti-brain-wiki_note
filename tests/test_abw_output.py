import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_output  # noqa: E402
import abw_proof  # noqa: E402


class AbwOutputTests(unittest.TestCase):
    def test_enforce_runner_output_rejects_non_dict(self):
        result = abw_output.enforce_runner_output("plain text")
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["reason"], "output not produced by runner")

    def test_enforce_runner_output_rejects_missing_binding_fields(self):
        result = abw_output.enforce_runner_output({"binding_status": "runner_checked"})
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")

    def test_enforce_runner_output_rejects_missing_runtime_id(self):
        result = abw_output.enforce_runner_output(
            {
                "binding_status": "runner_checked",
                "validation_proof": "fake",
            }
        )
        self.assertEqual(result["binding_status"], "rejected")

    def test_enforce_runner_output_passes_runner_payload(self):
        runtime_id = "123"
        payload = {
            "binding_status": "runner_checked",
            "validation_proof": abw_proof.generate_proof("ok", "## Finalization\n- current_state: verified", runtime_id),
            "answer": "ok",
            "finalization_block": "## Finalization\n- current_state: verified",
            "runtime_id": runtime_id,
        }
        self.assertEqual(abw_output.enforce_runner_output(payload), payload)

    def test_cli_returns_rejected_shape_for_invalid_input(self):
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "abw_output.py")],
            input=json.dumps({"binding_status": "runner_checked"}),
            text=True,
            capture_output=True,
            check=False,
            cwd=str(REPO_ROOT),
        )

        self.assertEqual(completed.returncode, 3)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["binding_status"], "rejected")
