import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_help  # noqa: E402


def commands(actions):
    return [action["command"] for action in actions]


class AbwHelpTests(unittest.TestCase):
    def test_default_help_shows_only_v2_public_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_help.run(tmp)

        self.assertFalse(result["advanced"])
        self.assertEqual(result["public_commands"], [
            "abw init",
            'abw ask "..."',
            "abw ingest raw/<file>",
            "abw review",
            "abw doctor",
            "abw version",
            "abw migrate",
            "abw help",
        ])
        self.assertEqual([section["title"] for section in result["sections"]], [
            "Quick start",
            "Commands",
            "Workspace",
            "Suggested next steps",
        ])
        rendered_items = "\n".join("\n".join(section["items"]) for section in result["sections"])
        self.assertIn("abw init", rendered_items)
        self.assertIn("abw ask", rendered_items)
        self.assertIn("abw doctor", rendered_items)
        self.assertIn("abw version", rendered_items)
        self.assertIn("abw migrate", rendered_items)
        self.assertNotIn("abw upgrade", rendered_items)
        self.assertNotIn("audit system", rendered_items)
        self.assertNotIn("coverage", rendered_items)

    def test_advanced_help_adds_power_user_commands_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = abw_help.run(tmp, advanced=True)

        self.assertTrue(result["advanced"])
        self.assertEqual(result["advanced_commands"], [
            "abw upgrade",
            "abw rollback",
            "abw repair",
            "abw research",
            "abw help --advanced",
        ])
        advanced_section = next(section for section in result["sections"] if section["title"] == "Advanced commands")
        text = "\n".join(advanced_section["items"])
        self.assertIn("abw upgrade", text)
        self.assertIn("abw rollback", text)
        self.assertIn("abw repair", text)
        self.assertNotIn("abw-pack", text)
        self.assertNotIn("abw-sync", text)

    def test_help_with_drafts_suggests_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "drafts").mkdir(parents=True, exist_ok=True)
            (workspace / "drafts" / "sample_draft.md").write_text("# Draft\n", encoding="utf-8")
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

            result = abw_help.run(tmp)

            self.assertEqual(result["state_snapshot"]["pending_drafts"], 1)
            self.assertIn("review drafts", commands(result["next_actions"]))


if __name__ == "__main__":
    unittest.main()
