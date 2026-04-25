from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.conflicts import detect_conflicts


class ConflictFalsePositiveTests(unittest.TestCase):
    def _workspace(self):
        return tempfile.TemporaryDirectory()

    def test_corruption_gate_skips_contradiction_check(self):
        with self._workspace() as tmp:
            workspace = Path(tmp)
            wiki = workspace / "wiki" / "ops-q2.md"
            wiki.parent.mkdir(parents=True, exist_ok=True)
            wiki.write_text("OPS status enabled version 2 qty 10", encoding="utf-8")

            incoming = "OPS status disabled " + ("Ã© " * 24) + ("�" * 8) + "version 2 qty 10"
            conflicts = detect_conflicts("raw/ops-q2.md", incoming, str(workspace))
            self.assertEqual(conflicts, [])

    def test_numeric_mismatch_requires_shared_keys(self):
        with self._workspace() as tmp:
            workspace = Path(tmp)
            wiki = workspace / "wiki" / "ops-supply.md"
            wiki.parent.mkdir(parents=True, exist_ok=True)
            wiki.write_text("OPS procurement version 3 capacity 40", encoding="utf-8")

            incoming = "OPS procurement page 88 line 200 station update qty 40"
            conflicts = detect_conflicts("raw/ops-supply.md", incoming, str(workspace))
            self.assertEqual(conflicts, [])

    def test_metadata_numbers_do_not_create_conflicts(self):
        with self._workspace() as tmp:
            workspace = Path(tmp)
            wiki = workspace / "wiki" / "ops-minutes.md"
            wiki.parent.mkdir(parents=True, exist_ok=True)
            wiki.write_text("OPS page 10 line 42 manifest id 777 section 3", encoding="utf-8")

            incoming = "OPS page 2 line 9 manifest id 101 section 1"
            conflicts = detect_conflicts("raw/ops-minutes.md", incoming, str(workspace))
            self.assertEqual(conflicts, [])

    def test_doc_class_mismatch_is_ignored(self):
        with self._workspace() as tmp:
            workspace = Path(tmp)
            concept = workspace / "wiki" / "concepts" / "factory-flow.md"
            concept.parent.mkdir(parents=True, exist_ok=True)
            concept.write_text("Factory station enabled", encoding="utf-8")
            entity = workspace / "wiki" / "entities" / "factory-flow.md"
            entity.parent.mkdir(parents=True, exist_ok=True)
            entity.write_text("Factory station disabled", encoding="utf-8")

            conflicts = detect_conflicts(
                "raw/concepts/factory-flow.md",
                "Factory station disabled",
                str(workspace),
            )
            self.assertEqual(len(conflicts), 1)
            self.assertIn("wiki/concepts/factory-flow.md", conflicts[0]["conflicting_file"])

    def test_source_files_compare_without_domain_specific_type_rules(self):
        with self._workspace() as tmp:
            workspace = Path(tmp)
            ops_note = workspace / "wiki" / "ops-weekly.md"
            ops_note.parent.mkdir(parents=True, exist_ok=True)
            ops_note.write_text("OPS decision enabled", encoding="utf-8")

            guide_note = workspace / "wiki" / "guide-weekly.md"
            guide_note.write_text("OPS decision enabled", encoding="utf-8")

            conflicts = detect_conflicts("raw/ops-2026-04-24.md", "OPS decision disabled", str(workspace))
            files = {item["conflicting_file"] for item in conflicts}
            self.assertIn("wiki/ops-weekly.md", files)
            self.assertIn("wiki/guide-weekly.md", files)


if __name__ == "__main__":
    unittest.main()

