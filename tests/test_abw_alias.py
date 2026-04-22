import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_alias  # noqa: E402


class AbwAliasTests(unittest.TestCase):
    def test_all_alias_targets_are_discovered_lanes(self):
        missing = abw_alias.unknown_aliases()

        self.assertEqual(missing, {})

    def test_rewrites_alias_with_arguments(self):
        self.assertEqual(
            abw_alias.rewrite_task('/abw-query "abc"'),
            'ask "abc"',
        )
        self.assertEqual(
            abw_alias.rewrite_task("/abw-approve drafts/x.md"),
            "approve draft drafts/x.md",
        )

    def test_unknown_alias_is_preserved_for_safe_fallback(self):
        self.assertEqual(abw_alias.rewrite_task("/abw-unknown"), "/abw-unknown")


if __name__ == "__main__":
    unittest.main()
