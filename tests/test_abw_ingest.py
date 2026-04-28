import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_ingest  # noqa: E402


class AbwIngestTests(unittest.TestCase):
    def _manifest_rows(self, workspace: Path) -> list[dict]:
        return [
            json.loads(line)
            for line in (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_raw_file_ingest_creates_draft_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "printer-notes.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "# Printer Notes\nDrum unit handles image transfer.\nToner cartridge feeds toner.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/printer-notes.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertEqual(result["raw_file"], "raw/printer-notes.md")
            self.assertTrue((workspace / result["draft_file"]).exists())
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 1)
            manifest_row = json.loads(manifest[0])
            self.assertEqual(manifest_row["source"], "raw/printer-notes.md")
            self.assertEqual(manifest_row["status"], "processed")

    def test_queue_updated_after_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "api.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("API latency depends on queue depth.\n", encoding="utf-8")

            result = abw_ingest.run("process raw/api.md", str(workspace))

            queue_path = workspace / ".brain" / "ingest_queue.json"
            self.assertTrue(queue_path.exists())
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["raw"], "raw/api.md")
            self.assertEqual(payload["items"][0]["draft"], result["draft_file"])
            self.assertEqual(payload["items"][0]["status"], "review_needed")

    def test_directory_ingest_recursively_processes_supported_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "raw" / "a.md").parent.mkdir(parents=True, exist_ok=True)
            (workspace / "raw" / "a.md").write_text("A\n", encoding="utf-8")
            (workspace / "raw" / "nested" / "b.txt").parent.mkdir(parents=True, exist_ok=True)
            (workspace / "raw" / "nested" / "b.txt").write_text("B\n", encoding="utf-8")
            (workspace / "raw" / "nested" / "skip.bin").write_bytes(b"\x00\x01")

            result = abw_ingest.run("ingest raw/", str(workspace))

            self.assertEqual(result["target_type"], "directory")
            self.assertEqual(result["scanned_count"], 3)
            self.assertEqual(result["changed_count"], 2)
            self.assertEqual(result["skipped_unchanged_count"], 0)
            self.assertEqual(result["ingested_count"], 2)
            self.assertIn("raw/a.md", result["ingested_files"])
            self.assertIn("raw/nested/b.txt", result["ingested_files"])
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 2)

    def test_directory_ingest_reports_skipped_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "valid.md").write_text("MOM WMS station handoff rule.\n", encoding="utf-8")
            (raw / "empty.txt").write_text("", encoding="utf-8")
            (raw / "broken.csv").write_bytes(b"name,value\x00broken")
            (raw / "random.tmp").write_text("junk", encoding="utf-8")

            result = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(result["ingested_count"], 1)
            self.assertEqual(result["scanned_count"], 4)
            self.assertEqual(result["changed_count"], 2)
            skipped = {item["path"]: item for item in result["skipped_files"]}
            self.assertEqual(skipped["raw/empty.txt"]["reason"], "skipped_empty")
            self.assertEqual(skipped["raw/broken.csv"]["reason"], "skipped_parse_error")
            self.assertEqual(skipped["raw/random.tmp"]["reason"], "skipped_unsupported_extension")
            self.assertTrue(all(item["action"] == "skipped" for item in skipped.values()))

    def test_html_ingest_supported_while_tmp_still_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "example.html").write_text(
                """
                <html>
                  <head>
                    <style>.hidden { display: none; }</style>
                    <script>window.secret = 'tag junk';</script>
                  </head>
                  <body>
                    <h1>AGV WMS Integration ERD</h1>
                    <table>
                      <tr><th>Table</th><th>Meaning</th></tr>
                      <tr><td>agv_command</td><td>Command queue for MOM and WMS handoff</td></tr>
                    </table>
                    <a href="https://example.invalid/spec">Interface Spec</a>
                  </body>
                </html>
                """,
                encoding="utf-8",
            )
            (raw / "random.tmp").write_text("junk", encoding="utf-8")

            result = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(result["ingested_files"], ["raw/example.html"])
            self.assertEqual(result["format"], "html")
            self.assertEqual(result["skipped_files"][0]["path"], "raw/random.tmp")
            self.assertEqual(result["skipped_files"][0]["reason"], "skipped_unsupported_extension")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("AGV WMS Integration ERD", draft)
            self.assertIn("agv_command", draft)
            self.assertIn("Interface Spec", draft)
            self.assertNotIn("window.secret", draft)
            self.assertNotIn("<table>", draft)

    def test_junk_skips_do_not_change_dedup_or_conflict_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "valid.md").write_text("Printer toner replacement is allowed.\n", encoding="utf-8")
            (raw / "empty.txt").write_text("", encoding="utf-8")
            (raw / "random.tmp").write_text("junk", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            second = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(first["conflict_count"], 0)
            self.assertEqual(second["conflict_count"], 0)
            self.assertEqual(second["ingested_files"], [])
            self.assertEqual(second["changed_count"], 0)
            self.assertEqual(second["skipped_unchanged_count"], 1)
            self.assertEqual(sorted(path.name for path in (workspace / "drafts").glob("*_draft.md")), ["valid_draft.md"])
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 1)

    def test_repeat_ingest_skips_unchanged_then_reprocesses_modified_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            source = raw / "ops.md"
            source.write_text("MOM station rule version one.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            second = abw_ingest.run("ingest raw", str(workspace))
            source.write_text("MOM station rule version two changed.\n", encoding="utf-8")
            third = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(first["scanned_count"], 1)
            self.assertEqual(first["changed_count"], 1)
            self.assertEqual(first["skipped_unchanged_count"], 0)
            self.assertEqual(second["status"], "no_drafts_created")
            self.assertEqual(second["changed_count"], 0)
            self.assertEqual(second["skipped_unchanged_count"], 1)
            self.assertEqual(third["changed_count"], 1)
            self.assertEqual(third["skipped_unchanged_count"], 0)
            draft = (workspace / third["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("version two changed", draft)
            state = json.loads((workspace / ".brain" / "ingest_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["last_run"]["changed_count"], 1)
            self.assertEqual(state["last_run"]["supported_source_counts"], {"md": 1})

    def test_ingest_detects_edit_when_size_and_mtime_match_cached_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            source = raw / "same-shape.md"
            source.write_text("alpha one\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            original_stat = source.stat()
            source.write_text("bravo two\n", encoding="utf-8")
            os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            second = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(first["changed_count"], 1)
            self.assertEqual(second["changed_count"], 1)
            self.assertEqual(second["reprocessed_count"], 1)
            self.assertEqual(second["skipped_unchanged_count"], 0)
            draft = (workspace / second["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("bravo two", draft)

    def test_ingest_detects_rename_without_duplicate_draft_or_new_source_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            original = raw / "ops.md"
            renamed = raw / "ops-renamed.md"
            original.write_text("MOM station routing rule.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            first_source_id = first["items"][0]["source_id"]
            original.rename(renamed)
            second = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(second["ingested_count"], 0)
            self.assertEqual(second["changed_count"], 0)
            self.assertEqual(second["renamed_count"], 1)
            self.assertEqual(second["reprocessed_count"], 0)
            self.assertEqual(second["skipped_unchanged_count"], 1)
            self.assertEqual(second["renamed_sources"][0]["from"], "raw/ops.md")
            self.assertEqual(second["renamed_sources"][0]["to"], "raw/ops-renamed.md")
            self.assertEqual(second["renamed_sources"][0]["source_id"], first_source_id)
            self.assertEqual(sorted(path.name for path in (workspace / "drafts").glob("*_draft.md")), ["ops_draft.md"])
            rows = [json.loads(line) for line in (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], first_source_id)
            self.assertEqual(rows[0]["source"], "raw/ops-renamed.md")
            queue = json.loads((workspace / ".brain" / "ingest_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(queue["items"][0]["raw"], "raw/ops-renamed.md")

    def test_rename_then_edit_preserves_source_id_and_original_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            original = raw / "file.txt"
            renamed = raw / "file_renamed.txt"
            original.write_text("Original source identity.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            first_source_id = first["items"][0]["source_id"]
            first_draft = first["items"][0]["draft_file"]
            original.rename(renamed)
            abw_ingest.run("ingest raw", str(workspace))
            renamed.write_text("Original source identity after edit.\n", encoding="utf-8")
            third = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(third["ingested_count"], 1)
            self.assertEqual(third["items"][0]["source_id"], first_source_id)
            self.assertEqual(third["items"][0]["draft_file"], first_draft)
            self.assertEqual(sorted(path.name for path in (workspace / "drafts").glob("*_draft.md")), ["file_draft.md"])
            draft = (workspace / first_draft).read_text(encoding="utf-8")
            self.assertIn("after edit", draft)
            rows = self._manifest_rows(workspace)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], first_source_id)
            self.assertEqual(rows[0]["source"], "raw/file_renamed.txt")
            self.assertIn("raw/file.txt", rows[0]["aliases"])
            self.assertIn("raw/file_renamed.txt", rows[0]["aliases"])

    def test_rename_then_multiple_edits_preserve_single_logical_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            original = raw / "policy.md"
            renamed = raw / "policy-current.md"
            original.write_text("Policy version one.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            source_id = first["items"][0]["source_id"]
            original.rename(renamed)
            abw_ingest.run("ingest raw", str(workspace))
            renamed.write_text("Policy version two.\n", encoding="utf-8")
            second_edit = abw_ingest.run("ingest raw", str(workspace))
            renamed.write_text("Policy version three.\n", encoding="utf-8")
            third_edit = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(second_edit["items"][0]["source_id"], source_id)
            self.assertEqual(third_edit["items"][0]["source_id"], source_id)
            self.assertEqual(sorted(path.name for path in (workspace / "drafts").glob("*_draft.md")), ["policy_draft.md"])
            rows = self._manifest_rows(workspace)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], source_id)
            self.assertIn("version three", (workspace / "drafts" / "policy_draft.md").read_text(encoding="utf-8"))

    def test_rename_chain_then_edit_preserves_lineage_and_source_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            a = raw / "a.md"
            b = raw / "b.md"
            c = raw / "c.md"
            a.write_text("Chain version one.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            source_id = first["items"][0]["source_id"]
            a.rename(b)
            abw_ingest.run("ingest raw", str(workspace))
            b.rename(c)
            abw_ingest.run("ingest raw", str(workspace))
            c.write_text("Chain version two edited.\n", encoding="utf-8")
            edited = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(edited["items"][0]["source_id"], source_id)
            rows = self._manifest_rows(workspace)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "raw/c.md")
            self.assertEqual([(row["from"], row["to"]) for row in rows[0]["lineage"]], [("raw/a.md", "raw/b.md"), ("raw/b.md", "raw/c.md")])
            self.assertEqual(sorted(path.name for path in (workspace / "drafts").glob("*_draft.md")), ["a_draft.md"])

    def test_rename_then_delete_marks_same_logical_source_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            original = raw / "remove.md"
            renamed = raw / "remove-renamed.md"
            original.write_text("Remove after rename.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw", str(workspace))
            source_id = first["items"][0]["source_id"]
            original.rename(renamed)
            abw_ingest.run("ingest raw", str(workspace))
            renamed.unlink()
            deleted = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(deleted["deleted_count"], 1)
            self.assertEqual(deleted["deleted_sources"][0]["source_id"], source_id)
            rows = self._manifest_rows(workspace)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], source_id)
            self.assertEqual(rows[0]["source"], "raw/remove-renamed.md")
            self.assertEqual(rows[0]["status"], "stale")

    def test_ingest_marks_deleted_source_stale_without_reprocessing_unchanged_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            keep = raw / "keep.md"
            remove = raw / "remove.md"
            keep.write_text("Keep this source active.\n", encoding="utf-8")
            remove.write_text("Remove this source later.\n", encoding="utf-8")

            abw_ingest.run("ingest raw", str(workspace))
            remove.unlink()
            second = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(second["ingested_count"], 0)
            self.assertEqual(second["changed_count"], 0)
            self.assertEqual(second["deleted_count"], 1)
            self.assertEqual(second["reprocessed_count"], 0)
            self.assertEqual(second["skipped_unchanged_count"], 1)
            self.assertEqual(second["deleted_sources"][0]["source"], "raw/remove.md")
            rows = [json.loads(line) for line in (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
            statuses = {row["source"]: row["status"] for row in rows}
            self.assertEqual(statuses["raw/keep.md"], "processed")
            self.assertEqual(statuses["raw/remove.md"], "stale")
            queue = json.loads((workspace / ".brain" / "ingest_queue.json").read_text(encoding="utf-8"))
            queue_statuses = {row["raw"]: row["status"] for row in queue["items"]}
            self.assertEqual(queue_statuses["raw/remove.md"], "stale_source_removed")

    def test_ingest_reports_mixed_delta_batch_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "edit.md").write_text("Edit version one.\n", encoding="utf-8")
            (raw / "move.md").write_text("Move this unchanged content.\n", encoding="utf-8")
            (raw / "delete.md").write_text("Delete this source.\n", encoding="utf-8")
            (raw / "stay.md").write_text("Stay unchanged.\n", encoding="utf-8")

            abw_ingest.run("ingest raw", str(workspace))
            (raw / "edit.md").write_text("Edit version two changed.\n", encoding="utf-8")
            (raw / "move.md").rename(raw / "moved.md")
            (raw / "delete.md").unlink()
            (raw / "new.md").write_text("New source added.\n", encoding="utf-8")
            second = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(second["changed_count"], 2)
            self.assertEqual(second["renamed_count"], 1)
            self.assertEqual(second["deleted_count"], 1)
            self.assertEqual(second["reprocessed_count"], 2)
            self.assertEqual(second["skipped_unchanged_count"], 2)
            self.assertEqual(set(second["ingested_files"]), {"raw/edit.md", "raw/new.md"})
            self.assertEqual(second["renamed_sources"][0]["to"], "raw/moved.md")
            self.assertEqual(second["deleted_sources"][0]["source"], "raw/delete.md")

    def test_pdf_and_pdf_text_siblings_merge_to_one_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_dir = workspace / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "report.pdf").write_bytes(b"%PDF-1.4\nFactory station complete\n%%EOF")
            (raw_dir / "report.pdf.txt").write_text("Factory station complete\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/", str(workspace))

            self.assertEqual(result["ingested_count"], 1)
            self.assertEqual(result["ingested_files"], ["raw/report.pdf"])
            self.assertEqual(result["draft_files"], ["drafts/report_draft.md"])
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 1)

    def test_manifest_dedups_legacy_pdf_text_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            manifest_path = workspace / "processed" / "manifest.jsonl"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps({"id": "old-1", "source": "raw/report.pdf.txt"}, ensure_ascii=False) + "\n"
                + json.dumps({"id": "old-2", "source": "raw/report.pdf.txt"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            raw_dir = workspace / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "report.pdf").write_bytes(b"%PDF-1.4\nFactory station complete\n%%EOF")
            (raw_dir / "report.pdf.txt").write_text("Factory station complete\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/", str(workspace))

            self.assertEqual(result["ingested_files"], ["raw/report.pdf"])
            rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "raw/report.pdf")

    def test_source_id_uses_normalized_stem_and_content_hash(self):
        left = abw_ingest.deterministic_id("raw/Report.pdf", "same content")
        right = abw_ingest.deterministic_id("raw/report.pdf.txt", "same content")
        changed = abw_ingest.deterministic_id("raw/report.pdf.txt", "different content")

        self.assertEqual(left, right)
        self.assertNotEqual(left, changed)
        self.assertEqual(abw_ingest.draft_relpath("raw/report.pdf.txt"), "drafts/report_draft.md")

    def test_ingest_merges_legacy_alias_draft_into_canonical_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "AMS_設計変更.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("AMS change approval workflow.\n", encoding="utf-8")
            legacy = workspace / "drafts" / "AMS_設計変更_draft.md"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text("# Old Draft\nlegacy reviewer note\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/AMS_設計変更.md", str(workspace))

            self.assertEqual(result["draft_file"], "drafts/ams_draft.md")
            self.assertTrue((workspace / "drafts" / "ams_draft.md").exists())
            self.assertFalse(legacy.exists())
            draft = (workspace / "drafts" / "ams_draft.md").read_text(encoding="utf-8")
            self.assertIn("AMS change approval workflow", draft)
            aliases = json.loads((workspace / ".brain" / "draft_aliases.json").read_text(encoding="utf-8"))
            self.assertEqual(aliases["aliases"]["drafts/AMS_設計変更_draft.md"], "drafts/ams_draft.md")

    def test_reingest_updates_existing_draft_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "AGV通信仕様.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("AGV communication version 1.\n", encoding="utf-8")

            first = abw_ingest.run("ingest raw/AGV通信仕様.md", str(workspace))
            raw_file.write_text("AGV communication version 2 updated.\n", encoding="utf-8")
            second = abw_ingest.run("ingest raw/AGV通信仕様.md", str(workspace))

            self.assertEqual(first["draft_file"], "drafts/agv_draft.md")
            self.assertEqual(second["draft_file"], "drafts/agv_draft.md")
            self.assertEqual(sorted(path.name for path in (workspace / "drafts").glob("*_draft.md")), ["agv_draft.md"])
            draft = (workspace / second["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("version 2 updated", draft)
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 1)

    def test_ingest_handles_unicode_paths_spaces_and_globs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_dir = workspace / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            text_file = raw_dir / "工程 メモ.md"
            text_file.write_text("工程管理 WMS ステータス確認\n", encoding="utf-8")
            pdf_file = raw_dir / "日本語 仕様.pdf"
            pdf_file.write_bytes("%PDF-1.4\n工程管理 WMS ステータス確認\n%%EOF".encode("utf-8"))

            text_result = abw_ingest.run("ingest raw/工程 メモ.md", str(workspace))
            pdf_result = abw_ingest.run("ingest raw/*.pdf", str(workspace))

            self.assertEqual(text_result["raw_file"], "raw/工程 メモ.md")
            self.assertEqual(pdf_result["ingested_files"], ["raw/日本語 仕様.pdf"])
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8")
            self.assertIn("工程 メモ.md", manifest)
            self.assertIn("日本語 仕様.pdf", manifest)

    def test_raw_folder_shortcut_ingests_raw_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "raw" / "one.md").parent.mkdir(parents=True, exist_ok=True)
            (workspace / "raw" / "one.md").write_text("One\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw", str(workspace))

            self.assertEqual(result["target"], "raw")
            self.assertEqual(result["target_type"], "directory")
            self.assertGreaterEqual(result["ingested_count"], 1)

    def test_ingest_does_not_write_wiki(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "network.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("Network retry strategy.\n", encoding="utf-8")

            abw_ingest.run("review raw/network.md", str(workspace))

            wiki_root = workspace / "wiki"
            self.assertFalse(wiki_root.exists() and any(wiki_root.rglob("*.md")))

    def test_ingest_with_conflict_creates_conflict_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "feature-flags.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("Feature X is disabled in version 2.\n", encoding="utf-8")
            wiki_file = workspace / "wiki" / "feature-flags.md"
            wiki_file.parent.mkdir(parents=True, exist_ok=True)
            wiki_file.write_text("Feature X is enabled in version 1.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/feature-flags.md", str(workspace))

            self.assertEqual(result["conflict_count"], 1)
            self.assertEqual(len(result["conflict_reports"]), 1)
            report_path = workspace / result["conflict_reports"][0]
            self.assertTrue(report_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Potential Contradiction", report)
            self.assertIn("review_required", report)
            self.assertIn("wiki/feature-flags.md", report)

            second = abw_ingest.run("ingest raw/feature-flags.md", str(workspace))
            self.assertEqual(second["conflict_count"], 0)
            self.assertEqual(second["skipped_unchanged_count"], 1)
            self.assertEqual(len(list((workspace / "drafts" / "conflicts").glob("*.md"))), 1)

    def test_ingest_without_conflict_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "printer-notes.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("The printer drum handles image transfer.\n", encoding="utf-8")
            wiki_file = workspace / "wiki" / "device-summary.md"
            wiki_file.parent.mkdir(parents=True, exist_ok=True)
            wiki_file.write_text("The scanner lamp needs calibration.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/printer-notes.md", str(workspace))

            self.assertEqual(result["status"], "draft_created")
            self.assertEqual(result["conflict_count"], 0)
            self.assertEqual(result["conflict_reports"], [])
            self.assertFalse((workspace / "drafts" / "conflicts").exists())

    def test_missing_path_returns_clear_help_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError) as exc:
                abw_ingest.run("ingest raw/missing.md", tmp)
            self.assertIn("Use: ingest raw/<file> or ingest raw/", str(exc.exception))

    def test_invalid_path_returns_explicit_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "wiki").mkdir(parents=True, exist_ok=True)
            with self.assertRaises(ValueError) as exc:
                abw_ingest.run("ingest wiki", tmp)
            self.assertIn("must point to raw/", str(exc.exception))

    def test_xlsx_ingest_extracts_structured_values_without_xml_junk(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            xlsx_path = workspace / "raw" / "report.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(xlsx_path, "w") as archive:
                archive.writestr(
                    "xl/workbook.xml",
                    '<workbook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="Ops MOM" sheetId="1" r:id="rId1"/></sheets></workbook>',
                )
                archive.writestr(
                    "xl/_rels/workbook.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
                )
                archive.writestr("xl/sharedStrings.xml", "<sst><si><t>Q1 output</t></si><si><t>Station table</t></si></sst>")
                archive.writestr(
                    "xl/worksheets/sheet1.xml",
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>42</v></c></row>'
                    '<row r="2" hidden="1"><c r="A2" t="s"><v>1</v></c></row></sheetData></worksheet>',
                )
                archive.writestr("xl/comments1.xml", '<comments><commentList><comment ref="A1"><text><t>note-a</t></text></comment></commentList></comments>')
                archive.writestr(
                    "xl/drawings/drawing1.xml",
                    '<xdr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><txBody><a:t>textbox alpha</a:t></txBody></xdr>',
                )
                archive.writestr(
                    "xl/charts/chart1.xml",
                    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:chart><c:title><a:t>capacity trend</a:t></c:title>'
                    '<c:dispBlanksAs val="gap"/></c:chart></c:chartSpace>',
                )
                archive.writestr("xl/styles.xml", '<styleSheet><t>xmlns junk rId99 550e8400-e29b-41d4-a716-446655440000</t></styleSheet>')
                archive.writestr("xl/theme/theme1.xml", "<theme><t>theme boilerplate</t></theme>")

            result = abw_ingest.run("ingest raw/report.xlsx", str(workspace))

            self.assertEqual(result["format"], "xlsx")
            self.assertGreaterEqual(result["provenance_count"], 5)
            self.assertIn(result["queue_status"], {"review_needed", "candidate_promoted"})
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("## Provenance", draft)
            self.assertIn("cells", draft)
            self.assertIn("comments", draft)
            self.assertIn("textboxes", draft)
            self.assertIn("charts", draft)
            self.assertIn("Ops MOM!A1: Q1 output", draft)
            self.assertIn("Ops MOM!B1: 42", draft)
            self.assertIn("note-a", draft)
            self.assertIn("textbox alpha", draft)
            self.assertIn("capacity trend", draft)
            self.assertIn("refs=Ops MOM!A1, Ops MOM!B1", draft)
            self.assertNotIn("Station table", draft)
            self.assertNotIn("xmlns junk", draft)
            self.assertNotIn("rId99", draft)
            self.assertNotIn("550e8400-e29b-41d4-a716-446655440000", draft)
            self.assertNotIn("theme boilerplate", draft)
            self.assertEqual(result["perception"]["version"], "enterprise_ingest_perception_v2")
            self.assertEqual(result["perception"]["document_type"]["type"], "spreadsheet")
            self.assertGreater(result["perception"]["stage_scores"]["native_structured"], 0.0)
            self.assertIn("Perception Pipeline", draft)

    def test_pptx_medium_confidence_is_candidate_ready_without_human_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            pptx_path = workspace / "raw" / "ops-review.pptx"
            pptx_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(pptx_path, "w") as archive:
                archive.writestr("ppt/slides/slide1.xml", "<p:sld><a:t>Operations review</a:t><a:t>Station throughput</a:t></p:sld>")
                archive.writestr("ppt/notesSlides/notesSlide1.xml", "<p:notes><a:t>Watch queue depth</a:t></p:notes>")

            result = abw_ingest.run("ingest raw/ops-review.pptx", str(workspace))

            self.assertEqual(result["format"], "pptx")
            self.assertEqual(result["queue_status"], "candidate_ready")
            self.assertEqual(result["review_reason"], "medium_confidence_enterprise_parse")
            self.assertEqual(result["perception"]["document_type"]["type"], "presentation")
            queue = json.loads((workspace / ".brain" / "ingest_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(queue["items"][0]["status"], "candidate_ready")
            self.assertEqual(queue["items"][0]["perception"]["document_type"]["type"], "presentation")
            manifest_row = json.loads((workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(manifest_row["queue_status"], "candidate_ready")
            self.assertEqual(manifest_row["perception"]["stage_scores"]["native_structured"], 0.7)
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("review_reason: medium_confidence_enterprise_parse", draft)
            self.assertIn("document_type: presentation", draft)

    def test_pdf_ingest_ai_mode_can_promote_candidate_with_provider_assist(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "x",
                "workspace_schema": 1,
                "abw_version": "0.2.6",
                "domain_profile": "generic",
                "raw_dir": "raw",
                "wiki_dir": "wiki",
                "drafts_dir": "drafts",
                "providers": {
                    "ingest_mode": "ai",
                    "default": "mock",
                    "fallback_chain": ["mock"],
                },
            }
            (workspace / "abw_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            raw_file = workspace / "raw" / "scan.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(b"%PDF-1.4\nFactory station line lead time improved\n%%EOF")

            result = abw_ingest.run("ingest raw/scan.pdf", str(workspace))

            self.assertEqual(result["ingest_mode"], "ai")
            self.assertEqual(result["format"], "pdf")
            self.assertTrue(result["provider"]["used"])
            self.assertEqual(result["provider"]["status"], "success")
            self.assertIn(result["queue_status"], {"candidate_promoted", "review_needed"})
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Provider semantic summary", draft)
            self.assertIn("confidence", draft)

    def test_text_pdf_prefers_real_text_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "text-layer.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
                b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
                b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj\n"
                b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
                b"5 0 obj << /Length 74 >> stream\n"
                b"BT /F1 12 Tf 72 720 Td (Factory station lead time improved) Tj ET\n"
                b"endstream endobj\n"
                b"xref\n0 6\n0000000000 65535 f \n"
                b"trailer << /Root 1 0 R /Size 6 >>\nstartxref\n435\n%%EOF\n"
            )

            result = abw_ingest.run("ingest raw/text-layer.pdf", str(workspace))

            self.assertEqual(result["format"], "pdf")
            self.assertGreater(result["confidence"], 0.45)
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("pdf_text_layer", draft)
            self.assertIn("Factory station lead time improved", draft)
            self.assertNotIn("pdf_binary_text_probe", draft)
            self.assertNotIn("pdf_page_render", draft)

    def test_clean_gate_suppresses_xml_pdf_and_binary_noise_in_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "noisy.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "<xml><tag>Useful machine label Save Status</tag></xml>\n"
                "xref obj endobj trailer /Type /Catalog /Pages /Resources\n"
                "IHDR IDAT IEND sRGB gAMA pHYs DDDDDDDDDDDDDDDDDDDD\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/noisy.md", str(workspace))

            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Useful machine label Save Status", draft)
            self.assertNotIn("<xml>", draft)
            self.assertNotIn("xref obj endobj trailer", draft)
            self.assertNotIn("IHDR IDAT IEND", draft)

    def test_semantic_layer_prioritizes_business_knowledge_over_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "mom-platform-outage.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "# MOM Platform Outage\n"
                "Meeting decision: API Gateway owner must reroute checkout traffic before Friday.\n"
                "Timeout error E42 affects payment-service and order queue during peak load.\n"
                "Action item: operations team reviews rollback workflow and customer impact.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/mom-platform-outage.md", str(workspace))

            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("## Business Summary", draft)
            self.assertIn("## Document Purpose", draft)
            self.assertIn("purpose: meeting_minutes", draft)
            self.assertIn("## Extracted Knowledge Signals", draft)
            self.assertIn("API Gateway", draft)
            self.assertIn("Timeout error E42", draft)
            self.assertIn("rollback workflow", draft)
            self.assertIn("Raw extraction trace kept separate from business summary.", draft)
            self.assertLess(draft.index("## Business Summary"), draft.index("## Provenance"))

    def test_image_ingest_hybrid_falls_back_to_local_on_provider_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "x",
                "workspace_schema": 1,
                "abw_version": "0.2.6",
                "domain_profile": "generic",
                "raw_dir": "raw",
                "wiki_dir": "wiki",
                "drafts_dir": "drafts",
                "providers": {
                    "ingest_mode": "hybrid",
                    "default": "mock",
                    "fallback_chain": ["mock"],
                    "task_routes": {"summarization": ["mock"]},
                    "sensitivity_routes": {"normal": ["mock"]},
                },
            }
            (workspace / "abw_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            raw_file = workspace / "raw" / "diagram.png"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(b"\x89PNG\r\n\x1a\n")

            with patch.dict("os.environ", {"ABW_PROVIDER_FORCE_FAIL": "mock"}, clear=False):
                result = abw_ingest.run("ingest raw/diagram.png", str(workspace))

            self.assertEqual(result["ingest_mode"], "hybrid")
            self.assertEqual(result["format"], "png")
            self.assertFalse(result["provider"]["used"])
            self.assertEqual(result["provider"]["status"], "failed")
            self.assertGreaterEqual(result["provider"]["fail_count"], 1)
            self.assertEqual(result["queue_status"], "review_needed")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Provider Assistance", draft)

    def test_supported_perception_providers_are_reported(self):
        providers = abw_ingest.supported_perception_providers()

        self.assertIn("paddleocr", providers["local_ocr"])
        self.assertIn("tesseract", providers["local_ocr"])
        self.assertIn("openai_vision", providers["cloud_vision"])
        self.assertIn("claude_vision", providers["cloud_vision"])
        self.assertIn("gemini_vision", providers["cloud_vision"])

    def test_image_ingest_detects_ui_tables_and_labels_with_provenance_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "screen.png"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (640).to_bytes(4, "big") + (360).to_bytes(4, "big")
            raw_file.write_bytes(
                png_header
                + b"\x08\x02\x00\x00\x00"
                + b" Login Save Cancel Status Required Total Qty Price 10 20 30 | table row |"
            )

            with patch.object(abw_ingest, "_run_paddleocr", return_value=([], {"provider": "paddleocr", "status": "unavailable"})), patch.object(
                abw_ingest,
                "_run_tesseract",
                return_value=(
                    ["Login Save Cancel", "Status Required", "Total Qty Price 10 20 30", "table row"],
                    {"provider": "tesseract", "status": "success", "tokens": 4},
                ),
            ):
                result = abw_ingest.run("ingest raw/screen.png", str(workspace))

            self.assertEqual(result["format"], "png")
            self.assertGreaterEqual(result["provenance_count"], 6)
            self.assertGreater(result["confidence"], 0.3)
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("visual_ui_detector", draft)
            self.assertIn("visual_table_detector", draft)
            self.assertIn("visual_label_button_detector", draft)
            self.assertIn("ref=image:screen.png#ui", draft)
            self.assertIn("Software window semantics", draft)
            self.assertIn("software_window_semantic_detector", draft)
            self.assertIn("ref=image:screen.png#window", draft)
            self.assertIn("OCR/Layout regions", draft)
            self.assertIn("region-01", draft)
            self.assertIn("Detected table-like regions", draft)
            self.assertIn("image_ordered_ocr_regions", draft)
            self.assertIn("ref=image:screen.png#regions", draft)
            self.assertEqual(result["perception"]["document_type"]["type"], "ui_screenshot")
            self.assertGreater(result["perception"]["stage_scores"]["ocr"], 0.0)
            self.assertGreater(result["perception"]["stage_scores"]["vision_layout"], 0.0)

    def test_local_ocr_chooses_higher_quality_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "screen.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n")

            with patch.object(
                abw_ingest,
                "_run_paddleocr",
                return_value=(["xx"], {"provider": "paddleocr", "status": "success", "tokens": 1}),
            ), patch.object(
                abw_ingest,
                "_run_tesseract",
                return_value=(
                    ["Status Qty Price 10 20 30", "Factory station complete"],
                    {"provider": "tesseract", "status": "success", "tokens": 2},
                ),
            ):
                result = abw_ingest._local_ocr_image(image)

            self.assertEqual(result["selected_provider"], "tesseract")
            self.assertTrue(result["real_ocr_success"])
            self.assertIn("Status Qty Price 10 20 30", result["text_lines"])

    def test_scanned_pdf_flow_adds_pages_layout_summary_and_low_noisy_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "scan.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Page /Resources << /XObject << /Im1 << /Subtype /Image >> >> >> >> endobj\n"
                b"2 0 obj << /Type /Page >> endobj\n"
                b"Factory Flow Step Input Output Total Qty 12 13 14\n"
                b"%%EOF"
            )

            result = abw_ingest.run("ingest raw/scan.pdf", str(workspace))

            self.assertEqual(result["format"], "pdf")
            self.assertLessEqual(result["confidence"], 0.18)
            self.assertEqual(result["queue_status"], "review_needed")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("PDF pages detected", draft)
            self.assertIn("Layout blocks", draft)
            self.assertIn("semantic_summary", draft)
            self.assertIn("ref=pdf:/pages/*/blocks", draft)
            self.assertIn("Detected table-like regions", draft)
            self.assertIn("pdf_estimated_text_regions", draft)
            self.assertIn("ref=pdf:/pages/*/regions", draft)

    def test_pdf_text_layer_adds_page_regions_and_table_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "table-text.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
                b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
                b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj\n"
                b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
                b"5 0 obj << /Length 120 >> stream\n"
                b"BT /F1 12 Tf 72 720 Td (Status Qty Price 10 20 30) Tj ET\n"
                b"endstream endobj\n"
                b"xref\n0 6\n0000000000 65535 f \n"
                b"trailer << /Root 1 0 R /Size 6 >>\nstartxref\n480\n%%EOF\n"
            )

            result = abw_ingest.run("ingest raw/table-text.pdf", str(workspace))

            self.assertEqual(result["format"], "pdf")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("OCR/Layout regions", draft)
            self.assertIn("page 1 region-01", draft)
            self.assertIn("Detected table-like regions", draft)
            self.assertIn("pdf_ordered_text_regions", draft)
            self.assertIn("pdf_table_region_detector", draft)

    def test_xlsx_ignores_embedded_image_probe_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            xlsx_path = workspace / "raw" / "image-report.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(xlsx_path, "w") as archive:
                archive.writestr(
                    "xl/workbook.xml",
                    '<workbook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>',
                )
                archive.writestr(
                    "xl/_rels/workbook.xml.rels",
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
                )
                archive.writestr("xl/sharedStrings.xml", "<sst><si><t>Station table</t></si></sst>")
                archive.writestr(
                    "xl/worksheets/sheet1.xml",
                    '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>',
                )
                archive.writestr("xl/media/image1.png", b"\x89PNG\r\n\x1a\nChart Label Save Button")

            result = abw_ingest.run("ingest raw/image-report.xlsx", str(workspace))

            self.assertEqual(result["format"], "xlsx")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Report!A1: Station table", draft)
            self.assertNotIn("Embedded image metadata/text probe", draft)
            self.assertNotIn("Chart Label Save Button", draft)
            self.assertNotIn("ref=xl/media/*", draft)

    def test_mom_like_png_binary_markers_do_not_inflate_ocr_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "mom-screen.png"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (1598).to_bytes(4, "big") + (852).to_bytes(4, "big")
            raw_file.write_bytes(png_header + b"sRGB\x00gAMA\x00pHYs\x00IDATx\x9cDDDDDDDDDDDDDDDDxref Obj /Type/Page")

            with patch.object(abw_ingest, "_run_paddleocr", return_value=([], {"provider": "paddleocr", "status": "unavailable"})), patch.object(
                abw_ingest,
                "_run_tesseract",
                return_value=([], {"provider": "tesseract", "status": "unavailable"}),
            ):
                result = abw_ingest.run("ingest raw/mom-screen.png", str(workspace))

            self.assertEqual(result["format"], "png")
            self.assertLessEqual(result["confidence"], 0.1)
            self.assertEqual(result["queue_status"], "review_needed")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("binary_text_probe=metadata_only", draft)
            self.assertIn("metadata_only=True", draft)
            self.assertIn("OCR text: - none recovered", draft)

    def test_image_low_ocr_routes_to_honest_warning_without_provider_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "empty-screen.png"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(b"\x89PNG\r\n\x1a\n")

            with patch.object(abw_ingest, "_run_paddleocr", return_value=([], {"provider": "paddleocr", "status": "empty"})), patch.object(
                abw_ingest,
                "_run_tesseract",
                return_value=([], {"provider": "tesseract", "status": "empty"}),
            ):
                result = abw_ingest.run("ingest raw/empty-screen.png", str(workspace))

            self.assertEqual(result["queue_status"], "review_needed")
            self.assertEqual(result["review_reason"], "low_confidence")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("OCR confidence routing: low_confidence", draft)
            self.assertIn("provider vision fallback: not_used (provider mode disabled)", draft)
            self.assertIn("provider_vision_image_ocr", draft)

    def test_image_low_ocr_uses_provider_vision_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "x",
                "workspace_schema": 1,
                "abw_version": "0.3.7",
                "raw_dir": "raw",
                "wiki_dir": "wiki",
                "drafts_dir": "drafts",
                "providers": {"ingest_mode": "ai", "default": "mock", "fallback_chain": ["mock"]},
            }
            (workspace / "abw_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raw_file = workspace / "raw" / "low-screen.png"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(b"\x89PNG\r\n\x1a\n")
            vision = {
                "used": True,
                "status": "success",
                "provider": "mock",
                "lines": ["Provider read Status Qty Price 10 20"],
                "confidence": 0.64,
                "quality": {"metadata_only": False, "usable": True},
                "attempts": [{"provider": "mock", "status": "success"}],
                "fail_count": 0,
            }

            with patch.object(abw_ingest, "_run_paddleocr", return_value=([], {"provider": "paddleocr", "status": "empty"})), patch.object(
                abw_ingest,
                "_run_tesseract",
                return_value=([], {"provider": "tesseract", "status": "empty"}),
            ), patch.object(abw_ingest, "_provider_vision_page", return_value=vision):
                result = abw_ingest.run("ingest raw/low-screen.png", str(workspace))

            self.assertGreater(result["confidence"], 0.45)
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("provider vision fallback: used", draft)
            self.assertIn("Provider read Status Qty Price", draft)

    def test_mom_like_pdf_metadata_probe_does_not_inflate_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "mom-scan.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj << /Type /Catalog /Pages 2 0 R /StructTreeRoot 10 0 R >> endobj\n"
                b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"
                b"3 0 obj << /Type /Page /Resources << /XObject << /Im1 << /Subtype /Image >> >> >> >> endobj\n"
                b"xref\n0 4\ntrailer\n%%EOF"
            )

            result = abw_ingest.run("ingest raw/mom-scan.pdf", str(workspace))

            self.assertEqual(result["format"], "pdf")
            self.assertLessEqual(result["confidence"], 0.1)
            self.assertEqual(result["queue_status"], "review_needed")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("pdf_page_render", draft)
            self.assertIn("pdf_page_local_ocr", draft)
            self.assertIn("provider mode disabled", draft)
            self.assertIn("0 OCR lines", draft)
            self.assertIn("OCR/local text extraction did not recover readable PDF text.", draft)
            self.assertEqual(result["review_reason"], "low_confidence")

    def test_scanned_pdf_rendered_page_uses_best_local_ocr(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "scanned.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n%%EOF")

            rendered_page = workspace / "page.png"
            rendered_page.write_bytes(b"\x89PNG\r\n\x1a\n")
            weak = {
                "text_lines": ["bad"],
                "metadata_lines": [],
                "attempts": [{"provider": "paddleocr", "status": "empty"}],
                "confidence": 0.08,
                "noise": 0.9,
                "real_ocr_success": False,
                "selected_provider": "none",
                "quality": {"metadata_only": True, "usable": False},
                "probe_quality": {"metadata_only": True, "usable": False},
                "candidates": [],
            }
            strong = {
                **weak,
                "text_lines": ["Status Qty Price 10 20 30", "Factory station complete"],
                "confidence": 0.62,
                "noise": 0.05,
                "real_ocr_success": True,
                "selected_provider": "tesseract",
                "quality": {"metadata_only": False, "usable": True},
            }

            with patch.object(abw_ingest, "_extract_pdf_text_layer", return_value=([], {"backend": "none", "status": "empty"})), patch.object(
                abw_ingest,
                "_render_pdf_pages",
                return_value=([{"page": 1, "path": rendered_page, "width": 600, "height": 800, "backend": "mock"}], {"backend": "mock", "status": "success", "pages": 1, "rendered": 1}),
            ), patch.object(abw_ingest, "_local_ocr_image", return_value=strong):
                result = abw_ingest.run("ingest raw/scanned.pdf", str(workspace))

            self.assertGreater(result["confidence"], 0.45)
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("PDF page render mode: mock", draft)
            self.assertIn("Page 1 OCR method: local_ocr:tesseract", draft)
            self.assertIn("Status Qty Price 10 20 30", draft)
            self.assertIn("pdf_page_table_region_detector", draft)

    def test_scanned_pdf_provider_vision_used_only_when_local_weak_and_ai_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            config = {
                "project_name": "x",
                "workspace_schema": 1,
                "abw_version": "0.3.4",
                "raw_dir": "raw",
                "wiki_dir": "wiki",
                "drafts_dir": "drafts",
                "providers": {"ingest_mode": "ai", "default": "mock", "fallback_chain": ["mock"]},
            }
            (workspace / "abw_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raw_file = workspace / "raw" / "provider-scan.pdf"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n%%EOF")
            rendered_page = workspace / "page.png"
            rendered_page.write_bytes(b"\x89PNG\r\n\x1a\n")
            weak = {
                "text_lines": [],
                "metadata_lines": [],
                "attempts": [{"provider": "tesseract", "status": "empty"}],
                "confidence": 0.08,
                "noise": 1.0,
                "real_ocr_success": False,
                "selected_provider": "none",
                "quality": {"metadata_only": True, "usable": False},
                "probe_quality": {"metadata_only": True, "usable": False},
                "candidates": [],
            }
            vision = {
                "used": True,
                "status": "success",
                "provider": "mock",
                "lines": ["Provider read invoice table Qty 10 Price 20"],
                "confidence": 0.64,
                "quality": {"metadata_only": False, "usable": True},
                "attempts": [{"provider": "mock", "status": "success"}],
                "fail_count": 0,
            }

            with patch.object(abw_ingest, "_extract_pdf_text_layer", return_value=([], {"backend": "none", "status": "empty"})), patch.object(
                abw_ingest,
                "_render_pdf_pages",
                return_value=([{"page": 1, "path": rendered_page, "width": 600, "height": 800, "backend": "mock"}], {"backend": "mock", "status": "success", "pages": 1, "rendered": 1}),
            ), patch.object(abw_ingest, "_local_ocr_image", return_value=weak), patch.object(abw_ingest, "_provider_vision_page", return_value=vision):
                result = abw_ingest.run("ingest raw/provider-scan.pdf", str(workspace))

            self.assertGreater(result["confidence"], 0.45)
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Provider vision fallback: used", draft)
            self.assertIn("Page 1 OCR method: provider_vision:mock", draft)
            self.assertIn("Provider read invoice table", draft)
            self.assertIn("provider_vision_page_ocr", draft)


if __name__ == "__main__":
    unittest.main()
