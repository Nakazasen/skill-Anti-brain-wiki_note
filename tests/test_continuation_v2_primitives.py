import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import continuation_claim as claim  # noqa: E402
import continuation_detect_unsafe as detect_unsafe  # noqa: E402
import continuation_execute as execute  # noqa: E402
import continuation_rollback as rollback  # noqa: E402
import continuation_status as status  # noqa: E402


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


class ContinuationV2PrimitiveTests(unittest.TestCase):
    def copy_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name) / "workspace"
        shutil.copytree(REPO_ROOT / "examples" / "resume-abw", workspace)
        return tmp, workspace

    def test_detect_unsafe_writes_heuristic_zones(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        try:
            (workspace / "src" / "auth").mkdir(parents=True)
            (workspace / "src" / "auth" / "login.py").write_text("def login(): pass\n", encoding="utf-8")
            detected = detect_unsafe.detect(workspace)
            self.assertTrue(any(zone["source"] == "heuristic_suspected" for zone in detected))

            merged = detect_unsafe.merge_zones(workspace, detected)
            self.assertGreaterEqual(len(merged["zones"]), 1)
            stored = load_json(workspace / ".brain" / "unsafe_zones.json")
            self.assertEqual(len(stored["zones"]), len(merged["zones"]))
        finally:
            tmp.cleanup()

    def test_rollback_plan_is_allowlisted_but_requires_confirm(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            execute.prepare_execution(workspace)
            plan = rollback.rollback_plan(workspace)
            self.assertEqual(plan["status"], "planned")
            self.assertTrue(plan["executable"])
            self.assertTrue(plan["requires_confirm"])

            blocked = rollback.execute_rollback(workspace)
            self.assertEqual(blocked["status"], "needs_confirm")

    def test_model_claim_conflict_blocks_overlapping_claim(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            first = claim.claim_step(workspace, "gemini-flash", step_id="step-safe-test")
            self.assertEqual(first["status"], "claimed")

            second = claim.claim_step(workspace, "claude", step_id="step-safe-test")
            self.assertEqual(second["status"], "conflict")
            self.assertTrue(second["conflicts"])

            released = claim.release_step(workspace, "gemini-flash", "step-safe-test")
            self.assertEqual(released["status"], "released")

            third = claim.claim_step(workspace, "claude", step_id="step-safe-test")
            self.assertEqual(third["status"], "claimed")

    def test_status_reports_dependency_and_claim_summaries(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            claim.claim_step(workspace, "gemini-flash", step_id="step-safe-test")
            result = status.evaluate_status(workspace)
            self.assertIn("dependencies", result)
            self.assertIn("model_claims", result)
            self.assertEqual(result["model_claims"]["active_count"], 1)


if __name__ == "__main__":
    unittest.main()
