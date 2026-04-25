import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import abw_knowledge  # noqa: E402
import abw_runner  # noqa: E402
from abw.doctor import build_doctor_report  # noqa: E402
from abw.workspace import ensure_workspace  # noqa: E402


def _version_report():
    return {
        "package_version": "0.3.1",
        "install_mode": "editable/dev",
        "release_match_state": "matched",
        "runtime_source": "packaged_legacy",
        "runtime_source_path": "d:/x/src/abw/_legacy",
        "mirror_status": "matched",
        "mirror_mismatches": [],
        "stale_install_suspected": False,
        "provider_ask_mode": "local",
        "provider_default": "mock",
        "provider_healthy_count": 0,
    }


class GapCoverageIntegrationTests(unittest.TestCase):
    def test_detect_knowledge_gap_marks_missing_evidence(self):
        gap = abw_knowledge.detect_knowledge_gap(
            "explain missing topic",
            {"source": "none", "content": "", "confidence": 0.0, "path": None},
        )

        self.assertTrue(gap["gap_detected"])
        self.assertEqual(gap["gap_type"], "missing_evidence")

    def test_detect_knowledge_gap_marks_weak_wiki_answer(self):
        gap = abw_knowledge.detect_knowledge_gap(
            "explain sparse topic",
            {
                "source": "wiki",
                "content": "Sparse note.",
                "confidence": 0.35,
                "path": "wiki/concepts/sparse.md",
            },
        )

        self.assertTrue(gap["gap_detected"])
        self.assertEqual(gap["gap_type"], "weak_answer")

    def test_detect_knowledge_gap_accepts_ordinary_single_wiki_match(self):
        gap = abw_knowledge.detect_knowledge_gap(
            "explain focused topic",
            {
                "source": "wiki",
                "content": "Focused wiki evidence.",
                "confidence": 0.50,
                "path": "wiki/concepts/focused.md",
            },
        )

        self.assertFalse(gap["gap_detected"])
        self.assertEqual(gap["gap_type"], "none")

    def test_detect_knowledge_gap_handles_invalid_confidence(self):
        gap = abw_knowledge.detect_knowledge_gap(
            "explain sparse topic",
            {
                "source": "wiki",
                "content": "Sparse note.",
                "confidence": "not-a-number",
                "path": "wiki/concepts/sparse.md",
            },
        )

        self.assertTrue(gap["gap_detected"])
        self.assertEqual(gap["confidence"], 0.0)

    def test_ask_body_surfaces_weak_answer_gap(self):
        body = abw_runner.knowledge_body(
            "explain sparse topic",
            {
                "knowledge_evidence_tier": "E2_wiki",
                "knowledge_context": {
                    "source": "wiki",
                    "content": "Sparse note.",
                    "confidence": 0.45,
                    "path": "wiki/concepts/sparse.md",
                },
                "knowledge_gap": {
                    "gap_detected": True,
                    "gap_type": "weak_answer",
                    "reason": "Wiki evidence is weak.",
                    "suggested_sources": ["raw/source.md"],
                    "confidence": 0.35,
                },
            },
        )

        self.assertIn("Knowledge gap:", body)
        self.assertIn("gap_type: weak_answer", body)
        self.assertIn("status: answer may be incomplete", body)
        self.assertIn("evidence_confidence:", body)
        self.assertIn("next_sources:", body)

    def test_doctor_reports_open_coverage_gaps_as_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ensure_workspace(root)
            gap_path = root / ".brain" / "knowledge_gaps.json"
            gap_path.parent.mkdir(parents=True, exist_ok=True)
            gap_path.write_text(
                json.dumps(
                    {
                        "gaps": [
                            {
                                "id": "gap-1",
                                "query": "Missing AGV source " + ("x" * 120),
                                "priority": "high",
                                "status": "open",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch("abw.doctor.build_version_report", return_value=_version_report()):
                report = build_doctor_report(root)

        messages = [item["message"] for item in report["engine_checks"]]
        self.assertIn("WARN", [item["level"] for item in report["engine_checks"]])
        self.assertTrue(any("coverage gaps open=1" in message for message in messages))
        self.assertTrue(any("high_priority=1" in message for message in messages))
        self.assertFalse(any("x" * 100 in message for message in messages))

    def test_doctor_reports_zero_open_coverage_gaps_as_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ensure_workspace(root)

            with patch("abw.doctor.build_version_report", return_value=_version_report()):
                report = build_doctor_report(root)

        messages = [item["message"] for item in report["engine_checks"]]
        self.assertTrue(any(message == "coverage gaps open=0" for message in messages))


if __name__ == "__main__":
    unittest.main()
