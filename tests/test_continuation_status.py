import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import continuation_execute as execute  # noqa: E402
import continuation_status as status  # noqa: E402


class ContinuationStatusTests(unittest.TestCase):
    def copy_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name) / "workspace"
        shutil.copytree(REPO_ROOT / "examples" / "resume-abw", workspace)
        return tmp, workspace

    def test_status_reports_ready_runtime_with_next_safe_step(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            result = status.evaluate_status(workspace)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["health"], "ready")
            self.assertEqual(result["next_safe_step"]["step_id"], "step-safe-test")
            self.assertEqual(result["backlog"]["by_status"]["pending"], 3)

    def test_status_reports_active_execution(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            execute.prepare_execution(workspace)
            result = status.evaluate_status(workspace)

            self.assertEqual(result["health"], "active")
            self.assertEqual(result["active_step"], "step-safe-test")
            self.assertEqual(result["active_execution"]["step_id"], "step-safe-test")


if __name__ == "__main__":
    unittest.main()
