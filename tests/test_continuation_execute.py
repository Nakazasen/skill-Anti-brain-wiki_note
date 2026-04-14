import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import continuation_execute as execute  # noqa: E402


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


class ContinuationExecuteTests(unittest.TestCase):
    def copy_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name) / "workspace"
        shutil.copytree(REPO_ROOT / "examples" / "resume-abw", workspace)
        return tmp, workspace

    def test_prepare_marks_selected_step_active(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            result = execute.prepare_execution(workspace, session_id="test-session")

            self.assertEqual(result["status"], "prepared")
            self.assertEqual(result["step_id"], "step-safe-test")
            self.assertTrue((workspace / ".brain" / "active_execution.json").exists())

            state = load_json(workspace / ".brain" / "resume_state.json")
            backlog = load_json(workspace / ".brain" / "continuation_backlog.json")
            active_step = next(s for s in backlog["steps"] if s["step_id"] == "step-safe-test")

            self.assertEqual(state["active_step"], "step-safe-test")
            self.assertEqual(active_step["status"], "active")

            handover = read_jsonl(workspace / ".brain" / "handover_log.jsonl")
            self.assertEqual(handover[-1]["event"], "step_started")

    def test_prepare_requires_explicit_approval_for_historical_zone(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            state = load_json(workspace / ".brain" / "resume_state.json")
            state["completed_steps"] = ["step-safe-test"]
            (workspace / ".brain" / "resume_state.json").write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            result = execute.prepare_execution(workspace, step_id="step-parser-impl")
            self.assertEqual(result["status"], "approval_required")
            self.assertTrue(result["required_approvals"])
            self.assertFalse((workspace / ".brain" / "active_execution.json").exists())

            approved = execute.prepare_execution(
                workspace,
                step_id="step-parser-impl",
                approved=True,
                approval_note="User approved historical-zone audit path.",
            )
            self.assertEqual(approved["status"], "prepared")
            self.assertTrue(approved["approved"])

    def test_record_execution_appends_history_and_clears_active_execution(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            prepared = execute.prepare_execution(workspace)
            step_id = prepared["step_id"]

            result = execute.record_execution(
                workspace,
                step_id=step_id,
                outcome="success",
                changed_files=["tests/test_resume.py"],
                test_result="pass",
                errors_introduced=0,
                session_id="test-session",
                acceptance_result="pass",
                handover_note="Focused test added.",
            )

            self.assertEqual(result["status"], "recorded")
            self.assertFalse((workspace / ".brain" / "active_execution.json").exists())

            state = load_json(workspace / ".brain" / "resume_state.json")
            backlog = load_json(workspace / ".brain" / "continuation_backlog.json")
            completed_step = next(s for s in backlog["steps"] if s["step_id"] == step_id)
            history = read_jsonl(workspace / ".brain" / "step_history.jsonl")
            handover = read_jsonl(workspace / ".brain" / "handover_log.jsonl")

            self.assertIsNone(state["active_step"])
            self.assertIsNone(state["last_completed_step"])
            self.assertNotIn(step_id, state["completed_steps"])
            self.assertEqual(completed_step["status"], "partial")
            self.assertEqual(history[-1]["step_id"], step_id)
            self.assertEqual(history[-1]["test_result"], "pass")
            self.assertFalse(history[-1]["accepted"])
            self.assertEqual(history[-1]["completion_artifact"]["acceptance_result"], "pass")
            self.assertEqual(history[-1]["completion_artifact"]["post_execute_audit"]["status"], "fail")
            self.assertTrue(history[-1]["completion_artifact"]["post_execute_audit"]["out_of_scope_files"])
            self.assertEqual(handover[-1]["event"], "step_completed")

    def test_record_requires_active_execution(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            result = execute.record_execution(
                workspace,
                step_id="step-safe-test",
                outcome="success",
            )
            self.assertEqual(result["status"], "error")
            self.assertIn("Run prepare before record", result["error"])

    def test_record_refuses_to_close_a_different_active_step(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            execute.prepare_execution(workspace)
            result = execute.record_execution(
                workspace,
                step_id="not-the-active-step",
                outcome="success",
            )
            self.assertEqual(result["status"], "error")
            self.assertIn("Active execution", result["error"])

    def test_record_audit_passes_when_changed_files_stay_inside_candidate_files(self):
        tmp, workspace = self.copy_fixture()
        with tmp:
            prepared = execute.prepare_execution(workspace)
            step_id = prepared["step_id"]

            result = execute.record_execution(
                workspace,
                step_id=step_id,
                outcome="success",
                changed_files=["tests/test_parser_resume.py"],
                test_result="pass",
                errors_introduced=0,
                acceptance_result="pass",
            )

            self.assertEqual(result["status"], "recorded")
            self.assertTrue(result["accepted"])
            self.assertEqual(result["post_execute_audit"]["status"], "pass")
            self.assertFalse(result["post_execute_audit"]["requires_abw_audit"])

            state = load_json(workspace / ".brain" / "resume_state.json")
            backlog = load_json(workspace / ".brain" / "continuation_backlog.json")
            completed_step = next(s for s in backlog["steps"] if s["step_id"] == step_id)
            self.assertEqual(state["last_completed_step"], step_id)
            self.assertIn(step_id, state["completed_steps"])
            self.assertEqual(completed_step["status"], "completed")


if __name__ == "__main__":
    unittest.main()
