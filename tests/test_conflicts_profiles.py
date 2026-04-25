from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.conflicts import detect_conflicts


class ConflictProfileSelectionTests(unittest.TestCase):
    def test_generic_profile_is_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wiki = workspace / "wiki" / "ops.md"
            wiki.parent.mkdir(parents=True, exist_ok=True)
            wiki.write_text("linea so luong 50 enabled", encoding="utf-8")

            conflicts = detect_conflicts("raw/ops.md", "linea qty 60 disabled", str(workspace))
            self.assertEqual(conflicts, [])

    def test_manufacturing_profile_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "abw_config.json").write_text(
                json.dumps({"domain_profile": "manufacturing"}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            wiki = workspace / "wiki" / "ops-weekly.md"
            wiki.parent.mkdir(parents=True, exist_ok=True)
            wiki.write_text("linea so luong 50 enabled", encoding="utf-8")

            conflicts = detect_conflicts("raw/ops-weekly.md", "linea qty 60 disabled", str(workspace))
            self.assertEqual(len(conflicts), 1)
            self.assertIn("wiki/ops-weekly.md", conflicts[0]["conflicting_file"])

    def test_generic_profile_keeps_existing_contradiction_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wiki = workspace / "wiki" / "feature-flags.md"
            wiki.parent.mkdir(parents=True, exist_ok=True)
            wiki.write_text("Feature X is enabled in version 1.", encoding="utf-8")

            conflicts = detect_conflicts(
                "raw/feature-flags.md",
                "Feature X is disabled in version 2.",
                str(workspace),
            )
            self.assertEqual(len(conflicts), 1)
            reasons = " ".join(conflicts[0]["reasons"])
            self.assertIn("opposite terms", reasons)


if __name__ == "__main__":
    unittest.main()

