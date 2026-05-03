import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import abw_ingest


class IngestEvidenceReportTests(unittest.TestCase):
    def _setup_workspace(self, tmp):
        workspace = Path(tmp)
        (workspace / "raw").mkdir(parents=True, exist_ok=True)
        (workspace / "drafts").mkdir(parents=True, exist_ok=True)
        (workspace / "processed").mkdir(parents=True, exist_ok=True)
        config = {
            "project_name": "test_evidence",
            "workspace_schema": 1,
            "abw_version": "0.2.9",
            "providers": {"ask_mode": "local", "default": "mock"},
        }
        (workspace / "abw_config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return workspace

    def test_ingest_report_created_on_basic_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\nMOM AGV WMS warehouse ops", encoding="utf-8")
            result = abw_ingest.run("ingest raw/test.md", str(workspace))
            self.assertIn(result.get("status"), ("draft_created", "drafts_created"))
            report_path = workspace / ".brain" / "ingest_report.json"
            self.assertTrue(report_path.exists(), "ingest_report.json should be created")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], "abw.ingest_report.v1")
            self.assertIn("run_id", report)
            self.assertIn("created_at", report)
            self.assertIsInstance(report["summary"], dict)
            self.assertGreaterEqual(report["summary"]["ingested_count"], 1)
            self.assertIsInstance(report["items"], list)
            self.assertGreaterEqual(len(report["items"]), 1)
            item = report["items"][0]
            self.assertEqual(item["source_path"], "raw/test.md")
            self.assertIn("source_id", item)
            self.assertFalse(item.get("skip_reason"))
            self.assertFalse(item.get("failure_reason"))

    def test_ingest_gaps_created_on_basic_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\nwarehouse operations", encoding="utf-8")
            result = abw_ingest.run("ingest raw/test.md", str(workspace))
            self.assertIn(result.get("status"), ("draft_created", "drafts_created"))
            gaps_path = workspace / ".brain" / "ingest_gaps.json"
            self.assertTrue(gaps_path.exists(), "ingest_gaps.json should be created")
            gaps = json.loads(gaps_path.read_text(encoding="utf-8"))
            self.assertEqual(gaps["schema_version"], "abw.ingest_gaps.v1")
            self.assertIn("run_id", gaps)
            self.assertIn("created_at", gaps)
            self.assertIsInstance(gaps["gap_summary"], dict)
            self.assertIn("total_gaps", gaps["gap_summary"])
            self.assertIsInstance(gaps["gaps"], list)

    def test_report_and_gaps_share_same_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            gaps = json.loads(
                (workspace / ".brain" / "ingest_gaps.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["run_id"], gaps["run_id"])
            self.assertEqual(report["created_at"], gaps["created_at"])
            self.assertEqual(report["schema_version"], "abw.ingest_report.v1")
            self.assertEqual(gaps["schema_version"], "abw.ingest_gaps.v1")

    def test_quarantined_file_appears_in_report_and_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            config = json.loads((workspace / "abw_config.json").read_text(encoding="utf-8"))
            config["domain_guard"] = {
                "allowed_keywords": ["warehouse", "agv"],
                "blocked_keywords": ["ecommerce", "blog"],
                "required_markers": [],
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            bad_md = workspace / "raw" / "bad.md"
            bad_md.write_text("# Blog\n\necommerce blog post about online shopping", encoding="utf-8")
            good_md = workspace / "raw" / "good.md"
            good_md.write_text("# Ops\n\nAGV warehouse operations", encoding="utf-8")
            result = abw_ingest.run("ingest raw/", str(workspace))
            self.assertGreaterEqual(result.get("quarantined_count", 0), 1)
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            self.assertGreaterEqual(report["summary"]["quarantined_count"], 1)
            quarantined_items = [i for i in report["items"] if i["status"] == "quarantined"]
            self.assertGreaterEqual(len(quarantined_items), 1)
            gaps = json.loads(
                (workspace / ".brain" / "ingest_gaps.json").read_text(encoding="utf-8")
            )
            quarantined_gaps = [g for g in gaps["gaps"] if g["gap_type"] == "quarantined_file"]
            self.assertGreaterEqual(len(quarantined_gaps), 1)
            self.assertEqual(quarantined_gaps[0]["severity"], "BLOCKING")

    def test_domain_guard_not_configured_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["safety"]["domain_guard_active"])
            gaps = json.loads(
                (workspace / ".brain" / "ingest_gaps.json").read_text(encoding="utf-8")
            )
            dg_gaps = [g for g in gaps["gaps"] if g["gap_type"] == "domain_guard_not_configured"]
            self.assertEqual(len(dg_gaps), 1)
            self.assertEqual(dg_gaps[0]["severity"], "INFO")

    def test_domain_guard_active_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            config = json.loads((workspace / "abw_config.json").read_text(encoding="utf-8"))
            config["domain_guard"] = {
                "allowed_keywords": ["warehouse"],
                "blocked_keywords": ["blog"],
                "required_markers": [],
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\nwarehouse operations data", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["safety"]["domain_guard_active"])
            gaps = json.loads(
                (workspace / ".brain" / "ingest_gaps.json").read_text(encoding="utf-8")
            )
            dg_gaps = [g for g in gaps["gaps"] if g["gap_type"] == "domain_guard_not_configured"]
            self.assertEqual(len(dg_gaps), 0)

    def test_domain_guard_not_configured_does_not_overclaim_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["safety"]["domain_guard_active"])

    def test_safety_auto_promote_default_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["safety"]["auto_promote_default"])

    def test_promotion_state_is_explicit_and_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            for item in report["items"]:
                self.assertIsInstance(item["promotion_state"], str)
                self.assertNotEqual(item["promotion_state"], "")

    def test_report_review_state_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report = json.loads(
                (workspace / ".brain" / "ingest_report.json").read_text(encoding="utf-8")
            )
            for item in report["items"]:
                self.assertIsInstance(item["review_state"], str)
                self.assertNotEqual(item["review_state"], "")

    def test_report_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report_path = workspace / ".brain" / "ingest_report.json"
            with report_path.open(encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertIsInstance(parsed, dict)
            self.assertIn("schema_version", parsed)

    def test_gaps_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            gaps_path = workspace / ".brain" / "ingest_gaps.json"
            with gaps_path.open(encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertIsInstance(parsed, dict)
            self.assertIn("schema_version", parsed)

    def test_no_bridge_implementation_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            report_path = workspace / ".brain" / "ingest_report.json"
            raw_text = report_path.read_text(encoding="utf-8")
            self.assertNotIn("bridge_ready", raw_text.lower())
            self.assertNotIn("bridge-client", raw_text.lower())
            self.assertNotIn("bridge_api", raw_text.lower())

    def test_gap_output_includes_promotion_not_performed(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            gaps = json.loads(
                (workspace / ".brain" / "ingest_gaps.json").read_text(encoding="utf-8")
            )
            promo_gaps = [g for g in gaps["gaps"] if g["gap_type"] == "promotion_not_performed"]
            self.assertGreaterEqual(len(promo_gaps), 1)

    def test_gap_output_includes_review_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            gaps = json.loads(
                (workspace / ".brain" / "ingest_gaps.json").read_text(encoding="utf-8")
            )
            review_gaps = [g for g in gaps["gaps"] if g["gap_type"] == "review_required"]
            self.assertGreaterEqual(len(review_gaps), 1)

    def test_ingest_does_not_write_wiki_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._setup_workspace(tmp)
            test_md = workspace / "raw" / "test.md"
            test_md.write_text("# Test\n\ncontent", encoding="utf-8")
            abw_ingest.run("ingest raw/test.md", str(workspace))
            wiki_dir = workspace / "wiki"
            wiki_files = list(wiki_dir.glob("*")) if wiki_dir.exists() else []
            self.assertEqual(len(wiki_files), 0, "Ingest must not write to wiki/")
