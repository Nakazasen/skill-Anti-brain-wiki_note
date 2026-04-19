import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_health  # noqa: E402


class AbwHealthTests(unittest.TestCase):
    def make_layout(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        workspace = root / "workspace"
        runtime = root / "runtime"
        (workspace / "scripts").mkdir(parents=True)
        (workspace / "workflows").mkdir(parents=True)
        (runtime / "scripts").mkdir(parents=True)
        (runtime / "global_workflows").mkdir(parents=True)
        return tmp, workspace, runtime

    def test_drift_detected_and_fixed(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "abw_runner.py").write_text("print('workspace')\n", encoding="utf-8")
            (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
            (runtime / "scripts" / "abw_runner.py").write_text("print('runtime')\n", encoding="utf-8")
            (runtime / "global_workflows" / "abw-ask.md").write_text("# stale\n", encoding="utf-8")

            drift = abw_health.check_drift(workspace=workspace, runtime_root=runtime)
            self.assertTrue(drift)

            fixed = abw_health.fix_drift(workspace=workspace, runtime_root=runtime)
            self.assertTrue(fixed)
            self.assertEqual(abw_health.check_drift(workspace=workspace, runtime_root=runtime), [])

    def test_encoding_issue_detected_and_fixed(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "bad.py").write_text("print('bad\ufffdtext')\n", encoding="utf-8")

            issues = abw_health.check_encoding(workspace=workspace)
            self.assertEqual(len(issues), 1)

            fixed = abw_health.fix_encoding(workspace=workspace)
            self.assertEqual(len(fixed), 1)
            self.assertEqual(abw_health.check_encoding(workspace=workspace), [])
            self.assertNotIn("\ufffd", (workspace / "scripts" / "bad.py").read_text(encoding="utf-8"))

    def test_run_health_clean_pass(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "abw_runner.py").write_text("print('ok')\n", encoding="utf-8")
            (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
            (runtime / "scripts" / "abw_runner.py").write_text("print('ok')\n", encoding="utf-8")
            (runtime / "global_workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")

            result = abw_health.run_health(workspace=workspace, runtime_root=runtime)
            self.assertEqual(result["binding_status"], "runner_enforced")
            self.assertTrue(result["validation_proof"])
            self.assertEqual(result["current_state"], "verified")
            self.assertIn("## Finalization", result["answer"])

    def test_run_health_audit_does_not_fix_drift(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "abw_runner.py").write_text("print('workspace')\n", encoding="utf-8")
            (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
            (runtime / "scripts" / "abw_runner.py").write_text("print('runtime')\n", encoding="utf-8")
            (runtime / "global_workflows" / "abw-ask.md").write_text("# stale\n", encoding="utf-8")

            result = abw_health.run_health(workspace=workspace, runtime_root=runtime, mode="audit")

            self.assertEqual(result["mode"], "audit")
            self.assertEqual(result["current_state"], "blocked")
            self.assertTrue(abw_health.check_drift(workspace=workspace, runtime_root=runtime))

    def test_run_health_repair_fixes_drift(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "abw_runner.py").write_text("print('workspace')\n", encoding="utf-8")
            (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
            (runtime / "scripts" / "abw_runner.py").write_text("print('runtime')\n", encoding="utf-8")
            (runtime / "global_workflows" / "abw-ask.md").write_text("# stale\n", encoding="utf-8")

            result = abw_health.run_health(workspace=workspace, runtime_root=runtime, mode="repair")

            self.assertEqual(result["mode"], "repair")
            self.assertEqual(result["current_state"], "verified")
            self.assertEqual(abw_health.check_drift(workspace=workspace, runtime_root=runtime), [])

    def test_detect_mojibake_false_for_normal_utf8(self):
        self.assertFalse(abw_health.detect_mojibake("Xin chao, day la noi dung UTF-8 hop le."))

    def test_detect_mojibake_true_for_suspicious_text(self):
        text = "Ã¡ Ã  Ã¢ Ã£ Ã¤ " * 5
        self.assertTrue(abw_health.detect_mojibake(text))

    def test_clean_file_has_no_mojibake_detection(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            (workspace / "scripts" / "clean.py").write_text("print('hello world')\n", encoding="utf-8")
            issues = abw_health.check_mojibake(workspace=workspace)
            self.assertEqual(issues, [])
