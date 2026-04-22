import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_wizard  # noqa: E402


class AbwWizardTests(unittest.TestCase):
    def test_wizard_starts_at_choose_action_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_wizard.run("wizard", tmp)

            self.assertEqual(result["status"], "menu")
            self.assertEqual(result["state"]["step"], "choose_action")
            self.assertFalse(result["should_execute"])
            self.assertEqual([item["command"] for item in result["options"]], ["/abw-wizard 1", "/abw-wizard 2", "/abw-wizard 3"])
            self.assertIn("/abw-wizard <number>", result["rendered"])
            self.assertTrue((Path(tmp) / ".brain" / "wizard_state.json").exists())

    def test_top_level_selection_runs_ingest_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.run("wizard", tmp)
            fake = {"status": "flow_completed", "flow": abw_wizard.INGEST_FLOW, "rendered": "done"}
            with patch("abw_wizard.run_flow", return_value=fake) as run_flow_mock:
                result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["status"], "flow_completed")
            run_flow_mock.assert_called_once()
            self.assertEqual(run_flow_mock.call_args.args[0], abw_wizard.INGEST_FLOW)

    def test_top_level_selection_runs_query_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.run("wizard", tmp)
            fake = {"status": "flow_completed", "flow": abw_wizard.QUERY_FLOW, "rendered": "done"}
            with patch("abw_wizard.run_flow", return_value=fake) as run_flow_mock:
                result = abw_wizard.run("wizard 2", tmp)

            self.assertEqual(result["status"], "flow_completed")
            self.assertEqual(run_flow_mock.call_args.args[0], abw_wizard.QUERY_FLOW)

    def test_top_level_selection_runs_health_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.run("wizard", tmp)
            fake = {"status": "flow_completed", "flow": abw_wizard.HEALTH_FLOW, "rendered": "done"}
            with patch("abw_wizard.run_flow", return_value=fake) as run_flow_mock:
                result = abw_wizard.run("wizard 3", tmp)

            self.assertEqual(result["status"], "flow_completed")
            self.assertEqual(run_flow_mock.call_args.args[0], abw_wizard.HEALTH_FLOW)

    def test_ingest_result_maps_to_list_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.save_state(tmp, {"step": "ingest_result", "selected_draft": None, "flow": "ingest_review_approve"})
            result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["selected_command"], "list drafts")
            self.assertEqual(result["state"]["step"], "explain_draft")

    def test_review_list_maps_draft_to_explain_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".brain").mkdir(parents=True, exist_ok=True)
            (workspace / ".brain" / "ingest_queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "draft": "drafts/sample_draft.md",
                                "status": "review_needed",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            abw_wizard.save_state(tmp, {"step": "review_item_loop", "selected_draft": None})
            result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["selected_command"], "explain draft drafts/sample_draft.md")
            self.assertEqual(result["state"]["step"], "approve_draft")
            self.assertEqual(result["state"]["selected_draft"], "drafts/sample_draft.md")

    def test_explain_step_maps_to_approve_step_without_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.save_state(tmp, {"step": "explain_draft", "selected_draft": "drafts/sample_draft.md"})
            result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["selected_command"], "explain draft drafts/sample_draft.md")
            self.assertEqual(result["state"]["step"], "approve_draft")
            self.assertFalse(result["should_execute"])

    def test_approve_step_returns_approve_command_without_running_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.save_state(tmp, {"step": "approve_draft", "selected_draft": "drafts/sample_draft.md"})
            result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["selected_command"], "approve draft drafts/sample_draft.md")
            self.assertEqual(result["state"]["step"], "choose_action")
            self.assertFalse(result["should_execute"])

    def test_invalid_selection_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_wizard.run("wizard 99", tmp)

            self.assertEqual(result["status"], "blocked")
            self.assertIn("Invalid wizard selection", result["reason"])

    def test_query_result_gap_action_maps_to_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.save_state(tmp, {"step": "query_result", "selected_draft": None, "flow": "query_gap_ingest"})
            result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["selected_command"], "ingest raw/<file>")
            self.assertEqual(result["state"]["step"], "gap_action")

    def test_query_flow_runs_deep_only_after_failure(self):
        calls = []

        def fake_execute(command, **_kwargs):
            calls.append(command)
            return {"current_state": "knowledge_gap_logged", "gap_logged": True, "next_actions": []}

        inputs = iter(["What is missing?"])
        with patch("abw_wizard.execute_step", side_effect=fake_execute):
            result = abw_wizard.run_flow(
                abw_wizard.QUERY_FLOW,
                input_func=lambda _prompt: next(inputs),
                output_func=lambda _text: None,
            )

        self.assertEqual(calls, ["/abw-query What is missing?", "/abw-deep What is missing?"])
        self.assertEqual(result["status"], "flow_completed")

    def test_query_flow_skips_deep_after_success(self):
        calls = []

        def fake_execute(command, **_kwargs):
            calls.append(command)
            return {"current_state": "knowledge_answered", "gap_logged": False, "next_actions": []}

        inputs = iter(["What is known?"])
        with patch("abw_wizard.execute_step", side_effect=fake_execute):
            result = abw_wizard.run_flow(
                abw_wizard.QUERY_FLOW,
                input_func=lambda _prompt: next(inputs),
                output_func=lambda _text: None,
            )

        self.assertEqual(calls, ["/abw-query What is known?"])
        self.assertEqual(result["history"][1]["result"]["status"], "skipped")

    def test_ingest_flow_does_not_auto_approve(self):
        calls = []

        def fake_execute(command, **_kwargs):
            calls.append(command)
            return {
                "current_state": "checked_only",
                "ingest_draft": {"draft": "drafts/x.md"},
                "next_actions": [{"label": "Review drafts", "command": "review drafts"}],
            }

        inputs = iter(["raw/x.md", ""])
        with patch("abw_wizard.execute_step", side_effect=fake_execute):
            result = abw_wizard.run_flow(
                abw_wizard.INGEST_FLOW,
                input_func=lambda _prompt: next(inputs),
                output_func=lambda _text: None,
            )

        self.assertNotIn("/abw-approve drafts/x.md", calls)
        self.assertEqual(result["history"][-1]["result"]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
