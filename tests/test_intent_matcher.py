import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import intent_matcher  # noqa: E402


class IntentMatcherTests(unittest.TestCase):
    def test_matches_english_help(self):
        matched = intent_matcher.match_intent("help")

        self.assertIsNotNone(matched)
        self.assertEqual(matched["intent"], "help")

    def test_matches_dashboard(self):
        matched = intent_matcher.match_intent("dashboard")

        self.assertIsNotNone(matched)
        self.assertEqual(matched["intent"], "dashboard")
        self.assertEqual(matched["lane"], "dashboard")

    def test_matches_vietnamese_help(self):
        matched = intent_matcher.match_intent("trợ giúp")

        self.assertIsNotNone(matched)
        self.assertEqual(matched["intent"], "help")

    def test_approve_without_path_does_not_match(self):
        matched = intent_matcher.match_intent("approve draft")

        self.assertIsNone(matched)

    def test_explain_with_path_extracts_params(self):
        matched = intent_matcher.match_intent("giai thich nhap drafts/sample_draft.md")

        self.assertIsNotNone(matched)
        self.assertEqual(matched["intent"], "explain_draft")
        self.assertEqual(matched["params"]["draft_path"], "drafts/sample_draft.md")


if __name__ == "__main__":
    unittest.main()
