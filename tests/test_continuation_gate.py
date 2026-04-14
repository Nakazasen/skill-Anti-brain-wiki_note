import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import continuation_gate as gate  # noqa: E402


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def base_step(**overrides):
    step = {
        "step_id": "step-test",
        "title": "Safe test step",
        "description": "Add a focused test.",
        "permission_class": "safe_write",
        "candidate_files": ["tests/test_example.py"],
        "preconditions": [],
        "exit_criteria": [],
        "affects_decision_ids": [],
        "evidence_delta_refs": [],
        "estimated_files_touched": 1,
        "estimated_lines_changed": 50,
        "blast_radius": "low",
        "reversibility": "easy",
        "surface_type": "test",
        "module": "example",
        "rollback_contract": {
            "method": "restore file",
            "cost": "low",
            "confidence": "high",
        },
        "blocked_by_gap": None,
        "status": "pending",
        "created_at": "2026-04-15T00:00:00Z",
    }
    step.update(overrides)
    return step


class ContinuationGateTests(unittest.TestCase):
    def make_workspace(self, steps, zones=None, decisions=None, gaps=None):
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        brain = workspace / ".brain"
        write_json(
            brain / "resume_state.json",
            {
                "effective_budget": {
                    "max_files_for_safe_write": 3,
                    "max_lines_for_safe_write": 150,
                    "max_files_for_multi_file_write": 8,
                    "max_lines_for_multi_file_write": 400,
                }
            },
        )
        write_json(
            brain / "continuation_policy.json",
            {
                "step_size_limits": {
                    "max_files_for_safe_write": 3,
                    "max_lines_for_safe_write": 150,
                    "max_files_for_multi_file_write": 8,
                    "max_lines_for_multi_file_write": 400,
                }
            },
        )
        write_json(brain / "continuation_backlog.json", {"steps": steps})
        write_json(brain / "unsafe_zones.json", {"zones": zones or []})
        write_json(brain / "locked_decisions.json", {"decisions": decisions or []})
        write_json(brain / "knowledge_gaps.json", {"gaps": gaps or []})
        (brain / "step_history.jsonl").write_text("", encoding="utf-8")
        return tmp, workspace

    def test_fixture_selects_safe_step(self):
        result = gate.evaluate_workspace(REPO_ROOT / "examples" / "resume-abw")
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected"]["step_id"], "step-safe-test")

    def test_user_declared_high_zone_is_hard_blocked(self):
        step = base_step(candidate_files=["src/auth/login.py"])
        zones = [
            {
                "zone_id": "auth",
                "path_pattern": "src/auth/**",
                "source": "user_declared",
                "confidence": "high",
            }
        ]
        tmp, workspace = self.make_workspace([step], zones=zones)
        with tmp:
            result = gate.evaluate_workspace(workspace)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["skipped"][0]["step_id"], "step-test")

    def test_historical_high_zone_requires_approval_but_can_pass(self):
        step = base_step(candidate_files=["src/parser/core.py"])
        zones = [
            {
                "zone_id": "parser-history",
                "path_pattern": "src/parser/**",
                "source": "historical",
                "confidence": "high",
            }
        ]
        tmp, workspace = self.make_workspace([step], zones=zones)
        with tmp:
            result = gate.evaluate_workspace(workspace)
        self.assertEqual(result["status"], "selected")
        approvals = result["selected"]["required_approvals"]
        self.assertTrue(any("Historical unsafe zone" in item for item in approvals))

    def test_line_budget_blocks_safe_write(self):
        step = base_step(estimated_lines_changed=151)
        tmp, workspace = self.make_workspace([step])
        with tmp:
            result = gate.evaluate_workspace(workspace)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("line budget", result["candidates"][0]["block_reasons"][0])

    def test_risky_rollback_downgrades_to_requires_approval(self):
        step = base_step(
            rollback_contract={
                "method": "manual undo",
                "cost": "high",
                "confidence": "medium",
            }
        )
        tmp, workspace = self.make_workspace([step])
        with tmp:
            result = gate.evaluate_workspace(workspace)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected"]["permission_class"], "requires_approval")
        self.assertTrue(result["selected"]["required_approvals"])


if __name__ == "__main__":
    unittest.main()
