import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from abw import cli as abw_cli


class TestAbwJsonHardening(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("D:/tmp/test_workspace")

    def assert_envelope(self, report, command_name):
        self.assertEqual(report["schema_version"], "1")
        self.assertEqual(report["command_name"], command_name)
        self.assertEqual(report["workspace"], str(self.workspace))
        self.assertIn("generated_at", report)
        self.assertIn("status", report)
        self.assertIsInstance(report["data"], dict)

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_inspect_report")
    def test_inspect_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"raw_stats": {"total": 1}}

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "inspect"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "inspect")
        self.assertEqual(report["data"]["raw_stats"]["total"], 1)

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_gap_report")
    def test_gaps_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"gaps": [{"type": "missing_wiki_coverage"}]}

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "gaps"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "gaps")
        self.assertEqual(report["data"]["gaps"][0]["type"], "missing_wiki_coverage")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_recovery_report")
    def test_recover_plan_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"steps": ["restore"]}

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "recover-plan"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "recover-plan")
        self.assertEqual(report["data"]["steps"], ["restore"])

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_verify_report")
    def test_recover_verify_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"verified": True}

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "recover-verify"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "recover-verify")
        self.assertTrue(report["data"]["verified"])

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_trend_report")
    def test_trend_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"snapshot_count": 2}

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "trend"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "trend")
        self.assertEqual(report["data"]["snapshot_count"], 2)

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_improvement_plan")
    def test_improve_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"actions": ["add wiki notes"]}

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "improve"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "improve")
        self.assertEqual(report["data"]["actions"], ["add wiki notes"])

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.run_apply")
    def test_apply_json_hardening(self, mock_apply, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_apply.return_value = {
            "action": "cleanup-drafts",
            "files_affected_count": 0,
            "changes_planned_count": 0,
            "risk_level": "low",
            "rollback_possible": False,
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "apply", "--dry-run", "cleanup-drafts"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "apply")
        self.assertEqual(report["data"]["action"], "cleanup-drafts")
        mock_apply.assert_called_once_with(self.workspace, "cleanup-drafts", yes=False)

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_version_report")
    def test_version_json_contract(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {
            "package_version": "1.1.0",
            "python": "3.12",
            "git_commit": "abc123",
            "git_tag": "v1.1.0",
            "install_mode": "editable/dev",
            "runtime_source": "repo",
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "version"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "version")
        self.assertEqual(report["data"]["version"], "1.1.0")
        self.assertEqual(report["data"]["package"], "abw_skill")
        self.assertEqual(report["data"]["python"], "3.12")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_doctor_report")
    def test_doctor_json_contract(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {
            "overall": "WARN",
            "checks": [{"level": "WARN", "message": "missing raw/"}],
            "top_warnings": ["missing raw/"],
            "workspace_health": "WARN",
            "engine_health": "OK",
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "doctor"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "doctor")
        self.assertEqual(report["status"], "warning")
        self.assertFalse(report["data"]["ok"])
        self.assertEqual(report["data"]["checks"][0]["message"], "missing raw/")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli._legacy_entry.final_output")
    @patch("abw.cli._legacy_entry.execute_command")
    @patch("abw.cli.prepare_ask_task")
    def test_ask_json_contract_known_query(self, mock_prepare, mock_execute, mock_final, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "wiki").mkdir(parents=True, exist_ok=True)
            (workspace / "wiki" / "agv.md").write_text("AGV communication uses MQTT.", encoding="utf-8")
            mock_resolve.return_value = workspace
            mock_prepare.return_value = {"task": "known query", "provider": "local"}
            ask_result = {
                "answer": "AGV communication uses MQTT.",
                "current_state": "knowledge_answered",
                "knowledge_evidence_tier": "E2_wiki",
                "knowledge_source_score": 2,
                "confidence": 75,
                "knowledge_output": {
                    "retrieval_status": "exact_match",
                    "source_summary": "local_wiki",
                },
                "citations": [{"path": "wiki/agv.md"}],
                "warnings": [],
            }
            mock_execute.return_value = ask_result
            mock_final.return_value = ask_result

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                abw_cli.main(["--json", "ask", "How does AGV communication work?"])

            report = json.loads(stdout.getvalue())
            self.assertEqual(report["workspace"], str(workspace))
            self.assertEqual(report["schema_version"], "1")
            self.assertEqual(report["command_name"], "ask")
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["data"]["answer"], "AGV communication uses MQTT.")
            self.assertEqual(report["data"]["retrieval_status"], "exact_match")
            self.assertEqual(report["data"]["trust_score"], 70)
            self.assertEqual(report["data"]["sources"][0]["path"], "wiki/agv.md")
            self.assertEqual(report["data"]["provider"], "local")
            self.assertEqual(report["data"]["knowledge_evidence_tier"], "E2_wiki")
            self.assertEqual(report["data"]["source_summary"], "local_wiki")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli._legacy_entry.final_output")
    @patch("abw.cli._legacy_entry.execute_command")
    @patch("abw.cli.prepare_ask_task")
    def test_ask_json_contract_no_match(self, mock_prepare, mock_execute, mock_final, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_prepare.return_value = {"task": "unknown query", "provider": "local"}
        ask_result = {
            "answer": "No grounded answer found.",
            "current_state": "knowledge_gap_logged",
            "gap_logged": True,
            "gap_id": "gap-123",
            "knowledge_evidence_tier": "E0_unknown",
            "knowledge_source_score": 0,
            "knowledge_output": {
                "retrieval_status": "no_match",
                "source_summary": "no_grounded_sources",
                "gap_logged": True,
            },
            "warnings": ["Need to ingest sources first."],
            "citations": [],
        }
        mock_execute.return_value = ask_result
        mock_final.return_value = ask_result

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "ask", "Who is missing?"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "ask")
        self.assertEqual(report["status"], "no_match")
        self.assertEqual(report["data"]["retrieval_status"], "no_match")
        self.assertTrue(report["data"]["gap_logged"])
        self.assertEqual(report["data"]["gap_id"], "gap-123")
        self.assertEqual(report["data"]["current_state"], "knowledge_gap_logged")
        self.assertEqual(report["data"]["warnings"], ["Need to ingest sources first.", "No supporting sources were returned."])

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.ingest_module.ingest")
    def test_ingest_json_contract(self, mock_ingest, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_ingest.return_value = {
            "current_state": "ingest_completed",
            "runner_status": "completed",
            "ingest_result": {
                "ingested_count": 2,
                "skipped_count": 1,
                "errors": [],
                "report_path": ".brain/ingest_report.json",
                "gaps_path": ".brain/ingest_gaps.json",
                "promotion_performed": False,
            },
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "ingest", "raw"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "ingest")
        self.assertEqual(report["data"]["ingested"], 2)
        self.assertEqual(report["data"]["skipped"], 1)
        self.assertEqual(report["data"]["report_path"], ".brain/ingest_report.json")
        self.assertFalse(report["data"]["promotion_performed"])

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli._legacy_entry.final_output")
    @patch("abw.cli._legacy_entry.execute_command")
    def test_review_json_contract(self, mock_execute, mock_final, mock_resolve):
        mock_resolve.return_value = self.workspace
        review_result = {
            "current_state": "review_ready",
            "runner_status": "completed",
            "draft_batch_review": {
                "items": [
                    {"draft": "drafts/a.md", "confidence": "high"},
                    {"draft": "drafts/b.md", "confidence": "medium"},
                ]
            },
            "next_actions": [{"label": "Approve", "command": "approve draft drafts/a.md"}],
            "warnings": [],
        }
        mock_execute.return_value = review_result
        mock_final.return_value = review_result

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "review"])

        report = json.loads(stdout.getvalue())
        self.assert_envelope(report, "review")
        self.assertEqual(report["data"]["reviewed"], 2)
        self.assertEqual(report["data"]["pending"], 2)
        self.assertEqual(report["data"]["actions"][0]["command"], "approve draft drafts/a.md")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.render_inspect_report")
    @patch("abw.cli.build_inspect_report")
    def test_human_readable_output_preserved_without_json(self, mock_build, mock_render, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"raw_stats": {"total": 1}}
        mock_render.return_value = "ABW Inspect Report"

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["inspect"])

        self.assertEqual(stdout.getvalue().strip(), "ABW Inspect Report")


if __name__ == "__main__":
    unittest.main()
