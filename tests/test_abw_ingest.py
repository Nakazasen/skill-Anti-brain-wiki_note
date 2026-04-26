import json
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
            self.assertEqual(result["ingested_count"], 2)
            self.assertIn("raw/a.md", result["ingested_files"])
            self.assertIn("raw/nested/b.txt", result["ingested_files"])
            manifest = (workspace / "processed" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(manifest), 2)

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

    def test_xlsx_ingest_extracts_cells_comments_textboxes_charts_and_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            xlsx_path = workspace / "raw" / "report.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(xlsx_path, "w") as archive:
                archive.writestr("xl/sharedStrings.xml", "<sst><si><t>Q1 output</t></si><si><t>42</t></si></sst>")
                archive.writestr("xl/comments1.xml", "<comments><commentList><comment><text><t>note-a</t></text></comment></commentList></comments>")
                archive.writestr("xl/drawings/drawing1.xml", "<xdr><txBody><a:t>textbox alpha</a:t></txBody></xdr>")
                archive.writestr("xl/charts/chart1.xml", "<c:chart><c:title><a:t>capacity trend</a:t></c:title></c:chart>")
                archive.writestr("xl/media/image1.png", b"PNG")

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
            self.assertIn("embedded_images", draft)
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
            self.assertEqual(result["perception"]["document_type"]["type"], "ui_screenshot")
            self.assertGreater(result["perception"]["stage_scores"]["ocr"], 0.0)
            self.assertGreater(result["perception"]["stage_scores"]["vision_layout"], 0.0)

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

    def test_xlsx_embedded_image_ocr_extracts_probe_text_and_cell_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            xlsx_path = workspace / "raw" / "image-report.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(xlsx_path, "w") as archive:
                archive.writestr("xl/sharedStrings.xml", "<sst><si><t>Station table</t></si></sst>")
                archive.writestr("xl/media/image1.png", b"\x89PNG\r\n\x1a\nChart Label Save Button")

            result = abw_ingest.run("ingest raw/image-report.xlsx", str(workspace))

            self.assertEqual(result["format"], "xlsx")
            draft = (workspace / result["draft_file"]).read_text(encoding="utf-8")
            self.assertIn("Embedded image metadata/text probe", draft)
            self.assertIn("Chart Label Save Button", draft)
            self.assertIn("ref=xl/media/*", draft)

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
            self.assertIn("pdf_metadata_probe", draft)
            self.assertIn("metadata_only=True", draft)
            self.assertIn("OCR/local text extraction did not recover readable PDF text.", draft)
            self.assertEqual(result["review_reason"], "low_confidence")


if __name__ == "__main__":
    unittest.main()
