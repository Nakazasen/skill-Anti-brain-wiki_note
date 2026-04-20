import json
import sys
import tempfile
import unittest
from pathlib import Path

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
            self.assertEqual([item["command"] for item in result["options"]], ["ingest raw/<file>", "list drafts", "What is <topic>?"])
            self.assertIn("wizard <number>", result["rendered"])
            self.assertTrue((Path(tmp) / ".brain" / "wizard_state.json").exists())

    def test_selection_maps_to_command_and_next_step_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.run("wizard", tmp)
            result = abw_wizard.run("wizard 1", tmp)

            self.assertEqual(result["status"], "selection_mapped")
            self.assertEqual(result["selected_command"], "ingest raw/<file>")
            self.assertEqual(result["state"]["step"], "ingest_input")
            self.assertFalse(result["should_execute"])
            self.assertIn("command was not executed", result["rendered"])

    def test_flow_two_selection_maps_to_review_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.run("wizard", tmp)
            result = abw_wizard.run("wizard 2", tmp)

            self.assertEqual(result["selected_command"], "list drafts")
            self.assertEqual(result["state"]["step"], "review_list")
            self.assertFalse(result["should_execute"])

    def test_flow_three_selection_maps_to_query_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            abw_wizard.run("wizard", tmp)
            result = abw_wizard.run("wizard 3", tmp)

            self.assertEqual(result["selected_command"], "What is <topic>?")
            self.assertEqual(result["state"]["step"], "query_input")
            self.assertFalse(result["should_execute"])

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


if __name__ == "__main__":
    unittest.main()
