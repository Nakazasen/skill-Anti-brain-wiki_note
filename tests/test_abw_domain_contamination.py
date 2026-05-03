import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import abw_ingest


class DomainContaminationUnitTests(unittest.TestCase):
    def test_check_domain_contamination_not_configured_when_no_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace), "raw/test.md", "MOM station workflow content"
            )
            self.assertEqual(result["domain_check_status"], "NOT_CONFIGURED")
            self.assertEqual(result["action"], "accept")
            self.assertIn("config", result["domain_check_reason"])

    def test_check_domain_contamination_passes_clean_domain_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom", "station", "warehouse"],
                    "blocked_keywords": ["website", "ecommerce", "blog"],
                    "required_markers": ["agv", "wms"],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace),
                "raw/mom_agv_ops.md",
                "AGV WMS station MOM handoff workflow procedure",
            )
            self.assertEqual(result["domain_check_status"], "PASS")
            self.assertEqual(result["action"], "accept")
            self.assertIn("agv", result["matched_keywords"])
            self.assertIn("wms", result["matched_keywords"])
            self.assertEqual(result["required_markers_missing"], [])
            self.assertEqual(result["blocked_keywords"], [])

    def test_check_domain_contamination_warns_on_missing_required_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website"],
                    "required_markers": ["agv", "wms"],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace),
                "raw/agv_ops.md",
                "AGV workflow for station routing",
            )
            self.assertEqual(result["domain_check_status"], "WARN")
            self.assertEqual(result["action"], "warn")
            self.assertEqual(result["domain_check_reason"], "required_markers_missing")
            self.assertIn("wms", result["required_markers_missing"])
            self.assertIn("agv", result["matched_keywords"])

    def test_check_domain_contamination_blocks_cross_domain_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website", "ecommerce", "blog"],
                    "required_markers": ["agv"],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace),
                "raw/website_launch.md",
                "Website launch blog post about ecommerce platform",
            )
            self.assertEqual(result["domain_check_status"], "BLOCKED")
            self.assertEqual(result["action"], "quarantine")
            self.assertEqual(result["domain_check_reason"], "blocked_keywords_detected")
            self.assertIn("ecommerce", result["blocked_keywords"])
            self.assertIn("blog", result["blocked_keywords"])

    def test_check_domain_contamination_warns_when_blocked_and_allowed_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["blog"],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace),
                "raw/agv_mom_blog_notice.md",
                "MOM AGV blog notice about warehouse automation",
            )
            self.assertEqual(result["domain_check_status"], "WARN")
            self.assertEqual(result["action"], "warn")
            self.assertIn("blog", result["blocked_keywords"])
            self.assertIn("mom", result["matched_keywords"])
            self.assertIn("agv", result["matched_keywords"])

    def test_check_domain_contamination_not_configured_when_guard_empty_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": [],
                    "blocked_keywords": [],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace), "raw/test.md", "Some content here"
            )
            self.assertEqual(result["domain_check_status"], "NOT_CONFIGURED")
            self.assertEqual(result["action"], "accept")

    def test_check_domain_contamination_error_on_malformed_guard_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": "not_a_list",
                    "blocked_keywords": 123,
                    "required_markers": None,
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace), "raw/test.md", "Content"
            )
            self.assertEqual(result["domain_check_status"], "ERROR")
            self.assertEqual(result["action"], "warn")
            self.assertIn("invalid keyword lists", result["domain_check_reason"])

    def test_check_domain_contamination_error_on_broken_config_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "abw_config.json").write_text(
                "{broken json!!!", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace), "raw/test.md", "Content"
            )
            self.assertEqual(result["domain_check_status"], "ERROR")
            self.assertEqual(result["action"], "warn")

    def test_check_domain_contamination_not_configured_without_missing_workspace(self):
        result = abw_ingest.check_domain_contamination(
            "/nonexistent/path/xyz", "raw/test.md", "Content"
        )
        self.assertEqual(result["domain_check_status"], "NOT_CONFIGURED")
        self.assertEqual(result["action"], "accept")


class DomainContaminationIngestTests(unittest.TestCase):
    def test_ingest_passes_clean_domain_file_with_domain_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website", "ecommerce"],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw_file = workspace / "raw" / "agv-mom-wms.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "AGV MOM WMS handoff workflow and station routing rules.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/agv-mom-wms.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertIsNotNone(result.get("domain_check"))
            self.assertEqual(result["domain_check"]["domain_check_status"], "PASS")
            self.assertEqual(result["domain_check"]["action"], "accept")

            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Domain Contamination Guard", draft)
            self.assertIn("domain_check_status: PASS", draft)

            manifest_row = json.loads(
                (workspace / "processed" / "manifest.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            self.assertIn("domain_check", manifest_row)
            self.assertEqual(manifest_row["domain_check"]["domain_check_status"], "PASS")

    def test_ingest_quarantines_blocked_domain_file_no_draft_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website", "ecommerce", "blog"],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw_file = workspace / "raw" / "website-blog-post.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "Website ecommerce blog launch announcement and marketing content.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/website-blog-post.md", str(workspace))

            self.assertEqual(result["quarantined_count"], 1)
            self.assertEqual(result["ingested_count"], 0)
            self.assertEqual(len(result["ingested_files"]), 0)
            self.assertFalse((workspace / "drafts").exists())
            self.assertFalse((workspace / "processed").exists())

            skipped = {item["path"]: item for item in result["skipped_files"]}
            self.assertIn("raw/website-blog-post.md", skipped)
            self.assertEqual(skipped["raw/website-blog-post.md"]["action"], "quarantined")
            self.assertEqual(skipped["raw/website-blog-post.md"]["reason"], "skipped_domain_quarantine")

    def test_ingest_warns_on_warn_domain_check_but_creates_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": [],
                    "required_markers": ["agv", "mom"],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw_file = workspace / "raw" / "ops-note.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "AGV routing for station operations only.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/ops-note.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertEqual(result["domain_check"]["domain_check_status"], "WARN")
            self.assertEqual(result["domain_check"]["action"], "warn")
            self.assertIn("mom", result["domain_check"]["required_markers_missing"])

            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("domain_check_status: WARN", draft)
            self.assertIn("required_markers_missing: mom", draft)

    def test_ingest_not_configured_without_domain_guard_still_creates_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "generic",
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw_file = workspace / "raw" / "generic-note.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("Website blog content.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/generic-note.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertEqual(result["domain_check"]["domain_check_status"], "NOT_CONFIGURED")
            self.assertEqual(result["quarantined_count"], 0)
            self.assertEqual(result["ingested_count"], 1)

    def test_ingest_domain_check_appears_in_queue_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website"],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw_file = workspace / "raw" / "agv-ops.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("AGV MOM operations report.\n", encoding="utf-8")

            abw_ingest.run("ingest raw/agv-ops.md", str(workspace))

            queue = json.loads(
                (workspace / ".brain" / "ingest_queue.json").read_text(encoding="utf-8")
            )
            self.assertIn("domain_check", queue["items"][0])
            self.assertEqual(
                queue["items"][0]["domain_check"]["domain_check_status"], "PASS"
            )

    def test_ingest_does_not_write_wiki_with_domain_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website"],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw_file = workspace / "raw" / "agv-report.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("AGV MOM station report.\n", encoding="utf-8")

            abw_ingest.run("ingest raw/agv-report.md", str(workspace))

            wiki_root = workspace / "wiki"
            self.assertFalse(wiki_root.exists() and any(wiki_root.rglob("*.md")))

    def test_ingest_quarantined_directory_mode_continues_processing_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": ["website", "ecommerce", "blog"],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "clean.md").write_text("AGV MOM station workflow.\n", encoding="utf-8")
            (raw / "bad.md").write_text("Website ecommerce blog post.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(result["ingested_count"], 1)
            self.assertEqual(result["ingested_files"], ["raw/clean.md"])
            self.assertEqual(result["quarantined_count"], 1)

            skipped = {item["path"]: item for item in result["skipped_files"]}
            self.assertIn("raw/bad.md", skipped)
            self.assertEqual(skipped["raw/bad.md"]["action"], "quarantined")

            draft_dir = workspace / "drafts"
            self.assertTrue((draft_dir / "clean_draft.md").exists())
            self.assertFalse(list(draft_dir.glob("bad_draft.md")))

    def test_check_domain_contamination_warns_on_missing_allowed_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "0.2.8",
                "domain_profile": "manufacturing",
                "domain_guard": {
                    "allowed_keywords": ["agv", "wms", "mom"],
                    "blocked_keywords": [],
                    "required_markers": [],
                },
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (workspace / "raw").mkdir(parents=True, exist_ok=True)
            result = abw_ingest.check_domain_contamination(
                str(workspace),
                "raw/unknown_topic.md",
                "Completely unrelated topic about gardening and flowers",
            )
            self.assertEqual(result["domain_check_status"], "WARN")
            self.assertEqual(result["action"], "warn")
            self.assertEqual(result["domain_check_reason"], "no_allowed_keywords_matched")
            self.assertEqual(result["matched_keywords"], [])
